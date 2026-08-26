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

### 3.1 Domain Controller Hierarchy & Lean Composite Root (`bridge.py` & `controllers/`)
The frontend architecture is orchestrated via a lean Composite Root pattern in `bridge.py`, which instantiates strongly-typed Domain Controllers inheriting from `BaseController`. Rather than defining monolithic passthrough slots on `bridge.py`, controllers are exposed directly to QML as read-only QProperties (`@pyqtProperty(QObject, constant=True)`):
* **`canvas` (`CanvasController`)**: Orchestrates macro UI states, zoom aperture (`cognitive_aperture`), theme toggles, workbench sizing, and omnibar focus bindings.
* **`node` (`NodeController`)**: Manages node/edge reactive lifecycle (CRUD), selection states, drag-and-drop spatial relocation, and media offloading.
* **`physics` (`PhysicsController`)**: Wraps the Stokes fluid dynamics engine (`engine.py`) and drives the 120Hz high-precision QTimer, handling metric exposition for SRE HUDs.
* **`search` (`SearchController`)**: Interfaces with `aia_weaver` IPC for semantic vector queries and exact-match title filters, maintaining the search candidate buffer.
* **`conversation` (`ConversationController`)**: Manages local/remote LLM conversation state, prompt dispatching, engine streaming, and provider metadata.

### 3.2 Asynchronous IPC Client (`ipc/client.py`)
* Executes inside a dedicated background worker thread hosting an independent `asyncio` event loop.
* Connects to `$XDG_RUNTIME_DIR/aia_weaver/aia_weaver.sock` via a non-blocking UNIX domain socket.
* Enforces a strict 64 KB per-frame buffer cap (`MAX_PAYLOAD_BYTES`) matching daemon specifications to prevent memory exhaustion.
* Handles dropped connections with non-blocking reconnection backoff.

### 3.3 Reactive Store & Graph Model (`store.py`, `models.py`)
* `models.py`: Wraps nodes and edges into `QObject` subclasses with native Qt signals (`pyqtProperty`, `pyqtSignal`).
* `store.py`: Serves as the primary in-memory graph ledger, maintaining local neighborhood adjacency lists and managing node lifetimes without coupling to rendering views.

### 3.4 Physics & Spatial Layout Engine (`physics/engine.py`)
* Integrates at 120Hz ($dt = 8\text{ms}$) on a dedicated high-precision timer.
* Implements quadratic Stokes fluid drag for biological, viscous movement.
* Dynamically derives non-penetration box bounds around the active focal card to prevent orbital card collisions.
* Evaluates multi-harmonic biological respiration to keep inactive nodes alive in the peripheral void.

### 3.5 Spatial Proximity Clustering & Shield Membranes (`qml/ClusterHalo.qml`)
* Resolves dense connected components using Breadth-First Search (BFS) bounded by a spatial proximity threshold ($300\text{px} \times \text{Aperture}^{0.7}$).
* Rejects distant outliers from cluster bounding radii, keeping shield bubbles compact.
* Filters centroid coordinates and radii through an exponential low-pass filter ($\alpha = 0.14$) to ensure jitter-free spatial transitions.
* Renders lightweight, multi-layer GPU vector rings with uniform interior glass washes.

### 3.6 Deconstructed OmniBar & Modular QML Subcomponents (`src/qml/bar/`)
The primary interaction and intent dispatch bar (`OmniBar.qml`) is deconstructed into 5 focused sub-components to isolate rendering and event logic:
* **`OmniInputCapsule.qml`**: Renders the central obsidian pill input field with dynamic border glow and cursor handling.
* **`SearchSuggestionRibbon.qml`**: Displays horizontal prefix completion suggestions and auto-fill tokens (`/`, `@`, `?`).
* **`DialogueDrawer.qml`**: Collapsible slate presenting live-streamed LLM responses and conversational turn histories.
* **`ShellOutputDrawer.qml`**: Terminal execution drawer showing command output, exit codes, and ANSI color formatting.
* **`ProviderBadge.qml`**: Displays active model/provider status badges (e.g. `Ollama / Qwen2.5`, `OpenAI`).

### 3.7 Desktop Integration & Subprocess Isolation (`utils/desktop.py`, `utils/security.py`)
* Desktop/OS subprocess operations are extracted from node controllers into `aia_canvas/src/utils/desktop.py`.
* Functions `open_in_file_manager(file_path)` and `open_in_external_editor(file_path)` use `utils.security.canonicalize_safe_path` to verify workspace containment.
* Spawns system handlers (`xdg-open`) via tokenized `subprocess.Popen` with `shell=False`, `start_new_session=True`, and redirected `stdout/stderr` streams.

### 3.8 Performance Telemetry & F3 Diagnostics Roadmap (`telemetry/metrics.py`, `DiagnosticsOverlay.qml`)
Telemetry collection is isolated in `TelemetryCollector` using fixed-size rolling ring buffers (`collections.deque(maxlen=120)`) to maintain bounded zero-allocation memory footprints:
* **Physics Tick Budget:** Measures 120Hz integration loop execution time ($8.0\text{ms}$ budget). Emits a red visual warning on `DiagnosticsOverlay.qml` if execution exceeds $6.5\text{ms}$.
* **SQLite Query Latency:** Measures query execution and KNN vector search latency from `aia_weaver` IPC responses.
* **IPC Ingestion Queue Depth & Latency:** Monitors non-blocking socket queue depths and payload frame decoding latencies.
* **LLM Streaming Throughput:** Tracks token delivery frequency and response chunk latencies during conversation streaming.

---

## 4. Performance & Concurrency

### 4.1 Asynchronous Media Worker Pipeline (`workers/media_worker.py`)
To ensure the Qt Main Thread (`GUI`) never blocks and achieves a consistent 120 FPS frame timing:
* All heavy I/O and media extraction operations (PDF rendering, CSV parsing, image loading) are offloaded to an asynchronous `QThreadPool` worker pipeline.
* Operations are wrapped in lightweight `QRunnable` instances (`MediaExtractionTask`).
* Results are safely marshalled back across thread boundaries via Qt Signals (`mediaReady`, `mediaError`) emitting complex `QVariantMap` payloads to non-blocking QML bindings.
* Prevents rendering jank when scanning multi-page high-resolution PDFs or parsing large dataset tokens.

## 5. Mathematical Models & Spatial Mechanics

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

## 6. Semantic Aperture & Visual LOD Hierarchy

### 6.1 UI State Machine Invariants
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

## 7. Drag Transit & Settle Mechanics

To eliminate kinetic disruption while ensuring high legibility during node rearrangement, `Node.qml` implements a stateful Drag Transit and Settle cycle:

```text
┌──────────────┐     Left Drag Press      ┌──────────────────────┐
│ Rest State   │ ───────────────────────► │ Dragging Active      │
│ (Tier 4/3/2) │                          │ (Tier 3 or Tier 2)   │
└──────────────┘                          └──────────┬───────────┘
       ▲                                             │
       │           1000ms Timeout                    │ Mouse Release
       └─────────────────────────────────────────────┴───────────┐
                  ┌──────────────────────┐                       │
                  │ Settling State       │ ◄─────────────────────┘
                  │ (Theme.accentCyan)   │
                  └──────────────────────┘
```

### 7.1 Tier Escalation During Transit
- **Tier 4 Escalation:** Micro-beads ($14 \times 14\text{px}$) escalate to **Tier 3 Capsule** ($32\text{px}$ height) when dragged, providing immediate visual surface area and title clarity.
- **Tier 3 / Tier 2 Escalation:** Ambient Tier 3 capsules and Tier 2 slates clamp directly to **Tier 2 Inspection Slate** ($220 \times 64\text{px}$) during transit.
- **Elevated Z-Index:** Active dragging promotes the node to `z: 1000`, rendering it above all standard cluster nodes and tendril paths.

### 7.2 1000ms Settle Delay & Luminosity Fade
- **Settle State:** Upon mouse release, `settleTimer` runs for `1000ms`, keeping the node in its escalated tier while transitioning its border to `Theme.accentCyan` (`#00F0FF`) with a width of `2px`.
- **Luminosity Dissipation:** As the settle timer elapses, the border smoothly transitions back to subtle ambient styling, and the node relaxes into the standard ambient tier.

### 7.3 Strict Input & Binding Isolation
- **Timer Muting:** Mouse dragging and settling actively clear and disable `intentTimer` and `hoverDwellTimer` to prevent spurious hover/dwell state escalation.
- **Coordinate Decoupling:** Property bindings (`x`, `y`) to the underlying physics model are conditionally disabled (`when: !rootItem.isDragging`) during drag, ensuring direct 1:1 cursor tracking without physics jitter.

---

## 8. Spotlight HUD & Search Architecture

The Spotlight search experience provides rapid query completion and orbital navigation without taking over the full viewport or displacing the physics layout:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Spotlight Search Architecture                                          │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ OmniBar (OmniBar.qml) - Input & Intent Dispatch                  │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │ onQuerySubmitted / Text Changed  │
│                                     ▼                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ SearchShelf (search/SearchShelf.qml)                             │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │ Tier 1.5 Active Preview Card (NodePreview.qml)             │  │  │
│  │  │ (Dynamically updates with currently focused match)         │  │  │
│  │  └───────────────────────────────┬────────────────────────────┘  │  │
│  │                                  │ Synchronized Index Selection  │  │
│  │  ┌───────────────────────────────▼────────────────────────────┐  │  │
│  │  │ Top 7 Ranked Results Carousel (ListView)                   │  │  │
│  │  │ [Card 0]  [Card 1]*  [Card 2]  [Card 3]  [Card 4]  ...     │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │ Enter / Key_Return               │
│                                     ▼                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Viewport Camera Focus & Search Shelf Dismissal                   │  │
│  │ (Smooth pan/zoom to target; zero physical grid displacement)     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### 8.1 Top 7 Ranked Carousel
- Search queries query the backend vector/graph index and return ranked candidate IDs (`searchResultIds`).
- `SearchShelf.qml` extracts the top 7 matches (`topMatches = searchResultIds.slice(0, 7)`) into a horizontal `ListView`.
- Each carousel item renders as a compact Tier 2 card displaying the file extension badge, file name, and preview snippet.

### 8.2 Live Tier 1.5 Active Preview Card
- An expanded Tier 1.5 preview card is anchored directly above the carousel.
- As the user navigates across candidates, the preview card reactively binds to `activeNodeData`, rendering rich markdown text, snippets, and connection stats.

### 8.3 Keyboard Traversal & Focus Flow
- **Traversal:** `Left Arrow`, `Right Arrow`, and `Tab` cycle through candidate items with automatic carousel centering (`positionViewAtIndex`).
- **Focus & Dismissal:** Pressing `Enter` or clicking an item invokes `canvasBridge.focus_node(nodeId)`, smoothly centering the viewport camera onto the target node while dismissing the OmniBar and clearing search scrims without altering physical cluster positions.

---

## 9. Modular HUD & Viewport Components

The UI shell separates global telemetry, status indicators, intent input, and search components into modular QML units:

```text
aia_canvas/src/qml/
├── Canvas.qml                  # Root window & viewport camera coordinator
├── bar/                        # Modular OmniBar & intent subcomponents
│   ├── OmniBar.qml             # Parent coordinator for input & drawers
│   ├── OmniInputCapsule.qml    # Central obsidian pill input capsule
│   ├── SearchSuggestionRibbon.qml # Real-time auto-completion suggestion ribbon
│   ├── DialogueDrawer.qml      # Streaming LLM response & dialogue slate
│   ├── ShellOutputDrawer.qml   # Terminal output execution drawer
│   └── ProviderBadge.qml       # Provider & LLM status badge
├── hud/
│   ├── DiagnosticsOverlay.qml  # F3 SRE telemetry HUD overlay
│   └── CanvasHud.qml           # Bottom-left IPC connection & Aperture pill
├── search/
│   └── SearchShelf.qml         # Spotlight search carousel & Tier 1.5 preview
├── node/
│   ├── NodeAura.qml            # GPU shaders for selection and glow
│   ├── NodePill.qml            # Compact capsule and badge delegate
│   └── NodePreview.qml         # Tier 1.5 rich preview card
├── slates/                     # Media & rich document content slates
├── SurfaceShell.qml            # Single-perimeter border and background shell
└── NodeContent.qml             # Adaptive content loader for active tier
```

* **`DiagnosticsOverlay.qml`:** Anchored to the top-right (`z: 9000`), toggled via `F3`. Displays live node counts, rendered edge counts, physics frametimes (with red alert highlighting above $6.5\text{ms}$), SQLite query latency, IPC ingestion metrics, and socket connection status.
* **`CanvasHud.qml`:** Anchored to the bottom-left (`z: 10`). Houses the IPC status indicator (pulsing green indicator when connected) and live cognitive aperture percentage gauge.
* **`SearchShelf.qml`:** Anchored above the OmniBar (`z: 10000`). Manages search carousel layout, active item previewing, and keyboard navigation.

---

## 10. IPC Protocol & Event Consumption

`aia_canvas` consumes the JSON-RPC 2.0 interface served by `aia_weaver` over `$XDG_RUNTIME_DIR/aia_weaver/aia_weaver.sock`:

### 10.1 RPC Methods Invoked
* **`get_neighbors`**: Dispatched when a node is selected to populate 1st-degree relational context.
  ```json
  {"jsonrpc": "2.0", "method": "get_neighbors", "params": {"node_id": 1}, "id": 1}
  ```

### 10.2 Broadcast Notifications Handled
* **`node_updated`**: Dynamically creates or updates spatial positions and metadata when files are touched.
* **`node_deleted`**: Prunes dead nodes and cascades edge removals immediately from the layout graph.

---

## 11. Teardown Lifecycle & POSIX Hygiene

1. **Signal Traps:** Intercepts `SIGINT` via a native terminal heartbeat timer, ensuring prompt termination under POSIX process managers.
2. **IPC Thread Termination:** Cancels pending futures, closes Unix streams, and terminates the background `asyncio` event loop cleanly.
3. **GPU Context Release:** Tears down QML Scene Graph textures, shape paths, and layer buffers without leaking Wayland/X11 display handles.