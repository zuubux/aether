"""
Plate Engine - Plate Summary Engine Subsystem
Lightweight, cache-first text compression and extractive summarization
when plates transition to the SUMMARY lifecycle tier.
"""

from __future__ import annotations

import html
import logging
import re
from pathlib import Path
from typing import Any, Sequence

from .lifecycle import PlateLifecycleTier
from .models import PlateArchetype, PlateNodePayload

logger = logging.getLogger("aia_canvas.plate_engine.summary_engine")


class PlateSummaryEngine:
    """
    Lightweight, cache-first text compression engine for Plates in the Aether Canvas.

    Inspects cached metadata summaries before falling back to an extractive
    micro-pipeline that pulls the top information-dense sentences from plate content
    or textual metadata, compiling a clean 2-sentence executive summary and permanently
    caching it back into plate.metadata["ai_summary"].
    """

    CACHE_KEY: str = "ai_summary"
    _MAX_DISK_READ_BYTES: int = 32_768

    _INFORMATIVE_KEYWORDS: frozenset[str] = frozenset({
        "provides", "implements", "manages", "handles", "contains",
        "summary", "overview", "architecture", "designed", "engine",
        "pipeline", "interface", "component", "system", "service",
        "configuration", "layer", "protocol", "model", "data", "process",
        "records", "coordinates", "represents", "executes", "tracks",
        "controller", "module", "lifecycle", "spatial", "geometry",
    })

    def __init__(self) -> None:
        self._cache: dict[Any, str] = {}

    def get_or_generate_summary(self, plate: Any) -> str:
        """
        Retrieves an existing cached summary or generates a new 2-sentence executive summary.

        - Cache-First Check: Inspects plate.metadata["ai_summary"] for existing cached snippet.
        - Extractive Generation: Triggered strictly if ai_summary is missing or empty.
        - Persistence: Writes generated summary strictly to plate.metadata["ai_summary"].
        """
        cache_key = self._resolve_cache_key(plate)

        # 1. In-memory engine cache lookup
        if cache_key is not None and cache_key in self._cache:
            return self._cache[cache_key]

        meta = self._get_metadata_dict(plate)

        # 2. Strict single-key check on plate.metadata["ai_summary"]
        if meta is not None:
            cached = meta.get(self.CACHE_KEY)
            if isinstance(cached, str) and cached.strip():
                clean_cached = cached.strip()
                if cache_key is not None:
                    self._cache[cache_key] = clean_cached
                return clean_cached

        # 3. Extractive Pipeline (strictly triggered when ai_summary is missing or empty)
        raw_text = self._extract_text_source(plate, meta)
        cleaned_text = self._clean_text(raw_text)
        candidates = self._extract_candidate_sentences(cleaned_text)

        summary = self._compile_executive_summary(plate, candidates)

        # 4. Persistence: Write generated summary strictly back to plate.metadata["ai_summary"]
        self._persist_summary(plate, meta, summary)

        if cache_key is not None:
            self._cache[cache_key] = summary

        return summary

    def handle_tier_transition(
        self, plate: Any, new_tier: PlateLifecycleTier | str
    ) -> str | None:
        """
        Automatically triggers get_or_generate_summary(plate) when new_tier == PlateLifecycleTier.SUMMARY.
        """
        tier = (
            new_tier
            if isinstance(new_tier, PlateLifecycleTier)
            else PlateLifecycleTier.from_str(new_tier)
        )
        if tier == PlateLifecycleTier.SUMMARY:
            return self.get_or_generate_summary(plate)
        return None

    def clear_cache(self) -> None:
        """Clears internal engine cache."""
        self._cache.clear()

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _resolve_cache_key(self, plate: Any) -> Any:
        """Extracts a stable identifier to serve as cache key."""
        if hasattr(plate, "node_id"):
            val = getattr(plate, "node_id")
            if val is not None:
                return val
        if hasattr(plate, "id"):
            val = getattr(plate, "id")
            if val is not None:
                return val
        if isinstance(plate, dict):
            for k in ("node_id", "id", "nodeId"):
                if plate.get(k) is not None:
                    return plate[k]
            if plate.get("file_path"):
                return plate["file_path"]

        if hasattr(plate, "file_path") and getattr(plate, "file_path"):
            return getattr(plate, "file_path")

        return id(plate)

    def _get_metadata_dict(self, plate: Any) -> dict[str, Any] | None:
        """Retrieves or normalizes the metadata dictionary from a plate."""
        if plate is None:
            return None

        if hasattr(plate, "metadata"):
            meta = getattr(plate, "metadata")
            if isinstance(meta, dict):
                return meta

        if isinstance(plate, dict):
            meta = plate.get("metadata")
            if isinstance(meta, dict):
                return meta

        return None

    def _get_title(self, plate: Any) -> str:
        """Derives a clean title string from plate properties."""
        for attr in ("display_title", "file_name", "title", "name"):
            val = getattr(plate, attr, None) if not isinstance(plate, dict) else plate.get(attr)
            if val and isinstance(val, str) and val.strip():
                return val.strip()

        file_path = getattr(plate, "file_path", None) if not isinstance(plate, dict) else plate.get("file_path")
        if file_path and isinstance(file_path, str) and file_path.strip():
            return Path(file_path).stem or Path(file_path).name

        return "Plate"

    def _get_archetype(self, plate: Any) -> str:
        """Derives a string archetype name from plate."""
        val = getattr(plate, "archetype", None) if not isinstance(plate, dict) else plate.get("archetype")
        if isinstance(val, PlateArchetype):
            return val.value
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
        return PlateArchetype.DOCUMENT.value

    def _extract_text_source(self, plate: Any, meta: dict[str, Any] | None) -> str:
        """Gathers raw text source from plate attributes, metadata, snippet, or disk."""
        for attr in ("content", "text", "body", "raw_text"):
            val = getattr(plate, attr, None) if not isinstance(plate, dict) else plate.get(attr)
            if isinstance(val, str) and val.strip():
                return val

        if meta:
            for key in ("content", "text", "body", "raw_text", "description"):
                val = meta.get(key)
                if isinstance(val, str) and val.strip():
                    return val

        snippet_val = getattr(plate, "snippet", None) if not isinstance(plate, dict) else plate.get("snippet")
        if isinstance(snippet_val, str) and snippet_val.strip():
            return snippet_val

        if meta and isinstance(meta.get("snippet"), str) and meta["snippet"].strip():
            return meta["snippet"]

        file_path = getattr(plate, "file_path", None) if not isinstance(plate, dict) else plate.get("file_path")
        if file_path and isinstance(file_path, str):
            try:
                p = Path(file_path)
                if p.is_file() and p.stat().st_size > 0:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        return f.read(self._MAX_DISK_READ_BYTES)
            except Exception as exc:
                logger.debug("Failed reading text from %s: %s", file_path, exc)

        return ""

    def _clean_text(self, raw: str) -> str:
        """Cleans HTML tags, Markdown artifacts, and excessive whitespace from text."""
        if not raw:
            return ""

        text = re.sub(r"<(br|p|div|li)\s*/?>", "\n", raw, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)

        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```[a-zA-Z0-9_-]*\n?", "", text)
        text = re.sub(r"[*_`]{1,3}([^*_`]+)[*_`]{1,3}", r"\1", text)
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s+([.,!?:;])", r"\1", text)
        return text.replace("\r\n", "\n").replace("\r", "\n")

    def _extract_candidate_sentences(self, text: str) -> list[str]:
        """
        Extracts and ranks key sentences from text, returning up to top 2-3 information-dense lines.
        Preserves relative document order for readability.
        """
        if not text.strip():
            return []

        raw_lines = [line.strip() for line in text.split("\n") if line.strip()]
        candidate_items: list[tuple[int, str]] = []
        idx = 0

        for line in raw_lines:
            if re.match(r"^(import|from|#include|package|\/\*|\*|\/\/|#!\/)", line):
                continue
            if line.startswith(("//", "/*", "*/", "#", "---", "===")):
                continue

            for s in re.split(r"(?<=[.!?])\s+", line):
                s_clean = s.strip()
                if not s_clean:
                    continue

                s_clean = re.sub(r"^[-*•\d+.)\]]+\s*", "", s_clean).strip()
                if len(s_clean) < 15:
                    continue

                alpha_count = sum(c.isalpha() for c in s_clean)
                if alpha_count / max(len(s_clean), 1) < 0.4:
                    continue

                candidate_items.append((idx, s_clean))
                idx += 1

        if not candidate_items:
            return []

        scored = [
            (pos, sentence, self._score_sentence(sentence))
            for pos, sentence in candidate_items
        ]

        scored.sort(key=lambda item: item[2], reverse=True)
        top_candidates = scored[:3]
        top_candidates.sort(key=lambda item: item[0])

        return [item[1] for item in top_candidates]

    def _score_sentence(self, sentence: str) -> float:
        """
        Computes an information density score for a candidate sentence.
        """
        words = re.findall(r"\b\w+\b", sentence.lower())
        if not words:
            return 0.0

        total_words = len(words)
        unique_words = len(set(words))
        lex_diversity = unique_words / total_words

        char_len = len(sentence)
        len_score = max(0.0, 1.0 - abs(char_len - 85) / 95.0)
        alpha_ratio = sum(c.isalpha() for c in sentence) / max(char_len, 1)

        kw_hits = sum(1 for w in words if w in self._INFORMATIVE_KEYWORDS)
        kw_bonus = min(0.6, kw_hits * 0.15)
        casing_bonus = 0.1 if sentence[0].isupper() else 0.0

        return (lex_diversity * 0.3) + (len_score * 0.3) + (alpha_ratio * 0.2) + kw_bonus + casing_bonus

    def _format_sentence(self, sentence: str) -> str:
        """Formats and punctuates a string as a clean grammatical sentence."""
        s = sentence.strip()
        if not s:
            return ""

        s = re.sub(r"[\s,:;—\-]+$", "", s).strip()
        s = re.sub(r"\s+([.,!?:;])", r"\1", s)
        if not s:
            return ""

        s = s[0].upper() + s[1:]
        if not s.endswith((".", "!", "?")):
            s = f"{s}."

        return s

    def _compile_executive_summary(
        self, plate: Any, candidates: Sequence[str]
    ) -> str:
        """
        Compiles a clean 2-sentence executive summary string from candidate sentences
        or metadata context.
        """
        title = self._get_title(plate)
        archetype = self._get_archetype(plate)

        if len(candidates) >= 2:
            s1 = self._format_sentence(candidates[0])
            s2 = self._format_sentence(candidates[1])
            return f"{s1} {s2}"

        if len(candidates) == 1:
            s1 = self._format_sentence(candidates[0])
            s2 = f"This resource is categorized under {archetype} architecture for {title}."
            return f"{s1} {s2}"

        s1 = f"{title} is preserved as an active {archetype} plate."
        s2 = "Detailed semantic body content is not currently available for this resource."
        return f"{s1} {s2}"

    def _persist_summary(self, plate: Any, meta: dict[str, Any] | None, summary: str) -> None:
        """Persists the generated summary strictly into plate.metadata["ai_summary"]."""
        if meta is not None:
            meta[self.CACHE_KEY] = summary
            return

        if hasattr(plate, "metadata"):
            try:
                if getattr(plate, "metadata") is None:
                    setattr(plate, "metadata", {})
                if isinstance(getattr(plate, "metadata"), dict):
                    getattr(plate, "metadata")[self.CACHE_KEY] = summary
                    return
            except Exception as exc:
                logger.debug("Failed setting plate metadata: %s", exc)

        if isinstance(plate, dict):
            if not isinstance(plate.get("metadata"), dict):
                plate["metadata"] = {}
            plate["metadata"][self.CACHE_KEY] = summary

