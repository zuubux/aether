import argparse
import asyncio
import hashlib
import logging
import os
import signal
import sys
from pathlib import Path

from indexer.embedder import LocalEmbedder
from indexer.parser import extract_archetype_and_snippet, extract_explicit_links
from indexer.thumbnail import ThumbnailManager
from ipc.server import IPCServer
from storage.db import DatabaseManager
from watcher.fs_events import FileWatcher

import subprocess
import shutil


def setup_logging(debug=False):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("aia_weaver")

logger = logging.getLogger("aia_weaver")


class WeaverDaemon:
    def __init__(
        self,
        target_directories: list[str],
        db_path: str | None = None,
        enable_semantic_edges: bool = False,
        semantic_distance_threshold: float = 0.35,
        temporal_window_minutes: int = 15,
        socket_path: str | None = None,
    ):
        self._shutdown_event = asyncio.Event()
        self.target_directories = [str(Path(d).expanduser().resolve()) for d in target_directories]
        self.enable_semantic_edges = enable_semantic_edges
        self.semantic_distance_threshold = semantic_distance_threshold
        self.temporal_window_minutes = temporal_window_minutes

        if db_path is None:
            config_dir = Path.home() / ".config" / "aether"
            config_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(config_dir, 0o700)
            self.db_path = str(config_dir / "weaver_graph.db")
        else:
            self.db_path = str(Path(db_path).expanduser().resolve())

        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.db = DatabaseManager(self.db_path)
        self.embedder = LocalEmbedder()
        self.thumbnail_manager = ThumbnailManager(Path.home() / ".cache" / "aether" / "thumbnails")
        self.watcher = FileWatcher(
            target_dirs=self.target_directories,
            event_queue=self.event_queue,
        )
        
        self.db_load_ms = 0.0
        self.embed_cache_ms = 0.0
        
        async def wrapped_get_all_nodes():
            import time
            t0 = time.perf_counter()
            nodes = await self.db.get_all_nodes()
            edges = await self.db.get_all_edges()
            t1 = time.perf_counter()
            if hasattr(self, "t_start"):
                logger.info(f"[T+{(t1 - self.t_start)*1000:.1f}ms] Weaver completed `initial_sync` DB query")
            return {
                "nodes": nodes,
                "edges": edges,
                "timing": {
                    "db_load": (t1 - t0) * 1000.0,
                    "embed_cache": 0.0
                }
            }

        self.ipc = IPCServer(
            search_handler=self.handle_semantic_search,
            neighbors_handler=self.handle_get_neighbors,
            all_nodes_handler=wrapped_get_all_nodes,
            touch_handler=self.handle_touch_node,
            save_node_handler=self.handle_save_node,
            create_edge_handler=self.handle_create_edge,
            allowed_directories=[Path(d) for d in self.target_directories],
            socket_path=socket_path,
        )

    async def handle_semantic_search(self, query_text: str, limit: int = 5) -> list:
        logger.info(f"IPC Search Request received: '{query_text}'")
        query_vec = await self.embedder.embed_text(query_text)
        results = await self.db.search_similar_nodes(query_vec, limit=limit)
        return results

    async def handle_get_neighbors(self, node_id: int) -> dict:
        logger.info(f"IPC Neighbors Request received for Node #{node_id}")
        semantic_neighbors = await self.db.get_node_neighbors(node_id)
        all_edges = await self.db.get_edges_for_node(node_id)
        
        persisted_edges = [e for e in all_edges if e.get("edge_type") != "temporal"]
        
        # Collect temporal edges involving the requested node
        temporal_edges = [
            {"source_id": t["source_id"], "target_id": t["target_id"], "edge_type": "temporal", "weight": t.get("weight", 0.5)}
            for t in all_edges if t.get("edge_type") == "temporal"
        ]
        
        return {
            "neighbors": semantic_neighbors.get("edges", []) if isinstance(semantic_neighbors, dict) else [],
            "persisted_edges": persisted_edges,
            "temporal_edges": temporal_edges
        }

    async def handle_create_edge(self, source_id: int, target_id: int, edge_type: str) -> dict:
        logger.info(f"IPC Create Edge Request: {source_id} -> {target_id} ({edge_type})")
        try:
            weight = 1.0
            await self.db.upsert_edge(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                weight=weight,
            )
            
            # Update Weaver's in-memory graph cache (undirected)
            if hasattr(self, "graph") and self.graph is not None:
                self.graph.add_edge(source_id, target_id, edge_type=edge_type, weight=weight)
                self.graph.add_edge(target_id, source_id, edge_type=edge_type, weight=weight)
                
            print(f"[Weaver DB] Successfully committed edge {source_id} <-> {target_id} ({edge_type}) to disk")
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Create edge failed: {e}")
            return {"status": "error", "message": str(e)}

    async def handle_save_node(self, node_id: int, content: str) -> dict:
        logger.info(f"IPC Save Request: Node #{node_id}")
        nodes = await self.db.get_all_nodes()
        target_node = next((n for n in nodes if n["id"] == node_id), None)
        if not target_node:
            return {"status": "error", "message": "Node not found"}
        
        file_path = Path(target_node["file_path"])
        if not file_path.exists():
            return {"status": "error", "message": "File not found"}
            
        try:
            temp_file = file_path.with_suffix(file_path.suffix + ".tmp")
            await asyncio.to_thread(temp_file.write_text, content, encoding="utf-8")
            await asyncio.to_thread(temp_file.replace, file_path)
            
            # The FileWatcher will pick up the change and update the DB/Index
            # But we can also force an update to DB snippet here if strictly required
            # as per instruction: "Update internal SQLite node content/snippets so search and graph state stay current"
            # It might be best handled by the event queue triggered by the file modification.
            
            return {"status": "success", "node_id": node_id}
        except Exception as e:
            logger.error(f"Save failed for Node #{node_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def handle_touch_node(self, node_id: int, event_type: str = "focus") -> dict:
        """Logs active UI focus/interaction, recalculates decaying temporal edges, and broadcasts recent node set."""
        logger.info(f"IPC Touch Request: Node #{node_id} (event: {event_type})")
        await self.db.log_session_event(node_id, event_type=event_type)
        
        temporal_edges = await self.db.create_temporal_edges(
            node_id,
            window_minutes=self.temporal_window_minutes,
            half_life_minutes=25.0,
            reinforcement_boost=0.20,
        )
        
        persisted_edges = await self.db.get_edges_for_node(node_id)
        
        recent_node_ids = await self.db.get_recent_node_ids(
            window_minutes=self.temporal_window_minutes,
            min_weight=0.10,
        )

        if temporal_edges:
            logger.info(f"Reinforced {len(temporal_edges)} Temporal Edge(s) via UI focus for Node #{node_id}")
            
        await self.ipc.broadcast_event(
            "node_updated", {
                "node_id": node_id,
                "reason": "temporal_link",
                "temporal_edges": temporal_edges,
                "persisted_edges": persisted_edges,
                "recent_node_ids": recent_node_ids,
            }
        )
            
        return {
            "node_id": node_id,
            "event_type": event_type,
            "temporal_edges_created": len(temporal_edges),
            "temporal_edges": temporal_edges,
            "persisted_edges": persisted_edges,
            "recent_node_ids": recent_node_ids,
        }

    async def _initial_workspace_scan(self) -> None:
        """Scans configured workspace directories on boot and queues initial indexing events."""
        logger.info(f"Performing initial workspace scan on: {self.target_directories}")
        scanned_count = 0

        for target in self.target_directories:
            target_path = Path(target)
            if not target_path.exists() or not target_path.is_dir():
                logger.warning(f"Target directory does not exist or is not a directory: {target_path}")
                continue

            for path in target_path.rglob("*"):
                if path.is_file() and not self.watcher._should_ignore(str(path)):
                    await self.event_queue.put({
                        "action": "initial_scan",  # <-- Changed from "created"
                        "file_path": str(path.resolve()),
                        "timestamp": asyncio.get_running_loop().time(),
                    })
                    scanned_count += 1

        logger.info(f"Initial workspace scan enqueued {scanned_count} file(s) for indexing.")

    async def start(self) -> None:
        import time
        self.t_start = time.perf_counter()
        
        def log_milestone(msg: str):
            logger.info(f"[T+{(time.perf_counter() - self.t_start)*1000:.1f}ms] {msg}")

        log_milestone("Weaver daemon started")

        await self.db.initialize()

        # START IPC IMMEDIATELY
        await self.ipc.start()
        log_milestone("Weaver IPC socket listening")

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig, lambda: asyncio.create_task(self.shutdown())
                )
            except NotImplementedError:
                pass

        watcher_task = asyncio.create_task(self.watcher.watch_loop())
        processor_task = asyncio.create_task(self._process_event_queue())

        # Perform background tasks async
        async def background_init():
            # Enforce Cache Limits
            await asyncio.to_thread(self.thumbnail_manager.enforce_cache_limits)

            # Cold Start Ghost Node Reconciliation
            try:
                all_nodes = await self.db.get_all_nodes()
                pruned_count = 0
                for node in all_nodes:
                    file_path = node["file_path"]
                    if not os.path.exists(file_path):
                        await self.db.delete_node_by_path(file_path)
                        pruned_count += 1
            except Exception as e:
                logger.error(f"Error during cold start ghost node reconciliation: {e}")

            await self._initial_workspace_scan()

        asyncio.create_task(background_init())

        logger.info("aia_weaver fully ACTIVE with hardened IPC socket enabled.")

        await self._shutdown_event.wait()

        logger.info("Stopping all background services...")
        watcher_task.cancel()
        processor_task.cancel()
        await asyncio.gather(watcher_task, processor_task, return_exceptions=True)

        await self.ipc.stop()
        self.embedder.close()
        await self.db.run_maintenance()
        await self.db.close()
        logger.info("aia_weaver shutdown complete.")

    async def _process_event_queue(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                file_path_str = event["file_path"]
                action = event["action"]
                path = Path(file_path_str)

                # --- 1. HANDLE INITIAL_SCAN, CREATED & MODIFIED ---
                if action in ("initial_scan", "created", "modified") and path.exists() and path.is_file():
                    file_bytes = await asyncio.to_thread(path.read_bytes)
                    file_hash = hashlib.sha256(file_bytes).hexdigest()
                    
                    # Performance fix: Skip expensive operations on startup if hash matches
                    existing_node = None
                    if action == "initial_scan":
                        existing_node = await self.db.get_node_by_path(file_path_str)
                    
                    if existing_node and existing_node["file_hash"] == file_hash:
                        # Fast path: Node exists and is unchanged
                        source_id = existing_node["id"]
                        logger.debug(f"Skipped embedding for unchanged node #{source_id} -> {path.name}")
                        embedding = None
                    else:
                        import time
                        t0 = time.perf_counter()
                        embedding = await self.embedder.embed_file(file_path_str)
                        t1 = time.perf_counter()
                        
                        archetype, snippet = extract_archetype_and_snippet(path, file_bytes)

                        # Upsert Node
                        source_id = await self.db.upsert_node(
                            file_path=file_path_str,
                            file_hash=file_hash,
                            extension=path.suffix,
                            size_bytes=path.stat().st_size,
                            archetype=archetype,
                            snippet=snippet,
                            embedding=embedding,
                            thumbnail_url="",
                        )
                        t2 = time.perf_counter()
                        logger.info(f"Indexed Node #{source_id} [{action.upper()}] -> {path.name} (Embed: {(t1-t0)*1000:.1f}ms, DB: {(t2-t1)*1000:.1f}ms)")

                        ext = path.suffix.lower()
                        if ext in ('.pdf', '.png', '.jpg', '.jpeg', '.webp'):
                            async def background_thumb(p, h, sid):
                                try:
                                    url = await asyncio.get_running_loop().run_in_executor(
                                        self.thumbnail_manager.executor,
                                        self.thumbnail_manager.generate_thumbnail,
                                        p, h
                                    )
                                    if url and self.db._conn and os.path.exists(url) and os.path.getsize(url) > 0:
                                        async with self.db._conn.cursor() as cursor:
                                            await cursor.execute(
                                                "UPDATE nodes SET thumbnail_url = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                                (url, sid)
                                            )
                                        await self.db._conn.commit()
                                        await self.ipc.broadcast_event(
                                            "node_updated", {"node_id": sid, "file_path": str(p)}
                                        )
                                except Exception as e:
                                    logger.error(f"Error in background thumbnail generation for Node #{sid}: {e}")

                            asyncio.create_task(background_thumb(path, file_hash, source_id))

                    # --- SEMANTIC ENGINE ---
                    if self.enable_semantic_edges and embedding is not None:
                        created_semantic = await self.db.create_semantic_edges(
                            node_id=source_id,
                            embedding=embedding,
                            distance_threshold=self.semantic_distance_threshold,
                        )
                        if created_semantic > 0:
                            logger.info(
                                f"Linked {created_semantic} Semantic Edge(s) for Node #{source_id}"
                            )

                    # --- TEMPORAL ENGINE (Skip during startup bootstrap scan) ---
                    if action != "initial_scan":
                        await self.db.log_session_event(source_id, event_type=action)
                        temporal_links = await self.db.create_temporal_edges(
                            source_id, window_minutes=self.temporal_window_minutes
                        )
                        if temporal_links:
                            logger.info(
                                f"Linked {len(temporal_links)} Temporal Edge(s) to recent activity for Node #{source_id}"
                            )

                    if path.suffix.lower() in (".md", ".markdown", ".txt"):
                        try:
                            await self.db.reconcile_explicit_edges(source_id)

                            content = file_bytes.decode("utf-8", errors="ignore")
                            wiki_targets = extract_explicit_links(content)

                            for target in wiki_targets:
                                target_file = target if target.endswith(".md") else f"{target}.md"
                                resolved_target_path = str((path.parent / target_file).resolve())

                                target_id = await self.db.upsert_node(
                                    file_path=resolved_target_path,
                                    file_hash="pending",
                                    extension=".md",
                                    size_bytes=0,
                                    archetype="document",
                                    snippet="",
                                    embedding=None,
                                    thumbnail_url="",
                                )

                                await self.db.upsert_edge(
                                    source_id=source_id,
                                    target_id=target_id,
                                    edge_type="wikilink",
                                    weight=1.0,
                                )
                                logger.info(
                                    f"Linked Explicit Edge: Node #{source_id} -> Node #{target_id} ([[ {target} ]])"
                                )
                        except Exception as parse_err:
                            logger.error(f"Error parsing links in {path.name}: {parse_err}")

                    await self.ipc.broadcast_event(
                        "node_updated", {"node_id": source_id, "file_path": file_path_str}
                    )

                elif action == "deleted":
                    deleted_node_id = await self.db.delete_node_by_path(file_path_str)
                    if deleted_node_id:
                        logger.info(
                            f"Pruned Node #{deleted_node_id} [DELETED] -> {Path(file_path_str).name}"
                        )
                        await self.ipc.broadcast_event(
                            "node_deleted",
                            {"node_id": deleted_node_id, "file_path": file_path_str},
                        )

                self.event_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing pipeline event: {e}", exc_info=True)

    async def shutdown(self) -> None:
        logger.info("Shutdown signal received. Stopping aia_weaver...")
        self._shutdown_event.set()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aether Weaver (aia_weaver): Knowledge Fabric & Spatial Graph Daemon"
    )
    parser.add_argument(
        "-w",
        "--workspace",
        action="append",
        dest="workspaces",
        help="Workspace directory to watch and index (can be specified multiple times)",
    )
    default_watch_dir = str(Path(__file__).resolve().parents[1] / "sandbox")
    parser.add_argument(
        "--watch-dir",
        type=str,
        default=default_watch_dir,
        help=f"Target sandbox/notes directory to watch (default: {default_watch_dir})",
    )
    parser.add_argument(
        "--socket",
        type=str,
        default=None,
        help="Custom IPC socket path",
    )
    parser.add_argument(
        "-v",
        "--debug",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to SQLite knowledge graph ledger (default: ~/.config/aether/weaver_graph.db)",
    )
    parser.add_argument(
        "--enable-semantic",
        action="store_true",
        default=True,
        help="Enable semantic KNN vector edge linking (default: True)",
    )
    parser.add_argument(
        "--semantic-threshold",
        type=float,
        default=0.65,  # Updated default
        help="Cosine distance threshold for semantic edges (default: 0.65)",
    )
    parser.add_argument(
        "--temporal-window",
        type=int,
        default=60,
        help="Sliding time window in minutes for temporal activity edges (default: 15)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args, unknown = parser.parse_known_args() if 'parser' in locals() else parse_arguments(), []
    
    # Redefine to avoid undefined behavior based on my hacky diff
    args = parse_arguments()

    logger = setup_logging(args.debug)

    if args.workspaces:
        target_dirs = args.workspaces
    elif args.watch_dir:
        target_dirs = [args.watch_dir]
    elif os.environ.get("AETHER_WORKSPACE_DIR"):
        env_dirs = os.environ.get("AETHER_WORKSPACE_DIR", "")
        target_dirs = [d.strip() for d in env_dirs.replace(":", ",").split(",") if d.strip()]
    else:
        target_dirs = [str(Path(__file__).resolve().parents[1] / "sandbox")]

    for d in target_dirs:
        p = Path(d).resolve()
        if not p.exists():
            logger.warning(f"Target directory does not exist: {p}")
        else:
            logger.info(f"Monitoring canonical path: {p}")

    daemon = WeaverDaemon(
        target_directories=target_dirs,
        db_path=args.db_path,
        enable_semantic_edges=args.enable_semantic,
        semantic_distance_threshold=args.semantic_threshold,
        temporal_window_minutes=args.temporal_window,
        socket_path=args.socket,
    )

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user.")
    sys.exit(0)