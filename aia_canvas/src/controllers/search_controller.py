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
                node_id_str = str(node.id)
                if node_id_str not in seen_ids:
                    node_ids.append(node_id_str)
                    seen_ids.add(node_id_str)
                    
            # Add server semantic search results
            for n in search_result:
                n_id = n.get('id') if 'id' in n else n.get('node_id')
                if n_id is not None:
                    node_id_str = str(n_id)
                    if node_id_str not in seen_ids:
                        node_ids.append(node_id_str)
                        seen_ids.add(node_id_str)

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
        if hasattr(self.bridge, "physics") and self.bridge.physics and hasattr(self.bridge, "store") and self.bridge.store:
            self.bridge.physics.set_staged_nodes([], self.bridge.physics.viewport_w, 0.0, self.bridge.store.get_all_nodes())
            
        if hasattr(self.bridge, "_wake_physics"):
            self.bridge._wake_physics()
            
        self.searchCleared.emit()

    @pyqtSlot(list, float, float)
    def set_staged_nodes(self, node_id_strs: list, viewport_w: float, shelf_y: float):
        node_ids = []
        for nid in node_id_strs:
            try:
                node_ids.append(int(nid))
            except ValueError:
                pass
                
        if hasattr(self.bridge, "physics") and self.bridge.physics and hasattr(self.bridge, "store") and self.bridge.store:
            self.bridge.physics.set_staged_nodes(node_ids, viewport_w, shelf_y, self.bridge.store.get_all_nodes())
            
        if hasattr(self.bridge, "_wake_physics"):
            self.bridge._wake_physics()
