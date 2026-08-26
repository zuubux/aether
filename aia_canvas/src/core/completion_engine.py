from typing import Any

def _get_node_name(node: Any) -> str:
    if isinstance(node, dict):
        return node.get("displayTitle") or node.get("display_title") or node.get("fileName") or node.get("label") or node.get("file_name") or ""
    return getattr(node, "displayTitle", "") or getattr(node, "display_title", "") or getattr(node, "fileName", "") or getattr(node, "label", "") or getattr(node, "file_name", "")

class CompletionEngine:
    STATIC_COMMANDS = ["/link", "/tag", "/re-embed", "/cluster", "/isolate", "/export"]
    STATIC_APERTURE = ["> md", "> pdf", "> images", "> code", "> dense", "> wide", "> 0.2", "> 0.5", "> 0.8", "> 1.0"]

    def __init__(self, bridge):
        self.bridge = bridge
        import os
        from omni.engines.shell import ShellEngine
        store = getattr(bridge, "store", None)
        workspace_root = getattr(bridge, "workspace_root", None) or os.getcwd()
        self.shell_engine = ShellEngine(workspace_root=workspace_root, store=store)

    def _extract_name(self, node: Any) -> str:
        if isinstance(node, dict):
            return (
                node.get("displayTitle")
                or node.get("display_title")
                or node.get("fileName")
                or node.get("file_name")
                or node.get("label")
                or node.get("title")
                or (node.get("path", "").split("/")[-1] if node.get("path") else "")
                or ""
            )
        for attr in ["displayTitle", "display_title", "fileName", "file_name", "label", "title", "name", "path"]:
            val = getattr(node, attr, None)
            if val:
                val_str = str(val)
                return val_str.rsplit("/", 1)[-1] if "/" in val_str else val_str
        return ""

    def _get_all_nodes(self):
        if hasattr(self.bridge, "node_controller") and hasattr(self.bridge.node_controller, "nodes"):
            return list(self.bridge.node_controller.nodes.values())
        if hasattr(self.bridge, "store") and hasattr(self.bridge.store, "get_all_nodes"):
            return self.bridge.store.get_all_nodes()
        return []

    def get_completions(self, text: str, cursor_pos: int) -> list:
        if not text:
            return []

        prefix = text[:cursor_pos] if (cursor_pos >= 0 and cursor_pos <= len(text)) else text
        print(f"[CompletionEngine] Query: '{text}', Prefix: '{prefix}'")

        if prefix.strip().startswith(">"):
            from omni.context import OmniContext
            focused_id = str(getattr(self.bridge, "selectedNodeId", 0) or 0)
            ctx = OmniContext(raw_query=text, focused_node_id=focused_id)
            return self.shell_engine.complete(text, cursor_pos, ctx)

        # Static commands
        if prefix.startswith("/") and " " not in prefix:
            matches = [cmd + " " for cmd in self.STATIC_COMMANDS if cmd.startswith(prefix)]
            print(f"[CompletionEngine] Static matches: {matches}")
            return matches

        # Target completion
        target_token = None
        base_prefix = ""
        if prefix.startswith("/link "):
            base_prefix = "/link "
            target_token = prefix[6:].strip().lower()
        elif "@" in prefix:
            base_prefix, target_token = prefix.rsplit("@", 1)
            base_prefix += "@"
            target_token = target_token.strip().lower()
        elif "&" in prefix:
            base_prefix, target_token = prefix.rsplit("&", 1)
            base_prefix += "& "
            target_token = target_token.strip().lower()

        if target_token is not None:
            active_id = getattr(self.bridge, "selectedNodeId", 0) or 0
            nodes = self._get_all_nodes()
            print(f"[CompletionEngine] Scanning {len(nodes)} nodes for token '{target_token}'")
            prefix_matches = []
            substring_matches = []
            
            for node in nodes:
                n_id = node.get("id") if isinstance(node, dict) else getattr(node, "id", None)
                if active_id and n_id == active_id:
                    continue
                name = self._extract_name(node)
                if not name:
                    continue
                    
                name_lower = name.lower()
                if name_lower.startswith(target_token):
                    prefix_matches.append(base_prefix + name)
                elif target_token in name_lower:
                    substring_matches.append(base_prefix + name)
                    
            # If we have direct prefix matches, prioritize them strictly
            results = prefix_matches if prefix_matches else substring_matches
            print(f"[CompletionEngine] Node matches: {results}")
            return results[:8]

        return []
