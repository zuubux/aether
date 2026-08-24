import re
import subprocess
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


def extract_archetype_and_snippet(path: Path, content_bytes: bytes) -> tuple[str, str]:
    ext = path.suffix.lower()
    if ext in ('.md', '.txt', '.csv', '.tsv', '.json'):
        archetype = 'document'
    elif ext in ('.py', '.sh', '.rs', '.qml', '.js', '.ts', '.html', '.css', '.c', '.cpp', '.h'):
        archetype = 'code'
    elif ext in ('.so', '.bin', '.db', '.exe'):
        archetype = 'binary'
    elif ext in ('.tar', '.zip', '.gz'):
        archetype = 'archive'
    elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico'):
        archetype = 'image'
    elif ext == '.pdf':
        archetype = 'document'
    else:
        archetype = 'binary'  # default fallback

    snippet = ""
    size_kb = len(content_bytes) / 1024

    if ext == '.pdf':
        try:
            # Extract first page text
            result = subprocess.run(
                ["pdftotext", "-f", "1", "-l", "1", str(path), "-"],
                capture_output=True, text=True, check=True
            )
            text = result.stdout.strip()
            if text:
                snippet = text[:1000]
        except Exception:
            pass
        if not snippet:
            snippet = f"PDF Document | {size_kb:.1f}KB"
            
    elif archetype in ('document', 'code'):
        try:
            text = content_bytes.decode('utf-8', errors='ignore').strip()
            if text:
                snippet = text[:1000]
        except Exception:
            pass

    if not snippet:
        header_hex = content_bytes[:16].hex().upper() if content_bytes else ''
        snippet = f"{size_kb:.1f}KB | Header: {header_hex}"
    
    return archetype, snippet
