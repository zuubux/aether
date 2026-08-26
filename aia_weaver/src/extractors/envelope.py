import html
import stat
from datetime import datetime, timezone
from pathlib import Path


def format_size(size_bytes: int) -> str:
    """Format size in bytes into human-readable string (e.g., 412.4 MB, 4.2 GB, 12.8 KB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_permissions(mode: int) -> str:
    """Format st_mode permissions into string like 'rw-r--r--' or 'rwxr-xr-x'."""
    try:
        perms = stat.filemode(mode)
        if len(perms) == 10 and perms[0] in "-dlsbc":
            return perms[1:]
        return perms
    except Exception:
        return "rw-r--r--"


def detect_binary_type(path_obj: Path) -> str:
    """Determine high-level MIME / format descriptor based on file extension / magic heuristics."""
    ext = path_obj.suffix.lower()
    if ext in ('.pcap', '.pcapng'):
        return "Packet Capture"
    elif ext in ('.iso', '.img'):
        return "Disk Image"
    elif ext in ('.stl', '.obj', '.step'):
        return "3D Geometry Model"
    elif ext == '.gcode':
        return "CNC / Slicer Toolpath"
    elif ext == '.parquet':
        return "Parquet Columnar Data"
    elif ext in ('.exe', '.dll'):
        return "PE Binary Executable / DLL"
    elif ext in ('.so', '.dylib', '.bin'):
        return "Binary / Shared Object"

    # Magic heuristics fallback
    if path_obj.exists() and path_obj.is_file():
        try:
            with open(path_obj, "rb") as f:
                header = f.read(16)
                if header.startswith(b"MZ"):
                    return "PE Binary Executable / DLL"
                elif header.startswith(b"\x7fELF"):
                    return "Binary / Shared Object"
                elif header.startswith(b"PAR1"):
                    return "Parquet Columnar Data"
                elif header.startswith((b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x0a\x0d\x0d\x0a")):
                    return "Packet Capture"
        except Exception:
            pass

    return "Binary File"


def extract_binary_envelope(path: Path | str) -> tuple[str, str, None]:
    """
    Extracts binary envelope metadata: OS stat metadata (size, perms, mtime),
    human-readable byte size, and format descriptor.
    Returns ("BINARY", formatted_snippet, None).
    """
    p = Path(path)
    filename = p.name

    size_bytes = 0
    perms = "rw-r--r--"
    mtime_str = ""

    if p.exists():
        try:
            st = p.stat()
            size_bytes = st.st_size
            perms = format_permissions(st.st_mode)
            mtime_dt = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
            mtime_str = mtime_dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    formatted_size = format_size(size_bytes)
    type_desc = detect_binary_type(p)

    line1 = f"<span class='title'>{filename}</span><br/>"
    line2 = f"<span class='label'>Type:</span> <span class='val'>{type_desc}</span><span class='dot'> • </span><span class='val'>{formatted_size}</span><span class='dot'> • </span><span class='val'>{perms}</span>"

    formatted_snippet = f"{line1}{line2}"
    return ("BINARY", formatted_snippet, None)
