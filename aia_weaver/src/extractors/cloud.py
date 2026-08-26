import json
from pathlib import Path
from urllib.parse import urlparse


def extract_gsuite(path: Path | str) -> tuple[str, str, None]:
    """Safely read and parse local Google Workspace pointer files (.gdoc, .gsheet, .gslides, .gdraw)."""
    path_obj = Path(path)
    filename = path_obj.name
    ext = path_obj.suffix.lower()

    if ext == ".gdoc":
        app_type = "Google Docs"
    elif ext == ".gsheet":
        app_type = "Google Sheets"
    elif ext == ".gslides":
        app_type = "Google Slides"
    elif ext == ".gdraw":
        app_type = "Google Drawings"
    else:
        app_type = "Google Drive"

    account = "Workspace"
    try:
        if path_obj.is_file():
            content = path_obj.read_text(encoding="utf-8", errors="ignore")
            data = json.loads(content)
            if isinstance(data, dict):
                email = data.get("email")
                if isinstance(email, str) and email.strip():
                    account = email.strip()
                else:
                    url = data.get("url")
                    if isinstance(url, str) and url.strip():
                        parsed = urlparse(url.strip())
                        if parsed.netloc:
                            account = parsed.netloc
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        pass

    snippet = (
        f"<span class='title'>{filename}</span><br/>"
        f"<span class='label'>Cloud:</span> <span class='val'>{app_type}</span>"
        f"<span class='dot'> • </span><span class='val'>{account}</span>"
    )

    return "DOCUMENT", snippet, None
