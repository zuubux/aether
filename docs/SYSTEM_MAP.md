# Aether System Architecture Map

## 1. System Layer Hierarchy

### Presentation Layer (QML Quick 6)
- **Primary Canvas (`aia_canvas/src/qml/Canvas.qml`):** 
  The master viewport that routes global input events and acts as the root render context.
- **Component Subsystems:**
  - `aia_canvas/src/qml/bar/`: 
    Input and command surfaces, including OmniBar, ShellDrawer, and file Drop targets.
  - `aia_canvas/src/qml/focal/`: 
    Immersive conversational mode and detailed slate previews (covering 85% of viewport).
  - `aia_canvas/src/qml/hud/`: 
    System diagnostics, engine status, and telemetry overlays (AmbientRadarHUD).
  - `aia_canvas/src/qml/node/`: 
    Spatial memory clusters and file visualizers (cards, auras, pills).

### IPC & Orchestration Boundary (PyQt6 Bridge / Controllers)
- **Central Event Bus (`aia_canvas/src/bridge.py`):** 
  Translates asynchronous QML actions into Python runtime tasks and emits UI state updates.
- **Domain Controllers (`aia_canvas/src/controllers/`):** 
  - `ConversationController`: Manages LLM turns and prompt assembly state boundaries.
  - `NodeController`: Orchestrates file parsing, visual node state, file drops, and staging.
  - `PhysicsController`: Safely wraps `PhysicsWorker` QThread interactions without blocking.
  - `SearchController`: Bridges local UI query routing to external vector/title databases.

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

### PhysicsEngine
- **Path:** `aia_canvas/src/physics/engine.py`
- **Responsibility:** High-performance vectorized force integration (Coulomb repulsion, Hooke's law springs, kinematic horizon tracking).
- **Signal Boundary:** Executed asynchronously by `PhysicsWorker`; dispatches massive array snapshots to QML via `positions_updated`.

---

## 3. Data Flow & Signal Pipelines

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

---

## 4. Non-Negotiable Architectural Invariants

* **Typographic Identity:** All AI dialogue MUST rigidly use `Cabinet Grotesk` (Regular static cut) and `Theme.aiVoiceGlacial` (`#BAE6FD` / Sky-200) locked at a 1.45 line height.
* **Slate Geometry (Single-Stroke Rule):** All visual slate cards must possess exactly one root element utilizing `border.width > 0`.
* **Dynamic Geometry:** Absolute ban on hardcoded fallback pixels for QML bounding rectangles. Coordinate querying is mandatory.
* **Physics Integration:** Pure Python loops are explicitly forbidden inside the physics integration step; all layout forces must be strictly NumPy vectorized.
* **Telemetry Rules:** Telemetry ring buffers must consistently employ fixed-capacity `collections.deque(maxlen=120)` with numeric scalars only.
* **Deterministic Tests (Diet Rule 10):** Zero wall-clock sleeps (`time.sleep` or `QTest.qWait`). Tests rigidly mandate deterministic condition polling (`qtbot.waitUntil`).
* **Database Constraints:** All SQLite database connections enforce WAL mode, `PRAGMA incremental_vacuum`, and `PRAGMA foreign_keys = ON`.
* **Concurrency Laws:** GUI threads must NEVER invoke background QThread worker methods directly. All boundary cross-communication must use strict PyQt signal/slot emissions.
