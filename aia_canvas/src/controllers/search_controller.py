from typing import Any, Dict, List, Optional

from PyQt6.QtCore import pyqtSignal, pyqtSlot

from omni import OmniContext, OmniResult, OmniRouter
from .base_controller import BaseController


class SearchController(BaseController):
    """
    Controller managing search queries, semantic match results,
    OmniRouter dispatching, filtering criteria, and search result staging.
    """

    searchResultsReceived = pyqtSignal(list)
    omniResultsReceived = pyqtSignal(list)
    shellOutputReceived = pyqtSignal(list)
    omniModeChanged = pyqtSignal('QVariantMap')
    searchCleared = pyqtSignal()

    def __init__(self, bridge):
        super().__init__(bridge)
        store = getattr(bridge, "store", None)
        self.router = OmniRouter(store=store)

    @pyqtSlot(str, float, str, list)
    def dispatch_omni(
        self,
        query: str,
        cadence_ms: float = 0.0,
        focused_node_id: str = "",
        selected_node_ids: Optional[list] = None,
    ):
        if selected_node_ids is None:
            selected_node_ids = []

        if hasattr(self.bridge, "store") and self.bridge.store:
            self.router.update_store(self.bridge.store)

        focused_node_path = None
        if focused_node_id and hasattr(self.bridge, "store") and self.bridge.store:
            try:
                n_id = int(focused_node_id)
                node = self.bridge.store.get_node(n_id)
                if node:
                    focused_node_path = getattr(node, "filePath", None) or getattr(node, "path", None)
            except (ValueError, TypeError):
                pass

        ctx = OmniContext(
            raw_query=query,
            focused_node_id=focused_node_id if focused_node_id else None,
            focused_node_path=focused_node_path,
            selected_node_ids=selected_node_ids,
            typing_cadence_ms=cadence_ms,
        )

        import time
        from core.telemetry import TelemetrySink
        t0 = time.perf_counter_ns()
        results = self.router.dispatch(query, ctx)
        t1 = time.perf_counter_ns()
        TelemetrySink.instance().record_db_query((t1 - t0) / 1e6)

        # Convert OmniResult objects to QML-friendly dicts
        qml_results = []
        node_ids = []

        for r in results:
            item_dict = {
                "id": r.id,
                "title": r.title,
                "category": r.category,
                "score": r.score,
                "icon": r.icon,
                "extension": r.metadata.get("extension", ""),
                "archetype": r.metadata.get("archetype", r.category),
                "path": r.metadata.get("path", ""),
                "snippet": r.metadata.get("snippet", ""),
                "node_id": r.metadata.get("node_id", r.id),
                "stream": r.metadata.get("stream", ""),
                "line": r.metadata.get("line", r.title),
                "cwd": r.metadata.get("cwd", ""),
                "exit_code": r.metadata.get("exit_code", None),
            }
            qml_results.append(item_dict)

            # Collect numeric node IDs for canvas selection/highlighting
            n_id = r.metadata.get("node_id", r.id)
            try:
                n_id_int = int(n_id)
                if n_id_int not in node_ids:
                    node_ids.append(n_id_int)
            except (ValueError, TypeError):
                pass

        self.omniResultsReceived.emit(qml_results)
        if query.strip().startswith(">"):
            self.shellOutputReceived.emit(qml_results)

        if node_ids and not (query.strip().startswith("?") or query.strip().startswith(">")):
            self.searchResultsReceived.emit(node_ids)
        elif not query.strip() or query.strip().startswith("?") or query.strip().startswith(">"):
            self.searchCleared.emit()

    @pyqtSlot(str, result='QVariantMap')
    def get_omni_mode(self, query: str) -> Dict[str, Any]:
        meta = self.router.get_mode_metadata(query)
        return meta

    @pyqtSlot(str)
    def submit_query(self, query: str):
        self.log_debug(f"OmniBar query submitted: {query}")
        self.dispatch_omni(query)

        is_connected = getattr(self.bridge, "_is_connected", False)
        if not is_connected:
            return

        if not query.strip() or query.strip().startswith("?") or query.strip().startswith(">"):
            self.searchCleared.emit()
            return

        def _handle_search(result: Any, error: str | None):
            search_result = result if (not error and isinstance(result, list)) else []
            self.log_debug(f"OmniBar search response: {search_result}")

            seen_ids = set()
            node_ids = []

            for n in search_result:
                n_id = n.get("id") if "id" in n else n.get("node_id")
                if n_id is not None:
                    try:
                        n_id_int = int(n_id)
                        if n_id_int not in seen_ids:
                            node_ids.append(n_id_int)
                            seen_ids.add(n_id_int)
                    except ValueError:
                        pass

            if node_ids:
                self.searchResultsReceived.emit(node_ids)

        if hasattr(self.bridge, "ipc") and self.bridge.ipc:
            self.bridge.ipc.call_rpc_sync(
                "search_graph",
                {"query": query, "limit": 5},
                callback=_handle_search,
            )

    @pyqtSlot()
    def clear_search(self):
        self.searchCleared.emit()

    @pyqtSlot(bool)
    def set_search_active(self, active: bool):
        if hasattr(self.bridge, "_search_active"):
            self.bridge._search_active = active
        if hasattr(self.bridge, "searchActiveChanged"):
            self.bridge.searchActiveChanged.emit(active)

