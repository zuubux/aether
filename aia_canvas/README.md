# ==============================================================================
# README.md
# ==============================================================================

# 🌌 Aether: Canvas (`aia_canvas`)

> **GPU-Accelerated Spatial Presentation Layer & Cognitive Workbench for Linux**[cite: 1]

`aia_canvas` is the visual presentation frontend for the **Aether Interface Architecture**[cite: 1]. Operating on an obsidian canvas, it renders knowledge nodes, project clusters, and relational tendrils driven by a 120Hz Stokes fluid dynamics engine[cite: 1, 2, 5].

Designed to eliminate traditional window chrome, `aia_canvas` projects files directly as interactive surfaces, dynamically adapting their detail from full documents down to glowing Star Beads based on cognitive aperture and gaze focus[cite: 8].

---

## ⚡ Features

* **120Hz Stokes Fluid Dynamics:** Viscous, biological movement using quadratic drag, aspect-conformal orbital docking, and non-penetration potential barriers[cite: 2, 5].
* **4-Tier Semantic Aperture:** Seamless LOD scaling ranging from live resizable Workbenches ($1400 \times 900\text{px}$) down to $16\text{px}$ luminous Star Beads with fish-eye hover blooms[cite: 2, 8]. Tier 1.5 previews (Preview Slates) are used for active search results and sustained hovers.
* **Focal Lens States:** Strict geometric focus locking that pulls related semantic history directly into view and decouples background clusters to preserve kinetic calm.
* **Tendril Pacing & Distance Damping:** Temporal and semantic edges breathe organically with slow pulse phases, dimming progressively based on span distance to reduce visual clutter across macro clusters.
* **Enterprise Shield Membranes:** GPU-native containment bubbles that organically envelop active clusters while rejecting distant outliers[cite: 5, 7].
* **Decoupled JSON-RPC 2.0 Architecture:** Asynchronous UNIX domain socket client connecting to `aia_weaver` with a 64 KB framing limit and auto-reconnect backoff[cite: 10].
* **Hardened Path Security:** Strict path canonicalization guaranteeing all file actions are verified within safe workspace boundaries[cite: 2].
* **SRE Golden Signal Observability:** Structured logging formatted for `systemd-journald` and an interactive `F3` diagnostic HUD tracking frametimes and socket saturation.

---

## 📂 Project Structure

```text
aia_canvas/
├── ipc/
│   └── client.py        # Asynchronous UNIX domain socket JSON-RPC 2.0 client[cite: 10]
├── physics/
│   └── engine.py        # 120Hz Stokes physics, clustering, and horizon anchors[cite: 5]
├── qml/
│   ├── Canvas.qml       # Root window, SRE HUD, and viewport orchestrator[cite: 6]
│   ├── ClusterHalo.qml  # GPU-accelerated shield membrane component[cite: 7]
│   ├── Node.qml         # 4-tier semantic card and Star Bead implementation[cite: 8]
│   └── Tendril.qml      # Synaptic cubic Bezier connection lines[cite: 9]
├── utils/
│   └── security.py      # Path canonicalization & boundary traversal guards
├── bridge.py            # Python/QML adapter, salience mapping, and telemetry[cite: 2]
├── models.py            # Reactive QObject data models (Node, Edge)[cite: 3]
├── store.py             # In-memory graph ledger and neighborhood store[cite: 4]
├── main.py              # Application entrypoint & systemd logger bootstrap[cite: 1]
├── ARCHITECTURE.md      # Detailed system design specification
└── requirements.txt
```

---

## 🚀 Quickstart

### 1. Prerequisites
* Linux (Fedora 38+, Ubuntu 22.04+, or Arch Linux)
* Python 3.11+
* GPU support with OpenGL 3.3+ / Vulkan

### 2. Installation
```bash
# Clone repository
git clone [https://github.com/your-username/aia_canvas.git](https://github.com/your-username/aia_canvas.git)
cd aia_canvas

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (PyQt6)
pip install -r requirements.txt
```

### 3. Running the Canvas
```bash
# Run standalone (Hardware/Mock mode or auto-attaching to live aia_weaver)
python3 src/main.py

# Available CLI Flags:
# --fullscreen / --full-screen : Launch the application in native full screen mode.
# --span-all : Span the window across all connected displays.
# --screen <idx> : Target specific display index (default: 0).
# -v / --debug : Enable verbose diagnostic logging.
```

---

## 🎮 Canvas Navigation & Keybindings

* **Aperture Zoom:** `Mouse Wheel` on empty void (scales cognitive aperture from $20\%$ macro constellation up to $220\%$ deep focus)[cite: 6].
* **Select / Expand Focus:** `Left Click` on any card or bead to open the live Workbench and pull related nodes into orbital horizon[cite: 2, 8].
* **Clear Focus / Return to Void:** `Esc` or `Left Click` anywhere on the empty canvas[cite: 6].
* **Drag & Relocate:** `Left Click + Drag` on any node to move it; nodes smoothly return to cluster equilibrium on release[cite: 8].
* **Resize Workbench:** `Left Click + Drag` on the bottom-right cyan corner handle of an active Workbench card[cite: 8].
* **Reveal in System File Manager:** `Right Click` any card or click **Reveal File** on the active Workbench[cite: 2, 8].
* **Toggle SRE Telemetry HUD:** `F3` (renders node count, edge count, physics step latency, and socket status).

---

## 🛠️ Diagnostics & Observability

### SRE Diagnostic HUD
Press `F3` while running to overlay real-time runtime metrics:
* **Physics Step Latency:** Real-time execution duration of the integration loop (alert threshold: $> 6.5\text{ms}$).
* **Active Topology:** Live counts of active nodes and edges.
* **Backend Socket:** Real-time state of the connection to `aia_weaver.sock`.

### Systemd Journald Logs
Inspect structured logs directly in the terminal or via `journalctl`:
```bash
# When running as a systemd user unit
journalctl --user -u aia_canvas -f
```

---

## 🤝 Development & Attribution

`aia_canvas` was designed and architected by Nic Mansfield as part of the Aether Interface Architecture, using human-in-the-loop AI pair programming (Gemini) for iterative implementation, graphics tuning, and documentation.