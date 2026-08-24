from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional


class IntentOperator(Enum):
    SEARCH = auto()
    NAVIGATE = auto()
    LINK = auto()
    APERTURE = auto()
    TAG = auto()
    COMMAND = auto()


@dataclass
class Intent:
    operator: IntentOperator
    raw_query: str = ""
    arguments: Dict[str, Any] = None

    def __post_init__(self):
        if self.arguments is None:
            self.arguments = {}


def parse_intent(text: str) -> Intent:
    text = text.strip()
    if not text:
        return Intent(IntentOperator.SEARCH, raw_query="")

    if text.startswith("@"):
        return Intent(IntentOperator.NAVIGATE, raw_query=text, arguments={"target": text[1:].strip()})
    
    if text.startswith("/link") or "&" in text:
        clean_text = text.strip()
        if clean_text.startswith("/link"):
            clean_text = clean_text[5:].strip()

        if "&" in clean_text:
            parts = [p.strip() for p in clean_text.split("&", 1)]
            return Intent(
                operator=IntentOperator.LINK,
                arguments={"source": parts[0], "target": parts[1]},
                raw_query=text
            )
        elif clean_text:
            return Intent(
                operator=IntentOperator.LINK,
                arguments={"target": clean_text},
                raw_query=text
            )
        else:
            return Intent(
                operator=IntentOperator.LINK,
                arguments={"target": ""},
                raw_query=text
            )

    if text.startswith(">"):
        raw_val = text[1:].strip()
        try:
            val = float(raw_val)
            # If typed as 50 or 80, normalize to 0.5 / 0.8
            if val > 1.0:
                val = val / 100.0
            val = max(0.0, min(1.0, val))
            return Intent(operator=IntentOperator.APERTURE, arguments={"value": val})
        except ValueError:
            # Handle extension filters like > md
            return Intent(operator=IntentOperator.APERTURE, arguments={"filter": raw_val})

    if text.startswith("/tag "):
        tag = text[5:].strip()
        if tag.startswith("#"):
            tag = tag[1:]
        return Intent(IntentOperator.TAG, raw_query=text, arguments={"tag": tag})

    if text.startswith("/"):
        return Intent(IntentOperator.COMMAND, raw_query=text, arguments={"command": text[1:].strip()})

    return Intent(IntentOperator.SEARCH, raw_query=text)
