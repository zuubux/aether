"""
Unit tests for ShellEngine.
Verifies prefix scoring, mode metadata, contextual CWD resolution, empty query guards,
and non-blocking subprocess stdout/stderr streaming.
"""

import asyncio
import os
import tempfile
import pytest
from omni import OmniContext, ShellEngine


class MockNode:
    def __init__(self, node_id: int, file_path: str):
        self.id = node_id
        self.filePath = file_path


class MockStore:
    def __init__(self, nodes=None):
        self._nodes = {n.id: n for n in (nodes or [])}

    def get_node(self, node_id: int):
        return self._nodes.get(node_id)


def test_shell_engine_prefix_scoring_and_metadata():
    engine = ShellEngine(workspace_root="/tmp")
    ctx = OmniContext(raw_query="> ls -la")

    assert engine.can_handle("> ls -la", ctx) == 1.0
    assert engine.can_handle(" > pwd", ctx) == 1.0
    assert engine.can_handle("ls -la", ctx) == 0.0

    meta = engine.get_mode_metadata()
    assert meta["mode"] == "shell"
    assert meta["glow_color"] == "#F59E0B"
    assert meta["glyph"] == ">_"
    assert meta["placeholder"] == "Run command..."
    assert meta["icon"] == "terminal"


def test_shell_engine_cwd_resolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        sub_dir = os.path.join(tmpdir, "subdir")
        os.makedirs(sub_dir, exist_ok=True)
        file_path = os.path.join(sub_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("hello")

        engine = ShellEngine(workspace_root=tmpdir)

        # 1. Fallback to workspace root
        ctx_default = OmniContext(raw_query="> pwd")
        assert engine.resolve_cwd(ctx_default) == tmpdir

        # 2. Focused node file path -> Parent directory
        ctx_file = OmniContext(raw_query="> pwd", focused_node_path=file_path)
        assert engine.resolve_cwd(ctx_file) == sub_dir

        # 3. Focused node directory path -> Same directory
        ctx_dir = OmniContext(raw_query="> pwd", focused_node_path=sub_dir)
        assert engine.resolve_cwd(ctx_dir) == sub_dir

        # 4. Focused node ID lookup via Store
        store = MockStore([MockNode(101, file_path)])
        engine_with_store = ShellEngine(workspace_root=tmpdir, store=store)
        ctx_id = OmniContext(raw_query="> pwd", focused_node_id="101")
        assert engine_with_store.resolve_cwd(ctx_id) == sub_dir


@pytest.mark.anyio
async def test_shell_engine_execution_stdout():
    engine = ShellEngine()
    ctx = OmniContext(raw_query="> echo hello_aether")

    results = [res async for res in engine.execute("> echo hello_aether", ctx)]
    assert len(results) >= 1
    lines = [r.title for r in results]
    assert any("hello_aether" in line for line in lines)
    first = results[0]
    assert first.category == "shell"
    assert first.metadata["stream"] == "stdout"
    assert first.metadata["command"] == "echo hello_aether"


@pytest.mark.anyio
async def test_shell_engine_execution_stderr():
    engine = ShellEngine()
    ctx = OmniContext(raw_query="> echo err_msg >&2")

    results = [res async for res in engine.execute("> echo err_msg >&2", ctx)]
    assert len(results) >= 1
    lines = [r.title for r in results]
    assert any("err_msg" in line for line in lines)
    first = results[0]
    assert first.category == "shell"
    assert first.metadata["stream"] == "stderr"


@pytest.mark.anyio
async def test_shell_engine_empty_query():
    engine = ShellEngine()
    for empty_cmd in [">", "> ", "  >   "]:
        ctx = OmniContext(raw_query=empty_cmd)
        results = [res async for res in engine.execute(empty_cmd, ctx)]
        assert results == []


def test_shell_engine_binary_completion():
    engine = ShellEngine()
    # "echo" is almost universally present on Unix
    completions = engine.complete("> ec", cursor_pos=4)
    assert any("echo" in c for c in completions)
    assert all(c.startswith("> ") for c in completions)


def test_shell_engine_path_completion():
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "alpha_file.txt")
        file2 = os.path.join(tmpdir, "beta_file.txt")
        dir1 = os.path.join(tmpdir, "gamma_dir")
        with open(file1, "w") as f:
            f.write("a")
        with open(file2, "w") as f:
            f.write("b")
        os.makedirs(dir1, exist_ok=True)

        engine = ShellEngine(workspace_root=tmpdir)
        ctx = OmniContext(raw_query="> cat al")

        # First word is command ("cat"), second word ("al") should match files in tmpdir
        completions_al = engine.complete("> cat al", cursor_pos=8, context=ctx)
        assert completions_al == ["> cat alpha_file.txt"]

        # Directories should end with a trailing slash
        completions_ga = engine.complete("> cat ga", cursor_pos=8, context=ctx)
        assert completions_ga == ["> cat gamma_dir/"]

        # Non-matching token returns empty list
        completions_none = engine.complete("> cat non_existent_foo", cursor_pos=21, context=ctx)
        assert completions_none == []
@pytest.mark.anyio
async def test_shell_engine_tui_interception():
    engine = ShellEngine()
    tui_cmds = ["vi", "vim", "nvim", "nano", "emacs", "top", "htop", "btop", "less", "more", "ssh", "gdb", "tig", "sudo vim /etc/hosts"]

    for cmd in tui_cmds:
        query = f"> {cmd}"
        ctx = OmniContext(raw_query=query)
        results = [res async for res in engine.execute(query, ctx)]

        assert len(results) == 1
        res = results[0]
        assert res.category == "shell"
        assert res.title == "[Interactive TUI session detected. Launch in external terminal via node action.]"
        assert res.metadata["stream"] == "system"
        assert res.metadata["color"] == "amber"
        assert res.metadata["is_tui_warning"] is True


@pytest.mark.anyio
async def test_shell_engine_ansi_formatting():
    from omni.engines.shell import ansi_to_html

    # Direct unit test of ansi_to_html converter
    raw = "\x1b[31mRED\x1b[0m \x1b[1mBOLD\x1b[22m"
    converted = ansi_to_html(raw)
    assert '<font color="#EF4444">RED</font>' in converted
    assert '<b>BOLD</b>' in converted

    # Test mapping of standard palette colors
    assert '<font color="#10B981">GREEN</font>' in ansi_to_html("\x1b[32mGREEN\x1b[0m")
    assert '<font color="#F59E0B">YELLOW</font>' in ansi_to_html("\x1b[33mYELLOW\x1b[0m")
    assert '<font color="#60A5FA">BLUE</font>' in ansi_to_html("\x1b[34mBLUE\x1b[0m")
    assert '<font color="#C084FC">MAGENTA</font>' in ansi_to_html("\x1b[35mMAGENTA\x1b[0m")
    assert '<font color="#06B6D4">CYAN</font>' in ansi_to_html("\x1b[36mCYAN\x1b[0m")
    assert '<font color="#71717A">GRAY</font>' in ansi_to_html("\x1b[30mGRAY\x1b[0m")

    # Integration via execute
    engine = ShellEngine()
    query = "> echo -e '\\033[31mANSI_RED_TEXT\\033[0m'"
    ctx = OmniContext(raw_query=query)

    results = [res async for res in engine.execute(query, ctx)]
    stdout_lines = [r.title for r in results if r.metadata.get("stream") == "stdout"]

    assert len(stdout_lines) == 1
    assert '<font color="#EF4444">ANSI_RED_TEXT</font>' in stdout_lines[0]


@pytest.mark.anyio
async def test_shell_engine_subprocess_forced_color_env():
    engine = ShellEngine()
    query = "> echo $CLICOLOR_FORCE:$FORCE_COLOR:$COLORTERM"
    ctx = OmniContext(raw_query=query)

    results = [res async for res in engine.execute(query, ctx)]
    stdout_lines = [r.title for r in results if r.metadata.get("stream") == "stdout"]

    assert len(stdout_lines) == 1
    assert "1:1:truecolor" in stdout_lines[0]


@pytest.mark.anyio
async def test_shell_engine_footer_suppression_and_error_emission():
    engine = ShellEngine(workspace_root="/tmp")

    # 1. Success execution (exit code 0) must suppress system status footer
    ctx_success = OmniContext(raw_query="> echo test_success")
    results_success = [res async for res in engine.execute("> echo test_success", ctx_success)]
    system_results_success = [r for r in results_success if r.metadata.get("stream") == "system"]
    assert len(system_results_success) == 0
    assert len(results_success) == 1
    assert "test_success" in results_success[0].title


@pytest.mark.anyio
async def test_shell_engine_ls_color_injection():
    engine = ShellEngine(workspace_root="/tmp")
    ctx = OmniContext(raw_query="> ls /tmp")

    results = [res async for res in engine.execute("> ls /tmp", ctx)]
    stdout_lines = [r for r in results if r.metadata.get("stream") == "stdout"]
    if stdout_lines:
        assert stdout_lines[0].metadata["command"] == "ls --color=always /tmp"

    # 2. Failure execution (exit_code != 0) must emit subtle error status footer
    ctx_fail = OmniContext(raw_query="> ls /nonexistent_path_aether_test")
    results_fail = [res async for res in engine.execute("> ls /nonexistent_path_aether_test", ctx_fail)]
    system_results_fail = [r for r in results_fail if r.metadata.get("stream") == "system"]
    assert len(system_results_fail) == 1

    footer = system_results_fail[0]
    assert footer.category == "shell"
    assert footer.metadata["stream"] == "system"
    assert footer.metadata["exit_code"] != 0
    assert "duration_ms" in footer.metadata
    assert "✗ exit" in footer.title
    assert "/tmp" in footer.title
