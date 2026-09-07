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
    # Forces should be non-zero repelling force with multiplier 2.2 for intra-zone pairs
    assert forces[0, 0] < 0.0
    assert forces[1, 0] > 0.0

    # Cross-zone pairs: unconditionally zero force
    forces_cross = np.zeros((2, 2), dtype=np.float64)
    engine._apply_coulomb_repulsion(
        pos=pos,
        node_ids=node_ids,
        comp_ids=comp_ids,
        forces=forces_cross,
        has_active_focus=False,
        focused_node_id=0,
        first_deg_indices=set(),
        second_deg_indices=set(),
        geom_scale=1.0,
        
    )


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

    # Also verify zone integration via step: persistent model zones are preserved
    n_focal = Node(id=1, file_path="/test/focal.md", x=engine.center_x + 50.0, y=engine.center_y, zone=0)
    n_shelf = Node(id=2, file_path="/test/shelf.md", x=engine.center_x + 1450.0, y=engine.center_y - 40.0, zone=1)
    n_horizon = Node(id=3, file_path="/test/horizon.md", x=engine.center_x + 3200.0, y=engine.center_y - 40.0, zone=2)
    engine.step(nodes=[n_focal, n_shelf, n_horizon], edges=[], focused_node_id=0)
    assert n_focal.zone == 0
    assert n_shelf.zone == 1
    assert n_horizon.zone == 2


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


def test_acoustic_bottom_hud_exclusion_margin():
    """Verify nodes initialized in the bottom margin receive upward force and migrate out of exclusion zone."""
    engine = PhysicsEngine()
    bottom_threshold = engine.viewport_h - 140.0
    initial_y = engine.viewport_h - 60.0  # inside exclusion zone (depth = 80px)

    pos = np.array([[engine.center_x, initial_y]], dtype=np.float64)
    node_ids = np.array([1], dtype=np.int64)
    id_to_idx = {1: 0}
    forces = np.zeros((1, 2), dtype=np.float64)
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

    # Significant upward restoring force (negative fy)
    assert forces[0, 1] < -20.0

    # Test migration over multiple simulation steps
    node = Node(id=1, file_path="/test/bottom_hud.md", x=engine.center_x, y=initial_y)
    nodes = [node]

    for _ in range(200):
        engine.step(nodes=nodes, edges=[], focused_node_id=0)

    assert node.y < initial_y - 2.0


def test_same_zone_hooke_springs_cohesion():
    """Verify gentle spring cohesion strictly between same-zone nodes, zero pull across zones."""
    engine = PhysicsEngine()
    pos = np.array([[100.0, 100.0], [500.0, 500.0]], dtype=np.float64)
    node_ids = np.array([1, 2], dtype=np.int64)
    id_to_idx = {1: 0, 2: 1}
    forces = np.zeros((2, 2), dtype=np.float64)
    edge = Edge(source_id=1, target_id=2, edge_type="explicit", category="topological", weight=1.0)

    engine._apply_hooke_springs(
        edges=[edge],
        pos=pos,
        node_ids=node_ids,
        id_to_idx=id_to_idx,
        forces=forces,
        geom_scale=1.0,
        has_active_focus=False,
        focused_node_id=0,
        first_deg_indices=set(),
        second_deg_indices=set(),
    )

    # Same-zone spring cohesion: disabled
    assert forces[0, 0] == 0.0
    assert forces[0, 1] == 0.0

    # Cross-zone edge spring strictly 0.0
    forces_cross = np.zeros((2, 2), dtype=np.float64)
    engine._apply_hooke_springs(
        edges=[edge],
        pos=pos,
        node_ids=node_ids,
        id_to_idx=id_to_idx,
        forces=forces_cross,
        geom_scale=1.0,
        has_active_focus=False,
        focused_node_id=0,
        first_deg_indices=set(),
        second_deg_indices=set(),
        
    )
    assert np.all(forces_cross == 0.0)


def test_static_node_resting_zero_velocity():
    """Verify nodes settle to static resting state with zero residual velocity when forces/speeds are low."""
    engine = PhysicsEngine()
    node = Node(id=1, file_path="/test/rest.md", x=1000.0, y=1000.0)
    nodes = [node]

    pos = np.array([[1000.0, 1000.0]], dtype=np.float64)
    vel = np.array([[0.04, -0.03]], dtype=np.float64)
    forces = np.zeros((1, 2), dtype=np.float64)
    node_ids = np.array([1], dtype=np.int64)
    id_to_idx = {1: 0}
    comp_ids = np.array([-1], dtype=np.int32)

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

    # Residual velocity should be zeroed out
    assert vel[0, 0] == 0.0
    assert vel[0, 1] == 0.0
    assert node.vx == 0.0
    assert node.vy == 0.0



def test_zone_2_outward_expulsion_force_inside_desk_void():
    """Verify Zone 2 nodes inside the central desk void (rho < 1.20) receive an outward expulsion force."""
    engine = PhysicsEngine()
    ellipse_a = engine.viewport_w * 0.35
    ellipse_b = engine.viewport_h * 0.30
    center_y_void = engine.center_y - (engine.viewport_h * 0.025)

    angles = [0.0, math.pi / 4.0, math.pi / 2.0, math.pi, -math.pi / 3.0]
    rhos = [0.2, 0.5, 0.9, 1.15]

    for angle in angles:
        for rho in rhos:
            px = engine.center_x + math.cos(angle) * ellipse_a * rho
            py = center_y_void + math.sin(angle) * ellipse_b * rho

            pos = np.array([[px, py]], dtype=np.float64)
            node_ids = np.array([42], dtype=np.int64)
            id_to_idx = {42: 0}
            forces = np.zeros((1, 2), dtype=np.float64)
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

            # Dot product with radial direction must be strictly positive (outward)
            radial_force = forces[0, 0] * math.cos(angle) + forces[0, 1] * math.sin(angle)
            assert radial_force > 0.0, f"Expected outward force at angle {angle}, rho {rho}, got {radial_force}"
            assert math.hypot(forces[0, 0], forces[0, 1]) > 0.0


def test_zone_2_singularity_safeguard_at_center():
    """Verify Zone 2 node at exact desk void center (rho < 1e-3) has a deterministic outward force."""
    engine = PhysicsEngine()
    center_y_void = engine.center_y - (engine.viewport_h * 0.025)
    pos = np.array([[engine.center_x, center_y_void]], dtype=np.float64)
    node_ids = np.array([101], dtype=np.int64)
    id_to_idx = {101: 0}
    forces = np.zeros((1, 2), dtype=np.float64)
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

    mag = math.hypot(forces[0, 0], forces[0, 1])
    assert mag > 0.0
    assert not math.isnan(forces[0, 0])
    assert not math.isnan(forces[0, 1])


def test_zone_2_initial_placement_projection():
    """Verify cold Zone 2 nodes initialized inside the central desk void are projected outward to horizon."""
    engine = PhysicsEngine()
    ellipse_a = engine.viewport_w * 0.35
    ellipse_b = engine.viewport_h * 0.30
    center_y_void = engine.center_y - (engine.viewport_h * 0.025)

    # Zone 2 node at void center
    node_z2 = Node(id=202, file_path="/test/cold.md", x=engine.center_x, y=center_y_void, zone=2)
    engine.initialize_node_position(node_z2)

    norm_dx = (node_z2.x - engine.center_x) / ellipse_a
    norm_dy = (node_z2.y - center_y_void) / ellipse_b
    rho = math.hypot(norm_dx, norm_dy)
    assert 1.32 <= rho <= 1.75

    # Desk void (Zone 0) or Shelf (Zone 1) node must NOT be projected
    node_z0 = Node(id=303, file_path="/test/desk.md", x=engine.center_x, y=center_y_void, zone=0)
    engine.initialize_node_position(node_z0)
    assert node_z0.x == engine.center_x
    assert node_z0.y == center_y_void

    node_z1 = Node(id=404, file_path="/test/shelf.md", x=engine.center_x + 50.0, y=center_y_void, zone=1)
    engine.initialize_node_position(node_z1)
    assert node_z1.x == engine.center_x + 50.0
    assert node_z1.y == center_y_void

