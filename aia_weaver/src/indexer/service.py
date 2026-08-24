import asyncio
import logging
import hashlib
import os
from pathlib import Path

from indexer.embedder import LocalEmbedder
from indexer.parser import extract_archetype_and_snippet, extract_explicit_links
from indexer.thumbnail import ThumbnailManager
from extractors.archive import is_archive_file

logger = logging.getLogger("aia_weaver")

class IndexingService:
    def __init__(
        self,
        db,
        ipc,
        embedder: LocalEmbedder,
        thumbnail_manager: ThumbnailManager,
        event_queue: asyncio.Queue,
        target_directories: list[str],
        enable_semantic_edges: bool,
        semantic_distance_threshold: float,
        temporal_window_minutes: int,
    ):
        self.db = db
        self.ipc = ipc
        self.embedder = embedder
        self.thumbnail_manager = thumbnail_manager
        self.event_queue = event_queue
        self.target_directories = target_directories
        self.enable_semantic_edges = enable_semantic_edges
        self.semantic_distance_threshold = semantic_distance_threshold
        self.temporal_window_minutes = temporal_window_minutes

    async def initial_workspace_scan(self) -> None:
        logger.info(f"Performing initial workspace scan on: {self.target_directories}")
        scanned_count = 0
        from watcher.service import FileWatcher # we can just use the ignore logic here but let's do it simply
        dummy_watcher = FileWatcher([], None)
        for target in self.target_directories:
            target_path = Path(target)
            if not target_path.exists() or not target_path.is_dir():
                continue
            for path in target_path.rglob("*"):
                if path.is_file() and not dummy_watcher._should_ignore(str(path)):
                    await self.event_queue.put({
                        "action": "initial_scan",
                        "file_path": str(path.resolve()),
                        "timestamp": asyncio.get_running_loop().time(),
                    })
                    scanned_count += 1
        logger.info(f"Initial workspace scan enqueued {scanned_count} file(s) for indexing.")

    async def process_event_queue(self, shutdown_event: asyncio.Event) -> None:
        while not shutdown_event.is_set():
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                file_path_str = event["file_path"]
                action = event["action"]
                path = Path(file_path_str)

                if action in ("initial_scan", "created", "modified") and path.exists() and path.is_file():
                    file_bytes = await asyncio.to_thread(path.read_bytes)
                    file_hash = hashlib.sha256(file_bytes).hexdigest()
                    
                    existing_node = None
                    if action == "initial_scan":
                        existing_node = await self.db.get_node_by_path(file_path_str)
                    
                    needs_reparse = False
                    if existing_node and is_archive_file(path) and (existing_node.get("archetype") != "ARCHIVE" or "Header:" in existing_node.get("snippet", "")):
                        needs_reparse = True

                    if existing_node and existing_node["file_hash"] == file_hash and not needs_reparse:
                        source_id = existing_node["id"]
                        embedding = None
                    else:
                        embedding = await self.embedder.embed_file(file_path_str)
                        archetype, snippet = extract_archetype_and_snippet(path, file_bytes)
                        
                        source_id = await self.db.upsert_node(
                            file_path=file_path_str, file_hash=file_hash, extension=path.suffix,
                            size_bytes=path.stat().st_size, archetype=archetype, snippet=snippet,
                            embedding=embedding, thumbnail_url="",
                        )

                        if path.suffix.lower() in ('.pdf', '.png', '.jpg', '.jpeg', '.webp'):
                            async def background_thumb(p, sid):
                                try:
                                    url = await asyncio.get_running_loop().run_in_executor(
                                        self.thumbnail_manager.executor,
                                        self.thumbnail_manager.generate_thumbnail, p, file_hash
                                    )
                                    if url and os.path.exists(url):
                                        async with self.db._conn.cursor() as cursor:
                                            await cursor.execute(
                                                "UPDATE nodes SET thumbnail_url = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                                (url, sid)
                                            )
                                        await self.db._conn.commit()
                                        await self.ipc.broadcast_event("node_updated", {"node_id": sid, "file_path": str(p)})
                                except Exception as e:
                                    pass
                            asyncio.create_task(background_thumb(path, source_id))

                    if self.enable_semantic_edges and embedding is not None:
                        await self.db.create_semantic_edges(source_id, embedding, self.semantic_distance_threshold)

                    if action != "initial_scan":
                        await self.db.log_session_event(source_id, event_type=action)
                        await self.db.create_temporal_edges(source_id, window_minutes=self.temporal_window_minutes)

                    if path.suffix.lower() in (".md", ".markdown", ".txt"):
                        try:
                            await self.db.reconcile_explicit_edges(source_id)
                            content = file_bytes.decode("utf-8", errors="ignore")
                            for target in extract_explicit_links(content):
                                target_file = target if target.endswith(".md") else f"{target}.md"
                                resolved_target_path = str((path.parent / target_file).resolve())
                                target_id = await self.db.upsert_node(
                                    file_path=resolved_target_path, file_hash="pending", extension=".md",
                                    size_bytes=0, archetype="document", snippet="", embedding=None, thumbnail_url=""
                                )
                                await self.db.upsert_edge(source_id, target_id, "wikilink", 1.0)
                        except Exception:
                            pass

                    await self.ipc.broadcast_event("node_updated", {"node_id": source_id, "file_path": file_path_str})

                elif action == "deleted":
                    deleted_node_id = await self.db.delete_node_by_path(file_path_str)
                    if deleted_node_id:
                        await self.ipc.broadcast_event("node_deleted", {"node_id": deleted_node_id, "file_path": file_path_str})
                
                self.event_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing pipeline event: {e}")

class IPCHandlers:
    def __init__(self, db, embedder, ipc, temporal_window_minutes: int):
        self.db = db
        self.embedder = embedder
        self.ipc = ipc
        self.temporal_window_minutes = temporal_window_minutes

    async def handle_semantic_search(self, query_text: str, limit: int = 5) -> list:
        query_vec = await self.embedder.embed_text(query_text)
        return await self.db.search_similar_nodes(query_vec, limit=limit)

    async def handle_get_neighbors(self, node_id: int) -> dict:
        semantic_neighbors = await self.db.get_node_neighbors(node_id)
        all_edges = await self.db.get_edges_for_node(node_id)
        return {
            "neighbors": semantic_neighbors.get("edges", []) if isinstance(semantic_neighbors, dict) else [],
            "persisted_edges": [e for e in all_edges if e.get("edge_type") != "temporal"],
            "temporal_edges": [{"source_id": t["source_id"], "target_id": t["target_id"], "edge_type": "temporal", "weight": t.get("weight", 0.5)} for t in all_edges if t.get("edge_type") == "temporal"]
        }

    async def handle_create_edge(self, source_id: int, target_id: int, edge_type: str) -> dict:
        try:
            await self.db.upsert_edge(source_id, target_id, edge_type, 1.0)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_save_node(self, node_id: int, content: str) -> dict:
        nodes = await self.db.get_all_nodes()
        target_node = next((n for n in nodes if n["id"] == node_id), None)
        if not target_node: return {"status": "error", "message": "Node not found"}
        file_path = Path(target_node["file_path"])
        if not file_path.exists(): return {"status": "error", "message": "File not found"}
        try:
            temp_file = file_path.with_suffix(file_path.suffix + ".tmp")
            await asyncio.to_thread(temp_file.write_text, content, encoding="utf-8")
            await asyncio.to_thread(temp_file.replace, file_path)
            return {"status": "success", "node_id": node_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_touch_node(self, node_id: int, event_type: str = "focus") -> dict:
        await self.db.log_session_event(node_id, event_type=event_type)
        temporal_edges = await self.db.create_temporal_edges(node_id, window_minutes=self.temporal_window_minutes, half_life_minutes=25.0, reinforcement_boost=0.20)
        persisted_edges = await self.db.get_edges_for_node(node_id)
        recent_node_ids = await self.db.get_recent_node_ids(window_minutes=self.temporal_window_minutes, min_weight=0.10)
        
        await self.ipc.broadcast_event("node_updated", {
            "node_id": node_id, "reason": "temporal_link", "temporal_edges": temporal_edges,
            "persisted_edges": persisted_edges, "recent_node_ids": recent_node_ids,
        })
        return {
            "node_id": node_id, "event_type": event_type, "temporal_edges_created": len(temporal_edges),
            "temporal_edges": temporal_edges, "persisted_edges": persisted_edges, "recent_node_ids": recent_node_ids,
        }
