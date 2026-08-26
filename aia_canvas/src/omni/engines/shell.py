"""
Shell Engine
Handles context-aware shell execution queries prefixed with '>'
"""

import asyncio
import html
import os
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from ..base import OmniEngine, OmniResult
from ..context import OmniContext

INTERACTIVE_TUI_BINARIES = {
    "vi", "vim", "nvim", "nano", "emacs",
    "top", "htop", "btop", "less", "more",
    "ssh", "gdb", "tig",
}

ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

COLOR_MAP = {
    30: "#71717A",  # Gray / Black
    31: "#EF4444",  # Red
    32: "#10B981",  # Green
    33: "#F59E0B",  # Yellow
    34: "#60A5FA",  # Blue
    35: "#C084FC",  # Magenta
    36: "#06B6D4",  # Cyan
    37: "#E5E7EB",  # White
    90: "#71717A",  # Bright Black / Gray
    91: "#EF4444",  # Bright Red
    92: "#10B981",  # Bright Green
    93: "#F59E0B",  # Bright Yellow
    94: "#60A5FA",  # Bright Blue
    95: "#C084FC",  # Bright Magenta
    96: "#06B6D4",  # Bright Cyan
    97: "#FFFFFF",  # Bright White
}


def strip_ansi(text: str) -> str:
    """Removes unprintable ANSI terminal control escapes from text."""
    return ANSI_ESCAPE_PATTERN.sub('', text)


def ansi_to_html(text: str) -> str:
    """Converts standard 8/16 ANSI color & bold codes into HTML font/bold tags for RichText rendering."""
    if not text:
        return ""

    pos = 0
    out = []
    open_font = False
    open_bold = False

    token_pattern = re.compile(r'\x1b\[([0-9;]*)m|\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    for match in token_pattern.finditer(text):
        start, end = match.span()
        if start > pos:
            chunk = text[pos:start]
            out.append(html.escape(chunk))
        pos = end

        sgr_param = match.group(1)
        if sgr_param is not None:
            if not sgr_param:
                codes = [0]
            else:
                codes = [int(c) for c in sgr_param.split(';') if c.isdigit()]

            for code in codes:
                if code == 0:
                    if open_font:
                        out.append("</font>")
                        open_font = False
                    if open_bold:
                        out.append("</b>")
                        open_bold = False
                elif code == 1:
                    if not open_bold:
                        out.append("<b>")
                        open_bold = True
                elif code == 22:
                    if open_bold:
                        out.append("</b>")
                        open_bold = False
                elif code in COLOR_MAP:
                    if open_font:
                        out.append("</font>")
                    out.append(f'<font color="{COLOR_MAP[code]}">')
                    open_font = True
                elif code == 39:
                    if open_font:
                        out.append("</font>")
                        open_font = False

    if pos < len(text):
        out.append(html.escape(text[pos:]))

    if open_font:
        out.append("</font>")
    if open_bold:
        out.append("</b>")

    body = "".join(out)
    return f'<span style="white-space: pre; font-family: monospace;">{body}</span>'


class ShellEngine(OmniEngine):
    def __init__(self, workspace_root: Optional[str] = None, store: Optional[Any] = None):
        self.workspace_root = workspace_root or os.getcwd()
        self.store = store

    def can_handle(self, query: str, context: OmniContext) -> float:
        if query.strip().startswith(">"):
            return 1.0
        return 0.0

    def resolve_cwd(self, context: OmniContext) -> str:
        """
        Resolves working directory from context.focused_node_path or focused_node_id via store.
        Falls back to workspace_root if none provided or invalid.
        """
        path = getattr(context, "focused_node_path", None)

        if not path and context.focused_node_id and self.store:
            try:
                node_id = int(context.focused_node_id)
                if hasattr(self.store, "get_node"):
                    node = self.store.get_node(node_id)
                    if node:
                        path = getattr(node, "filePath", None) or getattr(node, "path", None)
            except (ValueError, TypeError):
                pass

        if path:
            if os.path.isfile(path):
                return os.path.dirname(path)
            elif os.path.isdir(path):
                return path

        return self.workspace_root

    def complete(
        self, query: str, cursor_pos: int = -1, context: Optional[OmniContext] = None
    ) -> List[str]:
        if cursor_pos < 0 or cursor_pos > len(query):
            cursor_pos = len(query)

        raw_prefix = query[:cursor_pos]
        sigil_idx = raw_prefix.find(">")
        if sigil_idx != -1:
            prefix_before_cmd = raw_prefix[: sigil_idx + 1]
            cmd_part = raw_prefix[sigil_idx + 1 :]
        else:
            prefix_before_cmd = ""
            cmd_part = raw_prefix

        if not cmd_part and sigil_idx == -1:
            return []

        lstripped = cmd_part.lstrip()
        leading_spaces = cmd_part[: len(cmd_part) - len(lstripped)]

        if not lstripped:
            active_token = ""
            full_prefix = prefix_before_cmd + leading_spaces
            token_index = 0
        elif cmd_part.endswith(" ") or cmd_part.endswith("\t"):
            active_token = ""
            full_prefix = prefix_before_cmd + leading_spaces + lstripped
            words = lstripped.split()
            token_index = len(words)
        else:
            tokens = lstripped.split(" ")
            active_token = tokens[-1]
            prior_cmd = lstripped[:-len(active_token)] if active_token else lstripped
            full_prefix = prefix_before_cmd + leading_spaces + prior_cmd
            token_index = len(prior_cmd.split())

        resolved_cwd = self.resolve_cwd(context or OmniContext(raw_query=query))

        candidates: List[str] = []
        is_path_target = "/" in active_token or active_token.startswith(".")

        if token_index == 0 and not is_path_target:
            # First word position: match binary executables in system PATH
            path_env = os.environ.get("PATH", "")
            path_dirs = path_env.split(os.pathsep)
            matches = set()
            for pdir in path_dirs:
                if not pdir or not os.path.isdir(pdir):
                    continue
                try:
                    with os.scandir(pdir) as entries:
                        for entry in entries:
                            if active_token and entry.name.startswith(active_token):
                                try:
                                    if os.access(entry.path, os.X_OK) and not entry.is_dir():
                                        matches.add(entry.name)
                                except OSError:
                                    continue
                except OSError:
                    continue
            candidates = sorted(list(matches))
        else:
            # Subsequent word positions or path token: match file/folder paths
            expanded_token = os.path.expanduser(active_token) if active_token.startswith("~") else active_token
            if "/" in expanded_token:
                dir_part, base_prefix = expanded_token.rsplit("/", 1)
                dir_part += "/"
            else:
                dir_part = ""
                base_prefix = expanded_token

            search_dir = os.path.join(resolved_cwd, dir_part) if not os.path.isabs(dir_part) else dir_part
            search_dir = os.path.abspath(search_dir)

            matches_list = []
            if os.path.isdir(search_dir):
                try:
                    with os.scandir(search_dir) as entries:
                        for entry in entries:
                            if entry.name.startswith(base_prefix):
                                if entry.name.startswith(".") and not base_prefix.startswith("."):
                                    continue
                                is_dir = False
                                try:
                                    is_dir = entry.is_dir(follow_symlinks=True)
                                except OSError:
                                    pass
                                matched_name = dir_part + entry.name + ("/" if is_dir else "")
                                matches_list.append(matched_name)
                except OSError:
                    pass
            candidates = sorted(matches_list)

        suffix = query[cursor_pos:]
        return [f"{full_prefix}{cand}{suffix}" for cand in candidates]

    async def execute(
        self, query: str, context: OmniContext
    ) -> AsyncIterator[OmniResult]:
        cmd_text = query.strip()
        if cmd_text.startswith(">"):
            cmd_text = cmd_text[1:].strip()

        if not cmd_text:
            return

        if re.match(r'^ls\b', cmd_text) and "--color" not in cmd_text:
            cmd_text = re.sub(r'^ls\b', 'ls --color=always', cmd_text, count=1)

        resolved_cwd = self.resolve_cwd(context)

        # 1. Interactive TUI Safety Guardrail
        tokens = cmd_text.split()
        primary_token = os.path.basename(tokens[0]) if tokens else ""
        if primary_token in ("sudo", "env", "time") and len(tokens) > 1:
            primary_token = os.path.basename(tokens[1])

        if primary_token in INTERACTIVE_TUI_BINARIES:
            tui_msg = "[Interactive TUI session detected. Launch in external terminal via node action.]"
            yield OmniResult(
                id="shell_tui_warn",
                title=tui_msg,
                category="shell",
                score=1.0,
                metadata={
                    "command": cmd_text,
                    "cwd": resolved_cwd,
                    "stream": "system",
                    "line": tui_msg,
                    "color": "amber",
                    "is_tui_warning": True,
                },
                icon="terminal",
            )
            return

        # 2. Execution & Telemetry Tracking
        start_time = time.perf_counter()

        try:
            env_override = os.environ.copy()
            env_override["CLICOLOR_FORCE"] = "1"
            env_override["FORCE_COLOR"] = "1"
            env_override["COLORTERM"] = "truecolor"

            proc = await asyncio.create_subprocess_shell(
                cmd_text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=resolved_cwd,
                env=env_override,
            )

            queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

            async def read_stream(stream, stream_type: str):
                if not stream:
                    return
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_str = line.decode("utf-8", errors="replace").rstrip("\r\n")
                    cleaned_line = ansi_to_html(line_str)
                    await queue.put((stream_type, cleaned_line))

            stdout_task = asyncio.create_task(read_stream(proc.stdout, "stdout"))
            stderr_task = asyncio.create_task(read_stream(proc.stderr, "stderr"))

            async def wait_done():
                await asyncio.gather(stdout_task, stderr_task)
                await proc.wait()
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                exit_code = proc.returncode if proc.returncode is not None else 0
                await queue.put(("DONE", f"{exit_code}:{duration_ms}"))

            done_task = asyncio.create_task(wait_done())

            line_count = 0
            while True:
                stream_type, text = await queue.get()
                if stream_type == "DONE":
                    parts = text.split(":")
                    exit_code = int(parts[0])
                    duration_ms = int(parts[1]) if len(parts) > 1 else 0
                    if exit_code != 0:
                        symbol = "✗"
                        footer_text = f"{symbol} exit {exit_code} • {resolved_cwd}"

                        line_count += 1
                        yield OmniResult(
                            id=f"shell_out_{line_count}",
                            title=footer_text,
                            category="shell",
                            score=1.0,
                            metadata={
                                "command": cmd_text,
                                "cwd": resolved_cwd,
                                "stream": "system",
                                "line": footer_text,
                                "exit_code": exit_code,
                                "duration_ms": duration_ms,
                            },
                            icon="terminal",
                        )
                    break

                line_count += 1
                yield OmniResult(
                    id=f"shell_out_{line_count}",
                    title=text,
                    category="shell",
                    score=1.0,
                    metadata={
                        "command": cmd_text,
                        "cwd": resolved_cwd,
                        "stream": stream_type,
                        "line": text,
                        "line_number": line_count,
                    },
                    icon="terminal",
                )
        except Exception as err:
            yield OmniResult(
                id="shell_err",
                title=f"Execution error: {err}",
                category="shell",
                score=1.0,
                metadata={
                    "command": cmd_text,
                    "cwd": resolved_cwd,
                    "stream": "stderr",
                    "line": str(err),
                },
                icon="terminal",
            )

    def get_mode_metadata(self) -> Dict[str, Any]:
        return {
            "mode": "shell",
            "glow_color": "#F59E0B",
            "glyph": ">_",
            "placeholder": "Run command...",
            "icon": "terminal",
        }

