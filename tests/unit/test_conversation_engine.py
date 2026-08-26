"""
Unit tests for ConversationEngine, BaseLLMProvider, GeminiProvider, and OmniRouter conversation integration.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, AsyncIterator, Dict

import pytest

from omni import (
    BaseLLMProvider,
    ConversationEngine,
    GeminiProvider,
    OmniContext,
    OmniRouter,
    ProviderMetadata,
)


def test_provider_metadata_contract():
    """Verify ProviderMetadata structure and reactivity across providers and controller."""
    meta = ProviderMetadata()
    assert meta.id == "gemini_flash"
    assert meta.display_name == "Flash"
    assert meta.accent_color == "#38BDF8"
    assert meta.icon_glyph == "✦"
    assert meta["id"] == "gemini_flash"
    assert meta.to_dict() == {
        "id": "gemini_flash",
        "display_name": "Flash",
        "accent_color": "#38BDF8",
        "icon_glyph": "✦",
    }

    provider = GeminiProvider()
    assert provider.metadata.id == "gemini_flash"
    assert provider.metadata.display_name == "Flash"

    engine = ConversationEngine(provider=provider)
    assert engine.provider_metadata.to_dict()["display_name"] == "Flash"

    # Test custom metadata provider
    class CustomLLMProvider(BaseLLMProvider):
        @property
        def metadata(self) -> ProviderMetadata:
            return ProviderMetadata(
                id="custom_llm",
                display_name="CustomAI",
                accent_color="#F97316",
                icon_glyph="★",
            )

        def validate_credentials(self) -> bool:
            return True

        async def stream_chat(self, prompt, context):
            yield "Custom"

    custom_provider = CustomLLMProvider()
    engine.set_provider(custom_provider)
    assert engine.provider_metadata.id == "custom_llm"
    assert engine.provider_metadata.display_name == "CustomAI"
    assert engine.provider_metadata.accent_color == "#F97316"
    assert engine.provider_metadata.icon_glyph == "★"


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider yielding canned chunks with non-blocking delays."""

    def __init__(self, response_chunks=None, valid_credentials=True):
        self.response_chunks = response_chunks or ["Hello ", "from ", "Mock ", "LLM!"]
        self.has_credentials = valid_credentials
        self.last_prompt = None
        self.last_context = None
        self.call_history = []

    def validate_credentials(self) -> bool:
        return self.has_credentials

    async def stream_chat(
        self, prompt: str, context: Dict[str, Any]
    ) -> AsyncIterator[str]:
        self.last_prompt = prompt
        self.last_context = context
        self.call_history.append({"prompt": prompt, "context": context})
        if not self.validate_credentials():
            yield "[Mock Advisory] Missing credentials."
            return

        for chunk in self.response_chunks:
            await asyncio.sleep(0.001)  # Simulate non-blocking async chunk streaming
            yield chunk


def test_conversation_engine_async_streaming():
    """Verify async chunk yielding and session history tracking."""
    async def _test():
        mock_provider = MockLLMProvider(["Aether ", "is ", "a ", "canvas."])
        engine = ConversationEngine(provider=mock_provider)

        chunks = []
        async for chunk in engine.query("? Tell me about Aether"):
            chunks.append(chunk)

        assert "".join(chunks) == "Aether is a canvas."

        history = engine.get_history()
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Tell me about Aether"}
        assert history[1] == {"role": "assistant", "content": "Aether is a canvas."}

    asyncio.run(_test())


def test_conversation_engine_history_bounds():
    """Verify max history sliding window."""
    async def _test():
        mock_provider = MockLLMProvider(["OK"])
        engine = ConversationEngine(provider=mock_provider, max_history=4)

        for i in range(3):
            async for _ in engine.query(f"? Message {i}"):
                pass

        history = engine.get_history()
        assert len(history) == 4
        assert history[-2] == {"role": "user", "content": "Message 2"}
        assert history[-1] == {"role": "assistant", "content": "OK"}

        engine.clear_history()
        assert len(engine.get_history()) == 0

    asyncio.run(_test())



def test_conversation_engine_provider_switch():
    """Verify dynamic provider switching."""
    async def _test():
        provider1 = MockLLMProvider(["Provider ", "One"])
        provider2 = MockLLMProvider(["Provider ", "Two"])

        engine = ConversationEngine(provider=provider1)
        chunks1 = [c async for c in engine.query("? Test 1")]
        assert "".join(chunks1) == "Provider One"

        engine.set_provider(provider2)
        chunks2 = [c async for c in engine.query("? Test 2")]
        assert "".join(chunks2) == "Provider Two"

    asyncio.run(_test())


def test_gemini_provider_missing_credentials_fallback(monkeypatch):
    """Verify GeminiProvider advisory when credentials are missing."""
    monkeypatch.delenv("AETHER_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    provider = GeminiProvider(api_key=None)
    assert not provider.validate_credentials()

    async def _collect():
        return [c async for c in provider.stream_chat("hello", {})]

    chunks = asyncio.run(_collect())
    assert len(chunks) == 1
    assert chunks[0].startswith("[Gemini Advisory]")
    assert "missing" in chunks[0].lower() or "set" in chunks[0].lower()


def test_gemini_provider_credentials_resolution(monkeypatch, tmp_path):
    """Verify API key resolution from env vars and settings.json fallback."""
    monkeypatch.delenv("AETHER_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # 1. Explicit key
    provider_explicit = GeminiProvider(api_key="explicit_key_123")
    assert provider_explicit.validate_credentials()
    assert provider_explicit._resolve_api_key() == "explicit_key_123"

    # 2. Env var AETHER_GEMINI_API_KEY
    monkeypatch.setenv("AETHER_GEMINI_API_KEY", "aether_env_key")
    provider_env = GeminiProvider()
    assert provider_env.validate_credentials()
    assert provider_env._resolve_api_key() == "aether_env_key"

    # 3. Env var GEMINI_API_KEY
    monkeypatch.delenv("AETHER_GEMINI_API_KEY")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini_env_key")
    provider_env2 = GeminiProvider()
    assert provider_env2.validate_credentials()
    assert provider_env2._resolve_api_key() == "gemini_env_key"

    # 4. Settings JSON fallback
    monkeypatch.delenv("GEMINI_API_KEY")

    # Mock Path.home to point to tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config_dir = tmp_path / ".config" / "aether"
    config_dir.mkdir(parents=True, exist_ok=True)
    settings_file = config_dir / "settings.json"
    settings_file.write_text(
        json.dumps({"AETHER_GEMINI_API_KEY": "json_key_999"})
    )

    provider_json = GeminiProvider()
    assert provider_json.validate_credentials()
    assert provider_json._resolve_api_key() == "json_key_999"


def test_omni_router_conversation_integration():
    """Verify OmniRouter routes '?' queries to ConversationEngine.query()."""
    async def _test():
        router = OmniRouter()
        mock_provider = MockLLMProvider(["Routed ", "LLM ", "Response"])
        router.conversation_engine.set_provider(mock_provider)

        ctx = OmniContext(raw_query="? summarize codebase")
        engine = router.resolve_engine("? summarize codebase", ctx)
        assert engine == router.conversation_engine

        chunks = []
        async for chunk in router.query("? summarize codebase", ctx):
            chunks.append(chunk)

        assert "".join(chunks) == "Routed LLM Response"
        assert len(router.conversation_engine.get_history()) == 2

    asyncio.run(_test())


def test_conversation_engine_focused_node_context_assembly(tmp_path):
    """Test execute_prompt gathers spatial context when a node is focused."""
    async def _test():
        test_file = tmp_path / "main.py"
        test_file.write_text("print('hello world')\n", encoding="utf-8")

        mock_provider = MockLLMProvider(["Context ", "received"])
        engine = ConversationEngine(provider=mock_provider)

        response = await engine.execute_prompt(
            "? Explain this script",
            context={"focused_node_id": str(test_file)},
        )

        assert response == "Context received"
        assert mock_provider.last_prompt is not None
        assert "[Spatial Context]" in mock_provider.last_prompt
        assert str(test_file.resolve()) in mock_provider.last_prompt
        assert "Explain this script" in mock_provider.last_prompt

    asyncio.run(_test())


def test_gemini_provider_system_instruction_and_envelope_passed(monkeypatch):
    """Test system instruction and spatial envelope are passed in Gemini request payload."""
    async def _test():
        from omni.engines.conversation.persona import AETHER_SYSTEM_INSTRUCTION

        monkeypatch.setenv("AETHER_GEMINI_API_KEY", "test_gemini_key_123")

        captured_payload = {}

        class DummyResponse:
            status_code = 200

            async def aiter_lines(self):
                chunk = {"candidates": [{"content": {"parts": [{"text": "Gemini response"}]}}]}
                yield f"data: {json.dumps(chunk)}"
                yield "data: [DONE]"

        class DummyAsyncClient:
            def __init__(self, timeout=30.0):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            def stream(self, method, url, headers=None, json=None):
                nonlocal captured_payload
                captured_payload = json
                return DummyResponseContextManager(DummyResponse())

        class DummyResponseContextManager:
            def __init__(self, response):
                self.response = response

            async def __aenter__(self):
                return self.response

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        import sys
        dummy_httpx = type(sys)("httpx")
        dummy_httpx.AsyncClient = DummyAsyncClient
        monkeypatch.setitem(sys.modules, "httpx", dummy_httpx)

        provider = GeminiProvider()
        chunks = []
        envelope_prompt = "[Spatial Context]\n- Target Path: /tmp/app.py\n\nHow do I run this?"
        async for chunk in provider.stream_chat(
            envelope_prompt, context={"system_instruction": AETHER_SYSTEM_INSTRUCTION}
        ):
            chunks.append(chunk)

        assert "".join(chunks) == "Gemini response"
        assert captured_payload is not None
        assert "systemInstruction" in captured_payload
        assert (
            captured_payload["systemInstruction"]["parts"][0]["text"]
            == AETHER_SYSTEM_INSTRUCTION
        )
        assert captured_payload["contents"][0]["parts"][0]["text"] == envelope_prompt

    asyncio.run(_test())


def test_conversation_engine_multiturn_history_stability(tmp_path):
    """Test multi-turn dialogue history stability (context envelope does not pollute turn history)."""
    async def _test():
        test_file = tmp_path / "module.py"
        test_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

        mock_provider = MockLLMProvider(["Response ", "chunk"])
        engine = ConversationEngine(provider=mock_provider)

        # Turn 1
        res1 = await engine.execute_prompt(
            "? Turn 1 prompt", context={"focused_node_id": str(test_file)}
        )
        assert res1 == "Response chunk"

        # Turn 2
        res2 = await engine.execute_prompt(
            "? Turn 2 prompt", context={"focused_node_id": str(test_file)}
        )
        assert res2 == "Response chunk"

        # Check in-memory history buffer
        history = engine.get_history()
        assert len(history) == 4
        # User history turns must retain clean prompt queries without [Spatial Context]
        assert history[0] == {"role": "user", "content": "Turn 1 prompt"}
        assert history[1] == {"role": "assistant", "content": "Response chunk"}
        assert history[2] == {"role": "user", "content": "Turn 2 prompt"}
        assert history[3] == {"role": "assistant", "content": "Response chunk"}

        # Verify call history passed to provider
        assert len(mock_provider.call_history) == 2
        call_1_prompt = mock_provider.call_history[0]["prompt"]
        call_2_prompt = mock_provider.call_history[1]["prompt"]

        assert call_1_prompt.startswith("[Spatial Context]")
        assert "Turn 1 prompt" in call_1_prompt

        assert call_2_prompt.startswith("[Spatial Context]")
        assert "Turn 2 prompt" in call_2_prompt

        # Call 2 history passed in context must contain clean user prompt for turn 1
        call_2_ctx_history = mock_provider.call_history[1]["context"]["history"]
        assert call_2_ctx_history[0]["content"] == "Turn 1 prompt"
        assert "[Spatial Context]" not in call_2_ctx_history[0]["content"]

    asyncio.run(_test())

def test_conversation_engine_bridge_context_resolution(tmp_path):
    """Test conversation engine resolves focus state directly from CanvasBridge."""
    async def _test():
        test_file = tmp_path / "bridge_test.py"
        test_file.write_text("x = 42\n", encoding="utf-8")

        class MockNode:
            def __init__(self, node_id, path):
                self.id = node_id
                self.filePath = str(path)

        class MockStore:
            def __init__(self, node):
                self.node = node

            def get_node(self, node_id):
                if node_id == self.node.id:
                    return self.node
                return None

        class MockBridge:
            def __init__(self, node):
                self.store = MockStore(node)
                self._selected_node_id = node.id
                self.node_ctrl = type("NodeCtrl", (), {"selectedNodeId": node.id})()

            def get_focused_node_id(self):
                return str(self._selected_node_id)

            def get_focused_node_path(self):
                node = self.store.get_node(self._selected_node_id)
                return getattr(node, "filePath", "")

        node = MockNode(101, test_file)
        bridge = MockBridge(node)

        mock_provider = MockLLMProvider(["Bridge ", "context ", "resolved"])
        engine = ConversationEngine(provider=mock_provider, bridge=bridge)

        res = await engine.execute_prompt("? What is x?")
        assert res == "Bridge context resolved"
        assert mock_provider.last_prompt is not None
        assert "[Spatial Context]" in mock_provider.last_prompt
        assert str(test_file.resolve()) in mock_provider.last_prompt
        assert "What is x?" in mock_provider.last_prompt

    asyncio.run(_test())
