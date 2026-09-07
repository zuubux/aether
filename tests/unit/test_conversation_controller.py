import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aia_canvas.src.controllers.conversation_controller import ConversationController
try:
    from aia_canvas.src.memory.synthesizer import MemorySynthesizer
except ModuleNotFoundError:
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
    
