import re
from pathlib import Path

# Matches [[Target]] or [[Target|Alias]]
WIKILINK_PATTERN = re.compile(r"\[\[(.*?)\]\]")


def extract_explicit_links(file_content: str) -> list[str]:
    """Parses text content and extracts raw [[WikiLink]] target names."""
    found_targets = []
    for match in WIKILINK_PATTERN.finditer(file_content):
        # Extract target name before any pipe character | (e.g. [[Note|Alias]])
        raw_target = match.group(1).split("|")[0].strip()
        if raw_target:
            found_targets.append(raw_target)
    return found_targets