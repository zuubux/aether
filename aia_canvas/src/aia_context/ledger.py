import json
import re
import sqlite3
from pathlib import Path

# Basic regex to reject common API key / token patterns in payloads
# e.g., sk-..., xoxb-..., Bearer ...
TOKEN_PATTERN = re.compile(
    r"(sk-[a-zA-Z0-9]{20,})|(xox[baprs]-[a-zA-Z0-9]{10,})|(Bearer\s+[a-zA-Z0-9\-\._~+/]+=*)",
    re.IGNORECASE
)

def _sanitize_payload(payload: dict) -> dict:
    if not payload:
        return {}
    
    sanitized = {}
    for k, v in payload.items():
        if isinstance(v, str):
            if TOKEN_PATTERN.search(v):
                sanitized[k] = "[REDACTED TOKEN]"
                continue
        sanitized[k] = v
    return sanitized

class ContextLedger:
    def __init__(self, db_path: str = None):
        if db_path is None:
            self.db_path = Path.home() / ".local" / "share" / "aether" / "ledger.db"
        else:
            self.db_path = Path(db_path)
            
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        self._init_schema()
        
    def _init_schema(self):
        cursor = self.conn.cursor()
        
        # PRAGMAs for performance
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        
        # ledger_events
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ledger_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            source_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            event_action TEXT NOT NULL,
            payload TEXT
        );
        """)
        
        # ledger_entities
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ledger_entities (
            entity_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            label TEXT NOT NULL,
            metadata TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # entity_affinity_edges
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_affinity_edges (
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            weight REAL DEFAULT 0.0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (source_id, target_id)
        );
        """)
        
        # semantic_embeddings
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_embeddings (
            entity_id TEXT PRIMARY KEY,
            vector_bytes BLOB NOT NULL,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_events_entity_id ON ledger_events(entity_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_events_timestamp ON ledger_events(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_entities_type ON ledger_entities(entity_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_affinity_source ON entity_affinity_edges(source_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_affinity_target ON entity_affinity_edges(target_id);")
        
        self.conn.commit()
        
    def close(self):
        self.conn.close()
