import json
import re
from pathlib import Path

BASE64_PATTERN = re.compile(r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+|[A-Za-z0-9+/=]{100,}')

def extract_ipynb(path: Path) -> tuple[str, str]:
    try:
        content = path.read_text(encoding='utf-8', errors='ignore')
        notebook = json.loads(content)
        cells = notebook.get('cells', [])
        
        snippet_parts = []
        md_count = 0
        code_count = 0
        
        for cell in cells:
            cell_type = cell.get('cell_type')
            source = cell.get('source', [])
            if isinstance(source, list):
                source = "".join(source)
            elif not isinstance(source, str):
                source = str(source)
                
            # Clean base64 strings
            source = BASE64_PATTERN.sub('[binary data]', source).strip()
            if not source:
                continue
            
            if cell_type == 'markdown' and md_count < 2:
                formatted = source[:200] + ("..." if len(source) > 200 else "")
                snippet_parts.append(formatted)
                md_count += 1
            elif cell_type == 'code' and code_count < 2:
                formatted = source[:300] + ("..." if len(source) > 300 else "")
                code_count += 1
                lines = formatted.splitlines()
                if lines:
                    prefix = f"In [{code_count}]: "
                    indent = " " * len(prefix)
                    code_block = prefix + lines[0] + ("\n" + "\n".join(indent + l for l in lines[1:]) if len(lines) > 1 else "")
                    snippet_parts.append(code_block)
                
            if md_count >= 2 and code_count >= 2:
                break
                
        snippet = "\n\n".join(snippet_parts)
        if not snippet:
            snippet = "Empty Notebook"
            
        return "NOTEBOOK", snippet
    except Exception:
        pass
    return "NOTEBOOK", ""
