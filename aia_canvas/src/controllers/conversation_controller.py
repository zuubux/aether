"""
Conversation Controller Implementation
Manages streaming dialogue execution, token signals, and provider state.
"""

import asyncio
import logging
import threading
from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from omni.engines.conversation import ConversationEngine
from .base_controller import BaseController

logger = logging.getLogger("aia_canvas.conversation_controller")


class ConversationController(BaseController):
    tokenReceived = pyqtSignal(str)
    responseFinished = pyqtSignal(str)
    engineStateChanged = pyqtSignal(str)
    providerMetadataChanged = pyqtSignal()

    def __init__(self, bridge):
        super().__init__(bridge)
        self._engine_state = "IDLE"
        if hasattr(bridge, "search_ctrl") and hasattr(bridge.search_ctrl, "router"):
            self.engine = bridge.search_ctrl.router.conversation_engine
        else:
            self.engine = ConversationEngine()
        self.engine.set_bridge(bridge)
        self._active_thread = None
        self._active_loop = None
        self._active_task = None

    @pyqtProperty(str, notify=engineStateChanged)
    def engineState(self) -> str:
        return self._engine_state

    @pyqtProperty("QVariantMap", notify=providerMetadataChanged)
    def providerMetadata(self) -> dict:
        if hasattr(self.engine, "provider_metadata"):
            meta = self.engine.provider_metadata
            return meta.to_dict() if hasattr(meta, "to_dict") else dict(meta)
        return {
            "id": "gemini_flash",
            "display_name": "Flash",
            "accent_color": "#38BDF8",
            "icon_glyph": "✦",
        }

    @pyqtSlot(str)
    def setEngineState(self, state: str) -> None:
        if self._engine_state != state:
            self._engine_state = state
            self.engineStateChanged.emit(state)

    @pyqtSlot()
    def stop(self) -> None:
        """Cancel active stream and cleanly teardown background thread."""
        loop = self._active_loop
        task = self._active_task
        if loop and loop.is_running() and task and not task.done():
            try:
                loop.call_soon_threadsafe(task.cancel)
            except Exception as e:
                logger.error(f"Error cancelling conversation task: {e}")
        
        thread = self._active_thread
        if thread and thread.is_alive():
            if threading.current_thread() != thread:
                thread.join(timeout=0.5)
        
        self._active_thread = None
        self._active_loop = None
        self._active_task = None
        if self._engine_state == "STREAMING":
            self.setEngineState("IDLE")

    @pyqtSlot(str)
    @pyqtSlot(str, str)
    def stream_prompt(self, prompt: str, context: Optional[Any] = None):
        """Invoke conversational streaming for prompt."""
        if not prompt or not prompt.strip():
            return

        self.stop()

        def _run_stream():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._active_loop = loop

            async def _async_stream():
                accumulated = []
                self.setEngineState("STREAMING")
                is_error = False
                try:
                    async for chunk in self.engine.stream_prompt(prompt, context=context):
                        if "[Gemini Advisory]" in chunk or ("error" in chunk.lower() and ("missing" in chunk.lower() or "failure" in chunk.lower() or "http" in chunk.lower())):
                            is_error = True
                            self.setEngineState("ERROR")
                        self.tokenReceived.emit(chunk)
                        accumulated.append(chunk)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error during conversation stream: {e}")
                    is_error = True
                    self.setEngineState("ERROR")
                finally:
                    if not is_error and self._engine_state == "STREAMING":
                        self.setEngineState("IDLE")

                full_resp = "".join(accumulated)
                self.responseFinished.emit(full_resp)

            task = loop.create_task(_async_stream())
            self._active_task = task
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                pass
            finally:
                loop.close()
                self._active_loop = None
                self._active_task = None

        self._active_thread = threading.Thread(target=_run_stream, daemon=True)
        self._active_thread.start()

    def get_history(self):
        """Return snapshot of active dialogue history."""
        return self.engine.get_history()

    def clear_history(self):
        """Clear active session history."""
        self.engine.clear_history()

    def set_provider(self, provider):
        """Switch the active LLM provider."""
        self.engine.set_provider(provider)
        self.providerMetadataChanged.emit()
