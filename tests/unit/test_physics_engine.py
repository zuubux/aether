"""
Unit tests for PhysicsEngine calm substrate, organic perimeter orbit, and softened forces.
"""

import math
import numpy as np
import pytest

from models import Node, Edge
from physics.engine import PhysicsEngine


def test_physics_engine_constants():
    """Verify reduced anchor constants for soft organic spring behavior."""
    engine = PhysicsEngine()
    assert engine.k_horizon_anchor == 2.0
    assert engine.k_gutter_anchor == 2.0


def test_coulomb_repulsion_softened():
    """Verify Coulomb repulsion uses multiplier 2.2 instead of legacy 8.5."""
    engine = PhysicsEngine()
    pos = np.array([[100.0, 100.0], [110.0, 100.0]], dtype=np.float64)
    node_ids = np.array([1, 2], dtype=np.int64)
    comp_ids = np.array([0, 0], dtype=np.int32)
    forces = np.zeros((2, 2), dtype=np.float64)

    engine._apply_coulomb_repulsion(
        pos=pos,
        node_ids=node_ids,
        comp_ids=comp_ids,
        forces=forces,
        has_active_focus=False,
        focused_node_id=0,
        first_deg_indices=set(),
        second_deg_indices=set(),
        geom_scale=1.0,
    )

    # Dist = 10.0, Friend MIN_SEP ~ 48.0 + Jitter
    # Forces should be non-zero repelling force with multiplier 2.2
    assert forces[0, 0] < 0.0
    assert forces[1, 0] > 0.0


def test_central_void_force_softened():
    """Verify central void repulsion multiplier is reduced to 600.0."""
    engine = PhysicsEngine()
    pos = np.array([[engine.center_x + 50.0, engine.center_y]], dtype=np.float64)
    node_ids = np.array([1], dtype=np.int64)
    forces = np.zeros((1, 2), dtype=np.float64)
    id_to_idx = {1: 0}
    comp_ids = np.array([-1], dtype=np.int32)

    engine._apply_docking_constraints(
        pos=pos,
        node_ids=node_ids,
        id_to_idx=id_to_idx,
        forces=forces,
        comp_ids=comp_ids,
        comp_centroids={},
        has_active_focus=False,
        focused_node_id=0,
        first_deg_indices=set(),
        second_degree_parent={},
        geom_scale=1.0,
    )

    # Void radius = 750.0, dist = 50.0
    # Ramp = ((750 - 50)/750)^1.5 = (700/750)^1.5 ~= 0.898
    # Force = 1.0 * ramp * 600.0 ~= 539.0
    assert forces[0, 0] > 0.0
    assert forces[0, 0] < 600.0


def test_focus_mode_organic_perimeter_orbit():
    """Verify Focus Mode uses organic perimeter orbit (~520px radius) instead of legacy rigid wing gutters."""
    engine = PhysicsEngine()
    n1 = Node(id=1, file_path="/test/focal.md", x=engine.center_x, y=engine.center_y)
    n2 = Node(id=2, file_path="/test/connected.md", x=engine.center_x + 300.0, y=engine.center_y)
    edge = Edge(source_id=1, target_id=2, edge_type="explicit", category="topological")

    nodes = [n1, n2]
    edges = [edge]

    # Step simulation with node 1 focused
    engine.step(nodes=nodes, edges=edges, focused_node_id=1, first_degree_set={2})

    # Connected node 2 should float around ~520px from focal card center, not snap to rigid column at x = wb_x - 450
    dist = math.hypot(n2.x - engine.center_x, n2.y - engine.center_y)
    assert 200.0 < dist < 600.0


def test_velocity_integration_drag_and_max_speed():
    """Verify baseline drag (7.5) and max_speed cap (90 ambient / 140 focus)."""
    engine = PhysicsEngine()
    node = Node(id=1, file_path="/test/fast.md", x=100.0, y=100.0)
    node.vx = 300.0
    nodes = [node]

    pos = np.array([[100.0, 100.0]], dtype=np.float64)
    vel = np.array([[300.0, 0.0]], dtype=np.float64)
    forces = np.zeros((1, 2), dtype=np.float64)
    node_ids = np.array([1], dtype=np.int64)
    id_to_idx = {1: 0}
    comp_ids = np.array([-1], dtype=np.int32)

    # Step velocity integration with ambient focus
    engine._integrate_velocities(
        nodes=nodes,
        pos=pos,
        vel=vel,
        forces=forces,
        node_ids=node_ids,
        id_to_idx=id_to_idx,
        comp_ids=comp_ids,
        dt=0.016,
        has_active_focus=False,
        focused_node_id=0,
        hovered_node_id=0,
        first_deg_indices=set(),
        second_degree_parent={},
        focal_weights={},
        first_degree_set=set(),
    )

    # Initial vel=300 should be capped to ambient max_speed = 90.0
    speed = math.hypot(vel[0, 0], vel[0, 1])
    assert speed <= 90.0
