"""
Conversation Controller Implementation
Manages streaming dialogue execution, token signals, and provider state.
"""

import asyncio
import logging
import threading
import time
from typing import Any, List, Optional

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from omni.engines.conversation import ConversationEngine
from .base_controller import BaseController

logger = logging.getLogger("aia_canvas.conversation_controller")


import os
import re
from datetime import datetime
from pathlib import Path

class ConversationController(BaseController):
    """Controller managing streaming dialogue execution, token emissions, and LLM provider state."""

    tokenReceived = pyqtSignal(str)
    responseFinished = pyqtSignal(str)
    engineStateChanged = pyqtSignal(str)
    providerMetadataChanged = pyqtSignal()
    requestAscensionToSlate = pyqtSignal(list)
    turnHistoryChanged = pyqtSignal()

    def __init__(self, bridge: Any):
        """Initialize ConversationController and connect underlying ConversationEngine.

        Args:
            bridge: CanvasBridge instance owning search and conversation state.
        """
        super().__init__(bridge)
        self._engine_state: str = "IDLE"
        self._turn_history: List[dict] = []
        if hasattr(bridge, "search_ctrl") and hasattr(bridge.search_ctrl, "router"):
            self.engine = bridge.search_ctrl.router.conversation_engine
        else:
            self.engine = ConversationEngine()
        self.engine.set_bridge(bridge)
        self._active_thread: Optional[threading.Thread] = None
        self._active_loop: Optional[asyncio.AbstractEventLoop] = None
        self._active_task: Optional[asyncio.Task] = None

    @pyqtProperty(str, notify=engineStateChanged)
    def engineState(self) -> str:
        """str: Current conversation execution state ('IDLE', 'STREAMING', 'ERROR')."""
        return self._engine_state

    @pyqtProperty("QVariantMap", notify=providerMetadataChanged)
    def providerMetadata(self) -> dict:
        """dict: Metadata dictionary describing active LLM provider display attributes."""
        if hasattr(self.engine, "provider_metadata"):
            meta = self.engine.provider_metadata
            return meta.to_dict() if hasattr(meta, "to_dict") else dict(meta)
        return {
            "id": "gemini_flash",
            "display_name": "3.7 Flash",
            "accent_color": "#38BDF8",
            "icon_glyph": "✦",
            "icon_path": "aia_canvas/assets/icons/providers/gemini.svg",
        }

    @pyqtSlot(str)
    def setEngineState(self, state: str) -> None:
        """Set conversation engine state and emit notification if changed.

        Args:
            state: Target engine state string.
        """
        if self._engine_state != state:
            self._engine_state = state
            self.engineStateChanged.emit(state)

    @pyqtSlot()
    def stop(self) -> None:
        """Cancel active dialogue stream and cleanly teardown background worker thread."""
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
    def stream_prompt(self, prompt: str, context: Optional[Any] = None) -> None:
        """Invoke non-blocking conversational streaming for input prompt.

        Args:
            prompt: Raw prompt text.
            context: Optional contextual node or message payload.
        """
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
                t0_ns = time.perf_counter_ns()
                first_token = True
                try:
                    async for chunk in self.engine.stream_prompt(prompt, context=context):
                        if first_token:
                            first_token = False
                            ttft_ms = (time.perf_counter_ns() - t0_ns) / 1e6
                            from core.telemetry import TelemetrySink
                            TelemetrySink.instance().record_llm_ttft(ttft_ms)
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
                if prompt and full_resp and not is_error:
                    turn_record = {"prompt": prompt, "response": full_resp}
                    self._turn_history.append(turn_record)
                    self.turnHistoryChanged.emit()
                    if len(self._turn_history) >= 3:
                        self.requestAscensionToSlate.emit(list(self._turn_history))
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

    @pyqtProperty("QVariantList", notify=turnHistoryChanged)
    def turnHistory(self) -> List[dict]:
        """List[dict]: Snapshot list of active dialogue turn history records."""
        return list(self._turn_history)

    def get_history(self) -> List[dict]:
        """Return snapshot list of active dialogue turn history.

        Returns:
            List[dict]: Historical dialogue turn records.
        """
        if self._turn_history:
            return list(self._turn_history)
        return self.engine.get_history()

    def clear_history(self) -> None:
        """Clear active session dialogue turn history."""
        self._turn_history.clear()
        self.turnHistoryChanged.emit()
        self.engine.clear_history()

    def set_provider(self, provider: Any) -> None:
        """Switch active LLM provider and notify metadata updates.

        Args:
            provider: Provider handle or provider name identifier.
        """
        self.engine.set_provider(provider)
        self.providerMetadataChanged.emit()

    def _resolve_sandbox_dir(self) -> Path:
        """Resolve the target conversations directory within the sandbox."""
        sandbox_env = os.environ.get("WEAVER_SANDBOX") or os.environ.get("AETHER_SANDBOX_DIR")
        if sandbox_env:
            base_dir = Path(sandbox_env)
        else:
            base_dir = Path.cwd() / "aia_weaver" / "sandbox"
        conv_dir = base_dir / "conversations"
        conv_dir.mkdir(parents=True, exist_ok=True)
        return conv_dir

    def _slugify(self, text: str) -> str:
        """Strip punctuation and format text into a clean slug string."""
        text = text.lstrip("?")
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '_', text)
        return text.lower()[:48].strip("_")

    def _derive_title(self, topic_hint: str) -> str:
        """Determine a clean title string from hint or history."""
        clean_hint = topic_hint.lstrip("?").strip()
        if clean_hint:
            return clean_hint
        if self._turn_history:
            return self._turn_history[0].get("prompt", "Conversation")
        return "Conversation"

    def _format_conversation_markdown(self, turns: list, topic_hint: str) -> str:
        """Generate strictly clean markdown for the conversation slate."""
        title = self._derive_title(topic_hint)
        # Format date as 'Sep 2026' or similar, e.g., 'Sep 06, 2026'
        date_str = datetime.now().strftime("%b %d, %Y")
        
        md_lines = []
        md_lines.append(f"### {title}")
        md_lines.append(f"*{date_str}*")
        
        for turn in turns:
            md_lines.append("")
            md_lines.append("**User**")
            md_lines.append(turn.get("prompt", "").strip())
            md_lines.append("")
            md_lines.append("**Aether**")
            md_lines.append(turn.get("response", "").strip())
            
        return "\n".join(md_lines)

    def pin_conversation_to_slate(self, topic_hint: str = "") -> str:
        """Generate and save the conversation to a markdown file in the sandbox."""
        title = self._derive_title(topic_hint)
        slug = self._slugify(title)
        if not slug:
            slug = "conversation"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{slug}.md"
        
        out_dir = self._resolve_sandbox_dir()
        out_path = out_dir / filename
        
        markdown_content = self._format_conversation_markdown(self._turn_history, topic_hint)
        # Separate turns/sections with double newlines logic is mostly handled by "\n".join() with empty strings
        # We ensure it replaces single newlines with double where needed or simply formats cleanly.
        # Actually our md_lines generation appends empty lines, resulting in \n\n between paragraphs.
        
        out_path.write_text(markdown_content, encoding="utf-8")
        
        return str(out_path.absolute())

    @pyqtSlot(result=str)
    @pyqtSlot(str, result=str)
    def pin_conversation(self, context_title: str = "") -> str:
        """Slot to pin the conversation to the slate."""
        return self.pin_conversation_to_slate(context_title)
