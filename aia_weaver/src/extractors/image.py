import re
import xml.etree.ElementTree as ET
from pathlib import Path


def extract_svg(path: Path | str) -> tuple[str, str, None]:
    """Extract canvas dimensions from SVG files using viewBox or width/height attributes."""
    path_obj = Path(path)
    filename = path_obj.name
    dimensions = "Unknown"

    try:
        content_bytes = path_obj.read_bytes()
        root = ET.fromstring(content_bytes)

        # 1. Check viewBox / viewbox attribute
        viewbox = None
        for k, v in root.attrib.items():
            if k.lower() == "viewbox":
                viewbox = v
                break

        if viewbox:
            parts = re.split(r"[\s,]+", viewbox.strip())
            if len(parts) == 4:
                w_str = parts[2].rstrip("px")
                h_str = parts[3].rstrip("px")
                try:
                    w_num = float(w_str)
                    h_num = float(h_str)
                    w_formatted = f"{int(w_num)}" if w_num.is_integer() else f"{w_num:g}"
                    h_formatted = f"{int(h_num)}" if h_num.is_integer() else f"{h_num:g}"
                    dimensions = f"{w_formatted}×{h_formatted}"
                except ValueError:
                    dimensions = f"{w_str}×{h_str}"

        # 2. Check width and height attributes if dimensions is still Unknown
        if dimensions == "Unknown":
            width = None
            height = None
            for k, v in root.attrib.items():
                if k.lower() == "width":
                    width = v
                elif k.lower() == "height":
                    height = v

            if width and height:
                w_str = width.strip().rstrip("px")
                h_str = height.strip().rstrip("px")
                try:
                    w_num = float(w_str)
                    h_num = float(h_str)
                    w_formatted = f"{int(w_num)}" if w_num.is_integer() else f"{w_num:g}"
                    h_formatted = f"{int(h_num)}" if h_num.is_integer() else f"{h_num:g}"
                    dimensions = f"{w_formatted}×{h_formatted}"
                except ValueError:
                    dimensions = f"{w_str}×{h_str}"
    except Exception:
        pass

    snippet = (
        f"<span class='title'>{filename}</span><br/>"
        f"<span class='label'>Canvas:</span> <span class='val'>{dimensions}</span>"
    )
    return "IMAGE", snippet, None
