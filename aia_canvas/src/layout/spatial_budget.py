"""
Aether Spatial Budget Engine - Elliptical Zoning & Dynamic Viewport Density Coordinator
Calculates dynamic elliptical boundaries, mass scores, zone allocations, and radial slotting.
"""

import math
from typing import Dict, List, Tuple, Optional, Union

ZONE_FOCAL = "ZONE_FOCAL"
ZONE_MID_FIELD = "ZONE_MID_FIELD"
ZONE_HORIZON = "ZONE_HORIZON"


class SpatialBudgetEngine:
    """
    Manages deterministic viewport spatial budgeting and dynamic elliptical zoning.
    """

    def __init__(self, viewport_w: float = 3840.0, viewport_h: float = 2160.0):
        self.viewport_w: float = max(800.0, float(viewport_w))
        self.viewport_h: float = max(600.0, float(viewport_h))

        self.center_x: float = 0.0
        self.center_y: float = 0.0
        self.a_focal: float = 0.0
        self.b_focal: float = 0.0
        self.a_mid: float = 0.0
        self.b_mid: float = 0.0

        self.focal_capacity: int = 5
        self.mid_capacity: int = 12

        self._nodes: Dict[int, dict] = {}
        self._previous_zones: Dict[int, str] = {}

        self._recalculate_boundaries()

    def _recalculate_boundaries(self):
        self.center_x = self.viewport_w / 2.0
        self.center_y = self.viewport_h / 2.0

        # Focal Well Ellipse semi-axes (Max capacity: 5 nodes)
        self.a_focal = 0.28 * self.viewport_w
        self.b_focal = 0.24 * self.viewport_h

        # Mid-Field Ellipse semi-axes (Max capacity: 12 nodes)
        self.a_mid = 0.52 * self.viewport_w
        self.b_mid = 0.46 * self.viewport_h

    def set_viewport_dimensions(self, width: float, height: float):
        """Dynamically adapts zone boundaries on viewport resize."""
        self.viewport_w = max(800.0, float(width))
        self.viewport_h = max(600.0, float(height))
        self._recalculate_boundaries()

    @staticmethod
    def calculate_mass_score(
        recency_score: float = 0.0,
        interaction_state: float = 0.0,
        alert_active: Union[float, bool] = 0.0,
        is_pinned: bool = False,
        last_interaction_epoch: Optional[float] = None,
        current_time: Optional[float] = None,
        decay_factor: Optional[float] = None,
    ) -> float:
        """
        Calculates composite mass score:
        Effective Mass = (decay_factor * 0.5) + (recency_score * 0.3) + (alert_active * 0.2)
        decay_factor = max(0.0, 1.0 - (current_time - last_interaction_epoch) / (72 * 3600))
        If is_pinned == True, Effective Mass = float('inf').

        Hover states are strictly read-only and do NOT alter mass score.
        """
        if is_pinned:
            return float("inf")

        if decay_factor is None:
            if last_interaction_epoch is not None:
                if current_time is None:
                    import time
                    current_time = time.time()
                decay_factor = max(0.0, 1.0 - (float(current_time) - float(last_interaction_epoch)) / (72.0 * 3600.0))
            else:
                decay_factor = max(0.0, min(1.0, float(interaction_state)))

        decay = max(0.0, min(1.0, float(decay_factor)))
        recency = max(0.0, min(1.0, float(recency_score)))
        alert = max(0.0, min(1.0, float(alert_active)))

        return (decay * 0.5) + (recency * 0.3) + (alert * 0.2)

    def register_or_update_node(
        self,
        node_id: int,
        recency_score: float = 0.0,
        interaction_state: float = 0.0,
        alert_active: Union[float, bool] = 0.0,
        is_pinned: bool = False,
        is_user_placed: bool = False,
        x: Optional[float] = None,
        y: Optional[float] = None,
        last_interaction_epoch: Optional[float] = None,
        current_time: Optional[float] = None,
        decay_factor: Optional[float] = None,
        is_explicit_action: bool = False,
    ):
        """Registers a node or updates its layout metadata and mass score."""
        mass = self.calculate_mass_score(
            recency_score=recency_score,
            interaction_state=interaction_state,
            alert_active=alert_active,
            is_pinned=is_pinned,
            last_interaction_epoch=last_interaction_epoch,
            current_time=current_time,
            decay_factor=decay_factor,
        )
        existing_node = self._nodes.get(node_id)
        if x is not None:
            curr_x = x
        elif existing_node is not None and "x" in existing_node:
            curr_x = existing_node["x"]
        else:
            curr_x = self.center_x

        if y is not None:
            curr_y = y
        elif existing_node is not None and "y" in existing_node:
            curr_y = existing_node["y"]
        else:
            curr_y = self.center_y

        node_data = {
            "node_id": node_id,
            "recency_score": recency_score,
            "interaction_state": interaction_state,
            "alert_active": alert_active,
            "is_pinned": is_pinned,
            "is_user_placed": is_user_placed,
            "is_explicit_action": is_explicit_action,
            "last_interaction_epoch": last_interaction_epoch,
            "mass": mass,
            "x": curr_x,
            "y": curr_y,
        }

        if node_id in self._nodes:
            self._nodes[node_id].update(node_data)
        else:
            self._nodes[node_id] = node_data

    def unregister_node(self, node_id: int):
        """Removes node from registry."""
        self._nodes.pop(node_id, None)
        self._previous_zones.pop(node_id, None)

    def get_ellipse_radius(self, angle_rad: float, a: float, b: float) -> float:
        """
        Calculates distance from center to ellipse boundary at angle_rad:
        R(theta) = (a * b) / sqrt((b * cos(theta))^2 + (a * sin(theta))^2)
        """
        cos_t = math.cos(angle_rad)
        sin_t = math.sin(angle_rad)
        denom = math.sqrt((b * cos_t) ** 2 + (a * sin_t) ** 2)
        if denom == 0:
            return 0.0
        return (a * b) / denom

    def is_point_in_ellipse(self, x: float, y: float, a: float, b: float) -> bool:
        """Checks if point (x, y) lies inside center-anchored ellipse with semi-axes (a, b)."""
        dx = x - self.center_x
        dy = y - self.center_y
        return ((dx / a) ** 2 + (dy / b) ** 2) <= 1.0

    def get_zone_for_point(self, x: float, y: float) -> str:
        """Returns the geometric zone classification for point (x, y)."""
        if self.is_point_in_ellipse(x, y, self.a_focal, self.b_focal):
            return ZONE_FOCAL
        elif self.is_point_in_ellipse(x, y, self.a_mid, self.b_mid):
            return ZONE_MID_FIELD
        return ZONE_HORIZON

    def evaluate_zones(self, selected_node_id: int = 0) -> Dict[int, str]:
        """
        Evaluates all registered nodes and classifies them strictly into:
        - ZONE_FOCAL: Top by mass (max capacity: 5)
        - ZONE_MID_FIELD: Next by mass (max capacity: 12)
        - ZONE_HORIZON: Remaining nodes

        Guarantees no more than 5 nodes can hold ZONE_FOCAL status.
        Asserts pinned nodes (infinite mass) take priority in ZONE_FOCAL.
        Enforces "Never Promote Inward via Hover Alone": inward zone promotion requires an
        explicit action (click/selection, drag, omnibar action, or pinned/user-placed).
        Hover states are strictly read-only for visual styling and preview states and do NOT
        alter mass scores or trigger zone re-sorting.
        """
        zone_ranks = {ZONE_FOCAL: 0, ZONE_MID_FIELD: 1, ZONE_HORIZON: 2}
        sorted_nodes = sorted(
            self._nodes.values(),
            key=lambda n: (-n["mass"], n["node_id"])
        )

        zone_assignments: Dict[int, str] = {}
        for idx, n in enumerate(sorted_nodes):
            nid = n["node_id"]
            if idx < self.focal_capacity:
                raw_zone = ZONE_FOCAL
            elif idx < (self.focal_capacity + self.mid_capacity):
                raw_zone = ZONE_MID_FIELD
            else:
                raw_zone = ZONE_HORIZON

            prev_zone = self._previous_zones.get(nid, n.get("current_zone"))
            if prev_zone is None and "x" in n and "y" in n:
                prev_zone = self.get_zone_for_point(n["x"], n["y"])

            # Check if raw evaluation would promote node inward
            if prev_zone is not None:
                is_inward_promotion = zone_ranks.get(raw_zone, 2) < zone_ranks.get(prev_zone, 2)
            else:
                is_inward_promotion = False

            if is_inward_promotion:
                is_explicit = (
                    n.get("is_pinned", False)
                    or n.get("is_user_placed", False)
                    or n.get("is_explicit_action", False)
                    or (nid == selected_node_id and selected_node_id > 0)
                )
                if not is_explicit:
                    zone = prev_zone
                else:
                    zone = raw_zone
            else:
                zone = raw_zone

            zone_assignments[nid] = zone
            n["current_zone"] = zone

        self._previous_zones = dict(zone_assignments)
        return zone_assignments

    def get_focal_slot_targets(self, focal_node_ids: List[int]) -> Dict[int, Tuple[float, float]]:
        """
        Provides target (x, y) coordinate offsets so nodes in ZONE_FOCAL
        naturally arrange around the center without direct overlaps.
        Respects user-placed coordinates and does not overwrite them with auto-slotted positions.
        """
        count = len(focal_node_ids)
        if count == 0:
            return {}

        targets: Dict[int, Tuple[float, float]] = {}
        auto_slot_ids = []
        for nid in focal_node_ids:
            node_info = self._nodes.get(nid, {})
            if node_info.get("is_explicit_action", False) and not node_info.get("is_user_placed", False):
                auto_slot_ids.append(nid)
            else:
                nx = node_info.get("x", self.center_x)
                ny = node_info.get("y", self.center_y)
                targets[nid] = (nx, ny)

        auto_count = len(auto_slot_ids)
        if auto_count == 1:
            targets[auto_slot_ids[0]] = (self.center_x, self.center_y)
        elif auto_count > 1:
            r_a = 0.45 * self.a_focal
            r_b = 0.45 * self.b_focal
            for i, nid in enumerate(auto_slot_ids):
                angle = -math.pi / 2.0 + (2.0 * math.pi * i / auto_count)
                tx = self.center_x + r_a * math.cos(angle)
                ty = self.center_y + r_b * math.sin(angle)
                targets[nid] = (tx, ty)

        return targets

    def compute_demotion_outward_vector(
        self,
        node_id: int,
        current_x: float,
        current_y: float,
        target_zone: str,
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        For nodes demoted across zone boundaries, computes:
        1. An outward radial unit direction vector (ux, uy)
        2. Designated orbit target position (tx, ty) to glide them into their orbits.

        Returns: ((ux, uy), (tx, ty))
        """
        dx = current_x - self.center_x
        dy = current_y - self.center_y
        dist = math.hypot(dx, dy)

        if dist < 1e-5:
            ux, uy = 1.0, 0.0
            angle = 0.0
        else:
            ux, uy = dx / dist, dy / dist
            angle = math.atan2(dy, dx)

        r_focal = self.get_ellipse_radius(angle, self.a_focal, self.b_focal)
        r_mid = self.get_ellipse_radius(angle, self.a_mid, self.b_mid)

        if target_zone == ZONE_MID_FIELD:
            target_r = r_focal + 0.5 * (r_mid - r_focal)
            target_r = max(target_r, 350.0)
            tx = self.center_x + ux * target_r
            ty = self.center_y + uy * target_r
        elif target_zone == ZONE_HORIZON:
            import random
            rng = random.Random(node_id)
            r_mult = 1.1 + 0.7 * rng.random()
            angle_dispersion = math.radians((rng.random() * 2.0 - 1.0) * 25.0)
            jittered_angle = angle + angle_dispersion
            ux = math.cos(jittered_angle)
            uy = math.sin(jittered_angle)
            r_mid_jittered = self.get_ellipse_radius(jittered_angle, self.a_mid, self.b_mid)
            target_r = max(r_mid_jittered * r_mult, 350.0)
            tx = self.center_x + ux * target_r
            ty = self.center_y + uy * target_r
        else:
            target_r = 0.5 * r_focal
            tx = self.center_x + ux * target_r
            ty = self.center_y + uy * target_r

        return (ux, uy), (tx, ty)

    def is_in_focal_core(self, x: float, y: float, core_radius: float = 350.0) -> bool:
        """Returns True if (x, y) falls inside the inner focal well core (radius < core_radius)."""
        return math.hypot(x - self.center_x, y - self.center_y) < float(core_radius)
