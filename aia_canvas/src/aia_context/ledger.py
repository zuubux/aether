import os
import json
import sqlite3
import re
from pathlib import Path
import datetime

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
        
    def record_event(self, source_type: str, entity_id: str, event_action: str, payload: dict = None):
        safe_payload = _sanitize_payload(payload)
        payload_str = json.dumps(safe_payload) if safe_payload else "{}"
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ledger_events (source_type, entity_id, event_action, payload)
            VALUES (?, ?, ?, ?)
        """, (source_type, entity_id, event_action, payload_str))
        self.conn.commit()
        
    def upsert_entity(self, entity_id: str, entity_type: str, label: str, metadata: dict = None):
        safe_meta = _sanitize_payload(metadata)
        meta_str = json.dumps(safe_meta) if safe_meta else "{}"
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ledger_entities (entity_id, entity_type, label, metadata, last_updated)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(entity_id) DO UPDATE SET
                entity_type=excluded.entity_type,
                label=excluded.label,
                metadata=excluded.metadata,
                last_updated=CURRENT_TIMESTAMP
        """, (entity_id, entity_type, label, meta_str))
        self.conn.commit()
        
    def update_embedding(self, entity_id: str, vector_bytes: bytes):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO semantic_embeddings (entity_id, vector_bytes, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(entity_id) DO UPDATE SET
                vector_bytes=excluded.vector_bytes,
                last_updated=CURRENT_TIMESTAMP
        """, (entity_id, vector_bytes))
        self.conn.commit()
        
    def get_recent_entities(self, limit: int = 10) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT entity_id, entity_type, label, metadata, last_updated 
            FROM ledger_entities
            ORDER BY last_updated DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            if row_dict.get('metadata'):
                try:
                    row_dict['metadata'] = json.loads(row_dict['metadata'])
                except json.JSONDecodeError:
                    row_dict['metadata'] = {}
            results.append(row_dict)
            
        return results
        
    def touch_affinity(self, source_id: str, target_id: str, delta_weight: float = 0.05):
        cursor = self.conn.cursor()
        
        # Check if edge exists
        cursor.execute("""
            SELECT weight FROM entity_affinity_edges
            WHERE source_id = ? AND target_id = ?
        """, (source_id, target_id))
        
        row = cursor.fetchone()
        if row:
            new_weight = row['weight'] + delta_weight
            cursor.execute("""
                UPDATE entity_affinity_edges
                SET weight = ?, last_updated = CURRENT_TIMESTAMP
                WHERE source_id = ? AND target_id = ?
            """, (new_weight, source_id, target_id))
        else:
            cursor.execute("""
                INSERT INTO entity_affinity_edges (source_id, target_id, weight, last_updated)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (source_id, target_id, delta_weight))
            
        self.conn.commit()
        
    def close(self):
        self.conn.close()

if __name__ == "__main__":
    import tempfile
    
    print("Initializing ContextLedger in temp directory...")
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ledger.db"
        ledger = ContextLedger(str(db_path))
        
        # Record a dummy event
        print("Recording dummy event (with API key sanitization test)...")
        ledger.record_event(
            source_type="sys", 
            entity_id="node_001", 
            event_action="spawn",
            payload={"test": "data", "secret": "sk-1234567890abcdefghij1234567890"}
        )
        
        # Update entity
        print("Upserting entity 'node_001'...")
        ledger.upsert_entity(
            entity_id="node_001",
            entity_type="component",
            label="Root Node",
            metadata={"status": "active"}
        )
        
        # Touch affinity
        print("Touching affinity between 'node_001' and 'node_002'...")
        ledger.touch_affinity("node_001", "node_002")
        
        # Get recent entities
        print("\nRecent Entities:")
        recent = ledger.get_recent_entities()
        for ent in recent:
            print(f" - {ent['entity_id']} ({ent['entity_type']}): {ent['label']} | Metadata: {ent['metadata']}")
            
        # Verify event redaction
        cursor = ledger.conn.cursor()
        cursor.execute("SELECT payload FROM ledger_events WHERE entity_id = 'node_001'")
        event_payload = cursor.fetchone()['payload']
        print(f"\nRecorded Event Payload: {event_payload}")
        
        ledger.close()
        print("\nContextLedger verification complete.")
