# Aether System Architecture Map

## 1. System Layer Hierarchy

### Presentation Layer (QML Quick 6)
- **Master Layout Shell & Root Canvas (`aia_canvas/src/qml/main.qml`):**
  Responsive master layout shell (`mainCanvasView`) organized into ambient spatial zones: Minimal Floating Horizon Anchors (top left weather/location, top right date & persona identity), Active Stage (`stageContainer`, expanding across the display with clean void when vacant), Peripheral Feed (floating semantic pill chips docked along the right perimeter), and self-morphing OmniBar bottom ambient pill. Enforces fluid responsive constraints and the Camera Lock Invariant: The root canvas viewport remains anchored to (0, 0) with camera translation slewing forbidden.
- **QML Module & Singleton Architecture (`aia_canvas/src/qml/qmldir`):**
  Exposes the `qml` module containing `singleton Theme 1.0 Theme.qml` and `AetherMotion 1.0 AetherMotion.qml`, registered as both a QML import module and Python context property (`Theme`) during bootstrap.
- **Component Subsystems:**
  - `aia_canvas/src/qml/components/`:
    Layout delegates including `FeedHeaderAnchor.qml` (micro-pill ribbon with left unread dot, active border glow, hover-to-grow, dwell-to-preview), `FeedFlowItem.qml` (graduated 30-day temporal rolling stack scaling across `full`, `compact`, and `fading` tiers), and `PlateCard.qml` (ratio-based Bento container with monospace log card rendering, visual media, and single-key `ai_summary` extraction).
  - `aia_canvas/src/qml/bar/`: 
    Input and command surfaces, including OmniBar, ShellDrawer, and file Drop targets.
  - `aia_canvas/src/qml/hud/`: 
    System diagnostics, engine status, and telemetry overlays (AmbientRadarHUD).
  - `aia_canvas/src/qml/slate/`: 
    Reusable window containers and visual shells (SlateFrame) supporting focal and satellite tiering.

### IPC & Orchestration Boundary (PyQt6 Bridge / Controllers)
- **Central Event Bus (`aia_canvas/src/bridge.py`):** 
  Translates asynchronous QML actions into Python runtime tasks, exposes dynamic viewport metrics (`viewportWidth`, `viewportHeight`, `centerX`, `centerY`), and emits UI state updates.
- **Domain Controllers (`aia_canvas/src/controllers/`):** 
  - `HorizonController`: Manages dynamic persona identity (user and hostname resolution) and ambient environmental telemetry for Stage 0 minimal horizon anchors.
  - `ConversationController`: Manages LLM turns and prompt assembly state boundaries.
  - `SearchController`: Bridges local UI query routing to external vector/title databases.
  - `WorkingSetController`: Manages active working set slates, coordinating Tier 1 focal focus and Tier 1.25 companion satellites with LRU capacity management.
  - `PlateCanvasController`: Orchestrates active canvas plates, Bento grid spatial allocations, spatial manipulation (move, resize, pin, close), and single-key `ai_summary` access.
  - `FeedController`: Bridges The Feed engine to UI surfaces, orchestrating header anchor micro-pills, graduated 30-day rolling flow stacks, and notification states.

### Domain Engines & Storage (Python 3.11+, NumPy, SQLite)
- **Conversational Intelligence (`aia_canvas/src/omni/engines/`):** 
  Streaming LLM handlers (Gemini) and dynamic workspace context aggregation.
- **Memory & Ledgers (`aia_canvas/src/memory/`):** 
  Persistent interaction logging and intelligent hot-context distillation via SQLite WAL. `memory.db` holds long-term cognitive facts and episodic summaries, keeping `weaver_graph.db` strictly dedicated to POSIX file metadata.
- **Plate Engine (`aia_canvas/src/plate_engine/`):** 
  Canonical data models (`PlateNodePayload`, `FeedItem`), semantic archetypes, temporal decay tracking, relational graph topology, cognitive mass calculation, editorial bento grid spatial allocation, 5-tier lifecycle management (`ACTIVE`, `WING`, `SUMMARY`, `MICRO`, `RAIL`) with pin locks, manual resize override timeouts, desktop sweep, lightweight cache-first text compression via `PlateSummaryEngine`, and The Feed engine orchestration for header anchor pins, graduated flow stacks, notification states, and ring buffer pruning.

---

## 2. Core Component Registry

### OmniBar & DialogueDrawer
- **Path:** `aia_canvas/src/qml/bar/OmniBar.qml`, `aia_canvas/src/qml/bar/DialogueDrawer.qml`
- **Responsibility:** Sole self-morphing ambient input component proportionally scaling between idle Stage 0 capsule pill ("What are we doing?") and expanded active workspace, quick-exec prefix detection (`?`, `>`), and smooth conversational surface expansion upon multi-turn engagement.
- **Signal Boundary:** QML `accepted` trigger maps to `SearchController.submit_query(str)` and `ConversationController` dispatch.

### SlateFrame
- **Path:** `aia_canvas/src/qml/slate/SlateFrame.qml`
- **Responsibility:** Reusable window container enforcing the Single-Stroke Rule; supports Tier 1 (Focal) and Tier 1.25 (Satellite) geometry, interactive resizing, and header drag translation.

### WorkspaceSlates
- **Path:** `aia_canvas/src/qml/slate/WorkspaceSlates.qml`
- **Responsibility:** Dynamic working set repeater managing Tier 1.25 satellite placement, fluid density scaling, promotion to focal center stage, and dismissal.

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
- **Signal Boundary:** Coordinates with `bridge.selectedNodeChanged`; invoked via `openSlate(nodeId, archetype, title)` from QML selection handlers; emits `focalSlateChanged(int)` and `activeSlatesChanged()`.


### PlateCanvasController
- **Path:** `aia_canvas/src/controllers/plate_controller.py`
- **Responsibility:** Domain controller bridging `PlateEngine` to QML; manages active plate registry, Bento grid layout calculations, single-key AI summary extraction (`ai_summary`), and spatial manipulation (move, resize, pin, close).
- **Signal Boundary:** Coordinates with QML Canvas and Bento views; exposes `activePlates`, `bentoGeometry`, `focalPlateId`, `plateCount`; emits `activePlatesChanged`, `bentoGeometryChanged`, `plateMoved`, `plateResized`, `platePinned`, `plateClosed`, `plateOpened`, `summaryUpdated`.

### FeedController
- **Path:** `aia_canvas/src/controllers/feed_controller.py`
- **Responsibility:** Domain controller bridging `FeedEngine` to QML; manages header anchor micro-pills, graduated 30-day temporal flow stacks (`full`, `compact`, `fading`), notification states (glow/dot), and ring buffer pruning.
- **Signal Boundary:** Coordinates with QML Feed surfaces; exposes `headerAnchors`, `flowStack`, `unreadCount`, `totalCount`; emits `headerAnchorsChanged`, `flowStackChanged`, `unreadCountChanged`, `feedRefreshed`, `itemNotificationChanged`, `itemPinnedChanged`, `itemAdded`, `itemRemoved`.

### HorizonController
- **Path:** `aia_canvas/src/controllers/horizon_controller.py`
- **Responsibility:** Domain controller managing dynamic horizon identity and ambient environmental status. Dynamically resolves user identity (`USER · HOSTNAME`) and provides reactive environmental telemetry.
- **Signal Boundary:** Coordinates with QML Horizon anchors; exposes `identity`, `ambientStatus`; emits `identityChanged(str)`, `ambientStatusChanged(str)`.

### PlateEngine
- **Path:** `aia_canvas/src/plate_engine/` (`models.py`, `parser.py`, `weights.py`, `bento.py`, `lifecycle.py`, `summary_engine.py`, `feed_engine.py`)
- **Responsibility:** Ingests Weaver IPC node dictionaries into strongly typed `PlateNodePayload` objects, maintaining archetype classification, temporal decay, relational graph topology, mass calculation, bento grid layout geometry, 5-tier lifecycle transitions (`ACTIVE`, `WING`, `SUMMARY`, `MICRO`, `RAIL`), cache-first extractive text compression for SUMMARY tier plates, and FeedEngine orchestration for header micro-pill anchor pins, graduated rolling flow stacks (`full`, `compact`, `fading`), notification states (glow/dot), and ring buffer / ephemeral time-decay pruning.
- **Signal Boundary:** Decoupled data model, ingestion parser, feed engine, and summary compression layer invoked during IPC sync / real-time graph events and lifecycle transitions, consumed by Canvas controllers and presentation components.



### MainCanvasView (Root)
- **Path:** `aia_canvas/src/qml/main.qml`
- **Responsibility:** Master responsive QML layout shell organizing the canvas into ambient zones: Minimal Floating Horizon Anchors (`leftHorizonAnchor` bound to `horizonController.ambientStatus`, `rightHorizonAnchor` bound to `liveDateText // horizonController.identity`), Active Stage (`stageContainer`, center/left, 64px top margin clearance to prevent collision with horizon anchors), Peripheral Feed (floating semantic pill chips docked along right perimeter), and self-morphing OmniBar bottom ambient pill. Summons/focuses OmniBar via clicking the ambient pill or pressing `Ctrl+Space` with `AetherMotion`, dismissing smoothly back to ambient equilibrium with `Escape`. Coordinates dynamic viewport synchronization with `PlateCanvasController.setViewportDimensions`.
- **Signal Boundary:** Bridges signals from `PlateCanvasController` (`activePlatesChanged`, `bentoGeometryChanged`, `focalPlateChanged`), `FeedController` (`headerAnchorsChanged`, `flowStackChanged`, `unreadCountChanged`), and `HorizonController` (`identityChanged`, `ambientStatusChanged`).

### FeedHeaderAnchor, FeedFlowItem & PlateCard Delegates
- **Path:** `aia_canvas/src/qml/components/FeedHeaderAnchor.qml`, `aia_canvas/src/qml/components/FeedFlowItem.qml`, `aia_canvas/src/qml/components/PlateCard.qml`
- **Responsibility:** Responsive presentation delegates for micro-pill ribbons (with left unread indicator and hover/dwell states), graduated temporal flow stack (with `full`, `compact`, `fading` view tiers), and Bento plate containers (with monospace log viewer, media cards, and single-key `ai_summary` synthesis drawers).
- **Signal Boundary:** Emits interaction triggers to `FeedController.markSeen`, `FeedController.pinItem`, `PlateCanvasController.selectPlate`, `PlateCanvasController.togglePin`, and `PlateCanvasController.closePlate`.
