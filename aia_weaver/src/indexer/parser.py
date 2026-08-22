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


def extract_archetype_and_snippet(path: Path, content_bytes: bytes) -> tuple[str, str]:
    ext = path.suffix.lower()
    if ext in ('.md', '.txt'):
        archetype = 'document'
    elif ext in ('.py', '.rs', '.qml', '.js', '.ts', '.html', '.css', '.c', '.cpp', '.h'):
        archetype = 'code'
    elif ext in ('.so', '.bin', '.db', '.exe'):
        archetype = 'binary'
    elif ext in ('.tar', '.zip', '.gz'):
        archetype = 'archive'
    elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg'):
        archetype = 'image'
    else:
        archetype = 'binary'  # default fallback

    snippet = ""
    if archetype in ('document', 'code'):
        try:
            text = content_bytes.decode('utf-8', errors='ignore')
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if lines:
                if ext in ('.md', '.markdown'):
                    header_index = -1
                    for i, line in enumerate(lines):
                        if line.startswith('#'):
                            header_index = i
                            break
                    if header_index != -1:
                        header_line = lines[header_index]
                        following_lines = lines[header_index + 1 : header_index + 4]
                        if following_lines:
                            snippet = f"{header_line}\n" + "\n".join(following_lines)
                        else:
                            snippet = header_line
                        snippet = snippet[:300].strip()
                    else:
                        snippet = "\n".join(lines[:3])[:150].strip()
                else:
                    snippet = "\n".join(lines[:5])[:300].strip()
            
            # Ensure snippet is not empty if file actually has lines or is of text type
            if not snippet and lines:
                snippet = "\n".join(lines[:5])[:300].strip()
        except Exception:
            archetype = 'binary'
            snippet = ''

    if not snippet:
        size_kb = len(content_bytes) / 1024
        header_hex = content_bytes[:16].hex().upper() if content_bytes else ''
        snippet = f"{size_kb:.1f}KB | Header: {header_hex}"
    
    return archetype, snippet
