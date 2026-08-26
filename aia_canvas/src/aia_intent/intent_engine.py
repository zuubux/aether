"""
Aether Intent Engine
Multi-modal intent ingestion and graph querying.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

logger = logging.getLogger("aia_canvas.intent")

@dataclass
class IntentSignal:
    source: str
    query: str
    context_tags: list[str] = field(default_factory=list)
    confidence: float = 1.0


class IntentEngine(QObject):
    nodesSummoned = pyqtSignal(list, float, float)  # list[str] node_ids, target_x, target_y

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    @pyqtSlot(str)
    def process_query(self, text: str):
        signal = IntentSignal(source="text", query=text)
        self.evaluate_intent(signal)

    def evaluate_intent(self, signal: IntentSignal):
        if not signal.query:
            return
            
        def _handle_search(result: Any, error: str):
            if error or not isinstance(result, list):
                logger.error(f"Intent search failed: {error}")
                return
            
            node_ids = []
            for n in result:
                n_id = n.get('id') if 'id' in n else n.get('node_id')
                if n_id is not None:
                    node_ids.append(str(n_id))
            
            if node_ids:
                target_x = self.bridge.physics_engine.center_x
                target_y = self.bridge.physics_engine.center_y
                self.nodesSummoned.emit(node_ids, target_x, target_y)
                # Wake physics up so the summoning can take effect
                self.bridge._wake_physics()

        self.bridge.ipc.call_rpc_sync(
            "search_graph",
            {"query": signal.query, "limit": 5},
            callback=_handle_search
        )
