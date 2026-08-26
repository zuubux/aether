import re
import subprocess
from pathlib import Path

from extractors.archive import extract_zip, extract_tar, extract_archive_manifest, is_archive_file, get_archive_type
from extractors.office import extract_docx, extract_pptx, extract_xlsx, extract_legacy_doc
from extractors.notebook import extract_ipynb
from extractors.database import extract_sqlite
from extractors.config import extract_config, extract_desktop, extract_email, extract_vdf, extract_reg
from extractors.markdown import extract_markdown
from extractors.media import extract_audio, extract_video
from extractors.data import extract_json, extract_yaml, extract_toml, extract_csv, extract_sql
from extractors.devops import extract_dockerfile, extract_compose
from extractors.image import extract_svg
from extractors.envelope import extract_binary_envelope
from extractors.cloud import extract_gsuite

EXTRACTOR_VERSION = 32

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


def extract_archetype_and_snippet(path: Path, content_bytes: bytes, file_hash: str | None = None) -> tuple:
    if is_archive_file(path):
        archive_type = get_archive_type(path)
        if archive_type == "TAR":
            return extract_tar(str(path))
        else:
            return extract_zip(str(path))

    filename_lower = path.name.lower()
    if filename_lower in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        return extract_compose(path)
    if filename_lower in ("dockerfile", "containerfile"):
        return extract_dockerfile(path)

    ext = path.suffix.lower()
    
    if ext == '.svg':
        return extract_svg(path)
    elif ext in ('.docx', '.doc'):
        return extract_docx(path)
    elif ext in ('.pptx', '.ppt', '.odp'):
        return extract_pptx(path)
    elif ext in ('.xlsx', '.ods'):
        return extract_xlsx(path)
    elif ext == '.ipynb':
        return extract_ipynb(path)
    elif ext in ('.sqlite', '.db'):
        return extract_sqlite(path)
    elif ext in ('.ini', '.cfg', '.properties'):
        return extract_config(path)
    elif ext in ('.vdf', '.acf'):
        return extract_vdf(path)
    elif ext == '.reg':
        return extract_reg(path)
    elif ext == '.desktop':
        return extract_desktop(path)
    elif ext == '.eml':
        return extract_email(path)
    elif ext in ('.md', '.markdown'):
        return extract_markdown(path)
    elif ext in ('.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac'):
        return extract_audio(path, file_hash=file_hash)
    elif ext in ('.mp4', '.mkv', '.webm', '.mov', '.avi'):
        return extract_video(path, file_hash=file_hash)
    elif ext == '.json':
        return extract_json(path)
    elif ext in ('.yaml', '.yml'):
        return extract_yaml(path)
    elif ext == '.toml':
        return extract_toml(path)
    elif ext in ('.csv', '.tsv'):
        return extract_csv(path)
    elif ext == '.sql':
        return extract_sql(path)
    elif ext in ('.dockerfile', '.containerfile'):
        return extract_dockerfile(path)
    elif ext in ('.pcap', '.pcapng', '.iso', '.img', '.stl', '.obj', '.step', '.gcode', '.parquet', '.bin', '.exe', '.dll', '.so', '.dylib'):
        return extract_binary_envelope(path)
    elif ext in ('.gdoc', '.gsheet', '.gslides', '.gdraw'):
        return extract_gsuite(path)

    if ext in ('.txt', '.csv', '.tsv', '.json'):
        archetype = 'document'
    elif ext in ('.py', '.sh', '.rs', '.qml', '.js', '.ts', '.html', '.css', '.c', '.cpp', '.h'):
        archetype = 'code'
    elif ext in ('.so', '.bin', '.db', '.exe'):
        archetype = 'binary'
    elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp'):
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
