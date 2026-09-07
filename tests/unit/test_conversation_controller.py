import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aia_canvas.src.controllers.conversation_controller import ConversationController
try:
    from aia_canvas.src.memory.event_ledger import EventLedger
    from aia_canvas.src.memory.synthesizer import MemorySynthesizer
except ModuleNotFoundError:
    from memory.event_ledger import EventLedger
    from memory.synthesizer import MemorySynthesizer

def test_engine_state_propagation_from_synthesizer(qapp):
    bridge = MagicMock()
    controller = ConversationController(bridge)
    
    # Verify initial state
    assert controller.engineState == "IDLE"
    
    # Trigger synthesizer state change
    controller.synthesizer.engineStateChanged.emit("DISTILLING")
    assert controller.engineState == "DISTILLING"
    
    # Return to latent
    controller.synthesizer.engineStateChanged.emit("LATENT")
    assert controller.engineState == "IDLE"

def test_streaming_priority(qapp):
    bridge = MagicMock()
    controller = ConversationController(bridge)
    
    # Start streaming
    controller.setEngineState("STREAMING")
    assert controller.engineState == "STREAMING"
    
    # Synthesizer fires distilling
    controller.synthesizer.engineStateChanged.emit("DISTILLING")
    
    # State should remain STREAMING
    assert controller.engineState == "STREAMING"
    
    # Stop streaming
    controller.setEngineState("IDLE")
    
    # Now synthesizer state is visible
    assert controller.engineState == "DISTILLING"


def test_stream_prompt_records_omni_query_to_event_ledger(tmp_path: Path, qapp):
    bridge = MagicMock()
    ledger = EventLedger(tmp_path / "events.db")
    synth = MemorySynthesizer(event_ledger=ledger, memory_db_path=tmp_path / "memory.db")
    controller = ConversationController(bridge, synthesizer=synth)

    async def mock_stream(prompt, context=None):
        if False:
            yield ""

    controller.engine.stream_prompt = mock_stream

    controller.stream_prompt("?How does the engine work?", context="node_123")
    controller.stop()

    events = ledger.get_recent_events(event_type="omni_query")
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "omni_query"
    assert event["payload"]["query"] == "How does the engine work?"
    assert event["payload"]["prompt"] == "How does the engine work?"
    assert event["payload"]["context"] == "node_123"

    ledger.close()

    
