import os
import tarfile
import zipfile
from pathlib import Path
from typing import Any

ARCHIVE_ZIP_EXTENSIONS = {".zip", ".whl", ".jar", ".war", ".egg", ".apk", ".epub"}
ARCHIVE_TAR_EXTENSIONS = {".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"}
ARCHIVE_EXTENSIONS = ARCHIVE_ZIP_EXTENSIONS | ARCHIVE_TAR_EXTENSIONS

IGNORED_ARCHIVE_PATTERNS = ("__pycache__", ".pyc", ".DS_Store", "Thumbs.db", "META-INF", "__MACOSX")


def is_archive_file(path: Path | str) -> bool:
    """Check if the given path has a supported archive extension."""
    name = Path(path).name.lower()
    if any(name.endswith(ext) for ext in ARCHIVE_TAR_EXTENSIONS):
        return True
    ext = Path(path).suffix.lower()
    return ext in ARCHIVE_ZIP_EXTENSIONS or ext in ARCHIVE_TAR_EXTENSIONS


def get_archive_type(path: Path | str) -> str:
    """Return archive classification ('ZIP', 'TAR', or 'ARCHIVE')."""
    name = Path(path).name.lower()
    if any(name.endswith(ext) for ext in ARCHIVE_TAR_EXTENSIONS):
        return "TAR"
    ext = Path(path).suffix.lower()
    if ext in ARCHIVE_ZIP_EXTENSIONS:
        return "ZIP"
    return "ARCHIVE"


def format_bytes(size: int) -> str:
    """Format raw byte size into a human-readable string."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"


def _format_manifest(total_count: int, entries: list[str]) -> str:
    """Format total count and up to 6 entry names into unified visual manifest snippet."""
    filtered_entries = [e for e in entries if not any(p in e for p in IGNORED_ARCHIVE_PATTERNS)]
    display_entries = filtered_entries if filtered_entries else entries
    lines = [f"ARCHIVE: {total_count} files"]
    for entry in display_entries[:6]:
        lines.append(f"↳ {entry}")
    return "\n".join(lines)


def extract_zip(file_path: str | Path) -> tuple[str, str, None]:
    """Extract zip archive manifest into archetype and snippet."""
    try:
        with zipfile.ZipFile(str(file_path), "r") as zf:
            names = zf.namelist()
            snippet = _format_manifest(len(names), names)
            return "ARCHIVE", snippet, None
    except Exception:
        return "ARCHIVE", "", None


def extract_tar(file_path: str | Path) -> tuple[str, str, None]:
    """Extract tarball manifest into archetype and snippet."""
    try:
        with tarfile.open(str(file_path), "r:*") as tar:
            names = tar.getnames()
            snippet = _format_manifest(len(names), names)
            return "ARCHIVE", snippet, None
    except (tarfile.TarError, Exception):
        return "ARCHIVE", "", None


def _extract_zip_manifest(path: Path, max_entries: int = 500) -> tuple[int, int, list[str]]:
    """Extract zip manifest metadata without writing any payload to disk."""
    file_count = 0
    uncompressed_size = 0
    top_entries: list[str] = []

    with zipfile.ZipFile(path, mode="r") as zf:
        infolist = zf.infolist()
        total_items = len(infolist)
        for idx, info in enumerate(infolist):
            if idx >= max_entries:
                break
            file_count += 1
            uncompressed_size += getattr(info, "file_size", 0)
            if len(top_entries) < 10:
                name = info.filename
                if getattr(info, "is_dir", lambda: False)() and not name.endswith("/"):
                    name += "/"
                top_entries.append(name)
        
        # If total members exceed max_entries, reflect total count from header table if available
        if total_items > file_count:
            file_count = total_items

    return file_count, uncompressed_size, top_entries


def _extract_tar_manifest(path: Path, max_entries: int = 500) -> tuple[int, int, list[str]]:
    """Extract tar manifest metadata without writing any payload to disk."""
    file_count = 0
    uncompressed_size = 0
    top_entries: list[str] = []

    with tarfile.open(path, mode="r:*") as tf:
        for idx, member in enumerate(tf):
            if idx >= max_entries:
                break
            file_count += 1
            uncompressed_size += member.size
            if len(top_entries) < 10:
                name = member.name
                if member.isdir() and not name.endswith("/"):
                    name += "/"
                top_entries.append(name)

    return file_count, uncompressed_size, top_entries


def extract_archive_manifest(path: Path | str, max_entries: int = 500) -> dict[str, Any]:
    """Extract archive metadata and header manifest in zero-extract read-only mode."""
    target_path = Path(path)
    compressed_size = 0
    if target_path.exists():
        try:
            compressed_size = target_path.stat().st_size
        except OSError:
            compressed_size = 0

    file_count = 0
    uncompressed_size = 0
    top_entries: list[str] = []
    error_msg: str | None = None

    try:
        archive_type = get_archive_type(target_path)
        if archive_type == "ZIP":
            file_count, uncompressed_size, top_entries = _extract_zip_manifest(target_path, max_entries=max_entries)
        else:
            file_count, uncompressed_size, top_entries = _extract_tar_manifest(target_path, max_entries=max_entries)
    except (zipfile.BadZipFile, tarfile.ReadError, tarfile.CompressionError, OSError, EOFError) as exc:
        error_msg = str(exc)
    except Exception as exc:
        error_msg = f"Archive read error: {exc}"

    if error_msg:
        summary = f"0 items • {format_bytes(compressed_size)} on disk"
        manifest = f"[Error reading archive: {error_msg}]"
        snippet = f"{summary}\n{manifest}"
        return {
            "file_count": 0,
            "uncompressed_size": 0,
            "compressed_size": compressed_size,
            "manifest": manifest,
            "summary": summary,
            "snippet": snippet,
        }

    # Format top 10 manifest lines
    manifest_lines = []
    for item in top_entries:
        manifest_lines.append(item)
    
    if file_count > len(top_entries):
        remaining = file_count - len(top_entries)
        manifest_lines.append(f"... (+{remaining} more)")
    
    manifest_str = "\n".join(manifest_lines) if manifest_lines else "(Empty archive)"
    
    item_label = "item" if file_count == 1 else "items"
    summary_str = f"{file_count} {item_label} • {format_bytes(uncompressed_size)} uncompressed"
    snippet_str = f"{summary_str}\n{manifest_str}"

    return {
        "file_count": file_count,
        "uncompressed_size": uncompressed_size,
        "compressed_size": compressed_size,
        "manifest": manifest_str,
        "summary": summary_str,
        "snippet": snippet_str,
    }
