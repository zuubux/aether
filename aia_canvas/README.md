# ==============================================================================
# README.md
# ==============================================================================

# 🌌 Aether: Canvas (`aia_canvas`)

> **GPU-Accelerated Spatial Presentation Layer & Cognitive Workbench for Linux**[cite: 1]

`aia_canvas` is the visual presentation frontend for the **Aether Interface Architecture**[cite: 1]. Operating on an obsidian canvas, it renders knowledge nodes, project clusters, and relational tendrils driven by a 120Hz Stokes fluid dynamics engine[cite: 1, 2, 5].

Designed to eliminate traditional window chrome, `aia_canvas` projects files directly as interactive surfaces, dynamically adapting their detail from full documents down to glowing Star Beads based on cognitive aperture and gaze focus[cite: 8].

---

## ⚡ Features

* **120Hz Stokes Fluid Dynamics:** Viscous, biological movement using quadratic drag, aspect-conformal orbital docking, and non-penetration potential barriers.
* **4-Tier Semantic Aperture:** Seamless LOD scaling ranging from live resizable Workbenches ($1400 \times 900\text{px}$) down to $14\text{px}$ luminous Star Beads with fish-eye hover blooms.
* **Drag Transit & Settle Dynamics:**
  * **Transit Escalation:** Moving nodes dynamically escalate (Tier 4 -> Tier 3 Capsule; Tier 3/2 -> Tier 2 Inspection Slate) for high legibility while dragging.
  * **1000ms Settle Grace Period:** Releasing a node triggers a 1000ms settle delay with an electric cyan border luminosity pulse (`Theme.accentCyan`) before easing into its target cluster position.
  * **Strict Input Isolation:** Drag gestures actively mute hover/dwell timers and model coordinate overrides to prevent kinetic fighting and visual flicker.
* **Spotlight HUD & Search Shelf (`SearchShelf.qml`):**
  * **Top 7 Ranked Carousel:** Smooth horizontal card shelf showing top vector/title matches above the OmniBar.
  * **Live Tier 1.5 Preview:** Displays an expanded markdown/media preview card for the currently focused match.
  * **Keyboard-Driven Traversal:** Seamless `Left` / `Right` / `Tab` index navigation and `Enter` selection with smooth camera focal transition (zero physics displacement).
* **Modular HUD & Diagnostic Overlays:**
  * **`DiagnosticsOverlay.qml`:** Toggleable `F3` SRE telemetry HUD showing frametimes, node/edge counts, and socket latency.
  * **`CanvasHud.qml`:** Bottom-left ambient status pill showing IPC daemon connectivity and cognitive aperture percentage.
* **Tendril Pacing & Distance Damping:** Temporal and semantic edges breathe organically with slow pulse phases, dimming progressively based on span distance.
* **Enterprise Shield Membranes:** GPU-native containment bubbles that organically envelop active clusters while rejecting distant outliers.
* **Decoupled JSON-RPC 2.0 Architecture:** Asynchronous UNIX domain socket client connecting to `aia_weaver` with a 64 KB framing limit and auto-reconnect backoff.
* **Hardened Path Security:** Strict path canonicalization guaranteeing all file actions are verified within safe workspace boundaries.

---

## 📂 Project Structure

```text
aia_canvas/
├── src/
│   ├── controllers/         # Domain Controller Hierarchy
│   │   ├── base_controller.py
│   │   ├── canvas_controller.py
│   │   ├── node_controller.py
│   │   ├── physics_controller.py
│   │   └── search_controller.py
│   ├── core/                # Core query and intent parsing
│   │   ├── completion_engine.py
│   │   ├── intent_dispatcher.py
│   │   └── intent_grammar.py
│   ├── ipc/
│   │   └── client.py        # Asynchronous UNIX domain socket JSON-RPC 2.0 client
│   ├── physics/
│   │   └── engine.py        # 120Hz Stokes physics, clustering, and horizon anchors
│   ├── qml/
│   │   ├── hud/             # Modular HUD Overlays
│   │   │   ├── CanvasHud.qml           # Bottom-left IPC & Aperture status
│   │   │   └── DiagnosticsOverlay.qml  # F3 Telemetry & Frametime overlay
│   │   ├── node/            # Modular Leaf Delegates
│   │   │   ├── NodeAura.qml # GPU-native semantic glow and selection halos
│   │   │   ├── NodePill.qml # Tier 3 compact capsules and extension badges
│   │   │   └── NodePreview.qml # Tier 1.5 hover-dwell preview cards
│   │   ├── search/          # Spotlight Search Subsystem
│   │   │   └── SearchShelf.qml         # Ranked result carousel & preview card
│   │   ├── slates/          # Specialized Media Slates
│   │   │   ├── ImageSlate.qml
│   │   │   ├── PdfSlate.qml
│   │   │   └── TableSlate.qml
│   │   ├── Canvas.qml       # Root window and viewport orchestrator
│   │   ├── ClusterHalo.qml  # GPU-accelerated shield membrane component
│   │   ├── Node.qml         # Interactive coordinator & state-machine container
│   │   ├── NodeContent.qml  # Slate/pill content loader delegate
│   │   ├── OmniBar.qml      # Spotlight search and intent command bar
│   │   ├── SurfaceShell.qml # Single-stroke perimeter and background shell
│   │   ├── Tendril.qml      # Synaptic cubic Bezier connection lines
│   │   ├── Theme.qml        # Global visual tokens, palettes, and easing
│   │   └── qmldir           # QML module declarations
│   ├── utils/
│   │   └── security.py      # Path canonicalization & boundary traversal guards
│   ├── workers/             # Asynchronous QThreadPool Pipelines
│   │   └── media_worker.py  # Non-blocking PDF, CSV, Image offloading tasks
│   ├── bridge.py            # Composite Root Coordinator & Python/QML adapter
│   ├── models.py            # Reactive QObject data models (Node, Edge)
│   ├── store.py             # In-memory graph ledger and neighborhood store
│   └── main.py              # Application entrypoint & systemd logger bootstrap
├── ARCHITECTURE.md          # Detailed system design specification
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

* **OmniBar / Spotlight Search:** `Ctrl+Space` activates the Spotlight HUD bar. Type to search title & vector embeddings.
* **Spotlight Carousel Navigation:** `Left Arrow` / `Right Arrow` / `Tab` cycles through top 7 ranked matches; dynamically updates the Tier 1.5 preview slate above.
* **Confirm Search Selection:** `Enter` or `Left Click` on a carousel card centers the camera smoothly on the target node and dismisses the shelf (zero physics grid displacement).
* **Aperture Zoom:** `Mouse Wheel` on empty void (scales cognitive aperture from $20\%$ macro constellation up to $220\%$ deep focus).
* **Select / Expand Focus:** `Left Click` on any card or bead to open the live Workbench and pull related nodes into orbital horizon.
* **Clear Focus / Return to Void:** `Esc` or `Left Click` anywhere on the empty canvas.
* **Drag & Relocate (Drag-Settle Physics):** `Left Click + Drag` on any node to move it. Dragging escalates the node's visual tier for readability and mutes hover/dwell timers. Releasing initiates a 1000ms settle grace period with cyan border luminosity before easing into cluster equilibrium.
* **Reveal in System File Manager:** `Right Click` any card or click **Reveal File** on the active Workbench.
* **Toggle SRE Telemetry HUD:** `F3` overlays real-time node count, render edge count, physics step frametime, and backend socket status.

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