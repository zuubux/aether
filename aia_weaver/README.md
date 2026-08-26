# 🕸️ Aether: Weaver (`aia_weaver`)

> **Headless Knowledge Fabric & Spatial Relationship Daemon for Linux**

`aia_weaver` is an asynchronous background engine built for the **Aether Interface Architecture**. It continuously indexes local workspaces, computes dense vector embeddings in an isolated CPU process pool, parses explicit document links, and dynamically correlates files based on real-time activity bursts.

State and relationship traversals are served over a secure, hardened UNIX domain socket using JSON-RPC 2.0 to decoupled consumers (such as `aia_canvas`).

---

## ⚡ Features

* **3-Tier Relationship Engine:**
  * **Explicit Edges:** Automatic resolution and dynamic reconciliation of Markdown `[[WikiLinks]]`.
  * **Semantic Edges:** 384-dimensional dense vector embeddings (`BAAI/bge-small-en-v1.5`) indexed in SQLite via `sqlite-vec`.
  * **Temporal Edges:** Real-time activity correlation tracking files edited in temporal proximity with linear time-decay weighting.
* **Non-Blocking Architecture:** Built on Python `asyncio` with CPU-intensive embedding inference isolated in a multi-process pool (`ProcessPoolExecutor`).
* **Security & Hardening:** Strict POSIX socket permissions (`0600`), 64 KB frame-size limits to prevent memory exhaustion, and path traversal guards.
* **Zero-Orphan Storage Ledger:** SQLite configured with Write-Ahead Logging (`WAL`), foreign key cascades, and automated maintenance/checkpointing on shutdown.
* **Native Linux Service:** Integrated with `systemd --user` and `journalctl`.

---

## 📂 Project Structure

```text
aia_weaver/
├── src/
│   ├── extractors/      # Multi-format extractors (markdown, office, devops, media, data, archive)
│   ├── indexer/
│   │   ├── embedder.py  # Vector generation & process pool (BAAI/bge-small-en-v1.5)
│   │   ├── parser.py    # WikiLink extraction regex & reconciliation
│   │   ├── service.py   # Asynchronous indexing pipeline orchestrator
│   │   └── thumbnail.py # Thumbnail extraction pipeline
│   ├── ipc/
│   │   └── server.py    # Hardened UNIX domain socket JSON-RPC 2.0 server (0600, 64 KB limit)
│   ├── storage/
│   │   └── db.py        # SQLite ledger, sqlite-vec (vec0 vtab), and graph logic
│   ├── utils/
│   │   └── security.py  # Path canonicalization & traversal guards
│   ├── watcher/
│   │   ├── fs_events.py # inotify sentinel with noise & secret security filtering
│   │   └── service.py   # Asynchronous file watcher service
│   └── main.py          # Daemon orchestrator & signal lifecycle
├── scripts/
│   ├── probe.py         # Standalone CLI socket diagnostic probe
│   └── seed.sandbox.py  # Seed generator for sandbox testing
├── sandbox/             # Development test workspace
├── ARCHITECTURE.md      # Detailed system design specification
└── requirements.txt
```

---

## 🚀 Quickstart

### 1. Prerequisites
* Linux (Kernel with `inotify` support)
* Python 3.11+

### 2. Installation
```bash
# Clone repository
git clone https://github.com/your-username/aia_weaver.git
cd aia_weaver

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Running Manually
```bash
python main.py
```

### 4. Running via Systemd (User Service)
To manage Weaver as a background service on demand:

```bash
# 1. Create user systemd directory if missing
mkdir -p ~/.config/systemd/user

# 2. Copy the unit file
cp systemd/aia_weaver.service ~/.config/systemd/user/

# 3. Reload systemd daemon
systemctl --user daemon-reload

# 4. Start the service on demand
systemctl --user start aia_weaver

# 5. Check status and follow live logs
systemctl --user status aia_weaver
journalctl --user -u aia_weaver -f

# 6. Stop the service
systemctl --user stop aia_weaver
```

---

## 🛠️ CLI Diagnostics

Use `scripts/probe.py` to interact directly with the running daemon over the UNIX socket:

```bash
# Health check ping
./scripts/probe.py ping

# Query node neighbors (1st-degree connections across all edge types)
./scripts/probe.py get_neighbors '{"node_id": 1}'

# Perform KNN vector search across indexed workspace files
./scripts/probe.py search_graph '{"query": "database architecture", "limit": 5}'
```

---

## 🔌 IPC Protocol Summary

* **Socket Path:** `$XDG_RUNTIME_DIR/aia_weaver/aia_weaver.sock` (Default: `/run/user/1000/aia_weaver/aia_weaver.sock`)
* **Framing:** Newline-delimited JSON-RPC 2.0 (Max frame: 64 KB)

### Methods
* `ping`: Health check (`pong`).
* `get_neighbors(node_id)`: Returns node metadata and all connected edges.
* `search_graph(query, limit)`: Returns nearest neighbors sorted by cosine distance over `sqlite-vec`.
* `touch_node(node_id, file_path)`: Records a temporal usage access log.
* `save_node(node_id, text_content)`: Writes updated document content back to disk.
* `create_edge(source_id, target_id, edge_type)`: Dynamically inserts a graph linkage.

### Broadcast Events (Sent to all connected clients)
* `node_updated`: Emitted on file creation or modification.
* `node_deleted`: Emitted when a file is removed and pruned from the ledger.

## 🤝 Development & Collaboration

`aia_weaver` was designed and architected by Nic Mansfield as part of the Aether Interface Architecture, using human-in-the-loop AI pair programming (Gemini) for iterative implementation, documentation, and prototyping.