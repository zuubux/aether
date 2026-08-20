# ==============================================================================
# AETHER: IMPLEMENTATION ROADMAP
# ==============================================================================

This document serves as the master execution plan for the Aether Interface Architecture[cite: 2]. 
Instructions for implementation agents (e.g., Cline): Do not proceed to a new phase until 
the current active phase is explicitly requested by the user, fully tested, and verified[cite: 2].

---

## 🟢 PHASE 1: Volumetric SDF Nebula Clusters (COMPLETED / REFINEMENT)
**Target:** `aia_canvas/src/qml/ClusterHalo.qml` & `aia_canvas/src/qml/halo.frag`

**Current State & Observations:**
* Basic GLSL SDF capsule shader compiled with `qsb` is functional with velocity-linked Brownian motion[cite: 2].
* Nebulas currently render as hard-edged boxes due to tight Item bounding boxes and missing edge alpha falloff.

**Refinement Tasks:**
* **Item Bounds Expansion:** Inflate `ClusterHalo.qml` geometry with a $+150\text{px}$ margin on all sides so the fragment shader decays cleanly to `0.0` alpha before hitting the Item edge.
* **Organic Falloff & Smooth-Min Absorption:**
  * Update `halo.frag` to use a smooth radial polynomial Hermite curve for border transparency.
  * Implement smooth-minimum (`smin`) blending in the distance field calculation so approaching nodes ($\le 120\text{px}$) cause the nebula boundary to organically stretch and envelope them.

---

## 🟡 PHASE 2: Focal Dominance, Progressive Z-Depth Yield & Elastic Cushions (ACTIVE)
**Target:** `aia_canvas/src/physics/engine.py`, `aia_canvas/src/bridge.py`, & `aia_canvas/src/qml/Node.qml`

**The Problem:**
1. Expanding the focal lens laterally compresses available wing space, pushing 1st and 2nd degree nodes off-screen instead of yielding naturally into 3D depth[cite: 2].
2. Zoom/aperture transforms calculate radially from monitor center rather than available void space.

**Design Intent & Architectural Constraints:**
* **Available Wing Calculation:** Dynamically compute available lateral space:
  $$\text{wing\_width} = \frac{\text{viewport\_width} - \text{focal\_lens\_width}}{2}$$
* **Progressive Z-Recession Cascade:**
  * **Comfortable ($\ge 260\text{px}$):** Tier 1 at $Z = 0$ (scale $1.0$, full labels); Tier 2 at $Z \approx -100\text{px}$ (scale $0.85$).
  * **Compressed ($120\text{px} - 260\text{px}$):** Tier 1 stays pinned at $Z = 0$; Tier 2 yields into depth ($Z \to -350\text{px}$, scale $0.6$, collapsed badge tokens).
  * **Extreme Squeeze ($< 120\text{px}$):** Tier 1 yields into depth ($Z \to -250\text{px}$, scale $0.7$, labels fade out leaving only glowing anchor ports along the lens flank). Tier 2 drops to $Z \to -500\text{px}$ (opacity $\to 0.2$).
* **Elastic Viewport Wall:**
  * Implement an exponential restoring force along a $32\text{px}$ inner boundary cushion on display borders in `engine.py` to prevent lateral clipping while retaining fluid kinetic bounce[cite: 2].
* **Viewport-Aware Zoom Origin:**
  * When a focal lens or wing is pinned, anchor the aperture zoom center to the midpoint of the available void (`(viewport_width - wing_width) / 2`).

**Verification:**
Resize the active focal workbench from compact to maximum width. Verify that Tier 2 nodes gracefully recede into the $Z$-depth with scaled down badges, Tier 1 nodes yield only under extreme expansion, and zero elements clip beyond physical monitor borders.

---

## ⚪ PHASE 3: Synaptic Tendril Respiration & Edge Weights (PENDING)
**Target:** `aia_canvas/src/qml/Tendril.qml`, `TendrilLayer.qml`, & `aia_canvas/src/bridge.py`

**The Problem:**
Tertiary and ambient connections appear statically faint rather than dynamically breathing, creating visual clutter across deep zoom levels[cite: 2].

**Design Intent & Constraints:**
* **Biological Respiration Loop:** Bind ambient and tertiary edge opacities to a low-frequency sine wave modulation ($\sin(\text{time} \times 0.8 + \text{edge\_id})$) so they gently breathe into view and fade out[cite: 2].
* **Weight-Tiered Visualization:**
  * **Explicit Edges ($W = 1.0$):** Radiant, crisp bezier arcs with active tension anchors.
  * **Semantic Edges ($W \in [0, 1]$):** Medium glow with distance-decayed alpha falloff.
  * **Temporal Edges ($W(t)$):** Transient synaptic pulses that scale down with memory half-life decay.
* **Hover Stabilization:** Instantly lock any hovered or focused tendril to full solid opacity[cite: 2].