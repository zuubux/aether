# Aether Interface Architecture: Anti-WIMP In-Place Spatial Roadmap

## 1. Architectural Philosophy & Anti-WIMP Core
* **Anti-WIMP Invariant:** No monolithic modal dialogs that lock screen context. Information expands directly in-place on the canvas without artificial viewport takeovers.
* **Single Surface Shell Invariant:** Exactly ONE visual element (`Surface`) per entity owns:
  * Solid background fill (`color: "#0B0F19"`, `opacity: 1.0`).
  * Perimeter border stroke (`border.width`, `border.color`).
  * Corner radius and bounding dimensions (`width`, `height`).
* **Universal Docking Contract:** Every entity implements `leftDock` and `rightDock` derived directly from outer shell boundaries in local/canvas space.
* **Spatial Filaments Over Flank Slots:** Tendrils trace organic Bezier curves across the canvas between nodes in their natural clusters, completely eliminating rigid left/right wing slots and physics fighting.

---

## 2. Interaction Tier Contract (In-Place Escalation)
1. **Tier 4 / 3 (Bead / Capsule at Rest):** Compact representations for ambient scanning.
2. **Tier 2 (Inspection Slate - 220x64):** Triggered at 250ms+ dwell or glance. Exposes title, badges, and socket anchors.
3. **Tier 1.5 (Rich In-Place Preview - 320x220 to 600x400):** Triggered by selection/sustained focus directly in canvas space. Renders markdown/media previews in-place. Multiple nodes can remain expanded simultaneously.

---

## 3. Phased Implementation Roadmap

## Phase 1: Single-Surface Shell & Universal Docking
- **Status:** COMPLETED
- Consolidated entity rendering into a single root `Rectangle` with solid background fills and border strokes.
- Removed margin/padding offsets from `.leftDock` and `.rightDock` anchors.

## Phase 2: Staged Interaction Engine (Timer-Driven Dwell)
- **Status:** COMPLETED
- Implemented non-disruptive 2-stage dwell escalation (250ms Tier 2 Slate, 1200ms Tier 1.5 Rich Preview) bound to `220ms` OutQuint easing curves.

## Phase 3: Decoupled Quota Tendril Engine
- **Status:** COMPLETED
- Backend (`bridge.py`) restricted to pure 8-slot quota distribution (Explicit -> Semantic -> Temporal with rollovers).
- QML handles declarative Bezier line rendering with defensive `(0,0)` visibility suppression.

---

## Phase 4: Deprecate Modal Wings & Implement In-Place Spatial Focus
- **Status:** IN PROGRESS
- **Scope:** `aia_canvas/src/physics/engine.py`, `aia_canvas/src/bridge.py`, `aia_canvas/src/qml/Canvas.qml`, `aia_canvas/src/qml/Node.qml`
- **Objectives:**
  1. **Purge Modal Wings:** Remove `compute_wing_slots`, left/right wing arrays, and artificial companion lock targets from `engine.py`. Nodes stay in their natural clusters.
  2. **In-Place Escalation:** Deprecate the centralized viewport-modal overlay. Clicking/focusing an entity expands its own `Node.qml` Surface Shell directly on the canvas to Tier 1.5.
  3. **Organic Tendril Filaments:** Re-route `Tendril.qml` to connect the active in-place card directly to companion nodes across the canvas using their dynamic `leftDock` / `rightDock` anchors.
  4. **Multi-Node Expansion:** Enable multiple nodes to remain expanded in-place simultaneously without forcing canvas-wide dimming.

## Phase 5: Surface Transparency, Ambient Falloff & Compositing
- **Status:** PENDING
- **Objectives:**
  - Enforce 100% solid background opacity on all Surface Shells to eliminate text/node bleed-through.
  - Tune the canvas ambient void falloff and background contrast.

## Phase 6: Filaments Polish & Spatial Teleportation
- **Status:** PENDING
- **Objectives:**
  - Polish cubic Bezier tension for long-distance canvas connections.
  - Implement smooth viewport camera shifts when clicking tendril connection sockets.
