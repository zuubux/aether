import re
import os
import html
import hashlib
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from extractors.formatting import format_tabular_preview

def _strip_namespaces(root: ET.Element):
    """Cleanly strip OpenXML namespaces from elements in-memory."""
    for el in root.iter():
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]

def _is_memo_header(line: str) -> bool:
    return bool(re.match(r'^\s*(To|From|Date|Subject|CC|RE|FAX|TEL)\s*:', line, re.IGNORECASE))

def _format_paragraph_blocks(paragraphs: list[str]) -> str:
    blocks = []
    current_header_lines = []
    for p in paragraphs:
        if _is_memo_header(p):
            current_header_lines.append(p)
        else:
            if current_header_lines:
                blocks.append('\n'.join(current_header_lines))
                current_header_lines = []
            blocks.append(p)
    if current_header_lines:
        blocks.append('\n'.join(current_header_lines))
    return '\n\n'.join(blocks)

def extract_legacy_doc(file_path: Path | str) -> tuple[str, str]:
    """Extract text snippet from legacy OLE2 binary Office documents (.doc / .ppt)."""
    path = Path(file_path)
    arch = "PRESENTATION" if path.suffix.lower() in ('.ppt', '.pptx') else "DOCX"
    try:
        data = path.read_bytes()
        if not data.startswith(b'\xD0\xCF\x11\xE0'):
            return arch, ""

        # Extract UTF-16LE blocks first (common in OLE2 presentation & document streams)
        utf16_blocks = re.findall(rb'(?:[\x09\x20-\x7E]\x00){4,}', data)
        # Extract printable byte blocks (ASCII) using regex
        ascii_blocks = re.findall(rb'[\x20-\x7E\t\n\r]{4,}', data)

        raw_strings = []
        for b in utf16_blocks:
            try:
                raw_strings.append(b.decode('utf-16le', errors='ignore'))
            except Exception:
                pass
        for b in ascii_blocks:
            try:
                raw_strings.append(b.decode('ascii', errors='ignore'))
            except Exception:
                pass

        skip_words = [
            'normal.dot', 'normal', 'table normal', 'no list', 'microsoft', 'worddocument',
            'root entry', 'summaryinformation', 'documentsummaryinformation', 'compobj',
            'objectpool', 'msworddoc', 'title', 'author', 'template', 'lastsavedby',
            'revisionnumber', 'totaleditingtime', 'created', 'lastsaved', 'lastprinted',
            'numberofpages', 'numberofwords', 'numberofchars', 'security', 'urn:schemas',
            'http://', 'https://', 'ihdr', 'plte', 'idat', 'phys', 'gama', 'srgb', 'bjbj',
            'visio', 'font', 'times new', 'arial', 'wingdings', '___ppt', 'paint.picture',
            'drawing', 'unknown', 'symbol', '1table', 'bitmap image', 'new roman', 'roman'
        ]

        paragraphs = []
        for s in raw_strings:
            lines = [line.rstrip() for line in re.split(r'[\r\n]+', s)]
            for line in lines:
                if not line or len(line.strip()) < 4:
                    continue
                line_lower = line.lower()
                if any(sk in line_lower for sk in skip_words):
                    continue

                if any(c in line for c in '{}^\\~|[]<>@#$%&*+=/'):
                    continue

                valid_chars = sum(1 for c in line if c.isalnum() or c.isspace() or c in '.,!?-:;()\'\"')
                if valid_chars / len(line) < 0.8:
                    continue

                letters = [c for c in line if c.isalpha()]
                if len(letters) < 3:
                    continue
                vowel_count = sum(1 for c in letters if c.lower() in 'aeiouy')
                if vowel_count / len(letters) < 0.15:
                    continue

                words = line.split()
                if len(words) == 1:
                    w = words[0]
                    if not (w.istitle() or w.isupper() or w.islower()):
                        continue
                    if len(w) < 4:
                        continue

                if line not in paragraphs:
                    paragraphs.append(line)
                    if len(paragraphs) >= 12:
                        break
            if len(paragraphs) >= 12:
                break

        snippet = _format_paragraph_blocks(paragraphs)
        return arch, snippet
    except Exception as e:
        print("Error extract_legacy_doc:", e)
        return arch, ""

def extract_docx(path: Path | str) -> tuple[str, str]:
    path = Path(path)
    try:
        with zipfile.ZipFile(path, 'r') as zf:
            if 'word/document.xml' in zf.namelist():
                xml_content = zf.read('word/document.xml')
                root = ET.fromstring(xml_content)
                _strip_namespaces(root)
                
                paragraphs = []
                for p in root.findall('.//p'):
                    p_parts = []
                    for child in p.iter():
                        tag = child.tag
                        if tag == 't' or tag.endswith('}t') or tag.endswith(':t'):
                            if child.text:
                                p_parts.append(child.text)
                        elif tag == 'tab' or tag.endswith('}tab') or tag.endswith(':tab'):
                            p_parts.append('\t')
                        elif tag == 'br' or tag.endswith('}br') or tag.endswith(':br'):
                            p_parts.append('\n')

                    p_str = "".join(p_parts).rstrip()
                    if p_str and p_str.strip():
                        paragraphs.append(p_str)
                        if len(paragraphs) >= 12:
                            break
                            
                snippet = _format_paragraph_blocks(paragraphs)
                return "DOCX", snippet
    except zipfile.BadZipFile:
        return extract_legacy_doc(path)
    except Exception as e:
        print("Error extract_docx:", e)
        pass
    return "DOCX", ""


def extract_pptx(path: Path | str, *args, **kwargs) -> tuple[str, str, str | None]:
    """Extract deck title, slide count, and embedded slide thumbnail from PPTX/ODP files."""
    path_obj = Path(path)
    filename = path_obj.name

    if not zipfile.is_zipfile(path_obj):
        return ("DOCUMENT", "<span class='label'>Type:</span> <span class='val'>Legacy PowerPoint Presentation</span>", None)

    deck_title = None
    slide_count = 0
    thumb_path = None

    try:
        with zipfile.ZipFile(path_obj, 'r') as zf:
            # Check for embedded thumbnail
            thumb_name = None
            for cand in ('docProps/thumbnail.jpeg', 'docProps/thumbnail.png', 'docProps/thumbnail.jpg'):
                if cand in zf.namelist():
                    thumb_name = cand
                    break

            if thumb_name:
                try:
                    thumb_bytes = zf.read(thumb_name)
                    file_hash = hashlib.sha256(path_obj.read_bytes()).hexdigest()
                    cache_dir = Path.home() / ".cache" / "aether" / "thumbnails"
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    out_path = cache_dir / f"pptx_{file_hash}.jpg"
                    out_path.write_bytes(thumb_bytes)
                    thumb_path = str(out_path)
                except Exception:
                    thumb_path = None

            # Count slides in ppt/slides/slide*.xml
            slide_count = sum(
                1 for name in zf.namelist()
                if name.startswith('ppt/slides/slide') and name.endswith('.xml')
            )

            # ODP fallback for slides count
            if slide_count == 0 and 'content.xml' in zf.namelist():
                c_content = zf.read('content.xml')
                c_root = ET.fromstring(c_content)
                for elem in c_root.iter():
                    if elem.tag == 'page' or elem.tag.endswith('}page'):
                        slide_count += 1

            # Extract deck title from docProps/core.xml (<dc:title>)
            if 'docProps/core.xml' in zf.namelist():
                core_content = zf.read('docProps/core.xml')
                core_root = ET.fromstring(core_content)
                for elem in core_root.iter():
                    if elem.tag == 'title' or elem.tag.endswith('}title'):
                        if elem.text and elem.text.strip():
                            deck_title = elem.text.strip()
                            break
            elif 'meta.xml' in zf.namelist():
                # ODP meta fallback
                meta_content = zf.read('meta.xml')
                meta_root = ET.fromstring(meta_content)
                for elem in meta_root.iter():
                    if elem.tag == 'title' or elem.tag.endswith('}title'):
                        if elem.text and elem.text.strip():
                            deck_title = elem.text.strip()
                            break
    except Exception:
        pass

    title_display = deck_title if deck_title else filename
    snippet = (
        f"<span class='title'>{title_display}</span><br/>"
        f"<span class='label'>Deck:</span> <span class='val'>{slide_count} slides</span>"
    )
    return "DOCUMENT", snippet, thumb_path


def extract_xlsx(path: Path | str) -> tuple[str, str, None]:
    """Extract tabular row preview from XLSX/ODS files."""
    path_obj = Path(path)
    sheet_name = "Sheet1"
    shared_strings = []
    rows = []

    def _tag(elem: ET.Element) -> str:
        return elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

    if not zipfile.is_zipfile(path_obj):
        return "DOCUMENT", f"<span class='label'>Sheet:</span> <span class='val'>{html.escape(sheet_name)}</span>", None

    try:
        with zipfile.ZipFile(path_obj, 'r') as zf:
            # 1. Parse sharedStrings.xml if present
            if 'xl/sharedStrings.xml' in zf.namelist():
                try:
                    ss_content = zf.read('xl/sharedStrings.xml')
                    ss_root = ET.fromstring(ss_content)
                    _strip_namespaces(ss_root)
                    for si in ss_root.iter():
                        if _tag(si) == 'si':
                            val = "".join([t.text for t in si.iter() if (_tag(t) == 't' or t.tag.endswith('t')) and t.text])
                            shared_strings.append(val)
                except Exception:
                    pass

            # 2. Extract sheet_name from workbook.xml or content.xml
            if 'xl/workbook.xml' in zf.namelist():
                try:
                    wb_content = zf.read('xl/workbook.xml')
                    wb_root = ET.fromstring(wb_content)
                    _strip_namespaces(wb_root)
                    for elem in wb_root.iter():
                        if (_tag(elem) == 'sheet' or elem.tag.endswith('sheet')) and elem.get('name'):
                            sheet_name = elem.get('name')
                            break
                except Exception:
                    pass
            elif 'content.xml' in zf.namelist():
                try:
                    content = zf.read('content.xml')
                    root = ET.fromstring(content)
                    _strip_namespaces(root)
                    for elem in root.iter():
                        if (_tag(elem) == 'table' or elem.tag.endswith('table')) and elem.get('name'):
                            sheet_name = elem.get('name')
                            break
                except Exception:
                    pass

            # 3. Stream worksheet XML (e.g. xl/worksheets/sheet1.xml)
            sheet_file = None
            if 'xl/worksheets/sheet1.xml' in zf.namelist():
                sheet_file = 'xl/worksheets/sheet1.xml'
            else:
                ws_files = [f for f in zf.namelist() if f.startswith('xl/worksheets/sheet') and f.endswith('.xml')]
                if ws_files:
                    sheet_file = sorted(ws_files)[0]

            if sheet_file:
                try:
                    with zf.open(sheet_file) as f:
                        total_rows_scanned = 0
                        for event, elem in ET.iterparse(f, events=('end',)):
                            tag = _tag(elem)
                            if tag == 'row' or elem.tag.endswith('row'):
                                _strip_namespaces(elem)
                                total_rows_scanned += 1
                                row_cells = []
                                cells = [c for c in elem if _tag(c) == 'c' or c.tag.endswith('c')]
                                if not cells:
                                    cells = [c for c in elem.iter() if (_tag(c) == 'c' or c.tag.endswith('c')) and c is not elem]
                                for c in cells:
                                    if len(row_cells) >= 8:
                                        break
                                    cell_type = c.get('t', '')
                                    is_inline = cell_type == 'inlineStr' or any(_tag(child) == 'is' or child.tag.endswith('is') for child in c)
                                    val = ""
                                    if cell_type == 's':
                                        v_elem = next((child for child in c.iter() if _tag(child) == 'v' or child.tag.endswith('v')), None)
                                        if v_elem is not None and v_elem.text is not None:
                                            try:
                                                idx = int(v_elem.text.strip())
                                                if 0 <= idx < len(shared_strings):
                                                    val = shared_strings[idx]
                                                else:
                                                    val = v_elem.text.strip()
                                            except ValueError:
                                                val = v_elem.text.strip()
                                    elif is_inline:
                                        t_nodes = [t for t in c.iter() if (_tag(t) == 't' or t.tag.endswith('t')) and t.text]
                                        if t_nodes:
                                            val = "".join([t.text for t in t_nodes])
                                        else:
                                            v_elem = next((child for child in c.iter() if _tag(child) == 'v' or child.tag.endswith('v')), None)
                                            if v_elem is not None and v_elem.text is not None:
                                                val = v_elem.text.strip()
                                    elif cell_type == 'str':
                                        v_elem = next((child for child in c.iter() if _tag(child) == 'v' or child.tag.endswith('v')), None)
                                        if v_elem is not None and v_elem.text is not None:
                                            val = v_elem.text.strip()
                                        else:
                                            t_nodes = [t for t in c.iter() if (_tag(t) == 't' or t.tag.endswith('t')) and t.text]
                                            if t_nodes:
                                                val = "".join([t.text for t in t_nodes])
                                    elif cell_type == 'b':
                                        v_elem = next((child for child in c.iter() if _tag(child) == 'v' or child.tag.endswith('v')), None)
                                        if v_elem is not None and v_elem.text is not None:
                                            v_str = v_elem.text.strip()
                                            if v_str in ('1', 'true', 'TRUE'):
                                                val = "TRUE"
                                            elif v_str in ('0', 'false', 'FALSE'):
                                                val = "FALSE"
                                            else:
                                                val = v_str
                                    else:
                                        v_elem = next((child for child in c.iter() if _tag(child) == 'v' or child.tag.endswith('v')), None)
                                        if v_elem is not None and v_elem.text is not None:
                                            val = v_elem.text.strip()
                                        else:
                                            t_nodes = [t for t in c.iter() if (_tag(t) == 't' or t.tag.endswith('t')) and t.text]
                                            if t_nodes:
                                                val = "".join([t.text for t in t_nodes])
                                    row_cells.append(val.strip())
                                while row_cells and not row_cells[-1]:
                                    row_cells.pop()
                                if any(row_cells):
                                    rows.append(row_cells)
                                elem.clear()
                                if len(rows) >= 8 or total_rows_scanned >= 20:
                                    break
                except Exception:
                    pass
    except Exception:
        pass

    snippet = format_tabular_preview(sheet_name, rows)
    return "DOCUMENT", snippet, None
