import argparse
import asyncio
import hashlib
import logging
import os
from pathlib import Path
import signal
import sys

from indexer.embedder import LocalEmbedder
from indexer.parser import extract_explicit_links
from ipc.server import IPCServer
from storage.db import DatabaseManager
from watcher.fs_events import FileWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aia_weaver")


class WeaverDaemon:
    def __init__(
        self,
        target_directories: list[str],
        db_path: str | None = None,
        enable_semantic_edges: bool = False,
        semantic_distance_threshold: float = 0.35,
        temporal_window_minutes: int = 15,
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
        self.watcher = FileWatcher(
            target_dirs=self.target_directories,
            event_queue=self.event_queue,
        )
        self.ipc = IPCServer(
            search_handler=self.handle_semantic_search,
            neighbors_handler=self.handle_get_neighbors,
            all_nodes_handler=self.db.get_all_nodes,
            touch_handler=self.handle_touch_node,
            allowed_directories=[Path(d) for d in self.target_directories],
        )

    async def handle_semantic_search(self, query_text: str, limit: int = 5) -> list:
        logger.info(f"IPC Search Request received: '{query_text}'")
        query_vec = await self.embedder.embed_text(query_text)
        results = await self.db.search_similar_nodes(query_vec, limit=limit)
        return results

    async def handle_get_neighbors(self, node_id: int) -> dict:
        logger.info(f"IPC Neighbors Request received for Node #{node_id}")
        return await self.db.get_node_neighbors(node_id)

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
                "recent_node_ids": recent_node_ids,
            }
        )
            
        return {
            "node_id": node_id,
            "event_type": event_type,
            "temporal_edges_created": len(temporal_edges),
            "temporal_edges": temporal_edges,
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
        logger.info("Initializing aia_weaver engine...")

        await self.db.initialize()
        await self.ipc.start()

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

        await self._initial_workspace_scan()

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
                    embedding = await self.embedder.embed_file(file_path_str)

                    # Upsert Node
                    source_id = await self.db.upsert_node(
                        file_path=file_path_str,
                        file_hash=file_hash,
                        extension=path.suffix,
                        size_bytes=path.stat().st_size,
                        embedding=embedding,
                    )
                    logger.info(f"Indexed Node #{source_id} [{action.upper()}] -> {path.name}")

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
                                    embedding=None,
                                )

                                await self.db.upsert_edge(
                                    source_id=source_id,
                                    target_id=target_id,
                                    edge_type="explicit",
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
    args = parse_arguments()

    if args.workspaces:
        target_dirs = args.workspaces
    elif os.environ.get("AETHER_WORKSPACE_DIR"):
        env_dirs = os.environ.get("AETHER_WORKSPACE_DIR", "")
        target_dirs = [d.strip() for d in env_dirs.replace(":", ",").split(",") if d.strip()]
    else:
        target_dirs = ["./sandbox"]

    daemon = WeaverDaemon(
        target_directories=target_dirs,
        db_path=args.db_path,
        enable_semantic_edges=args.enable_semantic,
        semantic_distance_threshold=args.semantic_threshold,
        temporal_window_minutes=args.temporal_window,
    )

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user.")
    sys.exit(0)