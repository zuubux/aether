"""
Aether Physics Bridge Layout Engine
Connects SpatialBudgetEngine with PhysicsEngine for dynamic spatial zoning and glided transit.
"""

import math
from typing import Dict, List, Tuple, Optional
from layout.spatial_budget import SpatialBudgetEngine, ZONE_FOCAL, ZONE_MID_FIELD, ZONE_HORIZON
from models import Node


def compute_harmonic_drift(node_id: int, t: float) -> Tuple[float, float]:
    """
    Computes low-frequency 2D harmonic wave drift offset (dx, dy) within a 30px to 45px wander envelope around (x0, y0).
    Phase offsets are deterministically derived from node_id.
    """
    nid = int(node_id)
    phase_x = (nid * 1.61803398875) % (2.0 * math.pi)
    phase_y = (nid * 2.71828182845 + 1.0) % (2.0 * math.pi)

    # Low frequency smooth waves (calm sub-pixel movement)
    w1 = 0.18
    w2 = 0.07

    raw_x = math.sin(w1 * t + phase_x) + 0.35 * math.sin(w2 * t + 2.1 * phase_x)
    raw_y = math.cos(w1 * t + phase_y) + 0.35 * math.cos(w2 * t + 2.1 * phase_y)

    base_amp = 30.0
    dx = (raw_x / 1.35) * base_amp
    dy = (raw_y / 1.35) * base_amp

    dist = math.hypot(dx, dy)
    if dist > 45.0:
        scale = 45.0 / dist
        dx *= scale
        dy *= scale

    return dx, dy


def _extract_target_coords(target_pos, default_x=0.0, default_y=0.0) -> Tuple[float, float]:
    if target_pos is None:
        return default_x, default_y
    if hasattr(target_pos, "x") and callable(target_pos.x):
        return float(target_pos.x()), float(target_pos.y())
    if hasattr(target_pos, "x") and hasattr(target_pos, "y"):
        return float(target_pos.x), float(target_pos.y)
    try:
        return float(target_pos[0]), float(target_pos[1])
    except (TypeError, IndexError, KeyError):
        return default_x, default_y


class PhysicsBridgeLayout:
    """
    Bridge module coordinating SpatialBudgetEngine zoning evaluations with Node physics layouts.
    """

    def __init__(self, viewport_w: float = 3840.0, viewport_h: float = 2160.0):
        self.spatial_engine = SpatialBudgetEngine(viewport_w, viewport_h)
        self.active_zones: Dict[int, str] = {}
        self.previous_zones: Dict[int, str] = {}

    def set_viewport_dimensions(self, width: float, height: float):
        self.spatial_engine.set_viewport_dimensions(width, height)

    def set_constellation_active(self, node_id: int, active: bool):
        """Sets or clears the active constellation target node ID."""
        if active:
            self.constellation_active_node_id = node_id
        elif getattr(self, "constellation_active_node_id", 0) == node_id:
            self.constellation_active_node_id = 0

    def is_node_frozen_in_constellation(
        self,
        node_id: int,
        target_node_id: int = 0,
        nodes: Optional[List[Node]] = None,
        edges: Optional[List[Any]] = None,
    ) -> bool:
        """
        Determines if a node's harmonic drift should be frozen during an active constellation dwell:
        1. Target hovered node itself.
        2. Nodes whose anchor datum is <= 180px Euclidean distance from target.
        3. Graph neighbors directly connected to target via active tendril edges.
        """
        target_id = target_node_id if target_node_id > 0 else getattr(self, "constellation_active_node_id", 0)
        if target_id <= 0:
            return False
        if node_id == target_id:
            return True

        nodes_list = nodes or []
        target_node = next((n for n in nodes_list if getattr(n, "id", None) == target_id), None)
        curr_node = next((n for n in nodes_list if getattr(n, "id", None) == node_id), None)

        if target_node and curr_node:
            tx, ty = self.get_anchor_datum(target_node)
            nx, ny = self.get_anchor_datum(curr_node)
            if math.hypot(nx - tx, ny - ty) <= 180.0:
                return True

        if edges:
            for e in edges:
                if isinstance(e, dict):
                    s_id = e.get("sourceId") or e.get("source_id") or e.get("source")
                    t_id = e.get("targetId") or e.get("target_id") or e.get("target")
                else:
                    s_id = getattr(e, "sourceId", None) or getattr(e, "source_id", None) or getattr(e, "source", None)
                    t_id = getattr(e, "targetId", None) or getattr(e, "target_id", None) or getattr(e, "target", None)
                if (s_id == target_id and t_id == node_id) or (t_id == target_id and s_id == node_id):
                    return True

        return False

    def compute_harmonic_drift(
        self,
        node_id: int,
        t: float,
        nodes: Optional[List[Node]] = None,
        edges: Optional[List[Any]] = None,
        target_node_id: int = 0,
    ) -> Tuple[float, float]:
        """Calculates low-frequency 2D harmonic drift offset for presentation layer, zeroing vector if frozen."""
        if self.is_node_frozen_in_constellation(node_id, target_node_id=target_node_id, nodes=nodes, edges=edges):
            return 0.0, 0.0
        return compute_harmonic_drift(node_id, t)

    def get_anchor_datum(self, node: Node) -> Tuple[float, float]:
        """
        Returns base anchor coordinate (x0, y0) from either user drop location or targetPosition.
        """
        if getattr(node, "is_user_placed", False):
            return float(node.x), float(node.y)
        if hasattr(node, "targetPosition") and node.targetPosition is not None:
            return _extract_target_coords(node.targetPosition, float(node.x), float(node.y))
        return float(node.x), float(node.y)

    def filter_physics_nodes(self, nodes: List[Node]) -> List[Node]:
        """
        Excludes ZONE_HORIZON nodes from active continuous force-directed physics loop.
        Freezes ZONE_HORIZON nodes once settled at their target positions.
        """
        active_nodes = []
        for n in nodes:
            zone = self.active_zones.get(n.id, getattr(n, "zone", ZONE_HORIZON))
            if zone == ZONE_HORIZON:
                if hasattr(n, "vx"):
                    n.vx = 0.0
                if hasattr(n, "vy"):
                    n.vy = 0.0
                if hasattr(n, "targetPosition") and n.targetPosition is not None:
                    tx, ty = _extract_target_coords(n.targetPosition, getattr(n, "x", 0.0), getattr(n, "y", 0.0))
                    n.x = tx
                    n.y = ty
            else:
                active_nodes.append(n)
        return active_nodes

    def sync_nodes(
        self,
        nodes: List[Node],
        pinned_node_id: int = 0,
        recent_node_ids: Optional[List[int]] = None,
        alert_node_ids: Optional[List[int]] = None,
        is_interacting: bool = False,
        current_time: Optional[float] = None,
        step_size: float = 0.02,
    ) -> Dict[int, str]:
        """
        Registers/updates nodes with SpatialBudgetEngine and evaluates zone assignments.
        Passive Hover Isolation: Node hover state/grace does NOT inflate mass score or interaction state.
        Visual hover tier escalations in QML remain 100% presentation-only and do not promote nodes into
        ZONE_FOCAL or ZONE_MID_FIELD or trigger demotion outward vector cascades for peripheral beads.
        Glacial outward drift is applied to demoted MID_FIELD nodes unless interaction is locked.
        """
        recent_set = set(recent_node_ids or [])
        alert_set = set(alert_node_ids or [])

        from PyQt6.QtCore import QPointF

        for n in nodes:
            nid = n.id
            is_pinned = getattr(n, "is_pinned", False)
            last_epoch = getattr(n, "last_interaction_epoch", None)
            recency = 1.0 if nid in recent_set else getattr(n, "recency", 0.0)
            interaction = getattr(n, "interaction_state", 0.0)
            if getattr(n, "focus", 0.0) > 0.5:
                interaction = max(interaction, getattr(n, "focus", 0.0))
            alert = 1.0 if nid in alert_set else getattr(n, "alert_active", 0.0)
            is_user_placed = getattr(n, "is_user_placed", False)
            is_explicit_action = getattr(n, "is_explicit_action", False)

            self.spatial_engine.register_or_update_node(
                node_id=nid,
                recency_score=recency,
                interaction_state=interaction,
                alert_active=alert,
                is_pinned=is_pinned,
                is_user_placed=is_user_placed,
                is_explicit_action=is_explicit_action,
                x=n.x,
                y=n.y,
                last_interaction_epoch=last_epoch,
                current_time=current_time,
            )

        self.previous_zones = dict(self.active_zones)
        self.active_zones = self.spatial_engine.evaluate_zones()

        # Update zone and targetPosition properties on each node model
        focal_nids = [n.id for n in nodes if self.active_zones.get(n.id) == ZONE_FOCAL]
        focal_targets = self.spatial_engine.get_focal_slot_targets(focal_nids)

        for n in nodes:
            zone = self.active_zones.get(n.id, ZONE_HORIZON)
            prev_zone = self.previous_zones.get(n.id)
            if hasattr(n, "zone"):
                n.zone = zone

            is_user_placed = getattr(n, "is_user_placed", False)
            n_is_pinned = getattr(n, "is_pinned", False) or (n.id == pinned_node_id)

            if is_user_placed:
                tx, ty = n.x, n.y
            elif zone == ZONE_FOCAL:
                tx, ty = focal_targets.get(n.id, (n.x, n.y))
            elif zone == ZONE_MID_FIELD:
                _, (tx, ty) = self.spatial_engine.compute_demotion_outward_vector(n.id, n.x, n.y, zone)
            else: # ZONE_HORIZON
                # Preserve existing target position if node was already in HORIZON to prevent horizon bead shifts
                need_reposition = True
                if prev_zone == ZONE_HORIZON and hasattr(n, "targetPosition") and n.targetPosition is not None:
                    tp = n.targetPosition
                    if isinstance(tp, QPointF):
                        tpx, tpy = tp.x(), tp.y()
                    elif isinstance(tp, (tuple, list)) and len(tp) >= 2:
                        tpx, tpy = float(tp[0]), float(tp[1])
                    else:
                        tpx, tpy = getattr(tp, "x", n.x), getattr(tp, "y", n.y)

                    dist_to_center = math.hypot(tpx - self.spatial_engine.center_x, tpy - self.spatial_engine.center_y)
                    if dist_to_center >= 350.0:
                        tx, ty = tpx, tpy
                        need_reposition = False

                if need_reposition:
                    dist_to_center = math.hypot(n.x - self.spatial_engine.center_x, n.y - self.spatial_engine.center_y)
                    if not self.spatial_engine.is_point_in_ellipse(n.x, n.y, self.spatial_engine.a_mid, self.spatial_engine.b_mid) and dist_to_center >= 350.0:
                        tx, ty = n.x, n.y
                    else:
                        _, (tx, ty) = self.spatial_engine.compute_demotion_outward_vector(n.id, n.x, n.y, zone)

            if hasattr(n, "targetPosition"):
                n.targetPosition = (tx, ty)

            # Glacial outward drift for demoted MID_FIELD nodes
            if zone == ZONE_MID_FIELD and not is_user_placed and not n_is_pinned:
                if not is_interacting:
                    dx = tx - n.x
                    dy = ty - n.y
                    dist = math.hypot(dx, dy)
                    if dist > 1e-4:
                        step = min(step_size, dist)
                        n.x += (dx / dist) * step
                        n.y += (dy / dist) * step

            if zone == ZONE_HORIZON and not is_user_placed:
                if hasattr(n, "vx"):
                    n.vx = 0.0
                if hasattr(n, "vy"):
                    n.vy = 0.0

        return self.active_zones

    def compute_layout_offsets(
        self,
        nodes: List[Node],
    ) -> Tuple[Dict[int, Tuple[float, float]], Dict[int, Tuple[Tuple[float, float], Tuple[float, float]]]]:
        """
        Calculates focal target slots for ZONE_FOCAL nodes and demotion vectors/targets for demoted nodes.
        Returns: (focal_slot_targets, demotion_glides)
        """
        focal_nids = [n.id for n in nodes if self.active_zones.get(n.id) == ZONE_FOCAL]
        focal_targets = self.spatial_engine.get_focal_slot_targets(focal_nids)

        demotion_glides: Dict[int, Tuple[Tuple[float, float], Tuple[float, float]]] = {}
        zone_ranks = {ZONE_FOCAL: 0, ZONE_MID_FIELD: 1, ZONE_HORIZON: 2}

        for n in nodes:
            nid = n.id
            prev_zone = self.previous_zones.get(nid)
            curr_zone = self.active_zones.get(nid, ZONE_HORIZON)

            if prev_zone and zone_ranks.get(curr_zone, 2) > zone_ranks.get(prev_zone, 2):
                radial_vec, target_pos = self.spatial_engine.compute_demotion_outward_vector(
                    nid, n.x, n.y, curr_zone
                )
                demotion_glides[nid] = (radial_vec, target_pos)

        return focal_targets, demotion_glides
