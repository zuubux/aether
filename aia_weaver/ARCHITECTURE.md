# Weaver Architecture & System Design Document

**Subsystem:** `aia_weaver` (Knowledge Fabric & Spatial Relationship Engine)  
**Parent Framework:** Aether Interface Architecture  
**Document Version:** 1.0.0  

---

## 1. System Context & Framework Topology

`aia_weaver` operates as the background relational backbone within the broader **Aether** spatial computing stack:

| Component | Subsystem | Responsibility |
| :--- | :--- | :--- |
| **Overarching Framework** | **Aether** | The spatial interface environment bridging physical workspace and digital context. |
| **Knowledge Fabric Daemon** | **Weaver** | Ingests files, resolves explicit/semantic/temporal connections, and serves the graph ledger. |
| **Intent Subsystem** | **Intent Engine** | Translates biological signals into high-level interaction commands. |
| **Biological Sensor** | **Saccade** | Real-time eye-tracking, gaze vector calculations, and fixation prediction. |
| **Spatial Canvas / UI** | **Canvas** | Visual frontend rendering spatial nodes and knowledge constellations. |

---

## 2. High-Level Architecture & Pipeline Flow

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                           AIA_WEAVER DAEMON                            │
 │                                                                        │
 │  ┌──────────────────┐                                                  │
 │  │ FileWatcher      │ (OS inotify via watchfiles)                      │
 │  │src/watcher/      │───┐                                              │
 │  │  fs_events.py    │   │                                              │
 │  └──────────────────┘   ▼                                              │
 │  ┌─────────────────────────────────┐                                   │
 │  │ asyncio Event Queue             │                                   │
 │  └─────────────────┬───────────────┘                                   │
 │                    │                                                   │
 │                    ▼                                                   │
 │  ┌────────────────────────────────────────────────────────┐            │
 │  │ Processing Pipeline (src/main.py)                      │            │
 │  │  ├─ Security / Traversal Checks (src/utils/security)   │            │
 │  │  ├─ Multi-format Extraction (src/extractors/)          │            │
 │  │  ├─ SHA-256 Hashing & Deduplication                    │            │
 │  │  └─ Extraction Dispatch                                │            │
 │  └───┬─────────────────────────┬──────────────────────┬───┘            │
 │      │                         │                      │                │
 │      ▼                         ▼                      ▼                │
 │  ┌───────────────┐     ┌───────────────┐      ┌───────────────┐        │
 │  │ Parser        │     │ LocalEmbedder │      │ Temporal      │        │
 │  │ src/indexer/  │     │ src/indexer/  │      │ Engine        │        │
 │  │   parser.py   │     │   embedder.py │      │ src/storage/  │        │
 │  │ [[WikiLinks]] │     │ (ProcessPool) │      │   db.py       │        │
 │  └───────┬───────┘     └───────┬───────┘      └───────┬───────┘        │
 │          │                     │                      │                │
 │          └─────────────────────┼──────────────────────┘                │
 │                                ▼                                       │
 │  ┌────────────────────────────────────────────────────────┐            │
 │  │ SQLite Ledger (src/storage/db.py)                     │            │
 │  │  ├─ nodes (Metadata)                                   │            │
 │  │  ├─ edges (Explicit, Semantic, Temporal)               │            │
 │  │  ├─ session_logs (Activity Stream)                     │            │
 │  │  └─ node_embeddings (sqlite-vec / vec0)                │            │
 │  └─────────────────────────────┬──────────────────────────┘            │
 │                                │                                       │
 │  ┌─────────────────────────────┴──────────────────────────┐            │
 │  │ Hardened IPC Server (src/ipc/server.py)                │            │
 │  │ UNIX Domain Socket (JSON-RPC 2.0 + Broadcast Streams)  │            │
 │  └─────────────────────────────┬──────────────────────────┘            │
 └────────────────────────────────┼───────────────────────────────────────┘
                                  │ /run/user/1000/aia_weaver/aia_weaver.sock
                                  ▼
                         Connected Clients (aia_canvas)
```

---

## 3. Subsystem Breakdown

### 3.1 Filesystem Sentinel (`src/watcher/fs_events.py`)
- Employs `watchfiles` to consume asynchronous OS kernel `inotify` signals.
- Implements strict noise filters: ignores `.git/`, `.venv/`, `__pycache__/`, `.obsidian/`, `node_modules/`, and swap files (`*.swp`, `*.tmp`).
- Implements security exclusion rules: immediately drops access to private keys (`.pem`, `.key`, `id_rsa`), certificates (`.crt`, `.pfx`), and environment secrets (`.env`, `.kdbx`).

### 3.2 Explicit Link Parser (`src/indexer/parser.py`)
- Extracts raw WikiLink tags matching `\[\[(.*?)\]\]`.
- Strips aliases formatted as `[[Target|Display Alias]]`.
- Invokes `reconcile_explicit_edges()` on the database ledger to ensure deletions of explicit links within Markdown documents immediately purge matching graph edges.

### 3.3 Vector Brain (`src/indexer/embedder.py`)
- Generates 384-dimensional dense sentence embeddings using ONNX-optimized `BAAI/bge-small-en-v1.5`.
- Isolates inference inside a dedicated `ProcessPoolExecutor` to ensure CPU matrix math does not contend with the async I/O event loop.
- Caches the model instance once per worker process initialization.

### 3.4 Knowledge Ledger & Storage (`src/storage/db.py`)
- Backed by SQLite3 configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) and foreign keys enforced (`PRAGMA foreign_keys=ON;`).
- Schema definition:
  - Table `nodes`: Primary metadata ledger (`id`, `file_path`, `file_hash`, `extension`, `size_bytes`, `archetype`, `snippet`, `thumbnail_url`, `extractor_version`, `created_at`, `updated_at`).
  - Table `edges`: Relational linkages (`id`, `source_id`, `target_id`, `edge_type`, `weight`, `created_at` with `ON DELETE CASCADE`).
  - Table `session_logs`: Temporal activity log (`id`, `event_type`, `node_id`, `timestamp`).
  - Virtual Table `node_embeddings`: `sqlite-vec` `vec0` table mapping `node_id INTEGER PRIMARY KEY` to `embedding float[384]`.
- Loads the `sqlite-vec` shared library extension to execute rapid KNN vector searches over 384-dimensional embeddings.

### 3.5 Hardened IPC Server (`src/ipc/server.py`)
- Listens on a dedicated UNIX domain socket located in `$XDG_RUNTIME_DIR/aia_weaver/aia_weaver.sock`.
- Restricts socket file permissions to `0600` (user read/write only).
- Enforces a strict maximum payload size of 64 KB (`MAX_PAYLOAD_BYTES`) per line frame to mitigate memory starvation attacks.
- Validates all file parameter arguments against workspace root boundaries using `utils.security:is_safe_path`.

---

## 4. Graph Edge Topology & Mathematical Models

Weaver records connections between file nodes using three distinct edge classifications:

### 4.1 Explicit Relationships (`edge_type = 'explicit'`)
* Created via direct author linkage (`[[WikiLinks]]`).
* Normalized edge weight:
  $$W_{explicit} = 1.000$$

### 4.2 Semantic Relationships (`edge_type = 'semantic'`)
* Generated via KNN cosine distance calculations over 384-dimensional embeddings.
* Let $d \in [0, 2]$ be the computed cosine distance, and $d_{threshold}$ be the cutoff threshold (default $0.35$):
  $$W_{semantic} = \max\left(0.0, \min\left(1.0, 1.0 - \frac{d}{d_{threshold}}\right)\right)$$

### 4.3 Temporal Relationships (`edge_type = 'temporal'`)
* Generated when two distinct nodes are modified within a sliding time window $T_{window}$ (default $15\text{ minutes} = 900\text{ seconds}$).
* Let $\Delta t = |t_{current} - t_{target}|$ be the elapsed seconds between file events:
  $$W_{temporal} = \max\left(0.100, \min\left(1.000, 1.0 - 0.9 \times \frac{\Delta t}{T_{window}}\right)\right)$$
* Ensures simultaneous edits receive $W \approx 1.0$, while edits near the 15-minute boundary scale down to $0.1$.

---

## 5. IPC Protocol & JSON-RPC 2.0 Specification

### 5.1 Request / Response Methods

#### `ping`
* **Request:** `{"jsonrpc": "2.0", "method": "ping", "id": 1}`
* **Response:** `{"jsonrpc": "2.0", "result": "pong", "id": 1}`

#### `search_graph`
* **Request:**
  ```json
  {
    "jsonrpc": "2.0",
    "method": "search_graph",
    "params": {
      "query": "system architecture",
      "limit": 3
    },
    "id": 2
  }
  ```
* **Response:**
  ```json
  {
    "jsonrpc": "2.0",
    "result": [
      {
        "id": 1,
        "file_path": "/home/user/workspace/architecture.md",
        "distance": 0.1245
      }
    ],
    "id": 2
  }
  ```

#### `get_neighbors`
* **Request:**
  ```json
  {
    "jsonrpc": "2.0",
    "method": "get_neighbors",
    "params": {
      "node_id": 1
    },
    "id": 3
  }
  ```
* **Response:**
  ```json
  {
    "jsonrpc": "2.0",
    "result": {
      "node": {
        "id": 1,
        "file_path": "/home/user/workspace/architecture.md",
        "extension": ".md",
        "size_bytes": 1024,
        "updated_at": "2026-08-14 08:30:00"
      },
      "edges": [
        {
          "source_id": 1,
          "target_id": 2,
          "edge_type": "temporal",
          "weight": 0.966,
          "source_path": "/home/user/workspace/architecture.md",
          "target_path": "/home/user/workspace/config.py"
        }
      ]
    },
    "id": 3
  }
  ```

---

## 5.2 Real-Time Broadcast Events

Clients connected to the UNIX socket receive framed event notifications as changes occur:

#### `node_updated`
```json
{
  "jsonrpc": "2.0",
  "method": "graph_event",
  "params": {
    "type": "node_updated",
    "data": {
      "node_id": 1,
      "file_path": "/home/user/workspace/notes.md"
    }
  }
}
```

#### `node_deleted`
```json
{
  "jsonrpc": "2.0",
  "method": "graph_event",
  "params": {
    "type": "node_deleted",
    "data": {
      "node_id": 1,
      "file_path": "/home/user/workspace/notes.md"
    }
  }
}
```

---

## 6. Teardown Lifecycle & Maintenance

1. **Signal Traps:** Intercepts `SIGINT` and `SIGTERM` to initiate graceful termination.
2. **Process Pool Disposal:** Closes `ProcessPoolExecutor` without hanging pending worker tasks.
3. **Database Maintenance Routine:**
   * Removes unreferenced placeholder nodes (`file_hash = 'pending'`).
   * Prunes activity history logs beyond retention window (`session_ttl_days = 30`).
   * Runs SQLite query planner index optimizations (`PRAGMA optimize;`).
   * Checkpoints and truncates Write-Ahead Log (`PRAGMA wal_checkpoint(TRUNCATE);`).
4. **Socket Cleanup:** Unlinks the UNIX socket file to prevent stale binding locks on subsequent launches.