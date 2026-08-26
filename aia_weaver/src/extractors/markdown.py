import re
from pathlib import Path


def extract_markdown(path: Path | str) -> tuple[str, str, None]:
    """Extract clean Markdown snippet with wikilinks transformed into semantic HTML spans."""
    path_obj = Path(path)
    try:
        content = path_obj.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            return "DOCUMENT", "", None

        # Replace [[target]] with <span class='wikilink'>target</span>
        transformed = re.sub(r"\[\[(.*?)\]\]", r"<span class='wikilink'>\1</span>", content)

        # Preserve document headings and body text lines in RichText by using <br/> for newlines
        formatted_snippet = transformed.replace("\n", "<br/>")

        return "DOCUMENT", formatted_snippet, None
    except Exception:
        return "DOCUMENT", "", None
