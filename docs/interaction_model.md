# Spatial Interaction Model & Mechanics Specification

**Framework:** Aether Interface Architecture  
**Document Version:** 2.0.0  
**Subsystems:** `aia_canvas`, `aia_intent`, `aia_weaver`

---

## 1. Overview & Core Tenets

The Aether spatial interaction model operates on an anti-WIMP (Windows, Icons, Menus, Pointer) paradigm where information adapts in-place directly on an infinite obsidian canvas. All entity interactions are governed by biological easing curves, dynamic LOD escalation, physical settle states, and spotlight search overlays.

---

## 2. Interaction Tier Matrix

| Tier | Name | Target Dimensions | Trigger / Condition | Visual Attributes |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 4** | **Star Bead** | $14 \times 14\text{px}$ | Aperture $< 40\%$ at rest | Pure glowing chromatic pip, zero text, high density constellation view |
| **Tier 3** | **Compact Capsule** | Height: $32\text{px}$, natural width | $40\% \le \text{Aperture} < 100\%$ OR Tier 4 Drag | Symmetrical pill with extension badge and truncated title |
| **Tier 2** | **Inspection Slate** | $220 \times 64\text{px}$ | $\text{Aperture} \ge 100\%$, 250ms dwell, Drag Transit, or Settle | Single-stroke bordered slate with path snippet and relation count |
| **Tier 1.5** | **Preview Slate** | $320 \times 220\text{px}$ to $600 \times 400\text{px}$ | Sustained Dwell (1200ms) OR Spotlight active match | Rich markdown / media preview rendered in-place or on search shelf |
| **Tier 1** | **Focal Workbench** | Full card dimensions | Left click selection | Full interactive buffer / media player with contextual orbital docking |

---

## 3. Drag Transit & Settle Mechanics

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

### 3.1 Dynamic Tier Escalation During Drag
* **Tier 4 Escalation:** Micro-beads ($14\times 14\text{px}$) escalate immediately to **Tier 3 Compact Capsules** ($32\text{px}$ height) when drag starts. This provides immediate visual target area and readable titles while moving across the canvas.
* **Tier 3 / Tier 2 Escalation:** Tier 3 capsules and Tier 2 slates clamp to **Tier 2 Inspection Slates** ($220 \times 64\text{px}$) during drag.
* **Z-Index Layering:** Nodes being dragged escalate to `z: 1000` so they float cleanly above background clusters and tendril lines.

### 3.2 1000ms Settle Grace Period & Luminosity Fade
* **Release Trigger:** When mouse drag releases, `settleTimer` is triggered with an interval of `1000ms` (`isSettling = true`).
* **Cyan Luminosity Boost:** During the settle window, the node's perimeter border switches to `Theme.accentCyan` (`#00F0FF`) with a stroke width of `2px` and `z: 500`.
* **Graceful Fade:** When `settleTimer` finishes, the border smoothly transitions back to ambient muted border styling, and the node relaxes back to its ambient tier.

### 3.3 Strict Separation & Muting Invariants
* **Hover / Dwell Muting:** While `isDragging` or `isSettling` is active, `intentTimer` (250ms) and `hoverDwellTimer` (1200ms) are stopped and prevented from triggering.
* **Coordinate Model Decoupling:** Model coordinate property bindings (`x`, `y`) are suspended (`when: !rootItem.isDragging`), giving the cursor direct 1:1 control without fighting physics spring integration.


---

## 4. Spotlight HUD & Search Shelf Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Spotlight Search HUD                                                   │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ OmniBar.qml (Ctrl+Space) - Search Query & Intent Engine          │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │ Live Results                     │
│                                     ▼                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ SearchShelf.qml                                                  │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │ Tier 1.5 Active Preview Slate (NodePreview.qml)            │  │  │
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
│  │ Viewport Camera Focus & Search Dismissal                         │  │
│  │ (Smooth camera pan to target; zero physical layout distortion)    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Deconstructed OmniBar Interaction Subsystem (`src/qml/bar/`)
* **`OmniBar.qml`**: Central interaction coordinator for search, natural language intent, and shell execution.
* **`OmniInputCapsule.qml`**: Obsidian pill input field capturing key events (`Ctrl+Space`, `Escape`, `Enter`).
* **`SearchSuggestionRibbon.qml`**: Auto-completion suggestion ribbon displaying prefix tokens (`/`, `@`, `?`).
* **`DialogueDrawer.qml`**: Collapsible slate presenting live-streamed LLM responses driven by `ConversationController`.
* **`ShellOutputDrawer.qml`**: Terminal execution drawer showing live stdout/stderr streams and exit statuses.
* **`ProviderBadge.qml`**: Provider metadata indicator (e.g., `Ollama / Qwen2.5`, `OpenAI`).

### 4.2 Non-Modal Orbital Carousel & Spotlight Search (`src/qml/search/SearchShelf.qml`)
* Search queries dispatched via `SearchController` execute vector KNN and graph searches in `aia_weaver`.
* `SearchShelf.qml` clamps the results to the **Top 7 matches** (`searchResultIds.slice(0, 7)`) and displays them in a centered, floating horizontal carousel.
* Each card renders as a Tier 2 inspection slate displaying file title, snippet, archetype color badge, and extension icon.

### 4.3 Real-Time Tier 1.5 Preview Card
* Positioned directly above the horizontal carousel is an active Tier 1.5 preview card (`NodePreview.qml`).
* As the active index changes, the preview card reactively queries `getNodeData(focusedNodeId)` to stream snippets, file metadata, and connection counts.

### 4.4 Keyboard-Driven Traversal & Focus Flow
* **`Left Arrow` / `Right Arrow` / `Tab`:** Cycles through carousel items with wraparound support and automatic list view positioning (`positionViewAtIndex`).
* **`Enter` / `Return`:** Invokes `canvasBridge.focus_node(nodeId)` and dismisses the search interface.
* **Camera Centering (Zero Physics Displacement):** Selecting a result smoothly centers the viewport camera on the target node without altering cluster equilibrium or physics coordinates.
* **`Escape`:** Dismisses search query, clears search shelf overlay, and restores normal canvas interaction.

---

## 5. Modular HUD Architecture & SRE Telemetry

Canvas HUD components are fully decoupled from root `Canvas.qml`:

1. **`aia_canvas/src/qml/hud/DiagnosticsOverlay.qml`**:
   - Toggled via `F3`.
   - Displays live active node and edge counters, physics step latency ($8.0\text{ms}$ budget / $6.5\text{ms}$ alert threshold in red), SQLite query latency, IPC ingestion metrics, and socket connection status.
   - Includes tendril color key legend for explicit, semantic, temporal, and active bloom links.

2. **`aia_canvas/src/qml/hud/CanvasHud.qml`**:
   - Positioned at the bottom-left of the viewport.
   - Houses the Weaver daemon connection status pill and live Aperture percentage gauge.

3. **`aia_canvas/src/qml/search/SearchShelf.qml`**:
   - Anchored above the OmniBar.
   - Hosts the ranked result carousel, Tier 1.5 active card preview, and keyboard traversal engine.

---

## 6. Desktop OS Subprocess Integration

External desktop file interactions are handled by `aia_canvas/src/utils/desktop.py`:
* **`open_in_file_manager(file_path)`**: Opens the containing folder using `xdg-open`.
* **`open_in_external_editor(file_path)`**: Launches the system default editor for the target file.
* **Path Security:** All operations enforce canonical path verification (`utils.security.canonicalize_safe_path`) and execute tokenized `subprocess.Popen` with `shell=False` and `start_new_session=True`.
