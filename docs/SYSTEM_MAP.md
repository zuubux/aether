# Aether System Architecture Map

## 1. System Layer Hierarchy

### Presentation Layer (QML Quick 6)
- **Primary Canvas (`aia_canvas/src/qml/Canvas.qml`):** 
  The master viewport that routes global input events and acts as the root render context. Enforces the Camera Lock Invariant: The root canvas viewport remains anchored to (0, 0) with camera translation slewing forbidden. Node selections only apply bounded micro-parallax nudges (+/- 32px max).
- **Component Subsystems:**
  - `aia_canvas/src/qml/bar/`: 
    Input and command surfaces, including OmniBar, ShellDrawer, and file Drop targets.
  - `aia_canvas/src/qml/focal/`: 
    Immersive conversational mode and detailed slate previews (covering 85% of viewport).
  - `aia_canvas/src/qml/hud/`: 
    System diagnostics, engine status, and telemetry overlays (AmbientRadarHUD).
  - `aia_canvas/src/qml/node/`: 
    Spatial memory clusters and file visualizers (cards, auras, pills).
  - `aia_canvas/src/qml/slate/`: 
    Reusable window containers and visual shells (SlateFrame) supporting focal and satellite tiering.

### IPC & Orchestration Boundary (PyQt6 Bridge / Controllers)
- **Central Event Bus (`aia_canvas/src/bridge.py`):** 
  Translates asynchronous QML actions into Python runtime tasks, exposes dynamic viewport metrics (`viewportWidth`, `viewportHeight`, `centerX`, `centerY`), and emits UI state updates.
- **Domain Controllers (`aia_canvas/src/controllers/`):** 
  - `ConversationController`: Manages LLM turns and prompt assembly state boundaries.
  - `NodeController`: Orchestrates file parsing, visual node state, file drops, and staging.
  - `PhysicsController`: Safely wraps `PhysicsWorker` QThread interactions without blocking, routing node drags, pin states, aperture updates, dynamic center updates (`set_center`), and viewport dimensions (`set_viewport_dimensions`).
  - `SearchController`: Bridges local UI query routing to external vector/title databases.
  - `WorkingSetController`: Manages active working set slates, coordinating Tier 1 focal focus and Tier 1.25 companion satellites with LRU capacity management.

### Domain Engines & Storage (Python 3.11+, NumPy, SQLite)
- **Physics Substrate (`aia_canvas/src/physics/engine.py`):** 
  Vectorized NumPy calculations for 120Hz node force simulations and spatial constraints.
- **Conversational Intelligence (`aia_canvas/src/omni/engines/`):** 
  Streaming LLM handlers (Gemini) and dynamic workspace context aggregation.
- **Memory & Ledgers (`aia_canvas/src/memory/`):** 
  Persistent interaction logging and intelligent hot-context distillation via SQLite WAL. `memory.db` holds long-term cognitive facts and episodic summaries, keeping `weaver_graph.db` strictly dedicated to POSIX file metadata and spatial physics.

---

## 2. Core Component Registry

### OmniBar & DialogueDrawer
- **Path:** `aia_canvas/src/qml/bar/OmniBar.qml`, `aia_canvas/src/qml/bar/DialogueDrawer.qml`
- **Responsibility:** Primary user input capsule, quick-exec prefix detection (`?`, `>`), and smooth conversational surface expansion upon multi-turn engagement.
- **Signal Boundary:** QML `accepted` trigger maps to `SearchController.submit_query(str)` and `ConversationController` dispatch.

### SlateFrame
- **Path:** `aia_canvas/src/qml/slate/SlateFrame.qml`
- **Responsibility:** Reusable window container enforcing the Single-Stroke Rule; supports Tier 1 (Focal) and Tier 1.25 (Satellite) geometry, interactive resizing, and header drag translation.

### WorkspaceSlates
- **Path:** `aia_canvas/src/qml/slate/WorkspaceSlates.qml`
- **Responsibility:** Dynamic working set repeater managing Tier 1.25 satellite placement, fluid density scaling, promotion to focal center stage, and dismissal.

### FocalLensFrame
- **Path:** `aia_canvas/src/qml/focal/FocalLensFrame.qml`
- **Responsibility:** Tier 1 deep conversational slate defaulting to 70% width / 80% height with interactive corner resize geometry; handles massive context dumps and dense token rendering without visual lag.
- **Signal Boundary:** Property bindings tied directly to active search/chat UI states exposed via the central `bridge`.

### AmbientRadarHUD
- **Path:** `aia_canvas/src/qml/hud/AmbientRadarHUD.qml`
- **Responsibility:** System telemetry visualizer representing the engine as a continuous 4-state rune: `LATENT`, `WORKING`, `DISTILLING`, `OFFLINE`.
- **Signal Boundary:** Strictly listens to `bridge.engineStateChanged` with raw string payloads (bypassing boolean mask logic).

### UnloadModal
- **Path:** `aia_canvas/src/qml/hud/UnloadModal.qml`
- **Responsibility:** Elevated confirmation modal protecting against accidental exit; initiates graceful application teardown.
- **Signal Boundary:** Invoked by ambient `Escape` tier; emits `confirmed` to `Qt.quit()` to engage the shutdown compaction pipeline.

### AetherContextBuilder
- **Path:** `aia_canvas/src/omni/context.py`
- **Responsibility:** Single authoritative assembler for the AI persona, spatial context boundaries, runtime telemetry parameters, and localized workspace ground truth.
- **Signal Boundary:** Synchronously invoked natively by LLM Providers before external API dispatches occur.

### MemorySynthesizer & EventLedger
- **Path:** `aia_canvas/src/memory/synthesizer.py`, `aia_canvas/src/memory/event_ledger.py`
- **Responsibility:** SQLite WAL ledger for deterministic interaction capture, and a background QThread compaction worker for incremental memory grooming.
- **Signal Boundary:** Background timer polling directly against SQLite rows; relies on minimal cross-thread UI locking.

### WorkingSetController
- **Path:** `aia_canvas/src/controllers/working_set_controller.py`
- **Responsibility:** Manages active working set slates, coordinating Tier 1 focal focus and Tier 1.25 companion satellites with LRU capacity management.
- **Signal Boundary:** Coordinates with `bridge.selectedNodeChanged`; invoked via `openSlate(nodeId, archetype, title)` from QML `Canvas.qml` selection handlers; emits `focalSlateChanged(int)` and `activeSlatesChanged()`, routing active/recent node IDs (`recent_node_ids`) via `CanvasBridge` to `PhysicsController.set_recent_nodes` and `PhysicsWorker` for spatial budgeting and repulsion clearance.

### PhysicsEngine & PhysicsWorker
- **Path:** `aia_canvas/src/physics/engine.py`, `aia_canvas/src/physics/worker.py`
- **Responsibility:** High-performance vectorized force integration (Coulomb repulsion, Hooke's law springs, dynamic center point updates, kinematic horizon tracking).
- **Signal Boundary:** Executed asynchronously on dedicated `QThread` by `PhysicsWorker`; dispatches massive array snapshots to QML via `positions_updated`. Receives dynamic center coordinates via `set_center(cx, cy)` and viewport dimensions via `set_viewport_dimensions(w, h)` routed from `PhysicsController.request_center` and `PhysicsController.request_viewport_dimensions`, recalculating horizon radii and waking the simulation loop when nodes exist.

---

## 3. Data Flow & Signal Pipelines

### Viewport Dimension & Center Synchronization Pipeline
1. **Window / Viewport Geometry Change:** `Canvas.qml` detects changes in window dimensions via `onWidthChanged` / `onHeightChanged` / `Component.onCompleted`.
2. **Bridge Dispatch:** Invokes `canvasBridge.update_viewport_dimensions(w, h)`, which updates dynamic properties `viewportWidth`, `viewportHeight`, `centerX`, `centerY`, and fires `viewportDimensionsChanged`.
3. **Cross-Thread Physics Center & Dimension Propagation:** `CanvasBridge` computes `centerX = w * 0.5`, `centerY = h * 0.5` and calls `physics_ctrl.set_viewport_dimensions(w, h)` and `physics_ctrl.set_center(centerX, centerY)`, which emit `request_viewport_dimensions(w, h)` and `request_center(cx, cy)` across threads to `PhysicsWorker.set_viewport_dimensions(w, h)` and `PhysicsWorker.set_center(cx, cy)`.
4. **Simulation Horizon Update:** `PhysicsWorker` updates `engine.center_x` and `engine.center_y`, recalculates horizon thresholds, and revives the simulation timer if nodes are registered.
5. **Dynamic QML Fallback Resolution:** `Node.qml` cascades center coordinate lookups across `bridge.centerX`/`centerY`, `bridge.centerPoint`, and viewport container dimensions, eliminating static screen resolution assumptions.

### Conversational Turn Pipeline
1. **User Input:** Captured securely via `OmniBar` text capsule or `FocalLens` context bindings.
2. **Bridge Relay:** Strings emit to `Bridge`, invoking `ConversationController.submit_query()`.
3. **Engine Execution:** Request pushed downstream to `ConversationEngine` for intent/dependency resolution.
4. **Context Assembly:** `AetherContextBuilder` synthesizes the static persona, current workspace telemetry, and available token limits.
5. **Provider Streaming:** `GeminiProvider` fires network request and begins yielding text chunks via Server-Sent Events (SSE).
6. **UI Hydration:** Text chunks traverse the PyQt Bridge as a Drip Emitter directly into dynamic QML text surfaces.

### Telemetry Pipeline
1. **State Mutation:** Background intelligence workers or LLM processors change their internal state strings.
2. **Signal Propagation:** Controllers aggressively emit `engineStateChanged` events on the primary Python event loop.
3. **Bridge Intercept:** `bridge.py` captures and cleanly mirrors the event to all connected QML view clients.
4. **QML Consumption:** `Canvas.qml` preserves raw payload verbatim (e.g., `DISTILLING` instead of mapping down to a true/false gate).
5. **Visualizer Update:** `AmbientRadarHUD` visually rotates through distinct graphical runes mapped directly to the current string state.

### Compaction Pipeline
1. **Interaction Event:** Any user action triggers `EventLedger.record_event()` containing metadata payloads.
2. **Ledger Commit:** Data is persisted to disk instantly utilizing SQLite WAL mode for guaranteed non-blocking I/O.
3. **Synthesizer Poll:** Background `MemorySynthesizer` wakes up consistently on a deterministic time threshold.
4. **Prune Phase:** `EventLedger.prune_events` actively evicts database rows older than the specified TTL horizon.
5. **Vacuum Phase:** `PRAGMA incremental_vacuum` ensures the database footprint remains statically bounded and minimal.
6. **Token Extraction:** Remaining relevant data rows map into context arrays for instant consumption by `AetherContextBuilder`.
7. **Shutdown Compaction Phase:** Upon application termination, `app.aboutToQuit` triggers `ConversationController.synthesizer.shutdown()`, executing a synchronous final compaction pass (`synthesize_sync`) to flush uncompacted ledger events and heuristic facts directly into `~/.local/share/aether/memory.db`.

### Selection-to-Working-Set Pipeline
1. **Node Selection:** User interacts with node on canvas, via Omnibar search, or via direct bridge invocation (`select_node(nodeId)`).
2. **Signal Propagation:** `canvasBridge.selectedNodeChanged(nodeId)` fires to all connected view handlers.
3. **Viewport & Working Set Handler:** `Canvas.qml` viewport `Connections` catches `onSelectedNodeChanged(nodeId)`. If `nodeId > 0`, it animates camera to target coordinates and calls `workingSetCtrl.openSlate(nodeId, "", "")`. If `nodeId <= 0`, camera targets reset to origin while working set slates remain preserved.
4. **Focal & Satellite State Management:** `WorkingSetController.open_slate()` sets `_focal_slate_id`, demotes prior focal slates to Tier 1.25 companion satellites with LRU eviction (cap at 6), and signals `focalSlateChanged` and `activeSlatesChanged`. `CanvasBridge` listens to these signals and immediately synchronizes `recent_node_ids` across threads to `PhysicsController`/`PhysicsWorker` and the spatial budget layout.
5. **UI Presentation:** `WorkspaceSlates.qml` re-renders active satellite slates flanking the canvas with dynamic density scaling.

---

## 4. Non-Negotiable Architectural Invariants

* **Working Set Lifecycle:** Selecting an active node (`nodeId > 0`) automatically promotes it to Tier 1 focal center stage via `WorkingSetController.openSlate()`. Deselection preserves active working set state according to user intent.
* **Typographic Identity:** All AI dialogue MUST rigidly use `Cabinet Grotesk` (Regular static cut) and `Theme.aiVoiceGlacial` (`#BAE6FD` / Sky-200) locked at a 1.45 line height.
* **Slate Geometry (Single-Stroke Rule):** All visual slate cards must possess exactly one root element utilizing `border.width > 0`.
* **Slate Tier Hierarchy:** Tier 1 Focal (70% vw x 80% vh, z=100) vs Tier 1.25 Satellite (~42% vw x 48% vh, z=50).
* **Dynamic Geometry & Viewport Sizing:** Absolute ban on hardcoded screen resolutions (2560x1440, 1920x1080) and fallback pixels for QML layout and physics calculations. Coordinates, horizons, and center points cascade dynamically from `CanvasBridge` properties and viewport container bounds.
* **Physics Integration:** Pure Python loops are explicitly forbidden inside the physics integration step; all layout forces must be strictly NumPy vectorized.
* **Telemetry Rules:** Telemetry ring buffers must consistently employ fixed-capacity `collections.deque(maxlen=120)` with numeric scalars only.
* **Deterministic Tests (Diet Rule 10):** Zero wall-clock sleeps (`time.sleep` or `QTest.qWait`). Tests rigidly mandate deterministic condition polling (`qtbot.waitUntil`).
* **Database Constraints:** All SQLite database connections enforce WAL mode, `PRAGMA incremental_vacuum`, and `PRAGMA foreign_keys = ON`.
* **Concurrency Laws:** GUI threads must NEVER invoke background QThread worker methods directly. All boundary cross-communication must use strict PyQt signal/slot emissions.
