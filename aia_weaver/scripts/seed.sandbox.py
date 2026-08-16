#!/usr/bin/env python3
"""
scripts/seed_sandbox.py
Populates the workspace sandbox with 50 stress-test documents.
Wipes the existing sandbox first to ensure a clean test state.
"""

import argparse
import shutil
from pathlib import Path

SAMPLE_FILES = {
    # =========================================================================
    # CLUSTER 1: AETHER CORE ENGINE (10 Files)
    # =========================================================================
    "aether_core.md": "# Aether Core Framework\nThe core runtime orchestrates the decoupled daemon topology for the [[manifesto]] ecosystem.",
    "event_pipeline.md": "# Asynchronous Event Pipeline\nDecouples filesystem events from downstream processing. Fed by [[watcher_sentinel]].",
    "vector_math.md": "# Semantic Vector Proximity\nCalculates 384-dimensional cosine distance for semantic edges. Integrated with [[aether_core]].",
    "watcher_sentinel.md": "# Filesystem Sentinel\nMonitors target directories via inotify. Sends events to [[event_pipeline]].",
    "tendril_physics.md": "# Canvas Tendril Physics\nNodes are positioned using continuous spring-damper physics and Hooke's law.",
    "saccade_gaze.md": "# Saccade Subsystem\nProvides biometric signals by estimating gaze vectors. Feeds the [[aether_core]].",
    "ipc_socket.md": "# IPC Socket Server\nJSON-RPC 2.0 over POSIX domain sockets. Connects [[aether_core]] to frontends.",
    "sqlite_ledger.md": "# SQLite Knowledge Ledger\nUses WAL mode and sqlite-vec for fast KNN searches. Backs the [[event_pipeline]].",
    "async_workers.md": "# Async Process Pool\nIsolates CPU-heavy BAAI embedding generation from the main [[event_pipeline]] thread.",
    "daemon_lifecycle.md": "# Daemon Teardown\nGraceful SIGINT trapping and WAL truncation for [[sqlite_ledger]] maintenance.",

    # =========================================================================
    # CLUSTER 2: ARCHITECTURE & UX (10 Files)
    # =========================================================================
    "manifesto.md": "# Aether Manifesto\nReplaces WIMP paradigms with living relationships. See [[spatial_ux]].",
    "spatial_ux.md": "# Spatial UX\nCrisp focal nodes and ambient peripheral blur. Governed by [[design_tokens]].",
    "design_tokens.md": "# Design Tokens\nObsidian void backgrounds, radiant cyan accents. Applied to [[borderless_lenses]].",
    "architecture_spec.md": "# System Architecture\nDecoupled ecosystem described in the [[manifesto]].",
    "interaction_taxonomy.md": "# Interaction Taxonomy\nPrimary driver is the mouse, assisted by [[saccade_gaze]] ambient biometrics.",
    "borderless_lenses.md": "# Borderless Lenses\nZero arbitrary windows. Content projected directly into the void. See [[spatial_ux]].",
    "obsidian_void.md": "# The Obsidian Void\nThe infinite black canvas that houses [[borderless_lenses]] and [[dynamic_orbitals]].",
    "dynamic_orbitals.md": "# Dynamic Orbitals\nPeripheral context nodes slowly rotate around the user's primary focus.",
    "qml_shaders.md": "# QML Render Shaders\nHardware-accelerated fragment shaders applied to [[borderless_lenses]] for depth of field.",
    "color_theory.md": "# Ethereal Color Theory\nUsing highly saturated accents against pure blacks to minimize eye strain. See [[design_tokens]].",

    # =========================================================================
    # CLUSTER 3: BMW E39 RESTOMOD (10 Files)
    # =========================================================================
    "e39_restomod_plan.md": "# BMW E39 Restomod\nComprehensive restoration plan. Includes the [[v8_engine_swap]] and [[drivetrain_specs]].",
    "v8_engine_swap.md": "# V8 Engine Swap\nMechanical refresh and custom wiring harness for the [[e39_restomod_plan]].",
    "suspension_geometry.md": "# Suspension Geometry\nAdjustable coilovers and polyurethane bushings to fix [[high_speed_shimmy]].",
    "drivetrain_specs.md": "# Drivetrain Specs\nGetrag 420G manual swap and 3.15 LSD for the [[e39_restomod_plan]].",
    "garage_tooling.md": "# Garage Tooling\nEngine hoist, micrometers, and INPA diagnostic laptop for the [[v8_engine_swap]].",
    "high_speed_shimmy.md": "# Front End Shimmy\nThrust arm bushing failure causes vibrations. Fixed in [[suspension_geometry]].",
    "ecu_tuning.md": "# Standalone ECU Tuning\nFuel maps and ignition timing adjustments post [[v8_engine_swap]].",
    "cooling_system.md": "# High-Flow Cooling\nAluminum radiator and electric fan conversion to support the [[v8_engine_swap]].",
    "exhaust_fabrication.md": "# Exhaust Fabrication\nCustom TIG-welded stainless headers and X-pipe routing.",
    "vanos_rebuild.md": "# VANOS Timing Rebuild\nReplacing high-pressure seals and timing chain guides on the V8.",

    # =========================================================================
    # CLUSTER 4: SRE & HOME LAB (10 Files)
    # =========================================================================
    "home_lab_topology.md": "# Home Lab Topology\nOverview of local infrastructure, including [[unraid_bux1]] and [[fedora_onyx]].",
    "unraid_bux1.md": "# BUX1 Unraid Server\nPrimary NAS and hypervisor running [[docker_containers]] and local network storage.",
    "fedora_onyx.md": "# ONYX Fedora Workstation\nPrimary Linux desktop utilizing KDE Plasma and local AI processing.",
    "docker_containers.md": "# Docker Swarm\nContainerized services hosted on [[unraid_bux1]].",
    "network_routing.md": "# VLAN Routing\nIsolating IoT devices from the primary [[home_lab_topology]] subnets.",
    "backup_strategy.md": "# 3-2-1 Backups\nAutomated rsync cron jobs pushing critical data off [[unraid_bux1]].",
    "grafana_dashboards.md": "# Grafana Telemetry\nVisualizing CPU temps and network I/O for [[unraid_bux1]] and [[fedora_onyx]].",
    "ups_power.md": "# UPS Power Delivery\nBattery backup runtimes and automated shutdown scripts for [[unraid_bux1]].",
    "ssh_keys.md": "# SSH Key Rotation\nEd25519 cryptographic keys for passwordless entry into [[fedora_onyx]].",
    "k3s_cluster.md": "# Lightweight Kubernetes\nExperimenting with K3s orchestration as an upgrade to standard [[docker_containers]].",

    # =========================================================================
    # TEST CASE: MIXED EDGES & CONFLICTS (5 Files)
    # =========================================================================
    "hub_node_moc.md": """# Master Index (Hub Node)
This file acts as a massive gravitational center with explicit links everywhere.
- [[aether_core]]
- [[manifesto]]
- [[e39_restomod_plan]]
- [[home_lab_topology]]""",

    "mixed_physics_conflict.md": """# Coilover Spring Rates
This document is entirely about automotive suspension, heavy steel springs, dampening, and roll centers for a BMW. 
However, I am explicitly linking it to [[tendril_physics]] to test Canvas tension.""",

    "mixed_lab_aether.md": """# Running Aether on Fedora
Testing the UNIX domain socket and IPC throughput specifically on [[fedora_onyx]]. 
It requires compiling the [[qml_shaders]] with local GPU drivers.""",

    "mixed_ux_car.md": """# Dashboard UX Design
Redesigning the digital instrument cluster for the BMW. It uses the pure blacks from [[design_tokens]] but connects to the [[ecu_tuning]] telemetry.""",

    "temporal_anchor.md": """# Activity Log Anchor
A completely generic log file. Open this file, then quickly edit another file to test the temporal decay strands!""",

    # =========================================================================
    # TEST CASE: PURE ORPHANS (Semantic Isolation - 5 Files)
    # =========================================================================
    "orphan_watch_collection.md": "# Watch Collection Goals\nFocusing exclusively on mechanical and automatic movements. Keeping dive watches and chronographs strictly separated. Searching for a good GMT complication. Exclude Seiko from current searches.",
    "orphan_wow_rp.md": "# WoW Character Backstory\nDrafting the roleplay history for Cordan, a Nightborne Fury Warrior, alongside my Orc Shaman alt. For the Horde!",
    "orphan_coffee_routine.md": "# Morning Coffee Prep\nStrictly plain black coffee. Manual kettle pour-over setup, prepared exactly one cup at a time.",
    "orphan_lawn_care.md": "# Lawn Overseeding Schedule\nPlanning to wait until late August or early September to overseed the lawn with a drought-tolerant Tall Fescue blend.",
    "orphan_grooming.md": "# Safety Razor Maintenance\nChanging out the double-edge blades in the Henson AL13. Much better than the multi-blade cartridge systems.",
}


def seed_sandbox(target_dir: Path) -> None:
    """Wipes and seeds the target sandbox directory."""
    
    # Clean slate
    if target_dir.exists():
        print(f"🧹 Wiping existing sandbox at: {target_dir.resolve()}")
        shutil.rmtree(target_dir)
        
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"🌱 Seeding fresh sandbox at: {target_dir.resolve()}")

    created_count = 0
    for filename, content in SAMPLE_FILES.items():
        file_path = target_dir / filename
        file_path.write_text(content.strip() + "\n", encoding="utf-8")
        created_count += 1
        
    print(f"✅ Successfully generated {created_count} stress-test files across 4 clusters and mixed edge cases.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Aether sandbox workspace with stress-test documents.")
    parser.add_argument(
        "-d",
        "--dir",
        type=str,
        default=None,
        help="Target directory to seed (defaults to ./sandbox relative to project root)",
    )
    args = parser.parse_args()

    if args.dir:
        target_path = Path(args.dir)
    else:
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent if script_dir.name == "scripts" else script_dir
        target_path = project_root / "sandbox"

    seed_sandbox(target_path)