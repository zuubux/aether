# OMNIBAR_ROADMAP.md: Modular Spatial Dispatch Architecture

## 1. System Vision & Interaction Principles
The OmniBar is Aether's central multimodal neural HUD—an organic, non-blocking interface unifying low-latency fuzzy search, camera steering, in-place conversational AI reasoning, contextual shell execution, and spatial telemetry.

* **Hardware-Agnostic Intent Bus:** Input ingestion (Keyboard, Speech Streams, Spatial Canvas Drag-and-Drop, Touch Gestures) normalizes into canonical Action Intent structures before execution, preventing hardware-locked logic.
* **Unobstructed Perspective Horizon:** The HUD is bottom-anchored (`y: parent.height - height - 36`), preserving the upper 75% of the viewport for perspective depth and distant node clusters.
* **Two-Tier Progressive Results:** Results present as a low-profile single horizontal carousel (~5–6 visible items across a 12–16 item buffer) by default, expanding vertically into a high-density shelf on demand.
* **Focal Tether & In-Place Morphing:** Operates as a global bottom-anchored HUD or dynamically tethers to an active node in world space. Mode shifts (Search -> LLM Persona -> Shell Exec) expand in-place without coordinate resets.
* **Dynamic Auric Glows:** 1px hairline glows communicate engine state:
  - Neutral Slate (`Theme.borderSubtle`): Standard Fuzzy Search.
  - Gemini Cyan / Indigo (`#38BDF8` / `#6366F1`) / Claude Coral (`#F97316`): Conversational AI.
  - Terminal Amber (`#F59E0B`) / Emerald (`#10B981`): Quick Exec Shell.
* **Typographic Provenance:** AI-generated reasoning and summaries strictly render in `Theme.fontAiVoice` (*Source Serif 4*), establishing an unmistakable visual provenance boundary distinct from UI sans-serif and machine monospace.
* **Temporal Decay:** Idle unpinned surfaces smoothly dissolve to eliminate visual clutter.

---

## 2. Dispatch Backend Architecture

```text
[ Multimodal Ingestion Tier ]
(Keyboard OmniBar, Voice Stream, Canvas Node Drop, Touch Gestures)
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
  (Non-blocking QThreadPool / asyncio)
              |
              v (Qt Slot / Signal)
  [ OmniBar Coordinator / Canvas HUD UI ]
```

* **OmniContext Dataclass (`aia_canvas/src/omni/context.py`):**
  - `raw_query: str`: Active input buffer.
  - `intent_type: str`: Normalized intent (`SEARCH`, `EXEC_SHELL`, `LLM_QUERY`, `DIAGNOSTIC`).
  - `focused_node_id: Optional[str]`: Target node ID if tethered.
  - `focused_node_path: Optional[str]`: Absolute disk path / cwd for contextual shell execution.
  - `selected_node_ids: list[str]`: All active selection IDs.
  - `attached_context_ids: list[str]`: Explicitly attached canvas nodes / cluster IDs for spatial RAG.
* **OmniEngine Protocol (`aia_canvas/src/omni/base.py`):**
  - `can_handle(query: str, context: OmniContext) -> float`: Evaluates affinity score (0.0 to 1.0).
  - `execute(query: str, context: OmniContext) -> AsyncIterator[OmniResult]`: Asynchronously yields standardized result objects.
  - `get_mode_metadata() -> ModeConfig`: Defines UI visual styling (glow color, icon glyph, placeholder text).
* **OmniRouter Dispatcher (`aia_canvas/src/omni/router.py`):**
  - Prioritizes deterministic prefixes (`>` Shell, `?` LLM, `:` System Actions, `/` Commands), falling back to `FuzzySearchEngine`.
  - Dispatches queries asynchronously to maintain 120 FPS scene-graph fluidity.

---

## 3. Implementation Phases & Work Chunks

### Phase 4.1: Dispatch Backend & Horizontal Carousel Ribbon (COMPLETED)
* **Backend:** `OmniContext`, `OmniResult`, `OmniRouter`, and in-memory `FuzzySearchEngine`.
* **Frontend:** Frosted acrylic bottom HUD, horizontal ribbon, typing cadence, and key bindings.
* **Verification:** Formalized unit tests in `tests/unit/test_omni_router.py` passing under pytest.

---

### Phase 4.2: Camera Steering & Single-Delegate Previews (COMPLETED)
* **Tasks:**
  - Viewport 2D affine glide centering target nodes on search navigation and selection.
  - Consolidated search preview to reuse standard `NodePreview.qml` (Tier 1.5).
  - Suppressed legacy focal cards and ghost bounding boxes.
* **Verification:** Full `pytest tests/` harness passing cleanly.

---

### Phase 4.3: System Quick Exec Engine (`>` Prefix) (COMPLETED)
* **Tasks:**
  - Implemented `ShellEngine` inheriting from `OmniEngine` with subprocess runner and ANSI color mapping.
  - Terminal Amber border styling (`#F59E0B`), select-on-submit, and up/down command history buffer.
* **Verification:** Unit tests in `tests/unit/test_shell_engine.py` passing under pytest.

---

### Phase 4.4: Modular Decomposition & Conversational Surface (ACTIVE FOCUS)

#### Chunk 4.4A: Component Modularization (`aia_canvas/src/qml/omni/`)
* **Scope:**
  - Decompose monolithic `OmniBar.qml` into modular sub-delegates:
    - `OmniPrefixBadge.qml`: Renders mode pill (`AI ?`, `SET /`, `CLI >`) with fixed bounds and 12px left padding.
    - `OmniInputBuffer.qml`: Encapsulates `TextInput` and placeholder text with dynamic left anchoring (`anchors.left: prefixBadge.right`, `anchors.leftMargin: 10`) to eliminate character clipping.
    - `OmniContextShelf.qml`: Horizontal container rendering attached context chips with $\ge 44\text{px}$ touch hitboxes.
    - `OmniDialogueSurface.qml`: Frosted glass drawer displaying streamed conversational tokens.
  - Refactor `OmniBar.qml` to act strictly as the coordinator shell.
* **Verification:** `pytest tests/qml/test_omnibar_keys.py`.

#### Chunk 4.4B: AI Typographic Provenance & Streaming Kinematics
* **Scope:**
  - Define `Theme.fontAiVoice: "Source Serif 4"` and `Theme.aiVoiceColor: "#E0F2FE"` in `Theme.qml`.
  - Bind `OmniDialogueSurface.qml` to render streamed tokens in `Theme.fontAiVoice`.
  - Add trailing luminescent cursor pip during generation that dissolves on `engineState == "IDLE"`.
* **Verification:** `pytest tests/unit/test_conversation_engine.py`.

#### Chunk 4.4C: Spatial Canvas Drag-and-Drop Ingress
* **Scope:**
  - Add `DropArea` to `OmniBar.qml` (`keys: ["aether/node"]`).
  - Attach `DragHandler` / `Drag.active` to canvas node delegates.
  - Dropping a canvas node registers it in `OmniBar.attachedContext` and renders a removable chip in `OmniContextShelf.qml`.
* **Verification:** New tests in `tests/qml/test_omnibar_context.py`.

#### Chunk 4.4D: Spatial Grounding (Local RAG Prompt Assembly)
* **Scope:**
  - Update `ConversationController.stream_prompt(prompt, context_ids)`.
  - Query `weaver_graph.db` to serialize attached node metadata, nearest graph neighbors, and file contents into system context.
  - Pre-flight secret sanitization pipeline for `.env` files and tokens.
* **Verification:** `pytest tests/unit/test_conversation_engine.py`.

---

### Phase 4.5: Node-Tether Engine & Spatial Interpolation
* **Objective:** Enable the OmniBar to break away from the bottom dock and tether directly to active canvas nodes.
* **Tasks:**
  - Smooth spring interpolation between screen-space bottom dock and canvas world-space coordinates.
  - Render visual tether filament connecting capsule to node origin.
* **Verification:** Verify smooth anchoring during high-speed canvas panning and zooming.

---

### Phase 4.6: In-App Diagnostics & Live Health Monitor
* **Objective:** Integrated "System Health & QA" HUD running pytest in background threads.
* **Tasks:**
  - Triggered via `:test` command in OmniBar or Settings menu.
  - Non-blocking `QRunnable` running the test runner with live JSON-RPC streaming.
  - Visual progress bars and expandable failure diff traces inside the UI.
* **Verification:** Test diagnostic engine execution and reporting contracts.

---

## 4. Architectural Guardrails

1. **Pointer-Agnostic Handlers:** Use QtQuick Pointer Handlers (`TapHandler`, `DragHandler`, `PinchHandler`) instead of legacy `MouseArea` to ensure mouse interactions translate directly to touch events on tablet/wall hardware.
2. **Dynamic Spacing & Zero-Clipping:** In `OmniInputBuffer.qml`, text fields must anchor dynamically to the right edge of `OmniPrefixBadge` with explicit margins (`anchors.leftMargin: 10`), avoiding hardcoded input offsets.
3. **Single-Stroke Perimeter Rule:** Capsules and dialogue surfaces must have exactly ONE visual root element rendering `border.width: 1` and `color: "#0B0F19"`—zero nested duplicate borders.
4. **Non-Blocking Thread Safety:** Subprocesses and AI streaming loops must execute strictly via background threads (`asyncio` / `QThreadPool`) without invoking methods directly across thread boundaries or blocking GUI rendering.