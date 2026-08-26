# Modular QML Frontend Contract

This document locks in the modularized QML frontend contract for knowledge nodes (`Node.qml` and associated leaf delegates), OmniBar sub-components (`bar/`), and domain controller bindings. This contract guarantees strict separation of concerns, robust state transition management, and performance safety metrics across the frontend ecosystem.

## 1. Component Boundaries & Directory Layout

### 1.1 Node Coordinator & Leaf Delegates (`aia_canvas/src/qml/node/`)

`Node.qml` acts strictly as an **interactive coordinator and state-machine container**. It handles:
- Position interpolation (from physics engine metrics).
- Mouse interaction, dragging, selection, and hovering timers.
- State evaluation and exposure of semantic zoom flags.
- Layout dimensions (target width, target height, radius, scale).

No rendering code (such as borders, backgrounds, glyph drawing, or text nodes) is defined directly in `Node.qml`. All visuals are offloaded to specialized leaf components in `aia_canvas/src/qml/node/`:

* **`NodePill.qml`**:
  * Renders Tier 3 compact capsules and Tier 4 extension badges/blooms.
  * Adjusts title text truncation, extension indicators, and compact pill margins.
* **`NodePreview.qml`**:
  * Renders Tier 1.5 hover-dwell and search preview cards ($320 \times 220\text{px}$).
  * Presents rich file summaries, snippets, and contextual metadata.
* **`NodeAura.qml`**:
  * Renders the GPU-native semantic glow, selection halo, and active search highlight shaders.
  * Animates relative focal brightness with optimal frame-rate performance.
* **`tokenView` (Inline Component in `Node.qml`)**:
  * Renders Tier 2 ambient inspection slates ($220 \times 64\text{px}$).
  * Displays file paths, extension badges, and downstream relation counters.

### 1.2 OmniBar Subsystem (`aia_canvas/src/qml/bar/`)

The interaction and intent bar (`OmniBar.qml`) is deconstructed into 5 focused sub-components:
* **`OmniInputCapsule.qml`**: Renders the central obsidian pill input field, keypress traps (`Ctrl+Space`, `Escape`, `Enter`), and cursor highlights.
* **`SearchSuggestionRibbon.qml`**: Renders real-time prefix completion tokens and auto-suggestions.
* **`DialogueDrawer.qml`**: Collapsible slate presenting live-streamed LLM responses and conversation turns.
* **`ShellOutputDrawer.qml`**: Terminal execution slate displaying command output, status codes, and ANSI formatting.
* **`ProviderBadge.qml`**: Active model provider indicator pill (e.g. `Ollama / Qwen2.5`, `OpenAI`).

### 1.3 Domain Controller Bindings (`bridge.py`)

`bridge.py` operates as a lean Composite Root exposing domain controllers directly to QML via read-only QProperties (`@pyqtProperty(QObject, constant=True)`), eliminating legacy passthrough slots:
* **`canvasBridge.node`**: Accesses `NodeController` (node CRUD, selection, drag relocation, media offload).
* **`canvasBridge.search`**: Accesses `SearchController` (vector KNN, prefix search, search shelf candidates).
* **`canvasBridge.conversation`**: Accesses `ConversationController` (LLM streaming, dialogue turns, engine state).
* **`canvasBridge.canvas`**: Accesses `CanvasController` (workbench dimensions, cognitive aperture, theme).
* **`canvasBridge.physics`**: Accesses `PhysicsController` (120Hz Stokes engine metrics, frametimes).

---

## 2. UI State Machine Invariants

To avoid overlapping delegates and visual glitches during spatial scaling, the system enforces the following invariants:

### 2.1 Mutually Exclusive State Flags
Exactly one of the following flags must evaluate to `true` at any given moment:
1. **`isPreviewMode`**: Active under active search result matches or hover-dwell activation (`isHovered && isDwellTriggered`).
2. **`isSlateMode`**: Active at standard cognitive aperture levels (Aperture $\ge 1.00$) when not selected.
3. **`isCapsuleMode`**: Active at medium cognitive aperture levels ($0.40 \le \text{Aperture} < 1.00$) or when hovering over a micro bead.
4. **`isBeadMode`**: Active at macro cognitive aperture levels (Aperture $< 0.40$) without hover focus.

### 2.2 Single Delegate Visibility Invariant
Exactly one visual delegate component must be visible (`opacity: 1.0`) at any time. When transition curves are active, opacity transitions must guarantee a clean crossfade without causing overlapping structural highlights or clipping artifacts.

### 2.3 Aperture & Dimensions thresholds
- **Tier 4 (<40% aperture)**: $14 \times 14\text{px}$ micro bead (`isBeadMode`).
- **Tier 3 (40%-100% aperture)**: Compact capsule with height of $32\text{px}$ and natural dynamic width (`isCapsuleMode`).
- **Tier 2 (>100% aperture)**: $220 \times 64\text{px}$ ambient inspection slate (`isSlateMode`).
- **Tier 1.5 (Dwell/Search)**: $320 \times 220\text{px}$ preview card (`isPreviewMode`).

### 2.4 Unified Animations
All dynamic layout transformations (e.g., width, height, and border-radius transitions) must use a unified duration of **220ms** paired with an **`Easing.OutQuint`** curve. This guarantees consistent, biological feeling spatial transitions.

---

## 3. Drag Transit & Settle Contract

* **Transit Tier Escalation:** Dragging elevates Tier 4 micro-beads to Tier 3 Capsule, and Tier 3 / Tier 2 nodes to Tier 2 Inspection Slate.
* **Settle Grace Period:** Releasing a dragged node triggers a 1000ms `settleTimer` with `Theme.accentCyan` border luminosity fade before settling into cluster equilibrium.
* **Input Isolation:** Dragging actively cancels and inhibits `intentTimer` and `hoverDwellTimer`, and decouples physics model bindings (`x`, `y`) during motion.

---

## 4. Performance Telemetry & F3 SRE Overlay Contract

* **Physics Frame Budget:** 120Hz integration loop target of $8.0\text{ms}$. If `canvasBridge.physicsFrametime` exceeds $6.5\text{ms}$, `DiagnosticsOverlay.qml` highlights the frametime reading in red (`#ef4444`).
* **In-Memory Telemetry Bounds:** Telemetry collectors must use fixed-size rolling ring buffers (`collections.deque(maxlen=120)`) with zero disk I/O churn or unbounded allocations.
* **Numeric Scalars Only:** Telemetry buffers strictly record numerical metrics (latencies, active node/edge counts, frametimes, threadpool counts). Content payloads and file paths are prohibited.

