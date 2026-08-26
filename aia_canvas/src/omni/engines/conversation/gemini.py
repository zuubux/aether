"""
Gemini Streaming Provider Adapter
"""

import json
import os
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

from .base import BaseLLMProvider, ProviderMetadata
from .persona import AETHER_SYSTEM_INSTRUCTION


class GeminiProvider(BaseLLMProvider):
    """Gemini streaming adapter utilizing Google Generative Language API via non-blocking SSE."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
    ):
        self._explicit_api_key = api_key
        self.model = model
        self._metadata = ProviderMetadata(
            id="gemini_flash",
            display_name="Flash",
            accent_color="#38BDF8",
            icon_glyph="✦",
        )

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata

    def _resolve_api_key(self) -> Optional[str]:
        """Resolve API key from explicit param, environment vars, or local config file."""
        if self._explicit_api_key and self._explicit_api_key.strip():
            return self._explicit_api_key.strip()

        # Check environment variables
        env_key = os.environ.get("AETHER_GEMINI_API_KEY") or os.environ.get(
            "GEMINI_API_KEY"
        )
        if env_key and env_key.strip():
            return env_key.strip()

        # Check local settings fallback (~/.config/aether/settings.json)
        config_path = Path.home() / ".config" / "aether" / "settings.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for key_name in (
                            "AETHER_GEMINI_API_KEY",
                            "GEMINI_API_KEY",
                            "gemini_api_key",
                        ):
                            val = data.get(key_name)
                            if isinstance(val, str) and val.strip():
                                return val.strip()
            except Exception:
                pass

        return None

    def validate_credentials(self) -> bool:
        """Return True if a non-empty API key is available."""
        key = self._resolve_api_key()
        return bool(key and len(key) > 0)

    async def stream_chat(
        self, prompt: str, context: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """Asynchronously stream Gemini completion chunks.

        If credentials are invalid or network/API errors occur, yield a friendly system advisory.
        """
        api_key = self._resolve_api_key()
        if not api_key:
            yield (
                "[Gemini Advisory] Gemini API key is missing. "
                "Please set AETHER_GEMINI_API_KEY or configure ~/.config/aether/settings.json."
            )
            return

        # Prepare request contents array with history if available
        contents = []
        history = context.get("history", []) if isinstance(context, dict) else []
        for msg in history:
            role = msg.get("role", "user")
            if role in ("assistant", "ai"):
                role = "model"
            content_text = msg.get("content", "")
            if content_text:
                contents.append(
                    {"role": role, "parts": [{"text": content_text}]}
                )

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:streamGenerateContent?alt=sse&key={api_key}"
        )
        headers = {"Content-Type": "application/json"}
        payload = {"contents": contents}

        system_instruction = (
            context.get("system_instruction")
            if isinstance(context, dict) and context.get("system_instruction")
            else AETHER_SYSTEM_INSTRUCTION
        )
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST", url, headers=headers, json=payload
                ) as response:
                    if response.status_code != 200:
                        error_bytes = await response.aread()
                        err_str = error_bytes.decode("utf-8", errors="ignore")
                        yield (
                            f"[Gemini Advisory] API error (HTTP {response.status_code}): "
                            f"{err_str if err_str else 'Unknown error'}"
                        )
                        return

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line.removeprefix("data: ").strip()
                        if not data_str or data_str == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(data_str)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get(
                                    "parts", []
                                )
                                for part in parts:
                                    text = part.get("text", "")
                                    if text:
                                        yield text
                        except json.JSONDecodeError:
                            continue
        except ImportError:
            yield "[Gemini Advisory] Missing 'httpx' dependency for Gemini streaming."
        except Exception as e:
            yield f"[Gemini Advisory] Network or connection failure: {str(e)}"
