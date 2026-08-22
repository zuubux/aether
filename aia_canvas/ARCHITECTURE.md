# ==============================================================================
# ARCHITECTURE.md
# ==============================================================================

# Canvas Architecture & System Design Document

**Subsystem:** `aia_canvas` (Spatial Presentation Layer & Cognitive Workbench)  
**Parent Framework:** Aether Interface Architecture  
**Document Version:** 1.0.0  

---

## 1. System Context & Framework Topology

`aia_canvas` operates as the decoupled visual frontend and human interaction surface within the **Aether** spatial computing stack[cite: 1]:

| Component | Subsystem | Responsibility |
| :--- | :--- | :--- |
| **Overarching Framework** | **Aether** | The spatial interface environment bridging physical workspace and digital context[cite: 11]. |
| **Knowledge Fabric Daemon** | **Weaver (`aia_weaver`)** | Headless backend indexing file topology, vector embeddings, and temporal activity ledgers[cite: 1, 11]. |
| **Intent Subsystem** | **Intent Engine** | Translates biological inputs and multimodal signals into spatial navigation directives[cite: 1, 11]. |
| **Biological Sensor** | **Saccade (`aia_saccade`)** | Real-time gaze tracking, fixation prediction, and foveal targeting[cite: 1, 11]. |
| **Spatial Presentation Layer** | **Canvas (`aia_canvas`)** | GPU-accelerated Scene Graph rendering 120Hz Stokes physics, semantic aperture zoom, and cognitive workbenches[cite: 1]. |

---

## 2. High-Level Architecture & Pipeline Flow

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                           AIA_CANVAS FRONTEND                          │
 │                                                                        │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │ UNIX Domain Socket Client (ipc/client.py)                        │  │
 │  │  ├─ Asyncio Event Loop in Background Worker Thread               │  │
 │  │  ├─ Frame Buffer Cap: 64 KB (MAX_PAYLOAD_BYTES)                  │  │
 │  │  └─ Auto-Reconnect with Exponential Backoff                      │  │
 │  └──────────────────────────────┬───────────────────────────────────┘  │
 │                                 │ Newline-framed JSON-RPC 2.0          │
 │                                 ▼                                      │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │ Python/C++ Bridge Adapter (bridge.py)                            │  │
 │  │  ├─ Multi-Tier Salience Assignment & Topological Distances       │  │
 │  │  ├─ Frame Latency Metering & Golden Signal Observability         │  │
 │  │  └─ Memory Store (store.py) & Reactive Models (models.py)        │  │
 │  └──────────────┬───────────────────────────────────┬───────────────┘  │
 │                 │                                   │                  │
 │                 ▼ (120Hz Tick / 8ms dt)             ▼ (Qt Properties)  │
 │  ┌──────────────────────────────┐   ┌───────────────────────────────┐  │
 │  │ Physics Engine               │   │ Qt Quick / QML Scene Graph    │  │
 │  │ (physics/engine.py)          │   │ (qml/Canvas.qml)              │  │
 │  │  ├─ Stokes Fluid Drag        │   │  ├─ F3 SRE Diagnostic HUD     │  │
 │  │  ├─ Conformal Horizon Hull   │   │  ├─ Shield Membranes (Halo)   │  │
 │  │  ├─ Selective Repulsion      │   │  ├─ Cubic Bezier Tendrils     │  │
 │  │  └─ Breadth-First Clustering │   │  └─ 4-Tier Semantic Cards     │  │
 │  └──────────────┬───────────────┘   └───────────────┬───────────────┘  │
 │                 │                                   │                  │
 │                 └─────────────────┬─────────────────┘                  │
 │                                   ▼                                    │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │ Native Linux Integration & Security Sandbox                      │  │
 │  │  ├─ Path Canonicalization & Boundary Guard (utils/security.py)   │  │
 │  │  ├─ Desktop-Agnostic Subprocess Spawning (xdg-open)              │  │
 │  │  └─ Structured stdout Logging (systemd-journald)                 │  │
 │  └──────────────────────────────────────────────────────────────────┘  │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Subsystem Breakdown

### 3.1 Asynchronous IPC Client (`ipc/client.py`)
* Executes inside a dedicated background worker thread hosting an independent `asyncio` event loop[cite: 10].
* Connects to `$XDG_RUNTIME_DIR/aia_weaver/aia_weaver.sock` via a non-blocking UNIX domain socket[cite: 1, 10].
* Enforces a strict 64 KB per-frame buffer cap (`MAX_PAYLOAD_BYTES`) matching daemon specifications to prevent memory exhaustion[cite: 1, 10].
* Handles dropped connections with non-blocking reconnection backoff[cite: 10].

### 3.2 Reactive Store & Graph Model (`store.py`, `models.py`)
* `models.py`: Wraps nodes and edges into `QObject` subclasses with native Qt signals (`pyqtProperty`, `pyqtSignal`)[cite: 3].
* `store.py`: Serves as the primary in-memory graph ledger, maintaining local neighborhood adjacency lists and managing node lifetimes without coupling to rendering views[cite: 4].

### 3.3 Physics & Spatial Layout Engine (`physics/engine.py`)
* Integrates at 120Hz ($dt = 8\text{ms}$) on a dedicated high-precision timer[cite: 2].
* Implements quadratic Stokes fluid drag for biological, viscous movement[cite: 5].
* Dynamically derives non-penetration box bounds around the active focal card to prevent orbital card collisions[cite: 5].
* Evaluates multi-harmonic biological respiration to keep inactive nodes alive in the peripheral void[cite: 5].

### 3.4 Spatial Proximity Clustering & Shield Membranes (`qml/ClusterHalo.qml`)
* Resolves dense connected components using Breadth-First Search (BFS) bounded by a spatial proximity threshold ($300\text{px} \times \text{Aperture}^{0.7}$)[cite: 5].
* Rejects distant outliers from cluster bounding radii, keeping shield bubbles compact[cite: 5].
* Filters centroid coordinates and radii through an exponential low-pass filter ($\alpha = 0.14$) to ensure jitter-free spatial transitions[cite: 5].
* Renders lightweight, multi-layer GPU vector rings with uniform interior glass washes[cite: 7].

### 3.5 Modular QML Component Hierarchy & 4-Tier Semantic Zoom Matrix (`qml/Node.qml`)

`Node.qml` acts strictly as an interactive coordinator / state-machine container, delegating all actual visual rendering of leaf delegates to dedicated components:
* **Leaf Delegate Subdirectory (`aia_canvas/src/qml/node/`):**
  * **`NodePill.qml`:** Renders Tier 3 (compact capsules) and Tier 4 (badges/bead-bloom capsules).
  * **`NodePreview.qml`:** Renders Tier 1.5 hover-dwell and search preview cards ($320 \times 220\text{px}$).
  * **`NodeAura.qml`:** Renders the GPU-native semantic glow, selection halo, and active search highlight shaders.
  * **`tokenView` (Inline in `Node.qml`):** Renders Tier 2 ambient inspection slates ($220 \times 64\text{px}$).
* **Zoom Matrix Tiers:**
  * **Tier 1 (Focal Workbench, $W=1400\text{px}, H=900\text{px}$):** Expanded active surface with interactive file actions and live viewport integration[cite: 2, 8].
  * **Tier 2 (Orbital Horizon Token, $W=220\text{px}, H=64\text{px}$):** High-salience inspection slates display file properties, badges, and downstream counters[cite: 8].
  * **Tier 3 (Compact Capsule, $H=32\text{px}$, natural width):** Streamlined symmetrical pills showing type badge and title, active at mid-range apertures or for secondary/unrelated nodes[cite: 8].
  * **Tier 4 (Macro Star Bead, $14 \times 14\text{px}$):** Luminous chromatic pips with centered light cores, blooming into preview capsules on hover[cite: 8].

### 3.6 Security & Subprocess Sandbox (`utils/security.py`)
* `canonicalize_safe_path`: Enforces strict path canonicalization to verify all target paths reside within `$HOME` or `$XDG_RUNTIME_DIR`.
* Eliminates shell-string evaluation by invoking `xdg-open` via tokenized `subprocess.Popen` within isolated process sessions (`start_new_session=True`).

### 3.7 SRE Observability & Telemetry (`main.py`, `bridge.py`, `qml/Canvas.qml`)
* Outputs structured logs (`%(asctime)s [%(levelname)s] %(name)s: %(message)s`) directly to `stdout` for ingestion by `systemd-journald`.
* Instruments `physics.step()` execution time; emits warnings if computation exceeds the 6.5ms threshold of the 8.0ms frame budget.
* Features a toggleable `F3` Diagnostic HUD rendering live node/edge counts, physics frame latency, and backend socket health.

---

## 4. Mathematical Models & Spatial Mechanics

### 4.1 Inertial Mass Scaling
Node inertial mass $M_i$ scales linearly with degree centrality $D_i$ to ensure hub nodes anchor the physical space while leaf nodes move flexibly[cite: 5]:
$$M_i = 1.0 + (0.55 \cdot D_i)$$
[cite: 5]

### 4.2 Stokes Quadratic Fluid Drag
To achieve biological flotation without abrupt velocity cutoffs, velocity $\mathbf{v}$ is damped using linear ($c_1$) and quadratic ($c_2$) coefficients[cite: 5]:
$$\mathbf{F}_{\text{drag}} = -(c_1 + c_2 \Vert{}\mathbf{v}\Vert{}) \mathbf{v}$$
[cite: 5]
* **Focused Mode:** $c_1 = 14.0$, $c_2 = 0.075$, $v_{\text{max}} = 24.0\text{ px/s}$[cite: 5].
* **Void Mode:** $c_1 = 9.0$, $c_2 = 0.075$, $v_{\text{max}} = 20.0\text{ px/s}$[cite: 5].

### 4.3 Selective Intra/Inter-Component Repulsion
Electrostatic repulsion is selectively disabled between nodes belonging to the same connected component ($C_a = C_b$), allowing internal springs to coalesce clusters while pushing unrelated projects away[cite: 5]:
$$\mathbf{F}_{\text{rep}} = \begin{cases}  \mathbf{0} & \text{if } C_a = C_b \text{ and } \Vert{}\mathbf{d}\Vert{} > d_{\text{overlap}} \\ \frac{Q_{\text{amb}}}{\Vert{}\mathbf{d}\Vert{}^2} \hat{\mathbf{d}} & \text{if } C_a \neq C_b  \end{cases}$$
[cite: 5]

### 4.4 Tendril Elasticity & Progressive Tractor Funnel
When edge distance $\Delta x$ exceeds resting span $s$, the Hookean spring constant $k$ scales with a progressive stretch multiplier to smoothly pull distant nodes into cluster membranes[cite: 5]:
$$\mathbf{F}_{\text{spring}} = k \cdot (\Delta x - s) \cdot \min\left(2.0, 1.0 + \frac{\Delta x - s}{450.0}\right) \hat{\mathbf{d}}$$
[cite: 5]

### 4.5 Conformal Horizon Hull
When a focal card is active, 1st-degree neighbors orbit along an aspect-conformal perimeter $R(\theta)$ derived from screen geometry and viewport padding[cite: 5]:
$$R(\theta) = \max\left(R_{\text{hull}}(\theta), \min\left(R_{\text{ideal}}, R_{\text{viewport}}(\theta) - 20\right)\right)$$
[cite: 5]
$$\text{where } R_{\text{hull}}(\theta) = \min\left(\frac{W_{\text{box}} / 2}{\vert{}\cos\theta\vert{}}, \frac{H_{\text{box}} / 2}{\vert{}\sin\theta\vert{}}\right) + 40.0$$
[cite: 5]

### 4.6 Multi-Harmonic Biological Respiration
Distant nodes experience organic floating drift driven by multi-harmonic sinusoidal oscillation[cite: 5]:
$$D_x(t) = A_r \left[\sin(0.18t + \phi_i) + 0.35\sin(0.07t + 2.1\phi_i)\right]$$
[cite: 5]
$$D_y(t) = 0.75 A_r \left[\cos(0.14t + 1.3\phi_i) + 0.35\cos(0.05t + 0.7\phi_i)\right]$$
[cite: 5]
$$\text{where } \phi_i = i \times 1.618033 \quad (\text{Golden Ratio Phase Shift})$$
[cite: 5]

### 4.7 Synaptic Cubic Bezier Tendrils
Tendril endpoints intersect card perimeters via bounding ray-box intersections, with gravitational sag applied along the midpoint[cite: 9]:
$$\mathbf{B}(t) = (1-t)^3 \mathbf{P}_0 + 3(1-t)^2 t \mathbf{P}_1 + 3(1-t)t^2 \mathbf{P}_2 + t^3 \mathbf{P}_3 \quad t \in [0, 1]$$
$$\mathbf{P}_1 = \mathbf{P}_0 + (\Delta x_{\text{clamped}}, S_{\text{sag}}), \quad \mathbf{P}_2 = \mathbf{P}_3 - (\Delta x_{\text{clamped}}, -S_{\text{sag}})$$
[cite: 9]

---

## 5. Semantic Aperture & Visual LOD Hierarchy

### 5.1 UI State Machine Invariants
* **Mutually Exclusive State Flags:** Strict mutual exclusivity must be maintained at all times between the state flags: `isPreviewMode`, `isSlateMode`, `isCapsuleMode`, and `isBeadMode`.
* **Single Delegate Visibility Invariant:** Exactly ONE visual leaf delegate must be active and visible (`opacity: 1.0`) at any given time to guarantee that multiple delegates do not render simultaneously.
* **Unified Animations:** To ensure absolute visual consistency across the canvas, all dimensional transitions (width, height, radius) must employ a unified **220ms `Easing.OutQuint`** easing curve.

### 5.2 Aperture & Dimensions Matrix

| Aperture ($\alpha$) / Trigger | Mode / Tier | Active Delegate | Dimensions | Typography / Visual Representation |
| :--- | :--- | :--- | :--- | :--- |
| **$\alpha \ge 1.00$** | **Tier 2: Horizon Token** | `tokenView` (inline in `Node.qml`) | $220 \times 64\text{px}$ | Amber-bordered ambient inspection slate, full file details |
| **$0.40 \le \alpha < 1.00$** | **Tier 3: Compact Capsule** | `NodePill.qml` | Height: $32\text{px}$, natural width | Symmetrical Pill, Ext Badge, truncated Monospace Title |
| **$\alpha < 0.40$** | **Tier 4: Star Bead** | `NodePill.qml` (bead sub-mode) | $14 \times 14\text{px}$ | Luminous Chromatic Pip + Light Core, pure color (Zero Text) |
| **Hover / Search Dwell** | **Tier 1.5: Dwell/Search** | `NodePreview.qml` (`isPreviewMode`) | $320 \times 220\text{px}$ | Hover-dwell & search preview card, rich file snippet content |
| **Selected / Focused** | **Tier 1: Focal Workbench** | Direct Workbench Overlay / Slates | $1400 \times 900\text{px}$ | Active interactive surface, Live Buffer, fully resizable |

---

## 6. IPC Protocol & Event Consumption

`aia_canvas` consumes the JSON-RPC 2.0 interface served by `aia_weaver` over `$XDG_RUNTIME_DIR/aia_weaver/aia_weaver.sock`[cite: 1, 10]:

### 6.1 RPC Methods Invoked
* **`get_neighbors`**: Dispatched when a node is selected to populate 1st-degree relational context[cite: 2].
  ```json
  {"jsonrpc": "2.0", "method": "get_neighbors", "params": {"node_id": 1}, "id": 1}
  ```

### 6.2 Broadcast Notifications Handled
* **`node_updated`**: Dynamically creates or updates spatial positions and metadata when files are touched[cite: 2, 10, 11].
* **`node_deleted`**: Prunes dead nodes and cascades edge removals immediately from the layout graph[cite: 2, 10, 11].

---

## 7. Teardown Lifecycle & POSIX Hygiene

1. **Signal Traps:** Intercepts `SIGINT` via a native terminal heartbeat timer, ensuring prompt termination under POSIX process managers[cite: 1].
2. **IPC Thread Termination:** Cancels pending futures, closes Unix streams, and terminates the background `asyncio` event loop cleanly[cite: 10].
3. **GPU Context Release:** Tears down QML Scene Graph textures, shape paths, and layer buffers without leaking Wayland/X11 display handles.

---
---

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
* **4-Tier Semantic Aperture:** Seamless LOD scaling ranging from live resizable Workbenches ($1400 \times 900\text{px}$) down to $16\text{px}$ luminous Star Beads with fish-eye hover blooms[cite: 2, 8].
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