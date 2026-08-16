"""
Aether Canvas - Graph Store (HARDWARE/MOCK MODE)
Maintains local cache of active QObject graph nodes and relational edges.
"""

from typing import Dict, List, Optional
from models import Node, Edge

class GraphStore:
    def __init__(self):
        self._nodes: Dict[int, Node] = {}
        self._edges: List[Edge] = []
        self._seed_default_graph()  # <-- KEEPING THIS FOR TUNING

    def _seed_default_graph(self):
        defaults = [
            Node(id=1, file_path="/home/user/workspace/tracker.py", x=1280.0, y=720.0, focus=1.0),
            Node(id=4, file_path="/home/user/workspace/decay_math.py", x=1100.0, y=1080.0, focus=0.65),
            Node(id=5, file_path="/home/user/workspace/system_metrics.sh", x=1550.0, y=1120.0, focus=0.25),
            Node(id=3, file_path="/home/user/workspace/aether_charter.md", x=1850.0, y=380.0, focus=0.65),
            Node(id=2, file_path="/home/user/workspace/notes.md", x=2100.0, y=240.0, focus=0.25),
            Node(id=6, file_path="/home/user/workspace/archive_notes.txt", x=2200.0, y=520.0, focus=0.25),
            Node(id=7, file_path="/home/user/workspace/e39_parts_list.md", x=450.0, y=380.0, focus=0.25),
            Node(id=8, file_path="/home/user/workspace/m62_torque_specs.txt", x=280.0, y=600.0, focus=0.25),
        ]
        for n in defaults:
            self._nodes[n.id] = n

        self._edges = [
            Edge(source_id=1, target_id=4, edge_type="explicit", weight=1.0),
            Edge(source_id=1, target_id=5, edge_type="temporal", weight=0.60),
            Edge(source_id=3, target_id=2, edge_type="explicit", weight=0.90),
            Edge(source_id=3, target_id=6, edge_type="semantic", weight=0.55),
            Edge(source_id=7, target_id=8, edge_type="explicit", weight=0.95),
            Edge(source_id=1, target_id=3, edge_type="semantic", weight=0.75),
        ]

    def get_node(self, node_id: int) -> Optional[Node]:
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def get_all_edges(self) -> List[Edge]:
        return list(self._edges)

    def upsert_node(self, node: Node):
        if node.id in self._nodes:
            self._nodes[node.id].filePath = node.filePath
        else:
            self._nodes[node.id] = node

    def remove_node(self, node_id: int):
        self._nodes.pop(node_id, None)
        self._edges = [e for e in self._edges if e.sourceId != node_id and e.targetId != node_id]

    def set_edges_for_neighborhood(self, primary_node_id: int, new_edges: List[Edge]):
        retained = [e for e in self._edges if e.sourceId != primary_node_id and e.targetId != primary_node_id]
        self._edges = retained + new_edges