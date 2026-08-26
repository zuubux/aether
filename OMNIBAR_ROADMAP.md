# OMNIBAR_ROADMAP.md: Modular Spatial Dispatch Architecture

## 1. System Vision & Interaction Principles
The OmniBar is Aether's central multimodal neural HUD—an organic, non-blocking interface unifying low-latency fuzzy search, camera steering, in-place conversational AI reasoning, contextual shell execution, and spatial telemetry.

* Hardware-Agnostic Intent Bus: Input ingestion (Keyboard, Voice/Whisper, Saccade/Gaze Dwell, Touch Gestures) normalizes into canonical Action Intent structures before execution, preventing hardware-locked logic.
* Unobstructed Perspective Horizon: The HUD is bottom-anchored (y: parent.height - height - 36), preserving the upper 75% of the viewport for perspective depth and distant node clusters.
* Two-Tier Progressive Results: Results present as a low-profile single horizontal carousel (~5–6 visible items across a 12–16 item buffer) by default, expanding vertically into a high-density shelf on demand.
* Focal Tether & In-Place Morphing: Operates as a global bottom-anchored HUD or dynamically tethers to an active node in world space. Mode shifts (Search -> LLM Persona -> Shell Exec) expand in-place without coordinate resets.
* Dynamic Auric Glows: 1px hairline glows communicate engine state:
  - Neutral Slate (Theme.borderSubtle): Standard Fuzzy Search.
  - Gemini Cyan / Indigo (#06B6D4 / #6366F1) / Claude Coral (#F97316): Conversational AI.
  - Terminal Amber (#F59E0B) / Emerald (#10B981): Quick Exec Shell.
* Temporal Decay: Idle unpinned surfaces smoothly dissolve to eliminate visual clutter.

---

## 2. Dispatch Backend Architecture

[ Multimodal Ingestion Tier ]
(Keyboard OmniBar, Voice Stream, Gaze, Radial Menu)
          |
          v
+-------------------------------+
|       Intent Normalizer       |
|  * Canonical Action Struct    |
|  * Assembles OmniContext      |
+---------------+---------------+
          |
          v (Qt Signal / Intent Bus)
+-------------------------------+
|          OmniRouter           |
|  * Deterministic Prefix Match |
|  * Dispatches to OmniEngine   |
+---------------+---------------+
          |
  +-------+-------+-------+
  v               v       v
+-----------+ +-----------+ +-----------+
|FuzzySearch| | ShellExec | | Conversat.|
|Engine     | | Engine    | | Engine    |
|(Phase 4.1)| |(Phase 4.3)| |(Phase 4.4)|
+-----+-----+ +-----+-----+ +-----+-----+
      |             |             |
      +-------+-----+-------------+
              |
              v
  [ Async Result Channel ]
  (Non-blocking QThreadPool)
              |
              v (Qt Slot / Signal)
  [ OmniBar / Canvas HUD UI ]

* OmniContext Dataclass (aia_canvas/src/omni/context.py):
  - raw_query: str -> Active input buffer.
  - intent_type: str -> Normalized intent (SEARCH, EXEC_SHELL, LLM_QUERY, DIAGNOSTIC).
  - focused_node_id: Optional[str] -> Target node ID if tethered.
  - focused_node_path: Optional[str] -> Absolute disk path / cwd for contextual shell execution.
  - selected_node_ids: list[str] -> All active selection IDs.
* OmniEngine Protocol (aia_canvas/src/omni/base.py):
  - can_handle(query: str, context: OmniContext) -> float: Evaluates affinity score (0.0 to 1.0).
  - execute(query: str, context: OmniContext) -> AsyncIterator[OmniResult]: Asynchronously yields standardized result objects.
  - get_mode_metadata() -> ModeConfig: Defines UI visual styling (glow color, icon glyph, placeholder text).
* OmniRouter Dispatcher (aia_canvas/src/omni/router.py):
  - Prioritizes deterministic prefixes (> Shell, ? LLM, : System Actions), falling back to FuzzySearchEngine.
  - Dispatches queries asynchronously to maintain 120 FPS scene-graph fluidity.

---

## 3. Implementation Phases

### Phase 4.1: Dispatch Backend & Horizontal Carousel Ribbon (COMPLETED)
* Backend: OmniContext, OmniResult, OmniRouter, and in-memory FuzzySearchEngine.
* Frontend: Frosted acrylic bottom HUD, horizontal ribbon, typing cadence, and key bindings.
* Verification: Formalized unit tests in tests/unit/test_omni_router.py passing under pytest.

---

### Phase 4.2: Camera Steering & Single-Delegate Previews (COMPLETED)
* Tasks:
  - Viewport 2D affine glide centering target nodes on search navigation and selection.
  - Consolidated search preview to reuse standard NodePreview.qml (Tier 1.5).
  - Suppressed legacy focal cards and ghost bounding boxes.
* Verification: Full pytest tests/ harness passing in < 2.0s.

---

### Phase 4.3: System Quick Exec Engine (> Prefix) (NEXT FOCUS)
Objective: Lightweight, non-blocking shell command execution directly from the OmniBar with live stream output.

* Backend Tasks (aia_canvas/src/omni/engines/shell.py):
  - Implement ShellEngine inheriting from OmniEngine.
  - Detect > prefix (affinity = 1.0).
  - Resolve working directory (cwd): Use active selected node's parent directory if available; fallback to workspace root.
  - Asynchronous subprocess runner via QThreadPool / asyncio to prevent UI thread locks.
  - Real-time streaming of stdout and stderr chunks wrapped into OmniResult tokens.
* Frontend Tasks (aia_canvas/src/qml/):
  - Switch OmniBar border glow to Terminal Amber (#F59E0B) or Emerald (#10B981) upon typing >.
  - Render an ephemeral mini output drawer above the OmniBar to stream stdout/stderr without opening external terminal windows.
  - Auto-dismiss on Esc or canvas click-away.
* Verification:
  - Add unit tests in tests/unit/test_shell_engine.py for command parsing, cwd resolution, and async output streaming.
  - Run: pytest tests/.

---

### Phase 4.4: Conversational Dialogue Surface & LLM Integration
Objective: In-place expansion into a grounded conversational reasoning surface powered by configurable LLMs (Gemini/Claude).

* Tasks:
  - Input capsule morphing into floating dialogue slate upon conversational prefixes (?, how, what).
  - Provider theming (Cyan/Indigo for Gemini, Coral for Claude) and glyph docking.
  - Spatial RAG grounding: injecting focused node topology from weaver_graph.db into prompt context.
  - Ephemeral in-memory chat state with secret sanitization.
* Verification: Tests in tests/unit/test_llm_engine.py for prompt payload generation and topology serialization.

---

### Phase 4.5: Node-Tether Engine & Spatial Interpolation
Objective: Enable the OmniBar to break away from the bottom dock and tether directly to active canvas nodes.

* Tasks:
  - Smooth spring interpolation between screen-space bottom dock and canvas world-space coordinates.
  - Render visual tether filament connecting capsule to node origin.
* Verification: Verify smooth anchoring during high-speed canvas panning and zooming.

---

### Phase 4.6: In-App Diagnostics & Live Health Monitor
Objective: Integrated "System Health & QA" HUD running pytest in background threads.

* Tasks:
  - Triggered via :test command in OmniBar or Settings menu.
  - Non-blocking QRunnable running the test runner with live JSON-RPC streaming.
  - Visual progress bars and expandable failure diff traces inside the UI.
* Verification: Test diagnostic engine execution and reporting contracts.