# Aether System Architecture & Technical Specifications

**Framework:** Aether Interface Architecture  
**Document Version:** 2.0.0  
**Authors:** Nic Mansfield (`zuubux`)

---

## 1. System Context & Overview

Aether is a decoupled spatial desktop and relational knowledge fabric for Linux that replaces traditional window management with an organic, intent-driven canvas:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           AETHER ECOSYSTEM                              │
│                                                                         │
│   ┌──────────────────┐  Passive Intent / Eye Gaze                       │
│   │   aia_saccade    │·························┐                        │
│   │(Biometric Assist)│                         ▼                        │
│   └──────────────────┘               ┌──────────────────┐               │
│                                      │    aia_canvas    │               │
│   ┌──────────────────┐  Direct       │(Spatial UI Shell)│               │
│   │  Explicit Input  │──────────────►│                  │               │
│   │ (Primary Driver) │  Execution    └─────────▲────────┘               │
│   └──────────────────┘                         │                        │
│                                     JSON-RPC   │ Graph Updates          │
│                                     UNIX IPC   │ & Vector KNN           │
│                                                ▼                        │
│                                      ┌──────────────────┐               │
│                                      │    aia_weaver    │               │
│                                      │(Knowledge Fabric)│               │
│                                      └──────────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Canvas UI Scene Graph & Modularization

The presentation layer (`aia_canvas`) utilizes PyQt6 / Qt Quick 6 with a strictly modularized component hierarchy:

```text
aia_canvas/src/qml/
├── Canvas.qml                  # Root window & viewport camera coordinator
├── HorizonGrid.qml             # Background iso-lines & horizon grid
├── ClusterHalo.qml             # GPU SDF shield membrane component
├── Tendril.qml                 # Synaptic cubic Bezier connection lines
├── OmniBar.qml                 # Spotlight search input & query dispatcher
├── SurfaceShell.qml            # Single-stroke perimeter & background shell
├── NodeContent.qml             # Tier-adaptive content loader
├── Theme.qml                   # Shared palette tokens, easing curves, metrics
├── hud/
│   ├── DiagnosticsOverlay.qml  # F3 SRE telemetry HUD overlay
│   └── CanvasHud.qml           # Bottom-left IPC connection & Aperture pill
├── search/
│   └── SearchShelf.qml         # Spotlight search carousel & Tier 1.5 preview
├── node/
│   ├── NodeAura.qml            # GPU shaders for selection and glow
│   ├── NodePill.qml            # Compact capsule and badge delegate
│   └── NodePreview.qml         # Tier 1.5 rich preview card
└── slates/
    ├── ImageSlate.qml          # Image rendering slate
    ├── PdfSlate.qml            # PDF rendering slate
    └── TableSlate.qml          # CSV/tabular rendering slate
```

### Component Boundaries
* **Root Viewport (`Canvas.qml`):** Manages keyboard shortcuts (`Ctrl+Space`, `F3`, `Escape`), camera centering, and root event flow.
* **Overlays (`hud/`):** Decoupled `DiagnosticsOverlay.qml` (F3 telemetry) and `CanvasHud.qml` (connection & aperture status) render independently of the graph layout.
* **Search HUD (`search/SearchShelf.qml`):** Hosts the ranked result carousel (top 7) and live Tier 1.5 active card preview.
* **Card Container (`Node.qml`):** Acts as an interactive coordinator managing drag transit, settle delays, hover/dwell timers, and dynamic LOD tier escalation.

---

## 3. Physics & Interaction Invariants

* **120Hz Stokes Fluid Dynamics:** Viscous integration using Stokes quadratic fluid drag, repulsive potential barriers, and breadth-first cluster centering.
* **Temporal Spring Decoupling:** Temporal connections (`edge_type == 'temporal'`) always have zero spring constant ($k = 0.0$) in the physics engine.
* **Kinematic Focus Isolation:** Focused node wing arrangements decouple peripheral background clusters to preserve kinetic calm.
* **Drag-Settle Dynamics:**
  - Dragging escalates nodes (Tier 4 -> Tier 3; Tier 3/2 -> Tier 2) and raises `z: 1000`.
  - Releasing triggers a 1000ms settle delay with `Theme.accentCyan` luminosity boost before relaxing into equilibrium.
  - Hover/dwell timers and model coordinate bindings are strictly muted during drag.
