from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from .base_controller import BaseController


class PhysicsController(BaseController):
    """
    Controller managing graph physics mechanics, simulation loops,
    repulsive/attractive forces, tendril physics telemetry, and relations.
    """

    nodesChanged = pyqtSignal()
    edgesChanged = pyqtSignal()
    clusterHalosChanged = pyqtSignal()
    telemetryChanged = pyqtSignal()
    connectionStatusChanged = pyqtSignal(bool)

    @pyqtProperty(list, notify=nodesChanged)
    def nodes(self) -> list:
        if hasattr(self.bridge, "store") and self.bridge.store:
            return self.bridge.store.get_all_nodes()
        return []

    @pyqtProperty(list, notify=edgesChanged)
    def edges(self) -> list:
        base_edges = []
        if getattr(self.bridge, "_selected_node_id", 0) > 0:
            # 1. Start with curated, deduplicated focal edges
            base_edges = list(getattr(self.bridge, "_focal_edges", []))
            
            # 2. Exclude any ambient edges touching the focused node to prevent duplicate filaments
            selected_node_id = self.bridge._selected_node_id
            for e in getattr(self.bridge, "_ambient_edges", []):
                if e.sourceId == selected_node_id or e.targetId == selected_node_id:
                    if getattr(e, "edgeType", None) not in ("explicit", "wikilink", "direct"):
                        continue
                base_edges.append(e)
        else:
            base_edges = getattr(self.bridge, "_ambient_edges", [])
            
        # 3. Global deduplication by priority to ensure no visual overlap
        unique_edges = {}
        priority = {
            "explicit": 3,
            "wikilink": 3,
            "direct": 3,
            "semantic_link": 2,
            "semantic": 1,
            "temporal": 0
        }
        for e in base_edges:
            # Include category in pair_key so temporal and topological can coexist as dual tendrils
            pair_key = (min(e.sourceId, e.targetId), max(e.sourceId, e.targetId), e.category)
            current = unique_edges.get(pair_key)
            if not current:
                unique_edges[pair_key] = e
            else:
                if priority.get(e.edgeType, 0) > priority.get(current.edgeType, 0) or (priority.get(e.edgeType, 0) == priority.get(current.edgeType, 0) and e.weight > current.weight):
                    unique_edges[pair_key] = e
                    
        return list(unique_edges.values())

    @pyqtProperty(list, notify=clusterHalosChanged)
    def clusterHalos(self) -> list:
        return getattr(self.bridge, "_cluster_halos", [])

    @pyqtProperty(float, notify=telemetryChanged)
    def physicsFrametime(self) -> float:
        return getattr(self.bridge, "_last_frametime_ms", 0.0)

    @pyqtProperty(int, notify=telemetryChanged)
    def activeNodeCount(self) -> int:
        if hasattr(self.bridge, "store") and self.bridge.store:
            return len(self.bridge.store.get_all_nodes())
        return 0

    @pyqtProperty(int, notify=telemetryChanged)
    def activeEdgeCount(self) -> int:
        return len(self.edges)

    @pyqtProperty(bool, notify=connectionStatusChanged)
    def isConnected(self) -> bool:
        return getattr(self.bridge, "_is_connected", False)
