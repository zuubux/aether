import asyncio
import logging
from pathlib import Path
import aiosqlite
import sqlite_vec

logger = logging.getLogger("aia_weaver.storage")

# Schema DDL
SCHEMA_SQL = """
-- 1. Core Node Metadata Table
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    file_hash TEXT NOT NULL,
    extension TEXT,
    size_bytes INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Graph Relationship Edges
CREATE TABLE IF NOT EXISTS edges (
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    edge_type TEXT NOT NULL,         -- 'explicit', 'semantic', 'temporal'
    weight REAL NOT NULL DEFAULT 1.0,-- 0.0 to 1.0 score
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_id, target_id, edge_type),
    FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
);

-- 3. Session / Temporal Activity Logs
CREATE TABLE IF NOT EXISTS session_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    node_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
);

-- Indexes for lightning-fast graph traversal
CREATE INDEX IF NOT EXISTS idx_nodes_path ON nodes(file_path);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
"""

# sqlite-vec Virtual Table DDL (384 dimensions matching all-MiniLM / BAAI)
VEC_TABLE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS node_embeddings USING vec0(
    node_id INTEGER PRIMARY KEY,
    embedding float[384]
);
"""


class DatabaseManager:
    def __init__(self, db_path: str = "weaver_graph.db"):
        self.db_path = Path(db_path).resolve()
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Connects to SQLite, loads sqlite-vec extension, and executes DDL schema."""
        logger.info(f"Initializing SQLite database ledger at: {self.db_path}")

        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row

        await self._conn.enable_load_extension(True)
        await self._conn.load_extension(sqlite_vec.loadable_path())
        await self._conn.enable_load_extension(False)

        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA foreign_keys=ON;")

        async with self._conn.cursor() as cursor:
            await cursor.executescript(SCHEMA_SQL)
            await cursor.execute(VEC_TABLE_SQL)

        await self._conn.commit()
        logger.info("Database schema and sqlite-vec vector table initialized.")

    async def upsert_node(
        self, file_path: str, file_hash: str, extension: str, size_bytes: int, embedding: list[float] | None = None
    ) -> int:
        """Inserts or updates a file node and its vector embedding."""
        if not self._conn:
            raise RuntimeError("Database not initialized.")

        async with self._conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO nodes (file_path, file_hash, extension, size_bytes, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash=excluded.file_hash,
                    size_bytes=excluded.size_bytes,
                    updated_at=CURRENT_TIMESTAMP
                RETURNING id;
                """,
                (file_path, file_hash, extension, size_bytes),
            )
            row = await cursor.fetchone()
            node_id = row[0]

            if embedding is not None:
                await cursor.execute(
                    "DELETE FROM node_embeddings WHERE node_id = ?",
                    (node_id,)
                )
                await cursor.execute(
                    "INSERT INTO node_embeddings (node_id, embedding) VALUES (?, ?)",
                    (node_id, sqlite_vec.serialize_float32(embedding))
                )

            await self._conn.commit()
            return node_id

    async def get_all_nodes(self) -> list[dict]:
        """Returns all indexed file nodes in the database for initial canvas sync."""
        if not self._conn:
            raise RuntimeError("Database not initialized.")

        async with self._conn.cursor() as cursor:
            await cursor.execute(
                "SELECT id, file_path, extension, size_bytes, updated_at FROM nodes ORDER BY id ASC;"
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def upsert_edge(
        self,
        source_id: int,
        target_id: int,
        edge_type: str,
        weight: float = 1.0,
    ) -> None:
        if not self._conn:
            raise RuntimeError("Database not initialized.")

        async with self._conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO edges (source_id, target_id, edge_type, weight)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, edge_type) DO UPDATE SET
                    weight = excluded.weight;
                """,
                (source_id, target_id, edge_type, weight),
            )
            await self._conn.commit()

    async def search_similar_nodes(self, query_vector: list[float], limit: int = 5) -> list[dict]:
        if not self._conn:
            raise RuntimeError("Database not initialized.")

        serialized_query = sqlite_vec.serialize_float32(query_vector)

        async with self._conn.cursor() as cursor:
            query = """
                SELECT 
                    n.id, 
                    n.file_path, 
                    v.distance 
                FROM node_embeddings v
                JOIN nodes n ON n.id = v.node_id
                WHERE v.embedding MATCH ? AND k = ?
                ORDER BY v.distance ASC;
            """
            await cursor.execute(query, (serialized_query, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def create_semantic_edges(
        self,
        node_id: int,
        embedding: list[float],
        distance_threshold: float = 0.65,  # Relaxed from 0.35 to 0.65 for natural topical discovery
        limit: int = 5,
    ) -> int:
        if not self._conn or embedding is None:
            return 0

        serialized_vec = sqlite_vec.serialize_float32(embedding)
        created_count = 0

        async with self._conn.cursor() as cursor:
            query = """
                SELECT n.id, v.distance 
                FROM node_embeddings v
                JOIN nodes n ON n.id = v.node_id
                WHERE v.embedding MATCH ? AND k = ? AND n.id != ?
                ORDER BY v.distance ASC;
            """
            await cursor.execute(query, (serialized_vec, limit + 1, node_id))
            matches = await cursor.fetchall()

            for match in matches:
                target_id = match["id"]
                dist = match["distance"]

                if dist <= distance_threshold:
                    weight = max(0.0, min(1.0, 1.0 - (dist / distance_threshold)))
                    weight = round(weight, 3)

                    # Upsert bidirectional edge (Node A <-> Node B)
                    await self.upsert_edge(
                        source_id=node_id,
                        target_id=target_id,
                        edge_type="semantic",
                        weight=weight,
                    )
                    await self.upsert_edge(
                        source_id=target_id,
                        target_id=node_id,
                        edge_type="semantic",
                        weight=weight,
                    )
                    created_count += 1

        return created_count

    async def get_node_neighbors(self, node_id: int) -> dict:
        if not self._conn:
            raise RuntimeError("Database not initialized.")

        async with self._conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            node = await cursor.fetchone()
            if not node:
                return {"error": "Node not found"}

            query = """
                SELECT 
                    e.source_id, 
                    e.target_id, 
                    e.edge_type, 
                    e.weight,
                    n_target.file_path AS target_path,
                    n_source.file_path AS source_path
                FROM edges e
                JOIN nodes n_source ON e.source_id = n_source.id
                JOIN nodes n_target ON e.target_id = n_target.id
                WHERE e.source_id = ? OR e.target_id = ?;
            """
            await cursor.execute(query, (node_id, node_id))
            edges = await cursor.fetchall()

            return {
                "node": dict(node),
                "edges": [dict(e) for e in edges],
            }
    
    async def delete_node_by_path(self, file_path: str) -> int | None:
        if not self._conn:
            raise RuntimeError("Database not initialized.")

        async with self._conn.cursor() as cursor:
            await cursor.execute("SELECT id FROM nodes WHERE file_path = ?", (file_path,))
            row = await cursor.fetchone()
            if not row:
                return None

            node_id = row[0]

            try:
                await cursor.execute("DELETE FROM node_embeddings WHERE node_id = ?", (node_id,))
            except Exception as e:
                logger.warning(f"Could not purge vector for Node #{node_id}: {e}")

            await cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            await self._conn.commit()

            return node_id

    async def reconcile_explicit_edges(self, source_id: int) -> None:
        if not self._conn:
            return
        async with self._conn.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM edges WHERE source_id = ? AND edge_type = 'explicit'",
                (source_id,),
            )
            await self._conn.commit()

    async def log_session_event(self, node_id: int, event_type: str = "modified") -> None:
        if not self._conn:
            return

        async with self._conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO session_logs (node_id, event_type, timestamp)
                VALUES (?, ?, CURRENT_TIMESTAMP);
                """,
                (node_id, event_type),
            )
            await self._conn.commit()

    async def create_temporal_edges(
        self,
        node_id: int,
        window_minutes: int = 60,
        half_life_minutes: float = 25.0,
        reinforcement_boost: float = 0.20,
    ) -> list[dict]:
        """
        Calculates exponential time-decayed temporal edges with interaction reinforcement
        and returns all active temporal edges connected to the node.
        """
        if not self._conn:
            return []

        half_life_seconds = half_life_minutes * 60.0
        created_edges = []

        async with self._conn.cursor() as cursor:
            # 1. Fetch recent nodes active within the expanded temporal window
            query = """
                SELECT 
                    s.node_id,
                    n.file_path,
                    (strftime('%s', 'now') - strftime('%s', MAX(s.timestamp))) AS delta_seconds
                FROM session_logs s
                JOIN nodes n ON s.node_id = n.id
                WHERE s.node_id != ?
                  AND s.timestamp >= datetime('now', ?)
                GROUP BY s.node_id;
            """
            await cursor.execute(query, (node_id, f"-{window_minutes} minutes"))
            recent_nodes = await cursor.fetchall()

            for record in recent_nodes:
                target_id = record["node_id"]
                target_path = record["file_path"]
                delta_sec = max(0.0, float(record["delta_seconds"]))

                # 2. Check for existing temporal edge weight to apply reinforcement
                await cursor.execute(
                    """
                    SELECT weight FROM edges 
                    WHERE ((source_id = ? AND target_id = ?) OR (source_id = ? AND target_id = ?))
                      AND edge_type = 'temporal'
                    LIMIT 1;
                    """,
                    (node_id, target_id, target_id, node_id),
                )
                existing_row = await cursor.fetchone()
                current_weight = existing_row[0] if existing_row else 1.0

                # 3. Exponential half-life decay + interaction reinforcement
                # W(t) = (W_curr * 2^(-dt / t_half)) + reinforcement
                decay_factor = 0.5 ** (delta_sec / half_life_seconds)
                calculated_weight = (current_weight * decay_factor) + reinforcement_boost
                clamped_weight = round(max(0.10, min(1.0, calculated_weight)), 3)

                # 4. Upsert bidirectional temporal connection
                await self.upsert_edge(
                    source_id=node_id,
                    target_id=target_id,
                    edge_type="temporal",
                    weight=clamped_weight,
                )

                created_edges.append({
                    "source_id": node_id,
                    "target_id": target_id,
                    "edge_type": "temporal",
                    "weight": clamped_weight,
                    "target_path": target_path,
                })

        return created_edges

    async def get_recent_node_ids(self, window_minutes: int = 60, min_weight: float = 0.10) -> list[int]:
        """Returns IDs of all nodes with active temporal edges or recent session activity."""
        if not self._conn:
            return []

        async with self._conn.cursor() as cursor:
            query = """
                SELECT DISTINCT id FROM (
                    -- Nodes active in session logs within window
                    SELECT node_id AS id FROM session_logs 
                    WHERE timestamp >= datetime('now', ?)
                    UNION
                    -- Nodes maintaining temporal edges above threshold
                    SELECT source_id AS id FROM edges 
                    WHERE edge_type = 'temporal' AND weight >= ?
                    UNION
                    SELECT target_id AS id FROM edges 
                    WHERE edge_type = 'temporal' AND weight >= ?
                ) ORDER BY id ASC;
            """
            await cursor.execute(query, (f"-{window_minutes} minutes", min_weight, min_weight))
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

        return created_edges    
    
    async def get_stats(self) -> dict:
        if not self._conn:
            return {"status": "uninitialized"}

        async with self._conn.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*), COUNT(DISTINCT extension) FROM nodes;")
            node_count, ext_count = await cursor.fetchone()

            await cursor.execute("SELECT edge_type, COUNT(*) FROM edges GROUP BY edge_type;")
            edge_rows = await cursor.fetchall()
            edges_by_type = {row[0]: row[1] for row in edge_rows}

            await cursor.execute("SELECT COUNT(*) FROM node_embeddings;")
            vec_count = (await cursor.fetchone())[0]

            await cursor.execute("SELECT COUNT(*) FROM session_logs;")
            log_count = (await cursor.fetchone())[0]

        db_size_kb = round(self.db_path.stat().st_size / 1024, 2) if self.db_path.exists() else 0.0

        return {
            "database": {"path": str(self.db_path), "size_kb": db_size_kb},
            "nodes": {"total": node_count, "unique_extensions": ext_count, "vectorized": vec_count},
            "edges": edges_by_type,
            "session_logs_retained": log_count,
        }
            
    async def run_maintenance(self, session_ttl_days: int = 30) -> None:
        if not self._conn:
            return

        async with self._conn.cursor() as cursor:
            await cursor.execute(
                """
                DELETE FROM nodes 
                WHERE file_hash = 'pending' 
                  AND id NOT IN (SELECT source_id FROM edges UNION SELECT target_id FROM edges);
                """
            )
            await cursor.execute(
                "DELETE FROM session_logs WHERE timestamp < datetime('now', ?)",
                (f"-{session_ttl_days} days",),
            )
            await cursor.execute("PRAGMA optimize;")

        await self._conn.commit()

        try:
            await self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        except Exception as e:
            logger.debug(f"WAL checkpoint skipped: {e}")

        logger.info("Database maintenance complete.")

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            logger.info("Database connection closed.")