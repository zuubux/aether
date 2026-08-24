from typing import Any

from PyQt6.QtCore import pyqtSignal, pyqtSlot

from .base_controller import BaseController


class SearchController(BaseController):
    """
    Controller managing search queries, semantic match results,
    filtering criteria, and search result staging.
    """
    
    searchResultsReceived = pyqtSignal(list)
    searchCleared = pyqtSignal()

    @pyqtSlot(str)
    def submit_query(self, query: str):
        self.log_debug(f"OmniBar query submitted: {query}")
        
        is_connected = getattr(self.bridge, "_is_connected", False)
        if not is_connected:
            return

        q_lower = query.lower().strip()
        local_matches = []
        
        if hasattr(self.bridge, "store") and self.bridge.store:
            if q_lower:
                ext_query = q_lower.removeprefix('.')
                for node in self.bridge.store.get_all_nodes():
                    fn = node.fileName.lower()
                    ext = node.extension.lower()
                    if (q_lower in fn) or (ext_query in ext) or (q_lower in ext):
                        local_matches.append(node)

        def _handle_search(result: Any, error: str | None):
            search_result = result if (not error and isinstance(result, list)) else []
            self.log_debug(f"OmniBar search response: {search_result}")
            
            seen_ids = set()
            node_ids = []
            
            # Prepend local extension/filename matches
            for node in local_matches:
                if node.id not in seen_ids:
                    node_ids.append(node.id)
                    seen_ids.add(node.id)
                    
            # Add server semantic search results
            for n in search_result:
                n_id = n.get('id') if 'id' in n else n.get('node_id')
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
            else:
                self.searchCleared.emit()

        if not query.strip():
            self.searchCleared.emit()
            return

        if hasattr(self.bridge, "ipc") and self.bridge.ipc:
            self.bridge.ipc.call_rpc_sync(
                "search_graph",
                {"query": query, "limit": 5},
                callback=_handle_search
            )

    @pyqtSlot()
    def clear_search(self):
        self.searchCleared.emit()

    @pyqtSlot(bool)
    def set_search_active(self, active: bool):
        if not active:
            if hasattr(self.bridge, "_search_active"):
                self.bridge._search_active = False
            if hasattr(self.bridge, "searchActiveChanged"):
                self.bridge.searchActiveChanged.emit(False)
            # Do NOT emit searchCleared or clear selection here
