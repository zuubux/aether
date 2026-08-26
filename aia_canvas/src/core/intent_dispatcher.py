"""
Intent Dispatcher
Dispatches parsed natural-language/operator intents directly to canonical controllers.
"""

import logging
from typing import Any, Callable, Dict, Optional

from core.intent_grammar import Intent, IntentOperator, parse_intent

def _get_node_name(node: Any) -> str:
    """Extract display title or file name from a node model instance or dictionary.

    Args:
        node: Node instance or dictionary representation.

    Returns:
        str: Display title, label, or file name.
    """
    if isinstance(node, dict):
        return node.get("displayTitle") or node.get("display_title") or node.get("fileName") or node.get("label") or node.get("file_name") or ""
    return getattr(node, "displayTitle", "") or getattr(node, "display_title", "") or getattr(node, "fileName", "") or getattr(node, "label", "") or getattr(node, "file_name", "")

logger = logging.getLogger("aia_canvas.intent_dispatcher")


class IntentDispatcher:
    """Dispatches parsed user intents directly to active controllers on the CanvasBridge."""

    def __init__(self, bridge: Any):
        """Initialize the intent dispatcher with a reference to the main CanvasBridge.

        Args:
            bridge: The CanvasBridge instance owning controller routes.
        """
        self.bridge = bridge
        self.handlers: Dict[IntentOperator, Callable[[Intent, int], None]] = {
            IntentOperator.NAVIGATE: self.handle_navigate,
            IntentOperator.LINK: self.handle_link,
            IntentOperator.APERTURE: self.handle_aperture,
            IntentOperator.SEARCH: self.handle_search,
            IntentOperator.COMMAND: self.handle_command,
        }

    def dispatch(self, raw_text: str, context_override: Optional[int] = None) -> None:
        """Parse raw query text into an Intent and dispatch to the matching handler.

        Args:
            raw_text: Raw query or action command string.
            context_override: Optional explicit context node ID override.
        """
        intent = parse_intent(raw_text)
        active_context = self.resolve_context(context_override)
        
        handler = self.handlers.get(intent.operator)
        if handler:
            handler(intent, active_context)
        else:
            logger.warning(f"No handler registered for intent operator: {intent.operator}")

    def resolve_context(self, context_override: Optional[int]) -> int:
        """Resolve active node context ID for intent execution.

        Args:
            context_override: Explicit node ID provided by caller, if any.

        Returns:
            int: Resolved node ID, defaulting to selected node ID or 0 (global).
        """
        if context_override is not None:
            return context_override
        selected_id = getattr(self.bridge.node_ctrl, "selectedNodeId", 0) if hasattr(self.bridge, "node_ctrl") else getattr(self.bridge, "selectedNodeId", 0)
        return selected_id if selected_id > 0 else 0

    def handle_navigate(self, intent: Intent, active_context: int) -> None:
        """Execute navigate intent by delegating directly to node_ctrl.

        Args:
            intent: Parsed intent containing target argument.
            active_context: Resolved context node ID.
        """
        target = intent.arguments.get("target")
        if target:
            logger.info(f"Navigating to {target}")
            self.bridge.node_ctrl.navigate_to_link(target)

    def _resolve_node_id(self, target_ref: Any) -> Optional[int]:
        """Resolve node ID from integer ID or fuzzy text match on node names/paths.

        Args:
            target_ref: Integer node ID or string query match.

        Returns:
            Optional[int]: Matched node ID if found, otherwise None.
        """
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

    def handle_link(self, intent: Intent, active_context: int) -> None:
        """Execute explicit link creation between source and target nodes via node_ctrl.

        Args:
            intent: Parsed intent containing source and target references.
            active_context: Resolved context node ID.
        """
        src_ref = intent.arguments.get("source") or active_context
        tgt_ref = intent.arguments.get("target")

        src_id = self._resolve_node_id(src_ref)
        tgt_id = self._resolve_node_id(tgt_ref)
        
        logger.info(f"Resolved link: source={src_id}, target={tgt_id}")
        if src_id and tgt_id and src_id != tgt_id:
            logger.info(f"Sending IPC link request: source={src_id}, target={tgt_id}")
            self.bridge.node_ctrl.create_edge(src_id, tgt_id, edge_type="explicit")

    def handle_aperture(self, intent: Intent, active_context: int) -> None:
        """Execute aperture adjustment intent directly via canvas_ctrl.

        Args:
            intent: Parsed intent containing numerical aperture value.
            active_context: Resolved context node ID.
        """
        val = intent.arguments.get("value")
        if val is not None:
            try:
                val_float = float(val)
                self.bridge.canvas_ctrl.set_aperture(val_float)
                logger.info(f"Set aperture to {val_float}")
            except ValueError:
                pass

    def handle_command(self, intent: Intent, active_context: int) -> None:
        """Execute system command intent.

        Args:
            intent: Parsed intent containing command string.
            active_context: Resolved context node ID.
        """
        cmd = intent.arguments.get("command", "")
        logger.info(f"Handling command: {cmd}")

    def handle_search(self, intent: Intent, active_context: int) -> None:
        """Execute search or search clear intent directly via search_ctrl.

        Args:
            intent: Parsed intent containing raw query string.
            active_context: Resolved context node ID.
        """
        query = intent.raw_query
        if query:
            logger.info(f"Executing search query: {query}")
            self.bridge.search_ctrl.submit_query(query)
        else:
            self.bridge.search_ctrl.clear_search()
