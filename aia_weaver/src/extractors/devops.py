import json
import re
from pathlib import Path
import yaml


def _clean_exec(raw: str) -> str:
    if not raw or raw == "None":
        return "None"
    raw_s = raw.strip()
    if raw_s.startswith("[") and raw_s.endswith("]"):
        try:
            items = json.loads(raw_s)
            if isinstance(items, list):
                return " ".join(str(x) for x in items)
        except Exception:
            pass
        inner = raw_s[1:-1]
        parts = [p.strip().strip("'\"") for p in inner.split(",")]
        cleaned = " ".join(p for p in parts if p)
        return cleaned if cleaned else raw_s
    return raw_s


def extract_dockerfile(path: Path | str) -> tuple[str, str, None]:
    """Scan Dockerfile for FROM, EXPOSE, ENTRYPOINT/CMD, WORKDIR, and ENV instructions."""
    path_obj = Path(path)
    try:
        text = path_obj.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "CONFIG", "<span class='title'>Base: Unknown</span><br/>", None

    base_image = "Unknown"
    ports = []
    workdir = "N/A"
    entrypoint = ""
    cmd = ""

    for line in text.splitlines():
        line_s = line.strip()
        if not line_s or line_s.startswith("#"):
            continue

        if line_s.upper().startswith("FROM "):
            parts = line_s.split()
            if len(parts) >= 2:
                base_image = parts[1]
        elif line_s.upper().startswith("EXPOSE "):
            parts = line_s.split()[1:]
            ports.extend(parts)
        elif line_s.upper().startswith("WORKDIR "):
            workdir = line_s[8:].strip()
        elif line_s.upper().startswith("ENTRYPOINT "):
            entrypoint = line_s[11:].strip()
        elif line_s.upper().startswith("CMD "):
            cmd = line_s[4:].strip()

    ports_str = " ".join(ports) if ports else "None"
    exec_raw = entrypoint or cmd or "None"
    cleaned_exec = _clean_exec(exec_raw)

    line1 = f"<span class='title'>Base: {base_image}</span><br/>"
    line2 = f"<span class='label'>Exposed:</span> <span class='val'>{ports_str}</span><span class='dot'> • </span><span class='label'>Workdir:</span> <span class='val'>{workdir}</span><br/>"
    line3 = f"<span class='label'>Entrypoint:</span> <span class='val'>{cleaned_exec}</span>"

    snippet = f"{line1}\n{line2}\n{line3}"
    return "CONFIG", snippet, None


def extract_compose(path: Path | str) -> tuple[str, str, None]:
    """Extract list of services, primary ports, and volumes from docker-compose / compose files."""
    path_obj = Path(path)
    try:
        text = path_obj.read_text(encoding="utf-8", errors="ignore")
        data = yaml.safe_load(text)
    except Exception:
        return "CONFIG", f"<span class='title'>{path_obj.name}</span><br/>", None

    if not isinstance(data, dict):
        return "CONFIG", f"<span class='title'>{path_obj.name}</span><br/>", None

    services_dict = data.get("services", {})
    service_names = list(services_dict.keys()) if isinstance(services_dict, dict) else []

    ports = []
    if isinstance(services_dict, dict):
        for s_name, s_conf in services_dict.items():
            if isinstance(s_conf, dict):
                s_ports = s_conf.get("ports", [])
                if isinstance(s_ports, list):
                    for p in s_ports:
                        ports.append(str(p))

    services_str = ", ".join(service_names[:5]) if service_names else "None"
    ports_str = ", ".join(ports[:5]) if ports else "None"

    line1 = f"<span class='title'>Compose ({len(service_names)} services)</span><br/>"
    line2 = f"<span class='label'>Services:</span> <span class='val'>{services_str}</span><br/>"
    line3 = f"<span class='label'>Ports:</span> <span class='val'>{ports_str}</span>"

    snippet = f"{line1}\n{line2}\n{line3}"
    return "CONFIG", snippet, None
