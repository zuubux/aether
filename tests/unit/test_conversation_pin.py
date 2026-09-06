import os
import pytest
from pathlib import Path
from datetime import datetime

from bridge import CanvasBridge
from controllers.conversation_controller import ConversationController

@pytest.fixture
def controller(mock_bridge):
    return mock_bridge.conversation_ctrl

def test_resolve_sandbox_dir(controller, monkeypatch, tmp_path):
    monkeypatch.setenv("WEAVER_SANDBOX", str(tmp_path))
    conv_dir = controller._resolve_sandbox_dir()
    assert conv_dir == tmp_path / "conversations"
    assert conv_dir.exists()

def test_slugify(controller):
    assert controller._slugify("?Hello World!") == "hello_world"
    assert controller._slugify("Some-Topic_With spaces.") == "some_topic_with_spaces"
    assert controller._slugify("A" * 60) == ("a" * 48).strip("_")

def test_derive_title(controller):
    assert controller._derive_title("?My Topic") == "My Topic"
    assert controller._derive_title("  ") == "Conversation"
    
    controller._turn_history.append({"prompt": "First turn", "response": "resp"})
    assert controller._derive_title("") == "First turn"

def test_format_conversation_markdown(controller):
    turns = [
        {"prompt": "Hello", "response": "Hi there!"},
        {"prompt": "How are you?", "response": "I am fine."}
    ]
    md = controller._format_conversation_markdown(turns, "?Greeting")
    
    # Check formatting
    assert md.startswith("### Greeting")
    assert "**User**" in md
    assert "Hello" in md
    assert "**Aether**" in md
    assert "Hi there!" in md
    
    # Check NO YAML / raw dividers
    assert "---" not in md
    assert "title:" not in md
    assert "type:" not in md
    
    # Check double newline separation between sections and turns
    assert "\n\n**User**" in md
    assert "\n\n**Aether**" in md
    
    # Check date formatting roughly
    current_year = str(datetime.now().year)
    assert current_year in md

def test_pin_conversation_to_slate(controller, monkeypatch, tmp_path):
    monkeypatch.setenv("WEAVER_SANDBOX", str(tmp_path))
    controller._turn_history.append({"prompt": "Test Prompt", "response": "Test Response"})
    
    file_path = controller.pin_conversation_to_slate("?Test Pin")
    assert file_path.endswith(".md")
    assert "test_pin" in file_path
    
    saved_file = Path(file_path)
    assert saved_file.exists()
    assert saved_file.parent == tmp_path / "conversations"
    
    content = saved_file.read_text(encoding="utf-8")
    assert "### Test Pin" in content
    assert "Test Prompt" in content
    assert "Test Response" in content

def test_bridge_slot_exposure(mock_bridge, monkeypatch, tmp_path):
    monkeypatch.setenv("WEAVER_SANDBOX", str(tmp_path))
    mock_bridge.conversation_ctrl._turn_history.append({"prompt": "Q", "response": "A"})
    
    res = mock_bridge.pin_conversation("?Slot Test")
    assert isinstance(res, str)
    assert "slot_test" in res
    assert Path(res).exists()
