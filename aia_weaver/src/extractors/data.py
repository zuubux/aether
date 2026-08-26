import csv
import json
import re
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

import yaml
from extractors.formatting import format_tabular_preview


def extract_json(path: Path | str) -> tuple[str, str, None]:
    """Extract summary from a JSON file (top-level keys, list item counts, nested key summaries)."""
    path_obj = Path(path)
    try:
        content = path_obj.read_text(encoding="utf-8", errors="ignore")
        data = json.loads(content)
    except Exception:
        return "CONFIG", "[Malformed JSON]", None

    lines = []
    if isinstance(data, dict):
        for k, v in list(data.items())[:12]:
            if isinstance(v, dict):
                if v:
                    keys_summary = ", ".join(list(v.keys())[:4])
                    if len(v) > 4:
                        keys_summary += "..."
                    lines.append(f"↳ {k}: {keys_summary}")
                else:
                    lines.append(f"↳ {k}: {{}}")
            elif isinstance(v, list):
                lines.append(f"↳ {k}: {len(v)} items")
            else:
                v_str = str(v)
                if len(v_str) > 50:
                    v_str = v_str[:47] + "..."
                lines.append(f"↳ {k}: {v_str}")
    elif isinstance(data, list):
        lines.append(f"Array ({len(data)} items)")
        for idx, item in enumerate(data[:6]):
            if isinstance(item, dict):
                keys_summary = ", ".join(list(item.keys())[:3])
                lines.append(f"↳ Item {idx+1}: {{{keys_summary}}}")
            else:
                item_str = str(item)
                if len(item_str) > 40:
                    item_str = item_str[:37] + "..."
                lines.append(f"↳ Item {idx+1}: {item_str}")
    else:
        lines.append(f"↳ {data}")

    snippet = "\n".join(lines) if lines else f"↳ {path_obj.name}"
    return "CONFIG", snippet, None


def extract_yaml(path: Path | str) -> tuple[str, str, None]:
    """Extract section keys and subkey counts from YAML files."""
    path_obj = Path(path)
    try:
        content = path_obj.read_text(encoding="utf-8", errors="ignore")
        data = yaml.safe_load(content)
    except Exception:
        return "CONFIG", "[Malformed YAML]", None

    lines = []
    if isinstance(data, dict):
        for k, v in list(data.items())[:12]:
            if isinstance(v, dict):
                lines.append(f"↳ {k}: {len(v)} keys")
            elif isinstance(v, list):
                lines.append(f"↳ {k}: {len(v)} items")
            else:
                v_str = str(v)
                if len(v_str) > 50:
                    v_str = v_str[:47] + "..."
                lines.append(f"↳ {k}: {v_str}")
    elif isinstance(data, list):
        lines.append(f"List ({len(data)} items)")
        for idx, item in enumerate(data[:6]):
            lines.append(f"↳ Item {idx+1}: {item}")
    else:
        lines.append(f"↳ {data}")

    snippet = "\n".join(lines) if lines else f"↳ {path_obj.name}"
    return "CONFIG", snippet, None


def extract_toml(path: Path | str) -> tuple[str, str, None]:
    """Extract [sections] and primary keys from TOML files."""
    path_obj = Path(path)
    try:
        content_bytes = path_obj.read_bytes()
        data = tomllib.loads(content_bytes.decode("utf-8", errors="ignore"))
    except Exception:
        return "CONFIG", "[Malformed TOML]", None

    lines = []
    if isinstance(data, dict):
        # Output top-level primitive key-value pairs
        for k, v in list(data.items()):
            if not isinstance(v, dict) and len(lines) < 12:
                v_str = str(v)
                if len(v_str) > 50:
                    v_str = v_str[:47] + "..."
                lines.append(f"↳ {k} = {v_str}")

        # Output [sections]
        for k, v in list(data.items()):
            if isinstance(v, dict) and len(lines) < 15:
                lines.append(f"[{k}]")
                for sub_k, sub_v in list(v.items())[:4]:
                    if not isinstance(sub_v, dict):
                        sub_v_str = str(sub_v)
                        if len(sub_v_str) > 40:
                            sub_v_str = sub_v_str[:37] + "..."
                        lines.append(f"↳ {sub_k} = {sub_v_str}")
                    else:
                        lines.append(f"↳ {sub_k} = {{...}}")

    snippet = "\n".join(lines) if lines else f"↳ {path_obj.name}"
    return "CONFIG", snippet, None



def extract_csv(path: Path | str) -> tuple[str, str, None]:
    """Extract tabular row preview from CSV/TSV files."""
    path_obj = Path(path)
    filename = path_obj.name
    rows = []

    try:
        delimiter = "\t" if path_obj.suffix.lower() == ".tsv" else ","
        with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
            if delimiter == ",":
                sample = f.readline()
                f.seek(0)
                if "\t" in sample and "," not in sample:
                    delimiter = "\t"
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                if row and any(cell.strip() for cell in row):
                    rows.append(row)
                    if len(rows) >= 8:
                        break
    except Exception:
        pass

    snippet = format_tabular_preview(filename, rows)
    return "DOCUMENT", snippet, None


def extract_sql(path: Path | str) -> tuple[str, str, None]:
    """Scan first 50 lines for DDL/DML operations and detected table names."""
    path_obj = Path(path)

    try:
        lines = []
        with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f):
                if idx >= 50:
                    break
                lines.append(line)
    except Exception:
        line1 = "<span class='label'>Tables:</span> <span class='val'>None</span>"
        line2 = "<span class='label'>Operations:</span> <span class='val'>None</span>"
        return "CODE", f"{line1}\n{line2}", None

    content = "".join(lines)

    ops_patterns = [
        ("CREATE TABLE", r"\bCREATE\s+TABLE\b"),
        ("ALTER TABLE", r"\bALTER\s+TABLE\b"),
        ("INSERT INTO", r"\bINSERT\s+INTO\b"),
        ("SELECT", r"\bSELECT\b"),
        ("UPDATE", r"\bUPDATE\b"),
        ("DROP TABLE", r"\bDROP\s+TABLE\b"),
        ("DELETE FROM", r"\bDELETE\s+FROM\b"),
        ("CREATE INDEX", r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\b"),
    ]

    detected_ops = []
    for op_name, pat in ops_patterns:
        if re.search(pat, content, re.IGNORECASE):
            detected_ops.append(op_name)

    table_pat = re.compile(
        r"\b(?:CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?|INSERT\s+INTO|ALTER\s+TABLE|FROM|UPDATE|JOIN)\s+[`\"]?([a-zA-Z0-9_]+)[`\"]?",
        re.IGNORECASE,
    )
    detected_tables = []
    keywords = {"SELECT", "SET", "WHERE", "VALUES", "INTO", "TABLE", "IF", "NOT", "EXISTS"}
    for match in table_pat.finditer(content):
        tbl = match.group(1)
        if tbl.upper() not in keywords and tbl not in detected_tables:
            detected_tables.append(tbl)

    ops_str = ", ".join(detected_ops[:5]) if detected_ops else "None"
    tables_str = ", ".join(detected_tables[:5]) if detected_tables else "None"

    line1 = f"<span class='label'>Tables:</span> <span class='val'>{tables_str}</span>"
    line2 = f"<span class='label'>Operations:</span> <span class='val'>{ops_str}</span>"

    snippet = f"{line1}\n{line2}"
    return "CODE", snippet, None
