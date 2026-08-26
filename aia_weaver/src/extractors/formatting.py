import html
import re
from typing import Sequence

GENERIC_VALUES = {
    "unknown",
    "unknown artist",
    "unknown title",
    "unknown album",
    "unknown track",
    "unknown codec",
    "unknown resolution",
    "n/a",
    "none",
    "null",
    "undefined",
}

_TAG_RE = re.compile(r"<[^>]*>")


def is_generic_or_empty(val: str | None) -> bool:
    """Check if a string value is None, empty, whitespace-only, or a generic fallback placeholder."""
    if val is None:
        return True
    s = str(val).strip()
    if not s:
        return True
    clean_text = _TAG_RE.sub("", s).strip().lower()
    if not clean_text or clean_text in GENERIC_VALUES or clean_text.startswith("unknown"):
        return True
    return False


def format_duration(seconds: float | int | None, default: str = "00:00") -> str:
    """
    Format duration in seconds.
    - If None or <= 0: return default ("00:00" or "0s" depending on context).
    - < 10.0 seconds: return fractional seconds with 1 decimal (e.g. 0.4s, 2.8s).
    - 10.0s to 59.9s: return "00:SS" (e.g. "00:42").
    - >= 60.0s: return "MM:SS" (or "HH:MM:SS" for >= 1 hour).
    """
    if seconds is None or seconds <= 0:
        return default
    if seconds < 10.0:
        return f"{seconds:.1f}s"

    total_secs = int(seconds)
    hrs = total_secs // 3600
    mins = (total_secs % 3600) // 60
    secs = total_secs % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_dot_list(*items: str | None) -> str:
    """
    Filter out None, empty strings, and generic strings (e.g., 'Unknown Artist', 'Unknown', 'N/A').
    Join remaining items with '<span class=\'dot\'> • </span>'.
    """
    if len(items) == 1 and isinstance(items[0], (list, tuple)):
        raw_items: Sequence[str | None] = items[0]
    else:
        raw_items = items

    valid_items = [str(item).strip() for item in raw_items if not is_generic_or_empty(item)]
    return "<span class='dot'> • </span>".join(valid_items)


def format_meta_row(label: str, value: str | None, css_class: str = "val") -> str:
    """
    Format a metadata row.
    If value is None, empty, or generic fallback ('Unknown Artist', etc.), return empty string "".
    Otherwise return "<span class='label'>{label}</span> <span class='{css_class}'>{value}</span>".
    """
    if is_generic_or_empty(value):
        return ""
    val_str = str(value).strip()
    return f"<span class='label'>{label}</span> <span class='{css_class}'>{val_str}</span>"


def format_tabular_preview(sheet_or_name: str, rows: list[list[str]], max_rows: int = 8) -> str:
    """
    Format tabular rows into a unified, clean monospace preview block with dynamic line budget.
    Template:
    Line 1: <span class='label'>Sheet:</span> <span class='val'>{sheet_or_name}</span> <span class='dim'>({fitted_cols}/{total_cols} cols)</span><br/>
    Followed by up to max_rows rendered inside <pre>:
    Col1           Col2           Col3           Col4
    10.0.30.1      wrath.bux.net  LAN            Physical
    """
    sheet_escaped = html.escape(str(sheet_or_name))

    valid_rows = []
    for r in rows:
        if any(c is not None and str(c).strip() for c in r):
            valid_rows.append(r)
            if len(valid_rows) >= max_rows:
                break

    if not valid_rows:
        return f"<span class='label'>Sheet:</span> <span class='val'>{sheet_escaped}</span>"

    MAX_LINE_CHARS = 58
    total_cols = max(len(r) for r in valid_rows)

    col_widths = []
    for i in range(total_cols):
        lens = [len(str(r[i])) for r in valid_rows if i < len(r) and r[i] is not None]
        col_w = min(max(lens, default=0), 18) + 2
        col_widths.append(col_w)

    cum_width = 0
    fitted_cols = 0
    for w in col_widths:
        if cum_width + w <= MAX_LINE_CHARS:
            cum_width += w
            fitted_cols += 1
        else:
            break

    if fitted_cols == 0 and total_cols > 0:
        fitted_cols = 1

    if fitted_cols < total_cols:
        header_line = (
            f"<span class='label'>Sheet:</span> "
            f"<span class='val'>{sheet_escaped}</span> "
            f"<span class='dim'>({fitted_cols}/{total_cols} cols)</span><br/>"
        )
    else:
        header_line = f"<span class='label'>Sheet:</span> <span class='val'>{sheet_escaped}</span><br/>"

    lines = []
    for r in valid_rows:
        row_parts = []
        for i in range(fitted_cols):
            val = str(r[i]) if (i < len(r) and r[i] is not None) else ""
            w = col_widths[i]
            row_parts.append(f"{val[:18]:<{w}}")
        row_str = "".join(row_parts).rstrip()
        lines.append(html.escape(row_str))

    table_text = "\n".join(lines)
    pre_style = (
        "margin-top: 8px; "
        "font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Consolas', monospace; "
        "font-size: 11px; "
        "line-height: 1.6; "
        "letter-spacing: 0.2px; "
        "color: #E2E8F0;"
    )
    return f"{header_line}<pre style=\"{pre_style}\">{table_text}</pre>"


