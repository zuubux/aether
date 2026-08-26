import logging
from typing import Any, Callable, Dict, Optional

from core.intent_grammar import Intent, IntentOperator, parse_intent

def _get_node_name(node: Any) -> str:
    if isinstance(node, dict):
        return node.get("displayTitle") or node.get("display_title") or node.get("fileName") or node.get("label") or node.get("file_name") or ""
    return getattr(node, "displayTitle", "") or getattr(node, "display_title", "") or getattr(node, "fileName", "") or getattr(node, "label", "") or getattr(node, "file_name", "")

logger = logging.getLogger("aia_canvas.intent_dispatcher")


class IntentDispatcher:
    def __init__(self, bridge: Any):
        self.bridge = bridge
        self.handlers: Dict[IntentOperator, Callable[[Intent, Any], None]] = {
            IntentOperator.NAVIGATE: self.handle_navigate,
            IntentOperator.LINK: self.handle_link,
            IntentOperator.APERTURE: self.handle_aperture,
            IntentOperator.SEARCH: self.handle_search,
            IntentOperator.COMMAND: self.handle_command,
        }

    def dispatch(self, raw_text: str, context_override: Optional[int] = None):
        intent = parse_intent(raw_text)
        active_context = self.resolve_context(context_override)
        
        handler = self.handlers.get(intent.operator)
        if handler:
            handler(intent, active_context)
        else:
            logger.warning(f"No handler registered for intent operator: {intent.operator}")

    def resolve_context(self, context_override: Optional[int]) -> int:
        if context_override is not None:
            return context_override
        # Fallbacks: selected node, gaze fixated (if available), or 0 (global)
        if hasattr(self.bridge, "selectedNodeId") and self.bridge.selectedNodeId > 0:
            return self.bridge.selectedNodeId
        
        # In the future, check saccade stream for gaze-fixated node
        return 0

    def handle_navigate(self, intent: Intent, active_context: int):
        target = intent.arguments.get("target")
        if target:
            logger.info(f"Navigating to {target}")
            # The node_ctrl has navigate_to_link which accepts target_name
            self.bridge.navigate_to_link(target)

    def _resolve_node_id(self, target_ref: Any) -> Optional[int]:
        if isinstance(target_ref, int) and target_ref > 0:
            return target_ref
        if isinstance(target_ref, str):
            target_str = target_ref.strip().lower()
            nodes = self.bridge.store.get_all_nodes()
            if isinstance(nodes, dict):
                nodes = nodes.values()
            for node in nodes:
                name = _get_node_name(node).lower()
                path = ""
                if isinstance(node, dict):
                    path = (node.get("filePath") or "").lower()
                else:
                    path = (getattr(node, "filePath", "") or "").lower()
                if target_str in name or target_str in path:
                    return node.get("id") if isinstance(node, dict) else getattr(node, "id", None)
        return None

    def handle_link(self, intent: Intent, active_context: int):
        src_ref = intent.arguments.get("source") or active_context
        tgt_ref = intent.arguments.get("target")

        src_id = self._resolve_node_id(src_ref)
        tgt_id = self._resolve_node_id(tgt_ref)
        
        print(f"[IntentDispatcher] Executing link: {src_id} -> {tgt_id}")
        if not src_id or not tgt_id:
            print(f"[IntentDispatcher] Failed to resolve nodes: src_ref='{src_ref}' ({src_id}), tgt_ref='{tgt_ref}' ({tgt_id})")
        logger.info(f"[IntentDispatcher] Resolved link: source={src_id}, target={tgt_id}")
        
        if src_id and tgt_id and src_id != tgt_id:
            print(f"[IntentDispatcher] Sending IPC link request: source={src_id}, target={tgt_id}")
            self.bridge.node_ctrl.create_edge(src_id, tgt_id, edge_type="explicit")

    def handle_aperture(self, intent: Intent, active_context: int):
        val = intent.arguments.get("value")
        if val is not None:
            try:
                val_float = float(val)
                self.bridge.canvas_ctrl.set_aperture(val_float)
                logger.info(f"Set aperture to {val_float}")
            except ValueError:
                pass

    def handle_command(self, intent: Intent, active_context: int):
        cmd = intent.arguments.get("command", "")
        logger.info(f"Handling command: {cmd}")

    def handle_search(self, intent: Intent, active_context: int):
        query = intent.raw_query
        if query:
            logger.info(f"Executing search query: {query}")
            if hasattr(self.bridge, "submit_query"):
                self.bridge.submit_query(query)
            elif hasattr(self.bridge, "search_ctrl"):
                self.bridge.search_ctrl.submit_query(query)
        else:
            if hasattr(self.bridge, "clear_search"):
                self.bridge.clear_search()
            elif hasattr(self.bridge, "search_ctrl"):
                self.bridge.search_ctrl.clear_search()
