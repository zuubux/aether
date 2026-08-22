"""
Aether Canvas - Graph Store
Maintains the reactive local cache of QObject graph nodes and relational edges.
"""


from models import Edge, Node


class GraphStore:
    def __init__(self):
        self._nodes: dict[int, Node] = {}
        self._edges: list[Edge] = []

    def get_node(self, node_id: int) -> Node | None:
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> list[Node]:
        return list(self._nodes.values())

    def get_all_edges(self) -> list[Edge]:
        return list(self._edges)

    def upsert_node(self, node: Node):
        if node.id in self._nodes:
            existing = self._nodes[node.id]
            existing.filePath = node.filePath
        else:
            self._nodes[node.id] = node

    def remove_node(self, node_id: int):
        self._nodes.pop(node_id, None)
        self._edges = [
            e for e in self._edges 
            if e.sourceId != node_id and e.targetId != node_id
        ]

    def set_edges_for_neighborhood(self, primary_node_id: int, new_edges: list[Edge]):
        retained = [
            e for e in self._edges
            if e.sourceId != primary_node_id and e.targetId != primary_node_id
        ]
        self._edges = retained + new_edges

    def clear(self):
        self._nodes.clear()
        self._edges.clear()