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

    @staticmethod
    def deduplicate_edges(raw_edges: list, topological_priority: dict | None = None) -> list[Edge]:
        topological_priority = topological_priority or {
            "explicit": 100, "wikilink": 90, "direct": 80, "knn": 50, "semantic": 40, "semantic_link": 30
        }
        topo_edges = {}
        temporal_edges = {}

        for e in raw_edges:
            is_obj = isinstance(e, Edge) or hasattr(e, "sourceId")
            src = e.sourceId if is_obj else (e.get("source") or e.get("sourceId") or e.get("source_id"))
            tgt = e.targetId if is_obj else (e.get("target") or e.get("targetId") or e.get("target_id"))
            etype = e.edgeType if is_obj else (e.get("edgeType") or e.get("edge_type", "semantic"))
            weight = e.weight if is_obj else float(e.get("weight", 1.0))
            if src is None or tgt is None:
                continue

            pair_key = tuple(sorted([int(src), int(tgt)]))

            if etype == "temporal":
                if pair_key not in temporal_edges:
                    temporal_edges[pair_key] = e if isinstance(e, Edge) else Edge(
                        source_id=int(src), target_id=int(tgt), edge_type=etype, weight=weight, category="temporal"
                    )
            else:
                if pair_key not in topo_edges:
                    topo_edges[pair_key] = e if isinstance(e, Edge) else Edge(
                        source_id=int(src), target_id=int(tgt), edge_type=etype, weight=weight, category="topological"
                    )
                else:
                    curr_type = getattr(topo_edges[pair_key], "edgeType", "semantic")
                    if topological_priority.get(etype, 0) > topological_priority.get(curr_type, 0):
                        topo_edges[pair_key] = e if isinstance(e, Edge) else Edge(
                            source_id=int(src), target_id=int(tgt), edge_type=etype, weight=weight, category="topological"
                        )

        return list(topo_edges.values()) + list(temporal_edges.values())