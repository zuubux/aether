import configparser
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
import re


def extract_config(path: Path | str) -> tuple[str, str, None]:
    """Extract sections and key-value pairs from .ini, .cfg, and .properties files."""
    path_obj = Path(path)
    try:
        content = path_obj.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            return "CONFIG", "", None

        parser = configparser.ConfigParser(strict=False)
        parser.optionxform = str
        try:
            parser.read_string(content)
        except configparser.MissingSectionHeaderError:
            parser.read_string("[GLOBAL]\n" + content)

        sections_to_process = []
        if parser.defaults():
            sections_to_process.append("DEFAULT")
        for s in parser.sections():
            if s != "DEFAULT":
                sections_to_process.append(s)

        sections_to_process = sections_to_process[:3]

        lines = []
        for section in sections_to_process:
            lines.append(f"[{section}]")

            if section == "DEFAULT":
                items = list(parser.defaults().items())
            else:
                items = [(k, parser.get(section, k, raw=True)) for k in parser[section].keys()]

            kv_count = 0
            for k, val in items:
                if kv_count >= 4:
                    break
                k_lower = k.lower()
                is_sensitive = any(term in k_lower for term in ("pass", "secret", "key", "token"))
                if is_sensitive:
                    display_val = "••••••"
                else:
                    v_str = " ".join(str(val).splitlines()).strip()
                    if len(v_str) > 50:
                        display_val = v_str[:47] + "..."
                    else:
                        display_val = v_str
                lines.append(f"↳ {k} = {display_val}")
                kv_count += 1

        formatted_snippet = "\n".join(lines).strip()
        return "CONFIG", formatted_snippet, None
    except Exception:
        return "CONFIG", "", None



def extract_desktop(path: Path | str) -> tuple[str, str, None]:
    """Extract standard Desktop Entry fields (Comment, Exec, Categories) from .desktop files, skipping Name and boilerplate."""
    path_obj = Path(path)
    try:
        content = path_obj.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            return "CONFIG", "", None

        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read_string(content)

        entry_section = None
        if "Desktop Entry" in parser:
            entry_section = parser["Desktop Entry"]
        elif parser.sections():
            entry_section = parser[parser.sections()[0]]

        if entry_section is None:
            return "CONFIG", "", None

        lines = []
        key_map = {k.lower(): (k, v.strip()) for k, v in entry_section.items() if v.strip()}

        # Line 1 & Line 2: Comment and empty spacer if comment exists
        if "comment" in key_map:
            comment_val = key_map["comment"][1]
            if comment_val:
                lines.append(comment_val)
                lines.append("")

        ignored_keys = {"name", "comment", "type", "terminal", "icon", "version", "encoding"}

        subsequent_count = 0
        for orig_k, val in entry_section.items():
            if subsequent_count >= 3:
                break
            k_lower = orig_k.lower()
            if k_lower in ignored_keys:
                continue
            if not val.strip():
                continue
            display_k = orig_k[0].upper() + orig_k[1:] if orig_k else orig_k
            lines.append(f"↳ {display_k}: {val.strip()}")
            subsequent_count += 1

        formatted_snippet = "\n".join(lines).strip()
        return "CONFIG", formatted_snippet, None
    except Exception:
        return "CONFIG", "", None


def _format_email_date(date_raw: str | None) -> str:
    if not date_raw:
        return ""
    try:
        dt = parsedate_to_datetime(date_raw)
        return f"{dt.day} {dt.strftime('%b %Y')}"
    except Exception:
        return date_raw.strip()


def _format_email_from(from_raw: str | None) -> str:
    if not from_raw:
        return ""
    _, addr = parseaddr(from_raw)
    if addr.strip():
        return addr.strip()
    return from_raw.strip()


def extract_email(path: Path | str) -> tuple[str, str, None]:
    """Extract clean email summary (Subject, From, Date, and plain text body snippet) from .eml files."""
    path_obj = Path(path)
    try:
        content_bytes = path_obj.read_bytes()
        if not content_bytes.strip():
            return "EMAIL", "", None

        msg = BytesParser(policy=policy.default).parsebytes(content_bytes)

        from_val = _format_email_from(msg.get("From")) or "Unknown"
        to_val = _format_email_from(msg.get("To")) or "Unknown"
        date_val = _format_email_date(msg.get("Date"))
        subj_val = str(msg.get("Subject") or "").strip() or "No Subject"

        # Header Line 1: From -> To • Date
        line1 = (
            f"<span class='label'>From:</span> "
            f"<span class='val'>{from_val}</span> "
            f"<span class='arrow'>➔</span> "
            f"<span class='label'>To:</span> "
            f"<span class='val'>{to_val}</span>"
        )
        if date_val:
            line1 += f" <span class='dot'>•</span> <span class='date'>{date_val}</span>"

        # Header Line 2: Subject
        line2 = f"<span class='label'>Subject:</span> <span class='subject'>{subj_val}</span>"

        body_text = ""
        try:
            body_part = msg.get_body(preferencelist=("plain",))
            if body_part:
                body_text = body_part.get_content()
        except Exception:
            pass

        if not body_text:
            try:
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disp = str(part.get("Content-Disposition", ""))
                        if content_type == "text/plain" and "attachment" not in content_disp:
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or "utf-8"
                                body_text = payload.decode(charset, errors="ignore")
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or "utf-8"
                        body_text = payload.decode(charset, errors="ignore")
                    elif isinstance(msg.get_payload(), str):
                        body_text = msg.get_payload()
            except Exception:
                pass

        clean_body_lines = []
        if body_text:
            for line in body_text.splitlines():
                line_str = line.strip()
                if not line_str:
                    continue
                if line_str.startswith("--") or line_str.lower().startswith("content-type:") or line_str.lower().startswith("content-transfer-encoding:"):
                    continue
                clean_body_lines.append(line_str)

        body_clean = "<br/>".join(clean_body_lines[:4])
        formatted_snippet = f"{line1}<br/>{line2}<div class='body-text'>{body_clean}</div>"
        return "EMAIL", formatted_snippet, None
    except Exception:
        return "EMAIL", "", None



def extract_vdf(path: Path | str) -> tuple[str, str, None]:
    """Extract Valve KeyValues metadata from .vdf and .acf (Steam app manifests, library folders, configs)."""
    path_obj = Path(path)
    try:
        content = path_obj.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            return "CONFIG", "", None

        tokens = []
        for line in content.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("//"):
                continue
            for match in re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"|(\{|\})|(\/\/[^\n]*)|(\S+)', line_str):
                q, brace, comment, word = match.groups()
                if comment:
                    break
                if q is not None:
                    tokens.append(q.replace(r'\"', '"').replace(r'\\', '\\'))
                elif brace is not None:
                    tokens.append(brace)
                elif word is not None:
                    tokens.append(word)

        if not tokens:
            return "CONFIG", "", None

        kv_map = {}
        sections = []
        current_section_stack = []
        current_section_kvs = []

        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            if tok == "{":
                i += 1
                continue
            elif tok == "}":
                if current_section_stack:
                    sec_name = current_section_stack.pop()
                    if current_section_kvs:
                        sections.append((sec_name, current_section_kvs))
                        current_section_kvs = []
                i += 1
                continue

            if i + 1 < n and tokens[i + 1] == "{":
                current_section_stack.append(tok)
                i += 2
                continue
            elif i + 1 < n and tokens[i + 1] not in ("{", "}"):
                k = tok
                v = tokens[i + 1]
                kv_map[k.lower()] = (k, v)
                if current_section_stack:
                    current_section_kvs.append((k, v))
                else:
                    current_section_kvs.append((k, v))
                i += 2
            else:
                i += 1

        if current_section_kvs:
            sec_name = current_section_stack[-1] if current_section_stack else "GLOBAL"
            sections.append((sec_name, current_section_kvs))

        is_acf = (
            path_obj.suffix.lower() == ".acf"
            or path_obj.name.lower().startswith("appmanifest_")
            or "name" in kv_map
        )

        if is_acf and "name" in kv_map:
            name_val = kv_map["name"][1]
            appid_val = kv_map.get("appid", ("", ""))[1]
            buildid_val = kv_map.get("buildid", ("", ""))[1]
            installdir_val = kv_map.get("installdir", ("", ""))[1]

            lines = [f"<span class='title'>{name_val}</span>"]
            line2_parts = []
            if appid_val:
                line2_parts.append(f"<span class='label'>AppID:</span> <span class='val'>{appid_val}</span>")
            if buildid_val:
                line2_parts.append(f"<span class='label'>Build:</span> <span class='val'>{buildid_val}</span>")
            if line2_parts:
                lines.append(" <span class='dot'> • </span> ".join(line2_parts))

            if installdir_val:
                lines.append(f"<span class='label'>Install Dir:</span> <span class='val'>{installdir_val}</span>")

            formatted_snippet = "\n".join(lines).strip()
            return "CONFIG", formatted_snippet, None

        lines = []
        if sections:
            for sec_name, kvs in sections[:3]:
                lines.append(f"[{sec_name}]")
                kv_count = 0
                for k, val in kvs:
                    if kv_count >= 4:
                        break
                    k_lower = k.lower()
                    is_sensitive = any(term in k_lower for term in ("pass", "secret", "key", "token"))
                    if is_sensitive:
                        display_val = "••••••"
                    else:
                        v_str = " ".join(str(val).splitlines()).strip()
                        display_val = v_str[:47] + "..." if len(v_str) > 50 else v_str
                    lines.append(f"↳ {k} = {display_val}")
                    kv_count += 1
        elif kv_map:
            lines.append("[GLOBAL]")
            kv_count = 0
            for orig_k, val in kv_map.values():
                if kv_count >= 4:
                    break
                k_lower = orig_k.lower()
                is_sensitive = any(term in k_lower for term in ("pass", "secret", "key", "token"))
                if is_sensitive:
                    display_val = "••••••"
                else:
                    v_str = " ".join(str(val).splitlines()).strip()
                    display_val = v_str[:47] + "..." if len(v_str) > 50 else v_str
                lines.append(f"↳ {orig_k} = {display_val}")
                kv_count += 1

        formatted_snippet = "\n".join(lines).strip()
        return "CONFIG", formatted_snippet, None
    except Exception:
        return "CONFIG", "", None



def extract_reg(path: Path | str) -> tuple[str, str, None]:
    """Extract sections and key-value pairs from text-based Windows Registry (.reg) files."""
    path_obj = Path(path)
    try:
        content = path_obj.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            return "CONFIG", "", None

        raw_lines = content.splitlines()
        processed_lines = []
        curr = ""
        for l in raw_lines:
            s = l.strip()
            if curr:
                curr += s
            else:
                curr = s
            if curr.endswith("\\"):
                curr = curr[:-1].strip()
            else:
                processed_lines.append(curr)
                curr = ""
        if curr:
            processed_lines.append(curr)

        sections = []
        current_sec_name = None
        current_kvs = []

        header_prefixes = (
            "wine registry version",
            "windows registry editor version",
            ";",
            "#",
            "//",
        )

        for line in processed_lines:
            if not line:
                continue
            line_lower = line.lower()
            if any(line_lower.startswith(p) for p in header_prefixes):
                continue

            if line.startswith("[") and line.endswith("]"):
                if current_sec_name and current_kvs:
                    sections.append((current_sec_name, current_kvs))
                    current_kvs = []
                current_sec_name = line[1:-1].strip()
                continue

            kv_match = re.match(r'^(?:"([^"]+)"|(@))\s*=\s*(.*)$', line)
            if kv_match:
                k_quoted, k_at, val_raw = kv_match.groups()
                key = k_quoted if k_quoted is not None else (k_at or "@")
                val = val_raw.strip()
                if val.startswith('"') and val.endswith('"') and len(val) >= 2:
                    val = val[1:-1].replace(r'\"', '"').replace(r'\\', '\\')

                if current_sec_name is None:
                    current_sec_name = "GLOBAL"

                current_kvs.append((key, val))

        if current_sec_name and current_kvs:
            sections.append((current_sec_name, current_kvs))

        valid_sections = [(s_name, kvs) for s_name, kvs in sections if kvs]
        if not valid_sections:
            return "CONFIG", "", None

        lines = []
        for sec_name, kvs in valid_sections[:3]:
            lines.append(f"[{sec_name}]")
            kv_count = 0
            for k, val in kvs:
                if kv_count >= 3:
                    break
                k_lower = k.lower()
                is_sensitive = any(term in k_lower for term in ("pass", "secret", "key", "token"))
                if is_sensitive:
                    display_val = "••••••"
                else:
                    v_str = " ".join(str(val).splitlines()).strip()
                    display_val = v_str[:47] + "..." if len(v_str) > 50 else v_str
                lines.append(f"↳ <span class='key'>{k}:</span> <span class='val'>{display_val}</span>")
                kv_count += 1

        formatted_snippet = "\n".join(lines).strip()
        return "CONFIG", formatted_snippet, None
    except Exception:
        return "CONFIG", "", None
