# Aether Interface Architecture (AIA)

> A post-WIMP spatial environment, intent-driven knowledge fabric, and relational desktop for Linux.

Aether reimagines desktop computing by replacing 30-year-old WIMP bureaucracy (overlapping windows, title bars, file dialogs, and manual desktop micromanagement) with an adaptive, spatial drafting table: **The Architect’s Workbench**.

Data and applications are not trapped inside isolated process windows. Instead, content is projected directly onto an obsidian substrate as responsive **Plates** from a living local semantic graph (`weaver_graph.db`).

---

## 🏛 Subsystem Architecture

The system is structured as an asynchronous, decoupled pipeline communicating over UNIX domain sockets:

- **aia_canvas (Presentation Shell):** Hardware-accelerated PyQt6/QML desktop surface. Manages Stage 0 equilibrium, Bento-proportional plate allocations, decoupled overlays, and fluid mode transitions.
- **aia_weaver (Relational Daemon):** High-performance background service managing local ingestion, `weaver_graph.db`, vector embeddings (`sqlite-vec`), and IPC query routing.
- **OmniBar (Intent Nexus):** A self-morphing input capsule anchored to the stage floor. Features prefix-based routing (`OMNI` search, `AI` reasoning, `CLI` shell streaming, `SET` system actions) with stage-projected dwell previews.
- **Peripheral Rail (Ambient Memory):** Edge-docked sediment rail housing temporal feed items, background notification jewels, and manually shelved plates (`⇥`) without workspace clutter.

---

## 📐 Spatial Ergonomics & Sacred Zones

1. **The Horizon (Top ~4.8%):** Non-intrusive ambient telemetry (weather, clock, user host) with proximity bloom.
2. **Active Bento Stage (Center ~79% width):** Bounded workspace for 1 to 4 active plates. No window chrome, no title-bar drag handles, and zero geometry squishing during drawer expansions.
3. **Peripheral Rail (Right ~18.5% width):** Compact semantic chips that hold background jobs and decayed sessions with leftward-blooming inspect flyouts.
4. **OmniBar (Bottom ~5.8% height):** Resting ambient capsule (`"What are we doing?"`) that blooms into search ribbons or floating slideout drawers on demand.
5. **Global Escape Cascade:** Unified 5-tier unwind hierarchy (`UnloadModal` → `OmniBar` → `Diagnostics` → `Preview` → `Plate Focus` → `Stage 0 Exit`).

---

## 🚀 Quickstart

```bash
# Launch virtual environment
source .venv/bin/activate

# Run test suite
python3 -m pytest tests/unit/ tests/qml/

# Launch desktop environment
./aether.sh
```
