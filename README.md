# 🌌 Aether Interface Architecture (AIA)

> **A human-centric, spatial interaction layer and relational desktop fabric for Linux.**

Aether reimagines human-computer interaction by abandoning legacy WIMP paradigms (Windows, Icons, Menus, Pointer) in favor of an organic, intent-driven spatial environment. 

Instead of rigid window frames and static file directories, data is organized as a dynamic semantic graph that moves to the user—condensing into radiant, etched-light focus where attention settles and evaporating into ambient peripheral space when inactive.

---

## 🏛️ Subsystem Architecture

The Aether framework is structured as a decoupled ecosystem of specialized daemons and presentation layers:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           AETHER ECOSYSTEM                              │
│                                                                         │
│   ┌──────────────────┐  Passive Signals / Context                       │
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

| Component | Role | Description |
| :--- | :--- | :--- |
| **`aia_canvas`** | Presentation Layer | Hardware-accelerated spatial canvas rendering borderless text lenses, dynamic bezier tendrils, and particle horizons. |
| **`aia_weaver`** | Relational Daemon | Ingests workspaces, parses explicit links, calculates dense vector embeddings, and builds a real-time graph. |
| **`aia_saccade`** | Ambient Biometrics | Optional sensor module predicting gaze vectors to pre-warm focal targets and guide cursor gravity wells. |
| **`aia_charter.md`** | System Manifesto | The core architectural ethos, design rules, and interaction guidelines. |

---

## ⚡ Core Pillars & Interaction Mechanics

* **Ego-Centric Magnetism:** You never manually traverse a complex 3D star map; the data shifts, orbits, and presents itself based on your focal intent.
* **Drag Transit & Settle Mechanics:**
  * **Dynamic Escalation:** Dragging temporarily escalates micro nodes (Tier 4 Macro Bead -> Tier 3 Capsule; Tier 3 / Tier 2 -> Tier 2 Inspection Slate) for ergonomic legibility during transit.
  * **Settle Delay & Border Glow:** Upon drop release, nodes enter a 1000ms settle grace period rendered with a cyan luminosity border glow (`Theme.accentCyan`) before easing into target cluster equilibrium.
  * **Timer & Binding Muting:** Drag operations strictly mute hover/dwell timers and model coordinate overrides to prevent kinetic jitter and layout fighting.
* **Spotlight HUD & Search Shelf:**
  * **Ranked Carousel:** Non-modal overlay presenting top 7 search matches in an orbital Tier 2 horizontal card carousel.
  * **Tier 1.5 Active Preview:** Inspects the active card in real-time with full markdown/media summary above the search carousel.
  * **Keyboard Navigation:** Full `Left` / `Right` / `Tab` keyboard traversal; `Enter` smoothly focuses the camera on the target node and dismisses the shelf without displacing the physical layout.
* **3-Tier Relational Graph:**
  * **Explicit Edges ($W = 1.0$):** Permanent, solid linkages driven by `[[WikiLinks]]` and code `import` trees.
  * **Semantic Edges ($W \in [0, 1]$):** Real-time KNN cosine proximity over 384-dimensional embeddings (`BAAI/bge-small-en-v1.5`).
  * **Temporal Edges ($W(t) \to 0$):** Associative working memory tracking concurrent file usage with dynamic half-life decay.
* **Decoupled POSIX & IPC Design:** High-performance async Python modules communicating over hardened local UNIX domain sockets (`$XDG_RUNTIME_DIR/aia_weaver/aia_weaver.sock`) using JSON-RPC 2.0.
* **Zero Arbitrary Windows:** No title bars, minimize buttons, or screen-wasting frames. Content is projected directly as etched light onto an obsidian void.

---

## 📂 Monorepo Structure

```text
aether/
├── aia_canvas/             # Visual presentation layer (PySide6 / QML / Shaders)
│   ├── src/                # Controllers, physics engine, HUDs, and QML lenses
│   │   ├── controllers/    # Domain controllers (Canvas, Node, Physics, Search)
│   │   ├── core/           # Intent grammar and query completion engine
│   │   ├── qml/            # Modular QML scene graph and delegates
│   │   │   ├── hud/        # Modular HUD overlays (CanvasHud, DiagnosticsOverlay)
│   │   │   ├── node/       # Leaf delegates (NodePill, NodePreview, NodeAura)
│   │   │   └── search/     # Spotlight Search Shelf and carousel
│   │   └── bridge.py       # Composite Root coordinator & Python/QML adapter
│   ├── ARCHITECTURE.md     # Canvas system design spec
│   └── README.md
├── aia_saccade/            # Eye tracking & intent prediction daemon
├── aia_weaver/             # Semantic graph & vector indexing daemon
│   ├── indexer/            # Embeddings & WikiLink extraction
│   ├── ipc/                # Hardened UNIX socket JSON-RPC server
│   ├── storage/            # SQLite ledger with sqlite-vec
│   ├── watcher/            # Asynchronous inotify sentinel
│   ├── ARCHITECTURE.md     # Weaver technical specification
│   └── README.md
├── docs/                   # Architectural contracts and audit documentation
│   ├── interaction_model.md# Detailed Drag-Settle, Spotlight HUD, and tier specs
│   └── qml_contract.md     # Modular QML frontend invariants
├── aia_charter.md          # Architectural mission charter
└── .gitignore
```

---

## 🚀 Getting Started

### Prerequisites
* Linux (Kernel with `inotify` support)
* Python 3.11+
* SQLite 3 with extension support

### Workspace Setup
```bash
# Clone the repository
git clone git@github.com:zuubux/aether.git
cd aether

# Set up virtual environment for weaver
cd aia_weaver
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🤝 Project Heritage

Designed and architected by **Nic Mansfield** (`zuubux`) as an exploration into post-WIMP human-computer symbiosis.
