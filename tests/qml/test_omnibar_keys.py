"""
QML Component & Key Interaction Tests for OmniBar.
Tests Tab/Shift+Tab traversal, shelf expand/collapse (Up/Down arrow), Enter/Esc keys,
glass readability, placeholder contrast, and mode badges/sigils.
"""

import time
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtQml import QQmlComponent, QQmlExpression

from controllers.conversation_controller import ConversationController


def test_omnibar_glass_readability_and_placeholder(qapp, qml_engine, canvas_qml_root):
    # 1. Verify Theme.surfaceGlass token value
    theme_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Theme.qml")
    assert theme_comp.status() == QQmlComponent.Status.Ready, f"Theme compilation failed: {theme_comp.errors()}"
    theme_inst = theme_comp.create()

    surface_glass_color = theme_inst.property("surfaceGlass")
    assert surface_glass_color is not None

    # 2. Verify OmniBar barShell color property matches Theme.surfaceGlass
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    assert omni_bar is not None
    bar_shell = omni_bar.findChild(object, "barShell")
    assert bar_shell is not None

    bar_color = bar_shell.property("color")
    assert bar_color.name() == surface_glass_color.name()

    # Verify shellDrawerBg & dialogueDrawerBg use transparent fill to share surfaceGlass
    shell_drawer_bg = omni_bar.findChild(object, "shellDrawerBg")
    assert shell_drawer_bg is not None
    drawer_bg_color = shell_drawer_bg.property("color")
    assert drawer_bg_color.alpha() == 0 or drawer_bg_color.name() == "#00000000"

    dialogue_drawer_bg = omni_bar.findChild(object, "dialogueDrawerBg")
    assert dialogue_drawer_bg is not None
    dialogue_bg_color = dialogue_drawer_bg.property("color")
    assert dialogue_bg_color.alpha() == 0 or dialogue_bg_color.name() == "#00000000"

    # 3. Verify Placeholder Contrast & Primary Text Color
    input_field = omni_bar.findChild(object, "inputField")
    assert input_field is not None
    placeholder_text = input_field.findChild(object, "customPlaceholderText")
    assert placeholder_text is not None

    assert placeholder_text.property("color").name() == theme_inst.property("textMuted").name()


def test_omnibar_key_events_and_shelf_expansion(qapp, qml_engine, canvas_qml_root):
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")
    ribbon_container = omni_bar.findChild(object, "ribbonContainer")

    omni_bar.open()
    qapp.processEvents()

    # Populate results list
    results = [
        {"id": "1", "node_id": "1", "title": "report.pdf", "archetype": "document"},
        {"id": "2", "node_id": "2", "title": "analytics.py", "archetype": "code"},
        {"id": "3", "node_id": "3", "title": "image.png", "archetype": "image"},
    ]
    omni_bar.setProperty("resultsList", results)
    omni_bar.setProperty("currentRibbonIndex", 0)
    qapp.processEvents()

    assert omni_bar.property("currentRibbonIndex") == 0

    # 1. Test Tab cycling
    tab_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(input_field, tab_evt)
    qapp.processEvents()
    assert omni_bar.property("currentRibbonIndex") == 1

    # Shift+Tab cycling back
    shift_tab_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)
    qapp.sendEvent(input_field, shift_tab_evt)
    qapp.processEvents()
    assert omni_bar.property("currentRibbonIndex") == 0

    # 2. Test Shelf expansion state transitions (Up / Down arrow)
    assert not omni_bar.property("shelfExpanded")

    # Press Up Arrow to expand
    up_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(input_field, up_evt)
    for _ in range(6):
        time.sleep(0.02)
        qapp.processEvents()

    assert omni_bar.property("shelfExpanded")
    assert abs(ribbon_container.property("height") - 240) < 5.0

    # Down Arrow to navigate/collapse
    down_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(input_field, down_evt)
    qapp.processEvents()
    qapp.sendEvent(input_field, down_evt)
    for _ in range(10):
        time.sleep(0.02)
        qapp.processEvents()

    assert not omni_bar.property("shelfExpanded")
    assert abs(ribbon_container.property("height") - 52) < 5.0

    # 3. Test Esc key search dismissal
    esc_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(input_field, esc_evt)
    qapp.processEvents()
    qapp.sendEvent(input_field, esc_evt)
    qapp.processEvents()

    assert not omni_bar.property("active")


def test_omnibar_mode_badges_and_sigils(qapp, qml_engine, canvas_qml_root):
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    prefix_icon = omni_bar.findChild(object, "prefixIcon")
    mode_badge = omni_bar.findChild(object, "modeBadge")
    mode_text = omni_bar.findChild(object, "modeText")
    mode_sigil = omni_bar.findChild(object, "modeSigil")
    input_field = omni_bar.findChild(object, "inputField")

    omni_bar.open()
    for _ in range(10):
        time.sleep(0.02)
        qapp.processEvents()

    # Standard query
    input_field.setProperty("text", "hello world")
    qapp.processEvents()
    assert prefix_icon.property("visible") is True

    # '>' Shell Execution mode
    input_field.setProperty("text", "> git status")
    qapp.processEvents()
    assert prefix_icon.property("visible") is False
    assert mode_badge.property("visible") is True
    assert mode_text.property("text") == "CLI"
    assert mode_badge.property("color").name().lower() == "#f59e0b"
    assert mode_sigil.property("text") == ">"

    # '?' AI Reasoning mode
    search_shelf = canvas_qml_root.findChild(object, "searchShelf")
    bar_shell = omni_bar.findChild(object, "barShell")
    input_field.setProperty("text", "? explain quantum")
    for _ in range(12):
        time.sleep(0.02)
        qapp.processEvents()
    assert prefix_icon.property("visible") is False
    assert mode_badge.property("visible") is True
    assert omni_bar.property("isConversationalMode") is True
    assert mode_text.property("text") == "AI"
    assert mode_badge.property("color").name().lower() == "#38bdf8"
    assert bar_shell.property("borderColor").name().lower() == "#38bdf8"
    assert mode_sigil.property("text") == "?"
    if search_shelf:
        assert search_shelf.property("opacity") == 0.0

    # Test Gemini provider badge dynamic identity
    omni_bar.setProperty("activeProvider", "gemini")
    qapp.processEvents()
    assert mode_text.property("text") == "GEM"
    omni_bar.setProperty("activeProvider", "")
    qapp.processEvents()
    assert mode_text.property("text") == "AI"

    # '/' System Command mode
    input_field.setProperty("text", "/reset")
    qapp.processEvents()
    assert prefix_icon.property("visible") is False
    assert mode_badge.property("visible") is True
    assert mode_text.property("text") == "SET"
    assert mode_badge.property("color").name().lower() == "#10b981"
    assert mode_sigil.property("text") == "/"

    theme_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Theme.qml")
    theme_inst = theme_comp.create()
    assert input_field.property("color").name() == theme_inst.property("textPrimary").name()


def test_omnibar_shell_drawer_rendering(qapp, qml_engine, canvas_qml_root):
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")
    ribbon_container = omni_bar.findChild(object, "ribbonContainer")
    shell_drawer = omni_bar.findChild(object, "shellDrawer")
    bar_shell = omni_bar.findChild(object, "barShell")
    internal_divider = omni_bar.findChild(object, "internalDivider")
    system_status_footer = omni_bar.findChild(object, "systemStatusFooter")

    omni_bar.open()
    for _ in range(12):
        time.sleep(0.02)
        qapp.processEvents()

    # Enter shell query
    input_field.setProperty("text", "> git status")
    results = [
        {"id": "shell_out_1", "title": "On branch main", "stream": "stdout"},
        {"id": "shell_out_2", "title": "nothing to commit", "stream": "stdout"},
        {"id": "shell_sys_1", "title": "✗ exit 1 • /home/nic", "stream": "system", "exit_code": 1},
    ]
    omni_bar.setProperty("resultsList", results)
    for _ in range(12):
        time.sleep(0.02)
        qapp.processEvents()

    # Ribbon container suppressed in shell mode
    assert ribbon_container.property("visible") is False

    # Shell drawer visible and rendering results in unified monolithic slate
    assert shell_drawer is not None
    assert shell_drawer.property("visible") is True
    border_col = bar_shell.property("borderColor")
    assert border_col is not None and border_col.name().lower() == "#f59e0b"
    assert internal_divider is not None
    assert internal_divider.property("visible") is True
    assert system_status_footer is not None
    assert system_status_footer.property("visible") is True

    # Test Esc key clears and dismisses
    esc_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(input_field, esc_evt)
    qapp.processEvents()
    assert input_field.property("text") == ""

    qapp.sendEvent(input_field, esc_evt)
    qapp.processEvents()
    assert omni_bar.property("active") is False
    assert shell_drawer.property("visible") is False


def test_omnibar_shell_no_premature_exec_and_tab_completion(qapp, qml_engine, canvas_qml_root, mock_bridge):
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")

    submitted_queries = []
    def on_query(q):
        submitted_queries.append(q)

    omni_bar.querySubmitted.connect(on_query)

    omni_bar.open()
    for _ in range(5):
        time.sleep(0.01)
        qapp.processEvents()

    # 1. Verify typing shell query (> ec) does not trigger premature execution
    input_field.setProperty("text", "> ec")
    input_field.setProperty("cursorPosition", 4)
    qapp.processEvents()
    time.sleep(0.2)  # Wait longer than 150ms debounce
    qapp.processEvents()

    # Verify no search query submitted during typing
    assert len(submitted_queries) == 0

    # 2. Press Tab in shell mode -> expands > ec to > echo
    tab_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(input_field, tab_evt)
    qapp.processEvents()

    assert input_field.property("text") == "> echo"

    # 3. Press Enter -> triggers single execution on Enter
    enter_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(input_field, enter_evt)
    qapp.processEvents()

    assert input_field.property("text") == "> echo"
    assert input_field.property("selectedText") == "echo"


def test_omnibar_shell_select_on_submit_and_command_history(qapp, qml_engine, canvas_qml_root, mock_bridge):
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")

    omni_bar.open()
    qapp.processEvents()

    enter_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    up_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
    down_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)

    # 1. Type and submit first command (> echo)
    input_field.setProperty("text", "> echo")
    qapp.processEvents()

    qapp.sendEvent(input_field, enter_evt)
    qapp.processEvents()

    # Check select-on-submit & history
    assert input_field.property("text") == "> echo"
    assert input_field.property("selectedText") == "echo"
    history = omni_bar.property("shellHistory").toVariant()
    assert len(history) >= 1
    assert history[-1] == "> echo"
    assert omni_bar.property("shellHistoryIndex") == -1

    # 2. Submit second command (> git status)
    input_field.setProperty("text", "> git status")
    qapp.processEvents()

    qapp.sendEvent(input_field, enter_evt)
    qapp.processEvents()

    assert input_field.property("text") == "> git status"
    assert input_field.property("selectedText") == "git status"
    history = omni_bar.property("shellHistory").toVariant()
    assert len(history) >= 2
    assert history[-1] == "> git status"
    assert omni_bar.property("shellHistoryIndex") == -1

    # 3. Test Up Arrow navigation (moves backward through history)
    # Press Up -> latest entry ("> git status")
    qapp.sendEvent(input_field, up_evt)
    qapp.processEvents()
    h_idx_latest = len(omni_bar.property("shellHistory").toVariant()) - 1
    assert omni_bar.property("shellHistoryIndex") == h_idx_latest
    assert input_field.property("text") == "> git status"

    # Press Up -> older entry ("> echo")
    qapp.sendEvent(input_field, up_evt)
    qapp.processEvents()
    assert omni_bar.property("shellHistoryIndex") == h_idx_latest - 1
    assert input_field.property("text") == "> echo"

    # 4. Test Down Arrow navigation (moves forward through history)
    # Press Down -> newer entry ("> git status")
    qapp.sendEvent(input_field, down_evt)
    qapp.processEvents()
    assert omni_bar.property("shellHistoryIndex") == h_idx_latest
    assert input_field.property("text") == "> git status"

    # Press Down again -> past latest entry -> returns to blank prompt "> "
    qapp.sendEvent(input_field, down_evt)
    qapp.processEvents()
    assert omni_bar.property("shellHistoryIndex") == -1
    assert input_field.property("text") == "> "


def test_omnibar_outer_border_and_viewport_clip(qapp, qml_engine, canvas_qml_root):
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    bar_shell = omni_bar.findChild(object, "barShell")
    bar_viewport = omni_bar.findChild(object, "barShellViewport")

    assert bar_shell is not None
    assert bar_shell.property("clip") is False
    assert bar_shell.property("radius") == 12

    assert bar_viewport is not None
    assert bar_viewport.property("clip") is True

    # Verify bottom anchor margin is 36
    expr = QQmlExpression(qml_engine.rootContext(), omni_bar, "anchors.bottomMargin")
    val, undef = expr.evaluate()
    assert not undef
    assert val == 36


def test_omnibar_conversational_drawer_rendering(qapp, qml_engine, canvas_qml_root):
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")
    bar_shell = omni_bar.findChild(object, "barShell")
    search_shelf = canvas_qml_root.findChild(object, "searchShelf")
    dialogue_drawer = omni_bar.findChild(object, "dialogueDrawer")
    provider_pill = omni_bar.findChild(object, "providerHeaderPill")
    ribbon_container = omni_bar.findChild(object, "ribbonContainer")

    omni_bar.open()
    qapp.processEvents()

    # 1. Type conversational query
    input_field.setProperty("text", "? Explain Aether")
    for _ in range(12):
        time.sleep(0.02)
        qapp.processEvents()

    assert omni_bar.property("isConversationalMode") is True
    assert bar_shell.property("borderColor").name().lower() == "#38bdf8"
    assert search_shelf.property("opacity") == 0.0
    assert ribbon_container.property("visible") is False

    # 2. Simulate streaming results arriving into resultsList
    stream_results = [
        {"title": "**Aether** is a high-performance spatial interface architecture.\n\n"},
        {"title": "It combines PyQt6, QML, and numerical graph dynamics."}
    ]
    omni_bar.setProperty("resultsList", stream_results)
    for _ in range(12):
        time.sleep(0.02)
        qapp.processEvents()

    # 3. Verify dialogue output drawer opens and expands
    assert omni_bar.property("showDialogueOutput") is True
    assert dialogue_drawer.property("visible") is True
    assert omni_bar.property("dialogueDrawerHeight") > 0
    assert omni_bar.property("height") > 48

    # 4. Verify Provider Badge as Top-Right Header Pill
    provider_pill = omni_bar.findChild(object, "providerHeaderPill")
    assert provider_pill is not None
    assert provider_pill.property("opacity") == 0.3
    assert provider_pill.property("radius") == 4

    name_text = omni_bar.findChild(object, "nameText")
    assert name_text is not None
    assert name_text.property("text") == "Flash"
    assert name_text.property("font").pixelSize() == 10

    glyph_text = omni_bar.findChild(object, "glyphText")
    assert glyph_text is not None
    assert glyph_text.property("text") == "✦"
    assert glyph_text.property("font").pixelSize() == 11

    # 5. Verify status indicator dot and scrollview properties
    status_dot = omni_bar.findChild(object, "statusIndicatorDot")
    assert status_dot is not None
    assert status_dot.property("visible") is True
    assert status_dot.property("width") == 6
    assert status_dot.property("height") == 6

    dialogue_scroll_view = omni_bar.findChild(object, "dialogueScrollView")
    assert dialogue_scroll_view is not None
    assert dialogue_scroll_view.property("clip") is True


def test_omnibar_search_suppressed_during_conversational_query(qapp, qml_engine, canvas_qml_root, mock_bridge, monkeypatch):
    monkeypatch.setattr(ConversationController, "stream_prompt", lambda *args, **kwargs: None)
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")
    search_shelf = canvas_qml_root.findChild(object, "searchShelf")
    debounce_timer = omni_bar.findChild(object, "debounceTimer")
    provider_pill = omni_bar.findChild(object, "providerHeaderPill")

    # First simulate active search results and node highlights
    mock_bridge.search_ctrl.searchResultsReceived.emit([1, 2, 3])
    qapp.processEvents()
    assert mock_bridge.searchActive is True

    search_active_signals = []
    mock_bridge.searchActiveChanged.connect(lambda active: search_active_signals.append(active))

    omni_bar.open()
    qapp.processEvents()

    # Type a conversational query starting with ?
    input_field.setProperty("text", "? What is the architecture?")
    for _ in range(10):
        time.sleep(0.02)
        qapp.processEvents()

    # Verify search shelf opacity is 0, bridge searchActive is False (node highlights cleared), debounceTimer stopped, provider pill opacity 0.3
    assert omni_bar.property("isConversationalMode") is True
    assert search_shelf.property("opacity") < 0.01
    assert mock_bridge.searchActive is False
    assert debounce_timer is not None
    assert debounce_timer.property("running") is False
    assert provider_pill is not None
    assert provider_pill.property("opacity") == 0.3
    assert True not in search_active_signals

    # Also test shell mode query starting with >
    mock_bridge.search_ctrl.searchResultsReceived.emit([4, 5])
    qapp.processEvents()
    assert mock_bridge.searchActive is True

    input_field.setProperty("text", "> ls -la")
    for _ in range(5):
        time.sleep(0.02)
        qapp.processEvents()

    assert omni_bar.property("isShellMode") is True
    assert search_shelf.property("opacity") == 0.0
    assert mock_bridge.searchActive is False
    assert debounce_timer.property("running") is False


def test_omnibar_ai_auto_send_debounce_and_idempotency(qapp, qml_engine, canvas_qml_root, mock_bridge, monkeypatch):
    monkeypatch.setattr(ConversationController, "stream_prompt", lambda *args, **kwargs: None)
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")
    auto_send_timer = omni_bar.findChild(object, "aiAutoSendTimer")

    assert auto_send_timer is not None
    assert omni_bar.property("lastExecutedPrompt") == ""

    submitted_queries = []
    omni_bar.querySubmitted.connect(lambda text: submitted_queries.append(text))

    omni_bar.open()
    qapp.processEvents()

    # 1. Type short query (<3 words) ending with punctuation: "? Hi!" -> timer should NOT run
    input_field.setProperty("text", "? Hi!")
    qapp.processEvents()
    assert auto_send_timer.property("running") is False

    # 2. Type 3-word query with no punctuation: "? What is Aether" -> timer should NOT run
    input_field.setProperty("text", "? What is Aether")
    qapp.processEvents()
    assert auto_send_timer.property("running") is False

    # 3. Type 3-word query with ending punctuation: "? What is Aether?" -> timer SHOULD start running
    input_field.setProperty("text", "? What is Aether?")
    qapp.processEvents()
    assert auto_send_timer.property("running") is True

    # Manually trigger timer to simulate 1200ms trigger without waiting
    auto_send_timer.metaObject().invokeMethod(auto_send_timer, "triggered")
    # Wait for the thread to reach STREAMING or ERROR state to avoid teardown crash
    import time
    for _ in range(50):
        if mock_bridge.engineState in ("STREAMING", "ERROR", "IDLE"):
            break
        time.sleep(0.02)
        qapp.processEvents()
    qapp.processEvents()

    assert len(submitted_queries) == 1
    assert submitted_queries[-1] == "? What is Aether?"
    assert omni_bar.property("lastExecutedPrompt") == "? What is Aether?"
    assert auto_send_timer.property("running") is False

    # 4. Idempotency test: Re-setting the exact same text should NOT restart timer
    input_field.setProperty("text", "? What is Aether?")
    qapp.processEvents()
    assert auto_send_timer.property("running") is False

    # 5. Enter key press dispatches query, updates lastExecutedPrompt and stops timer
    input_field.setProperty("text", "? How does Aether scale?")
    qapp.processEvents()
    assert auto_send_timer.property("running") is True

    enter_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(input_field, enter_evt)
    qapp.processEvents()

    assert auto_send_timer.property("running") is False
    assert submitted_queries[-1] == "? How does Aether scale?"
    assert omni_bar.property("lastExecutedPrompt") == "? How does Aether scale?"
    auto_send_timer.stop()
    qapp.processEvents()


def test_omnibar_cross_mode_state_isolation_and_cleanup(qapp, qml_engine, canvas_qml_root):
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")
    placeholder_text = input_field.findChild(object, "customPlaceholderText")
    shell_drawer = omni_bar.findChild(object, "shellDrawer")
    dialogue_drawer = omni_bar.findChild(object, "dialogueDrawer")

    omni_bar.open()
    qapp.processEvents()

    # 1. Start in Conversational Mode ('?')
    input_field.setProperty("text", "? Tell me about Aether")
    qapp.processEvents()

    assert omni_bar.property("isConversationalMode") is True
    assert omni_bar.property("isShellMode") is False
    assert placeholder_text.property("text") == "Ask AI reasoning engine..."

    # Populate AI dialogue results
    stream_results = [
        {"title": "Aether is a real-time spatial graph canvas."}
    ]
    omni_bar.setProperty("resultsList", stream_results)
    for _ in range(6):
        time.sleep(0.01)
        qapp.processEvents()

    assert omni_bar.property("showDialogueOutput") is True
    assert dialogue_drawer.property("visible") is True
    assert omni_bar.property("dialogueFullText") == "Aether is a real-time spatial graph canvas."
    assert "Ask AI:" not in omni_bar.property("dialogueFullText")
    assert omni_bar.property("showShellOutput") is False

    # 2. Transition directly to Shell Mode ('>')
    input_field.setProperty("text", "> ls -la")
    for _ in range(6):
        time.sleep(0.01)
        qapp.processEvents()

    assert omni_bar.property("isShellMode") is True
    assert omni_bar.property("isConversationalMode") is False
    assert placeholder_text.property("text") == "Run command..."

    # Ensure AI state and results are completely cleared/reset
    assert omni_bar.property("showDialogueOutput") is False
    assert omni_bar.property("dialogueFullText") == ""
    assert omni_bar.property("showShellOutput") is False
    assert omni_bar.property("systemStatusItem") is None
    assert omni_bar.property("shellOutputModel").toVariant() == []

    # 3. Populate Shell results
    shell_results = [
        {"line": "drwxr-xr-x 5 user user 4096 Aug 25 10:00 .", "stream": "stdout"},
        {"line": "Command exited with code 0", "stream": "system", "exit_code": 0}
    ]
    omni_bar.setProperty("resultsList", shell_results)
    for _ in range(6):
        time.sleep(0.01)
        qapp.processEvents()

    assert omni_bar.property("showShellOutput") is True
    assert shell_drawer.property("visible") is True
    assert omni_bar.property("systemStatusItem") is not None
    assert len(omni_bar.property("shellOutputModel").toVariant()) == 1
    assert omni_bar.property("showDialogueOutput") is False

    # 4. Transition directly back to Conversational Mode ('?')
    input_field.setProperty("text", "? Summarize logs")
    for _ in range(6):
        time.sleep(0.01)
        qapp.processEvents()

    assert omni_bar.property("isConversationalMode") is True
    assert omni_bar.property("isShellMode") is False
    assert placeholder_text.property("text") == "Ask AI reasoning engine..."

    # Ensure Shell state (exit codes, monospace lines, system status) is cleared
    assert omni_bar.property("showShellOutput") is False
    assert omni_bar.property("systemStatusItem") is None
    assert omni_bar.property("shellOutputModel").toVariant() == []
    assert omni_bar.property("dialogueFullText") == ""
    assert omni_bar.property("showDialogueOutput") is False

    # 5. Transition to standard search mode (empty prefix)
    input_field.setProperty("text", "architecture")
    for _ in range(6):
        time.sleep(0.01)
        qapp.processEvents()

    assert omni_bar.property("isShellMode") is False
    assert omni_bar.property("isConversationalMode") is False
    assert placeholder_text.property("text") == "Search nodes, content, or commands..."
    assert omni_bar.property("showShellOutput") is False
    assert omni_bar.property("showDialogueOutput") is False




def test_omnibar_enter_key_triggers_conversation_execution(qapp, qml_engine, canvas_qml_root, mock_bridge, monkeypatch):
    monkeypatch.setattr(ConversationController, "stream_prompt", lambda *args, **kwargs: None)
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")
    dialogue_drawer = omni_bar.findChild(object, "dialogueDrawer")

    mock_bridge.node.select_node(2)
    assert mock_bridge.focusedNodeId == "2"

    omni_bar.open()
    qapp.processEvents()

    input_field.setProperty("text", "? What is the system state?")
    for _ in range(6):
        time.sleep(0.01)
        qapp.processEvents()

    assert omni_bar.property("isConversationalMode") is True

    # Press Enter key in AI mode
    enter_evt = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(input_field, enter_evt)
    for _ in range(6):
        time.sleep(0.01)
        qapp.processEvents()

    # OmniBar must NOT close on Enter in AI mode
    assert omni_bar.property("active") is True
    assert omni_bar.property("showDialogueOutput") is True
    assert dialogue_drawer.property("visible") is True

    # Emit token signal from conversation engine
    mock_bridge.conversation.tokenReceived.emit("System is operational.")
    qapp.processEvents()

    full_text = omni_bar.property("dialogueFullText")
    assert "Ask AI:" not in full_text
    assert "System is operational." in full_text


def test_focused_node_retained_and_lit_in_conversational_mode(qapp, qml_engine, canvas_qml_root, mock_bridge, monkeypatch):
    monkeypatch.setattr(ConversationController, "stream_prompt", lambda *args, **kwargs: None)
    from store import Node
    n1 = Node(id=1, file_path="/docs/aether.md", x=100.0, y=100.0, archetype="document")
    n2 = Node(id=2, file_path="/src/main.py", x=300.0, y=300.0, archetype="code")
    mock_bridge.store.upsert_node(n1)
    mock_bridge.store.upsert_node(n2)
    mock_bridge.nodesChanged.emit()
    qapp.processEvents()

    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")

    # 1. Select node 1
    mock_bridge.node.select_node(1)
    qapp.processEvents()
    assert mock_bridge.focusedNodeId == "1"

    # 2. Transition into AI mode (?)
    omni_bar.open()
    input_field.setProperty("text", "? Tell me about this node")
    for _ in range(30):
        time.sleep(0.01)
        qapp.processEvents()

    # 3. Verify focusedNodeId is retained and not cleared
    assert mock_bridge.focusedNodeId == "1"
    assert omni_bar.property("isConversationalMode") is True

    # 4. Verify target node has opacity == 1.0 and z == 10, unfocused node has opacity == 0.15 and z == 1
    viewport = canvas_qml_root.findChild(object, "canvasViewport")
    assert viewport is not None
    node1 = viewport.getNode(1)
    node2 = viewport.getNode(2)
    assert node1 is not None
    assert node2 is not None

    assert node1.property("isSelected") is True
    assert node1.property("isFocusedTarget") is True
    assert node1.property("opacity") == 1.0
    assert node1.property("z") == 10

    assert node2.property("isFocusedTarget") is False
    assert node2.property("opacity") == 0.15
    assert node2.property("z") == 1



def test_omnibar_ai_typography_and_status_dot_states(qapp, qml_engine, canvas_qml_root, mock_bridge, monkeypatch):
    monkeypatch.setattr(ConversationController, "stream_prompt", lambda *args, **kwargs: None)
    # 0. Verify bridge.providerMetadata contract
    provider_meta = mock_bridge.property("providerMetadata")
    assert provider_meta is not None
    assert "id" in provider_meta
    assert "display_name" in provider_meta
    assert "accent_color" in provider_meta
    assert "icon_glyph" in provider_meta
    assert provider_meta["id"] == "gemini_flash"
    assert provider_meta["display_name"] == "Flash"
    assert provider_meta["accent_color"] == "#38BDF8"
    assert provider_meta["icon_glyph"] == "✦"

    # 1. Verify Theme.qml Typographic Tokens fontAiBody and fontAiCode
    theme_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Theme.qml")
    assert theme_comp.status() == QQmlComponent.Status.Ready, f"Theme compilation failed: {theme_comp.errors()}"
    theme_inst = theme_comp.create()

    font_ai_body = theme_inst.property("fontAiBody")
    assert font_ai_body is not None
    assert "Inter" in font_ai_body.family()
    assert font_ai_body.pixelSize() == 13

    font_ai_code = theme_inst.property("fontAiCode")
    assert font_ai_code is not None
    assert "JetBrains Mono" in font_ai_code.family()
    assert font_ai_code.pixelSize() == 12

    # 2. Open OmniBar in Conversational Mode ('?')
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    input_field = omni_bar.findChild(object, "inputField")
    status_dot = omni_bar.findChild(object, "statusIndicatorDot")

    omni_bar.open()
    input_field.setProperty("text", "? Explain graph database")
    qapp.processEvents()

    # Emit token response
    mock_bridge.conversation.tokenReceived.emit("A graph database stores nodes and edges.")
    for _ in range(10):
        time.sleep(0.01)
        qapp.processEvents()

    assert omni_bar.property("showDialogueOutput") is True
    assert omni_bar.property("dialogueFullText") == "A graph database stores nodes and edges."

    # Verify dialogueText delegate font and formatting (if delegate instantiated)
    dialogue_text_items = omni_bar.findChildren(object, "dialogueText")
    if len(dialogue_text_items) > 0:
        dialogue_text = dialogue_text_items[0]
        assert "Inter" in dialogue_text.property("font").family()
        assert dialogue_text.property("font").pixelSize() == 13

    # 3. Test Status Dot States: IDLE, STREAMING, ERROR
    # A) IDLE State: Color = Theme.accentAI (#38BDF8), static opacity = 0.5
    mock_bridge.conversation.setEngineState("IDLE")
    qapp.processEvents()
    assert omni_bar.property("engineState") == "IDLE"
    assert status_dot.property("color").name().lower() == "#38bdf8"
    assert status_dot.property("opacity") == 0.5

    # B) STREAMING State: Color = Theme.accentAI (#38BDF8), active pulsing
    mock_bridge.conversation.setEngineState("STREAMING")
    qapp.processEvents()
    assert omni_bar.property("engineState") == "STREAMING"
    assert status_dot.property("color").name().lower() == "#38bdf8"

    # C) ERROR State: Color = Theme.accentRed / Theme.ansiRed (#EF4444), static opacity = 1.0
    mock_bridge.conversation.setEngineState("ERROR")
    qapp.processEvents()
    assert omni_bar.property("engineState") == "ERROR"
    assert status_dot.property("color").name().lower() == "#ef4444"
    assert status_dot.property("opacity") == 1.0






    time.sleep(0.1)
    qapp.processEvents()
