# Project Charter: Aether Interface Architecture (AIA)

## 1. High-Level Vision & Mission
We are designing a fundamentally new interaction paradigm between humans and technology (starting on the Linux desktop, but architecturally adaptable to tablets, spatial displays, and mobile). 

We reject legacy WIMP metaphors (Windows, Icons, Menus, Pointer) and rigid sci-fi HUD tropes. Our goal is to build an interface tailored to human physiology, sensory intake, and subconscious intent—creating an interaction loop that feels like pure **intuition**.

---

## 2. Core Architectural Pillars
- **Anticipatory Intent:** Understand what the user wants before they execute manual labor.
- **Input-Agnostic Core:** The spatial canvas and semantic engine are decoupled from physical input hardware. Navigation operates across any high-precision direct input modality (physical typing, touch surfaces, micro-gestures, or direct pointer vectors).
- **Ambient Intent Assist (`aia_saccade`):** Optional biometric signals (gaze tracking, head pose) act as passive intent lubricants—pre-warming target hitboxes and reducing travel without triggering destructive actions (solving the "Midas Touch" problem).
- **Underlying Semantic Graph (`aia_weaver`):** Files, notes, media, and tools are dynamically linked by semantic, explicit, and temporal relevance rather than trapped in rigid folder silos.
- **Visual Presentation Layer (`aia_canvas`):** A windowless, borderless spatial surface where content is projected as etched light on a calm obsidian void.

---

## 3. The Visual & Sensory Experience
- **Ambient Data Clouds:** Inactive tasks and background context drift softly in the periphery as gentle, flowing particles—never hidden in a taskbar, never demanding central attention.
- **Focal Condensation:** Where user focus settles (via direct intent, active summoning, or glance), data condenses into crisp, radiant focus.
- **Neuron-Like Tendrils:** Contextually related items gently materialize glowing, organic connections that draw supporting documents, notes, or media into the user's near focal orbit.
- **Aesthetic Tone:** Ethereal, organic, calm, and deeply comforting. No harsh edges, no visual clutter, and zero window management overhead.

---

## 4. Engineering Stance
- **Never repeat legacy design just because "that's how it's always been done."**
- **Keep it grounded:** Maintain compatibility with real POSIX substrates (`.py`, `.txt`, `.md`, media) and underlying system performance.
- **Kinetic Calm & Computational Silence:** The interface rests when the mind rests. Layout forces, animations, and IPC streams must cleanly settle and sleep when idle—zero unbounded loops, zero CPU waste, and zero unprovoked visual movement.
