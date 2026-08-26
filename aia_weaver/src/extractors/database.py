import sqlite3
import urllib.parse
from pathlib import Path

def extract_sqlite(path: Path) -> tuple[str, str]:
    try:
        abs_path = str(path.absolute())
        safe_path = urllib.parse.quote(abs_path)
        uri = f"file:{safe_path}?mode=ro"
        
        snippet_lines = []
        with sqlite3.connect(uri, uri=True, timeout=1.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                return "DATABASE", "Empty Database"
                
            for table in tables[:6]:
                safe_table = table.replace('"', '""')
                cursor.execute(f'PRAGMA table_info("{safe_table}");')
                cols = cursor.fetchall()
                col_count = len(cols)
                col_defs = [f"{col[1]}: {col[2]}" if col[2] else col[1] for col in cols[:4]] if cols else []
                col_summary = ", ".join(col_defs)
                if col_count > 4:
                    col_summary += f", ... (+{col_count - 4} cols)"
                
                snippet_lines.append(f"TABLE {table} ({col_count} cols)")
                if col_summary:
                    snippet_lines.append(f"  ↳ {col_summary}")
                
            if len(tables) > 6:
                snippet_lines.append(f"... (+{len(tables) - 6} more tables)")
                
        return "DATABASE", "\n".join(snippet_lines)
    except Exception:
        pass
    return "DATABASE", ""
