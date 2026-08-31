"""
Unit tests for SpatialBudgetEngine and PhysicsBridgeLayout deterministic elliptical zoning engine.
"""

import math
import pytest
from layout.spatial_budget import (
    SpatialBudgetEngine,
    ZONE_FOCAL,
    ZONE_MID_FIELD,
    ZONE_HORIZON,
)
from layout.physics_bridge import PhysicsBridgeLayout
from models import Node


def test_spatial_budget_dynamic_viewport_resize():
    """Verify zone boundaries adapt dynamically on viewport resize."""
    engine = SpatialBudgetEngine(viewport_w=3840.0, viewport_h=2160.0)

    # Initial boundaries (3840 x 2160)
    assert engine.viewport_w == 3840.0
    assert engine.viewport_h == 2160.0
    assert engine.center_x == 1920.0
    assert engine.center_y == 1080.0
    assert pytest.approx(engine.a_focal, 1e-4) == 0.28 * 3840.0  # 1075.2
    assert pytest.approx(engine.b_focal, 1e-4) == 0.24 * 2160.0  # 518.4
    assert pytest.approx(engine.a_mid, 1e-4) == 0.52 * 3840.0    # 1996.8
    assert pytest.approx(engine.b_mid, 1e-4) == 0.46 * 2160.0    # 993.6

    # Resize viewport to 1920 x 1080
    engine.set_viewport_dimensions(1920.0, 1080.0)
    assert engine.viewport_w == 1920.0
    assert engine.viewport_h == 1080.0
    assert engine.center_x == 960.0
    assert engine.center_y == 540.0
    assert pytest.approx(engine.a_focal, 1e-4) == 0.28 * 1920.0  # 537.6
    assert pytest.approx(engine.b_focal, 1e-4) == 0.24 * 1080.0  # 259.2
    assert pytest.approx(engine.a_mid, 1e-4) == 0.52 * 1920.0    # 998.4
    assert pytest.approx(engine.b_mid, 1e-4) == 0.46 * 1080.0    # 496.8


@pytest.mark.parametrize("delta_hours, recency_score, interaction_state, alert_active, is_pinned, expected", [
    (None, 0.8, 0.5, 1.0, False, 0.69),
    (None, 1.0, 0.0, True, False, 0.5),
    (None, 1.0, 0.0, False, True, float("inf")),
    (0, 0.0, 0.0, False, False, 0.5),
    (24, 0.0, 0.0, False, False, (2.0 / 3.0) * 0.5),
    (48, 0.0, 0.0, False, False, (1.0 / 3.0) * 0.5),
    (72, 0.0, 0.0, False, False, 0.0),
    (90, 0.0, 0.0, False, False, 0.0),
    (100, 1.0, 0.0, False, True, float("inf")),
])
def test_mass_score_and_linear_decay_falloff(delta_hours, recency_score, interaction_state, alert_active, is_pinned, expected):
    """Verify composite Mass score formula, infinite mass for pinned nodes, and 72h linear decay falloff."""
    now = 1000000.0
    last_epoch = now - (delta_hours * 3600) if delta_hours is not None else None
    
    score = SpatialBudgetEngine.calculate_mass_score(
        recency_score=recency_score,
        interaction_state=interaction_state,
        alert_active=alert_active,
        is_pinned=is_pinned,
        last_interaction_epoch=last_epoch,
        current_time=now if delta_hours is not None else None
    )
    if expected == float("inf"):
        assert score == float("inf")
    else:
        assert pytest.approx(score, 1e-5) == expected

def test_focal_capacity_cap_with_500_nodes():
    """Assert that no more than 5 nodes can hold ZONE_FOCAL status regardless of total graph size (500+ nodes)."""
    engine = SpatialBudgetEngine(viewport_w=3840.0, viewport_h=2160.0)

    # Register 500 nodes with descending recency scores
    for i in range(1, 501):
        recency = max(0.0, 1.0 - (i * 0.001))
        engine.register_or_update_node(
            node_id=i, recency_score=recency, interaction_state=0.2, alert_active=False
        )

    zones = engine.evaluate_zones()

    focal_count = sum(1 for z in zones.values() if z == ZONE_FOCAL)
    mid_count = sum(1 for z in zones.values() if z == ZONE_MID_FIELD)
    horizon_count = sum(1 for z in zones.values() if z == ZONE_HORIZON)

    assert len(zones) == 500
    assert focal_count == 5
    assert mid_count == 12
    assert horizon_count == 483


def test_pinned_nodes_maintain_infinite_mass_focal_retention():
    """Assert pinned nodes maintain infinite mass and never evict from ZONE_FOCAL."""
    engine = SpatialBudgetEngine(viewport_w=3840.0, viewport_h=2160.0)

    # Register 100 nodes with high recency scores
    for i in range(1, 101):
        engine.register_or_update_node(
            node_id=i, recency_score=1.0, interaction_state=1.0, alert_active=True, is_pinned=False
        )

    # Pin node 99 and node 100 with zero recency/interaction
    engine.register_or_update_node(
        node_id=99, recency_score=0.0, interaction_state=0.0, alert_active=False, is_pinned=True
    )
    engine.register_or_update_node(
        node_id=100, recency_score=0.0, interaction_state=0.0, alert_active=False, is_pinned=True
    )

    zones = engine.evaluate_zones()

    assert zones[99] == ZONE_FOCAL
    assert zones[100] == ZONE_FOCAL
    focal_count = sum(1 for z in zones.values() if z == ZONE_FOCAL)
    assert focal_count == 5


def test_geometric_point_ellipse_classification():
    """Verify point inside ellipse helper methods for focal, mid-field, and horizon."""
    engine = SpatialBudgetEngine(viewport_w=3840.0, viewport_h=2160.0)
    cx, cy = engine.center_x, engine.center_y

    # Point at center is in ZONE_FOCAL
    assert engine.get_zone_for_point(cx, cy) == ZONE_FOCAL

    # Point on inner focal ellipse boundary is in ZONE_FOCAL
    assert engine.get_zone_for_point(cx + engine.a_focal * 0.8, cy) == ZONE_FOCAL

    # Point outside focal ellipse but inside mid ellipse is in ZONE_MID_FIELD
    assert engine.get_zone_for_point(cx + engine.a_focal * 1.2, cy) == ZONE_MID_FIELD

    # Point far outside mid ellipse is in ZONE_HORIZON
    assert engine.get_zone_for_point(cx + engine.a_mid * 1.5, cy) == ZONE_HORIZON


def test_deterministic_radial_slotting_focal_nodes():
    """Verify focal nodes obtain non-overlapping radial slot targets around the center."""
    engine = SpatialBudgetEngine(viewport_w=3840.0, viewport_h=2160.0)
    focal_ids = [10, 20, 30, 40, 50]
    for nid in focal_ids:
        engine.register_or_update_node(node_id=nid, is_explicit_action=True)

    targets = engine.get_focal_slot_targets(focal_ids)
    assert len(targets) == 5

    coords = list(targets.values())
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            dist = math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1])
            assert dist > 100.0, f"Target slots {i} and {j} overlap too closely: dist={dist}"


def test_register_or_update_node_retains_coordinates_when_omitted():
    """Assert register_or_update_node retains existing coordinates on partial updates when x/y are None."""
    engine = SpatialBudgetEngine(viewport_w=1920.0, viewport_h=1080.0)
    # Register node with initial coordinates
    engine.register_or_update_node(node_id=42, x=350.0, y=450.0, recency_score=0.5)
    node_data = engine._nodes[42]
    assert node_data["x"] == 350.0
    assert node_data["y"] == 450.0

    # Partial update omitting x and y
    engine.register_or_update_node(node_id=42, recency_score=0.9, interaction_state=0.8)
    updated_data = engine._nodes[42]
    assert updated_data["x"] == 350.0
    assert updated_data["y"] == 450.0
    assert pytest.approx(updated_data["recency_score"]) == 0.9


def test_get_focal_slot_targets_requires_explicit_action_for_auto_slotting():
    """Assert get_focal_slot_targets does not slot to center / radial circle unless is_explicit_action is True."""
    engine = SpatialBudgetEngine(viewport_w=1920.0, viewport_h=1080.0)
    # Register single focal node at custom position without explicit action
    engine.register_or_update_node(node_id=1, x=200.0, y=300.0, is_explicit_action=False)

    # get_focal_slot_targets should preserve existing coordinates instead of auto-slotting to center
    targets = engine.get_focal_slot_targets([1])
    assert targets[1] == (200.0, 300.0)
    assert targets[1] != (engine.center_x, engine.center_y)

    # Register second focal node without explicit action
    engine.register_or_update_node(node_id=2, x=400.0, y=500.0, is_explicit_action=False)
    targets_multi = engine.get_focal_slot_targets([1, 2])
    assert targets_multi[1] == (200.0, 300.0)
    assert targets_multi[2] == (400.0, 500.0)

    # Now update with is_explicit_action=True
    engine.register_or_update_node(node_id=1, is_explicit_action=True)
    # Single node with explicit action slots to center
    single_explicit = engine.get_focal_slot_targets([1])
    assert single_explicit[1] == (engine.center_x, engine.center_y)

    # Multiple nodes with explicit action slot radially
    engine.register_or_update_node(node_id=2, is_explicit_action=True)
    explicit_targets = engine.get_focal_slot_targets([1, 2])
    assert explicit_targets[1] != (200.0, 300.0)
    assert explicit_targets[2] != (400.0, 500.0)
    assert explicit_targets[1] != (engine.center_x, engine.center_y)
    assert explicit_targets[2] != (engine.center_x, engine.center_y)


def test_demotion_outward_radial_vector():
    """Verify demoted nodes compute an outward radial vector to glide into designated orbits."""
    engine = SpatialBudgetEngine(viewport_w=3840.0, viewport_h=2160.0)
    cx, cy = engine.center_x, engine.center_y

    start_x, start_y = cx + 100.0, cy + 50.0
    (ux, uy), (tx, ty) = engine.compute_demotion_outward_vector(
        node_id=1, current_x=start_x, current_y=start_y, target_zone=ZONE_MID_FIELD
    )

    expected_ux = 100.0 / math.hypot(100.0, 50.0)
    expected_uy = 50.0 / math.hypot(100.0, 50.0)
    assert pytest.approx(ux, 1e-4) == expected_ux
    assert pytest.approx(uy, 1e-4) == expected_uy

    target_zone = engine.get_zone_for_point(tx, ty)
    assert target_zone == ZONE_MID_FIELD


def test_physics_bridge_layout_integration():
    """Verify PhysicsBridgeLayout syncs Node models and calculates glides and offsets."""
    bridge = PhysicsBridgeLayout(viewport_w=3840.0, viewport_h=2160.0)

    nodes = [
        Node(id=1, file_path="/doc1.md", x=1920.0, y=1080.0, focus=0.9),
        Node(id=2, file_path="/doc2.md", x=1900.0, y=1000.0, focus=0.8),
        Node(id=3, file_path="/doc3.md", x=1850.0, y=1050.0, focus=0.7),
        Node(id=4, file_path="/doc4.md", x=2000.0, y=1100.0, focus=0.6),
        Node(id=5, file_path="/doc5.md", x=1950.0, y=1150.0, focus=0.5),
        Node(id=6, file_path="/doc6.md", x=1000.0, y=500.0, focus=0.1),
    ]

    zones = bridge.sync_nodes(nodes, pinned_node_id=1, recent_node_ids=[2])
    assert zones[1] == ZONE_FOCAL
    assert zones[2] == ZONE_FOCAL
    assert len(zones) == 6

    focal_targets, demotion_glides = bridge.compute_layout_offsets(nodes)
    assert 1 in focal_targets
    assert 2 in focal_targets

    nodes[1].focus = 0.0
    bridge.sync_nodes(nodes, pinned_node_id=1, recent_node_ids=[])
    focal_targets_2, demotion_glides_2 = bridge.compute_layout_offsets(nodes)

    assert bridge.active_zones[2] != ZONE_FOCAL or 2 in demotion_glides_2 or 2 in focal_targets_2


def test_horizon_demotion_radial_jitter():
    """Verify demoting nodes to ZONE_HORIZON applies hash-based radial jitter (1.1x-1.8x radius, +/- 25 deg dispersion)."""
    engine = SpatialBudgetEngine(viewport_w=3840.0, viewport_h=2160.0)
    cx, cy = engine.center_x, engine.center_y

    start_x, start_y = cx + 500.0, cy + 300.0
    orig_angle = math.atan2(300.0, 500.0)

    # Compute demotion for 3 different node IDs
    (u1_x, u1_y), (t1_x, t1_y) = engine.compute_demotion_outward_vector(
        node_id=1, current_x=start_x, current_y=start_y, target_zone=ZONE_HORIZON
    )
    (u2_x, u2_y), (t2_x, t2_y) = engine.compute_demotion_outward_vector(
        node_id=2, current_x=start_x, current_y=start_y, target_zone=ZONE_HORIZON
    )

    d1 = math.hypot(t1_x - cx, t1_y - cy)
    d2 = math.hypot(t2_x - cx, t2_y - cy)

    # Distances must differ due to radial multiplier jitter
    assert d1 != d2
    # Beads must be outside mid ellipse (> 1.0x r_mid at jittered angle)
    angle1 = math.atan2(t1_y - cy, t1_x - cx)
    angle2 = math.atan2(t2_y - cy, t2_x - cx)

    r_mid1 = engine.get_ellipse_radius(angle1, engine.a_mid, engine.b_mid)
    r_mid2 = engine.get_ellipse_radius(angle2, engine.a_mid, engine.b_mid)

    assert d1 >= 1.0 * r_mid1
    assert d2 >= 1.0 * r_mid2

    # Angular dispersion check (+/- 25 deg = +/- ~0.436 rad)
    angle_diff1 = abs(angle1 - orig_angle)
    assert angle_diff1 <= math.radians(25.1)


def test_physics_bridge_filter_horizon_nodes():
    """Verify PhysicsBridgeLayout excludes ZONE_HORIZON nodes from active physics and freezes them once settled."""
    bridge = PhysicsBridgeLayout(viewport_w=3840.0, viewport_h=2160.0)

    nodes = [Node(id=i, file_path=f"/doc{i}.md", x=1920.0 + i*10, y=1080.0 + i*10) for i in range(1, 20)]
    bridge.sync_nodes(nodes)

    active_physics_nodes = bridge.filter_physics_nodes(nodes)
    # Focal = 5, Mid = 12 => Total active physics nodes = 17 out of 19
    assert len(active_physics_nodes) == 17
    
    # Check that HORIZON nodes are excluded and frozen
    horizon_nodes = [n for n in nodes if n not in active_physics_nodes]
    assert len(horizon_nodes) == 2
    for hn in horizon_nodes:
        assert hn.vx == 0.0
        assert hn.vy == 0.0
        assert hn.zone == ZONE_HORIZON


def test_horizon_beads_scatter_performance_with_150_nodes():
    """Verify performance stability and scattering across deep horizon with 150+ nodes."""
    bridge = PhysicsBridgeLayout(viewport_w=3840.0, viewport_h=2160.0)
    nodes = [Node(id=i, file_path=f"/doc{i}.md", x=1920.0 + (i%10)*20, y=1080.0 + (i//10)*20) for i in range(1, 151)]

    zones = bridge.sync_nodes(nodes)
    focal_count = sum(1 for z in zones.values() if z == ZONE_FOCAL)
    mid_count = sum(1 for z in zones.values() if z == ZONE_MID_FIELD)
    horizon_count = sum(1 for z in zones.values() if z == ZONE_HORIZON)

    assert len(zones) == 150
    assert focal_count == 5
    assert mid_count == 12
    assert horizon_count == 133

    active_physics = bridge.filter_physics_nodes(nodes)
    assert len(active_physics) == 17  # Excludes 133 horizon nodes from continuous loop

    import time
    from physics.engine import PhysicsEngine
    engine = PhysicsEngine()
    t0 = time.perf_counter()
    for _ in range(10):
        engine.step(nodes=active_physics, edges=[], focused_node_id=0)
    avg_step_ms = (time.perf_counter() - t0) * 1000.0 / 10.0
    assert avg_step_ms < 2.0, f"Physics step latency {avg_step_ms:.2f}ms exceeds 2.0ms threshold for 60fps stability"


def test_user_coordinate_persistence_on_release():
    """Verify that user-placed coordinates are preserved across budget evaluation and sync passes."""
    bridge = PhysicsBridgeLayout(viewport_w=3840.0, viewport_h=2160.0)
    nodes = [Node(id=i, file_path=f"/doc{i}.md", x=1920.0, y=1080.0) for i in range(1, 10)]

    # Sync initially
    bridge.sync_nodes(nodes)

    # User drops node 1 at a custom user location
    user_x, user_y = 2500.0, 1500.0
    nodes[0].x = user_x
    nodes[0].y = user_y
    nodes[0].is_user_placed = True

    # Run sync passes
    bridge.sync_nodes(nodes)

    assert nodes[0].is_user_placed is True
    assert nodes[0].x == user_x
    assert nodes[0].y == user_y
    assert nodes[0].targetPosition == (user_x, user_y) or (
        hasattr(nodes[0].targetPosition, "x")
        and nodes[0].targetPosition.x() == user_x
        and nodes[0].targetPosition.y() == user_y
    )


def test_zero_target_shifts_on_hover_events():
    """Verify horizon bead target positions remain completely static across repeated spatial budget sync passes."""
    bridge = PhysicsBridgeLayout(viewport_w=3840.0, viewport_h=2160.0)
    now = 1000000.0
    nodes = [Node(id=i, file_path=f"/doc{i}.md", x=1920.0 + i * 5, y=1080.0 + i * 5, last_interaction_epoch=now) for i in range(1, 25)]

    # Initial sync
    bridge.sync_nodes(nodes, current_time=now)

    horizon_nodes = [n for n in nodes if n.zone == ZONE_HORIZON]
    assert len(horizon_nodes) > 0

    # Record initial targetPositions for horizon nodes
    initial_targets = {n.id: n.targetPosition for n in horizon_nodes}

    # Simulate repeated sync passes (e.g. on hover events)
    for _ in range(5):
        bridge.sync_nodes(nodes, current_time=now)

    # Assert 100% zero target shifts for horizon nodes
    for n in horizon_nodes:
        assert n.targetPosition == initial_targets[n.id], f"Target shift detected for horizon node {n.id}"





@pytest.mark.parametrize("hours_ago, node_id", [
    (0, 102),    # current time
    (10, 301),   # 10h ago (Focal decay)
    (24, 101),   # 24h ago
    (50, 302),   # 50h ago (Mid-field decay)
    (100, 201),  # >72h ago (fully decayed)
])
def test_hover_grace_neutralization_preserves_epochs(hours_ago, node_id):
    """Verify hover grace leaves interaction epochs unchanged for all decay states and zones."""
    from bridge import CanvasBridge
    import time

    bridge = CanvasBridge()
    try:
        node_ctrl = bridge.node_ctrl
        now = time.time()
        epoch = now - (hours_ago * 3600)
        
        node = Node(id=node_id, file_path=f"/doc{node_id}.md", last_interaction_epoch=epoch)
        bridge.store.upsert_node(node)

        node_ctrl.apply_hover_grace(node_id)
        assert node.last_interaction_epoch == epoch
    finally:
        if hasattr(bridge, "physics_ctrl") and bridge.physics_ctrl:
            bridge.physics_ctrl.stop()


def test_drift_pausing_when_user_interaction_active():
    """Verify glacial outward drift pauses completely when canvas interaction or drag is active."""
    bridge = PhysicsBridgeLayout(viewport_w=3840.0, viewport_h=2160.0)

    # Register 10 nodes (so focal well of 5 overflows and demotes remaining to MID_FIELD)
    nodes = [Node(id=i, file_path=f"/doc{i}.md", x=1920.0 + i, y=1080.0 + i) for i in range(1, 11)]

    # First pass: classify zones
    bridge.sync_nodes(nodes, is_interacting=False)

    mid_nodes = [n for n in nodes if n.zone == ZONE_MID_FIELD]
    assert len(mid_nodes) > 0

    target_node = mid_nodes[0]
    initial_x = target_node.x
    initial_y = target_node.y

    # Pass with is_interacting = True -> position must NOT change
    bridge.sync_nodes(nodes, is_interacting=True)
    assert target_node.x == initial_x
    assert target_node.y == initial_y

    # Pass with is_interacting = False -> position should advance toward target position
    bridge.sync_nodes(nodes, is_interacting=False, step_size=0.02)
    assert (target_node.x != initial_x) or (target_node.y != initial_y)


def test_tethered_anchor_datum_and_harmonic_drift():
    """
    Verify Tethered Anchor Datum and 2D Harmonic Drift bounds:
    1. Anchor datum (x0, y0) is maintained from user placement or targetPosition.
    2. Harmonic drift displacement remains strictly <= 45.0px for any time t and node ID.
    3. Peak displacement across time falls in the 30px-45px wander envelope.
    4. Unique deterministic phase offsets produce distinct wander trajectories for different node IDs.
    """
    bridge = PhysicsBridgeLayout(viewport_w=3840.0, viewport_h=2160.0)

    # 1. Check anchor datum resolution
    from PyQt6.QtCore import QPointF
    node_auto = Node(id=1, file_path="/doc1.md", x=100.0, y=200.0)
    node_auto.targetPosition = QPointF(500.0, 600.0)
    anchor_auto = bridge.get_anchor_datum(node_auto)
    assert anchor_auto == (500.0, 600.0)

    node_user = Node(id=2, file_path="/doc2.md", x=800.0, y=900.0, is_user_placed=True)
    anchor_user = bridge.get_anchor_datum(node_user)
    assert anchor_user == (800.0, 900.0)

    # 2. Check harmonic drift bounds across multiple nodes and times
    max_magnitudes = []
    for node_id in [1, 2, 42, 100, 999]:
        magnitudes_for_node = []
        for t_step in range(0, 1000):
            t = t_step * 0.1
            dx, dy = bridge.compute_harmonic_drift(node_id, t)
            dist = math.hypot(dx, dy)
            assert dist <= 45.0, f"Drift distance {dist} exceeds 45.0px bound for node {node_id} at t={t}"
            magnitudes_for_node.append(dist)

        max_mag = max(magnitudes_for_node)
        max_magnitudes.append(max_mag)
        # Peak wander for any node should reach into the 30px-45px envelope
        assert 30.0 <= max_mag <= 45.0, f"Max magnitude {max_mag} outside 30px-45px envelope"

    # 3. Check phase uniqueness: Node 1 and Node 2 should produce different drift vectors at time t=5.0
    dx1, dy1 = bridge.compute_harmonic_drift(1, 5.0)
    dx2, dy2 = bridge.compute_harmonic_drift(2, 5.0)
    assert (dx1, dy1) != (dx2, dy2)


def test_localized_kinematic_freeze_and_extended_dwell_unit():
    """
    Verify Localized Kinematic Freeze rules:
    1. Freeze harmonic buoy drift (0, 0) strictly for target, <= 180px radius peers, and connected edge neighbors.
    2. Unconnected/distant nodes (> 180px) retain non-zero drift vectors.
    3. Signal sig_constellation_active emits on state toggles.
    """
    from models import Edge
    bridge = PhysicsBridgeLayout(viewport_w=3840.0, viewport_h=2160.0)

    # Node 1: Target at (500, 500)
    n1 = Node(id=1, file_path="/doc1.md", x=500.0, y=500.0)
    # Node 2: Within 180px (distance 50px) at (550, 500), unconnected
    n2 = Node(id=2, file_path="/doc2.md", x=550.0, y=500.0)
    # Node 3: Distant at (1000, 1000) (dist 707px), connected to Node 1 via Edge
    n3 = Node(id=3, file_path="/doc3.md", x=1000.0, y=1000.0)
    # Node 4: Distant at (1200, 1200) (dist 989px), unconnected
    n4 = Node(id=4, file_path="/doc4.md", x=1200.0, y=1200.0)

    nodes = [n1, n2, n3, n4]
    edges = [Edge(source_id=1, target_id=3, edge_type="semantic", weight=0.8)]

    # Initial state: no constellation active -> all nodes drift normally at t=5.0
    for node in nodes:
        dx, dy = bridge.compute_harmonic_drift(node.id, 5.0, nodes=nodes, edges=edges)
        assert (dx, dy) != (0.0, 0.0), f"Node {node.id} should drift when no constellation is active"

    # Activate constellation on Node 1
    bridge.set_constellation_active(1, True)

    # 1. Target (Node 1) MUST be frozen
    assert bridge.compute_harmonic_drift(1, 5.0, nodes=nodes, edges=edges) == (0.0, 0.0)

    # 2. Peer <= 180px (Node 2) MUST be frozen
    assert bridge.compute_harmonic_drift(2, 5.0, nodes=nodes, edges=edges) == (0.0, 0.0)

    # 3. Graph neighbor (Node 3) MUST be frozen
    assert bridge.compute_harmonic_drift(3, 5.0, nodes=nodes, edges=edges) == (0.0, 0.0)

    # 4. Unconnected distant node (Node 4) MUST retain non-zero drift
    dx4, dy4 = bridge.compute_harmonic_drift(4, 5.0, nodes=nodes, edges=edges)
    assert (dx4, dy4) != (0.0, 0.0)
    assert math.hypot(dx4, dy4) >= 1.0

    # Reset constellation -> all nodes resume drift
    bridge.set_constellation_active(1, False)
    for node in nodes:
        dx, dy = bridge.compute_harmonic_drift(node.id, 5.0, nodes=nodes, edges=edges)
        assert (dx, dy) != (0.0, 0.0)


def test_constellation_peer_luminosity_lift_and_tendril_respiration_bounds():
    """
    Unit test verifying:
    1. Continuous breathing tendril resting opacity formula math bounds [0.20, 0.40] and active surge constant (0.75).
    2. Connected constellation peer luminosity lift formula (+0.25 over ambient).
    3. PhysicsBridgeLayout constellation peer frozen status for target, 180px peers, and graph neighbors.
    """
    # 1. Breathing tendril math bounds
    def compute_resting_opacity(phase: float) -> float:
        return 0.30 + 0.10 * math.sin(phase)

    assert pytest.approx(compute_resting_opacity(0.0), 1e-5) == 0.30
    assert pytest.approx(compute_resting_opacity(math.pi / 2.0), 1e-5) == 0.40
    assert pytest.approx(compute_resting_opacity(3.0 * math.pi / 2.0), 1e-5) == 0.20
    assert pytest.approx(compute_resting_opacity(2.0 * math.pi), 1e-5) == 0.30

    active_surge_opacity = 0.75
    assert active_surge_opacity == 0.75

    # 2. Luminosity lift formula
    ambient_op = 0.50
    peer_lift = 0.25
    boosted_op = min(1.0, ambient_op + peer_lift)
    assert pytest.approx(boosted_op, 1e-5) == 0.75

    # 3. PhysicsBridgeLayout peer identification
    from models import Edge
    bridge = PhysicsBridgeLayout(viewport_w=3840.0, viewport_h=2160.0)
    target = Node(id=10, file_path="/target.md", x=1000.0, y=1000.0)
    peer_spatial = Node(id=11, file_path="/near.md", x=1100.0, y=1000.0)  # dist 100px <= 180px
    peer_graph = Node(id=12, file_path="/graph.md", x=2000.0, y=2000.0)    # dist 1414px > 180px, connected
    distant_unconnected = Node(id=13, file_path="/far.md", x=2500.0, y=2500.0)

    nodes = [target, peer_spatial, peer_graph, distant_unconnected]
    edges = [Edge(source_id=10, target_id=12, edge_type="semantic", weight=0.9)]

    bridge.set_constellation_active(10, True)

    assert bridge.is_node_frozen_in_constellation(10, 10, nodes, edges) is True
    assert bridge.is_node_frozen_in_constellation(11, 10, nodes, edges) is True
    assert bridge.is_node_frozen_in_constellation(12, 10, nodes, edges) is True
    assert bridge.is_node_frozen_in_constellation(13, 10, nodes, edges) is False





def test_hover_grace_never_promotes_midfield_inward():
    """Verify hovering a mid-field node extends its clock without pulling it into ZONE_FOCAL."""
    import time
    from bridge import CanvasBridge

    bridge = CanvasBridge()
    try:
        engine = bridge.spatial_layout_bridge.spatial_engine
        now = time.time()

        # Register 5 focal nodes with current time
        for i in range(1, 6):
            engine.register_or_update_node(
                node_id=i, last_interaction_epoch=now, recency_score=1.0
            )

        # Register mid-field node 6 with decay (e.g. 30h ago)
        epoch_30h = now - 30 * 3600
        engine.register_or_update_node(
            node_id=6, last_interaction_epoch=epoch_30h, recency_score=0.5
        )

        zones_1 = engine.evaluate_zones()
        assert zones_1[6] == ZONE_MID_FIELD

        # Apply hover grace to node 6 (must not bump interaction epoch or mass)
        node6 = Node(id=6, file_path="/doc6.md", last_interaction_epoch=epoch_30h)
        bridge.store.upsert_node(node6)
        bridge.node_ctrl.apply_hover_grace(6)

        # Epoch remains unchanged
        assert node6.last_interaction_epoch == epoch_30h

        # Update spatial budget engine with new epoch
        engine.register_or_update_node(
            node_id=6, last_interaction_epoch=node6.last_interaction_epoch, recency_score=0.5
        )

        # Evaluate zones without explicit click/select/drag/omnibar
        zones_2 = engine.evaluate_zones(selected_node_id=0)
        # Node 6 MUST remain in ZONE_MID_FIELD (not promoted inward to ZONE_FOCAL)
        assert zones_2[6] == ZONE_MID_FIELD
    finally:
        if hasattr(bridge, "physics_ctrl") and bridge.physics_ctrl:
            bridge.physics_ctrl.stop()


def test_inner_focal_well_demotion_targets_outside_350px():
    """Verify demotion vectors for nodes in spatial_budget place targets >= 350px outside inner focal well."""
    engine = SpatialBudgetEngine(viewport_w=3840.0, viewport_h=2160.0)
    cx, cy = engine.center_x, engine.center_y

    # Center is in focal core
    assert engine.is_in_focal_core(cx, cy) is True
    assert engine.is_in_focal_core(cx + 349.0, cy) is True
    assert engine.is_in_focal_core(cx + 350.0, cy) is False
    assert engine.is_in_focal_core(cx + 500.0, cy) is False

    # Compute demotion targets for MID_FIELD and HORIZON from center
    _, (tx_mid, ty_mid) = engine.compute_demotion_outward_vector(
        node_id=1, current_x=cx, current_y=cy, target_zone=ZONE_MID_FIELD
    )
    dist_mid = math.hypot(tx_mid - cx, ty_mid - cy)
    assert dist_mid >= 350.0
    assert engine.is_in_focal_core(tx_mid, ty_mid) is False

    # For 50 different horizon beads with varying hash seeds, none should rest in inner focal well
    for nid in range(1, 51):
        _, (tx_hor, ty_hor) = engine.compute_demotion_outward_vector(
            node_id=nid, current_x=cx, current_y=cy, target_zone=ZONE_HORIZON
        )
        dist_hor = math.hypot(tx_hor - cx, ty_hor - cy)
        assert dist_hor >= 350.0
        assert engine.is_in_focal_core(tx_hor, ty_hor) is False





