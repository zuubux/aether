import argparse, asyncio, logging, os, signal, sys
from pathlib import Path
from indexer.embedder import LocalEmbedder
from indexer.thumbnail import ThumbnailManager
from indexer.service import IndexingService, IPCHandlers
from ipc.server import IPCServer
from storage.db import DatabaseManager
from watcher.service import FileWatcher

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aia_weaver")

class WeaverDaemon:
    def __init__(self, dirs: list[str], db_path: str, enable_sem: bool, sem_thresh: float, temp_win: int, sock: str):
        self._shutdown = asyncio.Event()
        self.dirs = [str(Path(d).expanduser().resolve()) for d in dirs]
        self.db = DatabaseManager(db_path)
        self.embedder = LocalEmbedder()
        self.thumbnail_manager = ThumbnailManager(Path.home() / ".cache" / "aether" / "thumbnails")
        self.event_queue = asyncio.Queue()
        self.watcher = FileWatcher(self.dirs, self.event_queue)
        
        self.ipc = IPCServer(
            search_handler=lambda q, l=5: self.handlers.handle_semantic_search(q, l),
            neighbors_handler=lambda n: self.handlers.handle_get_neighbors(n),
            all_nodes_handler=self._wrapped_get_all_nodes,
            touch_handler=lambda n, e="focus": self.handlers.handle_touch_node(n, e),
            save_node_handler=lambda n, c: self.handlers.handle_save_node(n, c),
            create_edge_handler=lambda s, t, e: self.handlers.handle_create_edge(s, t, e),
            allowed_directories=[Path(d) for d in self.dirs], socket_path=sock
        )
        self.handlers = IPCHandlers(self.db, self.embedder, self.ipc, temp_win)
        self.service = IndexingService(self.db, self.ipc, self.embedder, self.thumbnail_manager, self.event_queue, self.dirs, enable_sem, sem_thresh, temp_win)

    async def _wrapped_get_all_nodes(self):
        return {"nodes": await self.db.get_all_nodes(), "edges": await self.db.get_all_edges(), "timing": {"db_load": 0.0, "embed_cache": 0.0}}

    async def start(self):
        await self.db.initialize()
        await self.ipc.start()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try: asyncio.get_running_loop().add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
            except NotImplementedError: pass
        wt = asyncio.create_task(self.watcher.watch_loop())
        pt = asyncio.create_task(self.service.process_event_queue(self._shutdown))
        async def bg():
            await asyncio.to_thread(self.thumbnail_manager.enforce_cache_limits)
            try:
                for n in await self.db.get_all_nodes():
                    if not os.path.exists(n["file_path"]): await self.db.delete_node_by_path(n["file_path"])
            except Exception: pass
            await self.service.initial_workspace_scan()
        asyncio.create_task(bg())
        await self._shutdown.wait()
        wt.cancel(); pt.cancel()
        await asyncio.gather(wt, pt, return_exceptions=True)
        await self.ipc.stop(); self.embedder.close(); await self.db.run_maintenance(); await self.db.close()

    async def shutdown(self): self._shutdown.set()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("-w", "--workspace", action="append", dest="workspaces")
    p.add_argument("--watch-dir", default=str(Path(__file__).resolve().parents[1] / "sandbox"))
    p.add_argument("--socket", default=None)
    p.add_argument("-v", "--debug", action="store_true")
    p.add_argument("--db-path", default=str(Path.home() / ".config" / "aether" / "weaver_graph.db"))
    p.add_argument("--enable-semantic", action="store_true", default=True)
    p.add_argument("--semantic-threshold", type=float, default=0.65)
    p.add_argument("--temporal-window", type=int, default=60)
    a = p.parse_args()
    if a.debug: logging.getLogger().setLevel(logging.DEBUG)
    dirs = a.workspaces or [a.watch_dir]
    if os.environ.get("AETHER_WORKSPACE_DIR"): dirs = [d.strip() for d in os.environ.get("AETHER_WORKSPACE_DIR", "").replace(":", ",").split(",") if d.strip()]
    Path(a.db_path).parent.mkdir(parents=True, exist_ok=True); os.chmod(Path(a.db_path).parent, 0o700)
    try: asyncio.run(WeaverDaemon(dirs, a.db_path, a.enable_semantic, a.semantic_threshold, a.temporal_window, a.socket).start())
    except KeyboardInterrupt: pass
