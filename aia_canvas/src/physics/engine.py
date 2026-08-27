"""
Aether Physics Engine - 2.5D Organic Force-Directed & Conformal Horizon Integrator
Handles multi-cluster galaxy dispersion, fluid splines, and wing companion slotting.
"""

import logging
import math
import numpy as np

from models import Edge, Node

logger = logging.getLogger("aia_canvas.physics")


class PhysicsEngine:
    def __init__(self):
        # Viewport and Center Anchor
        self.viewport_w: float = 3840.0
        self.viewport_h: float = 2160.0
        self.center_x: float = 1920.0
        self.center_y: float = 1080.0

        # Focal Lens Dimensions
        self.focal_card_w: float = 1600.0
        self.focal_card_h: float = 1000.0
        self.aperture: float = 1.0

        # Interaction State
        self.pinned_node_id: int = 0
        self.custom_anchors: dict[int, tuple[float, float]] = {}
        self.recent_node_ids: list[int] = []

        # Smoothing & Geometry Cache
        self._smoothed_halos: dict[str, dict] = {}
        self._horizon_bearings: dict[int, float] = {}

        # Spring & Field Constants
        self.k_horizon_anchor: float = 9.5
        self.k_gutter_anchor: float = 11.5
        self.k_satellite_drift: float = 8.5

        self.box_bound_x: float = 0.0
        self.box_bound_y: float = 0.0
        self.soft_buffer: float = 120.0
        self.ideal_horizon_radius: float = 1200.0
        
        # Summoning state
        self.summoning_targets: dict[int, tuple[tuple[float, float], float]] = {}
        
        # Staging state
        self.staged_origins: dict[int, tuple[float, float]] = {}
        self.staged_targets: dict[int, tuple[float, float]] = {}

        self._recalculate_horizons()

    def set_viewport_dimensions(self, width: float, height: float):
        self.viewport_w = max(800.0, width)
        self.viewport_h = max(600.0, height)
        self.center_x = self.viewport_w / 2.0
        self.center_y = self.viewport_h / 2.0
        self._recalculate_horizons()

    def set_focal_card_dimensions(self, width: float, height: float):
        self.focal_card_w = max(680.0, width)
        self.focal_card_h = max(420.0, height)
        self._recalculate_horizons()

    def set_aperture(self, aperture: float):
        self.aperture = max(0.20, min(2.20, aperture))
        self._recalculate_horizons()

    def pin_node(self, node_id: int):
        self.pinned_node_id = node_id

    def unpin_node(self):
        self.pinned_node_id = 0

    def set_custom_anchor(self, node_id: int, x: float, y: float):
        self.custom_anchors[node_id] = (x, y)

    def summon_nodes(self, node_ids: list, target_x: float, target_y: float, strength: float = 0.6):
        """Applies an active spring/attractor vector toward (target_x, target_y) for only the target node IDs."""
        for nid_str in node_ids:
            try:
                nid = int(nid_str)
                self.summoning_targets[nid] = ((target_x, target_y), strength)
            except ValueError:
                pass

    def set_staged_nodes(self, node_ids: list[int], viewport_w: float, shelf_y: float, nodes: list[Node]):
        node_map = {n.id: n for n in nodes}
        
        for nid in list(self.staged_targets.keys()):
            if nid not in node_ids:
                if nid in self.staged_origins:
                    ox, oy = self.staged_origins[nid]
                    self.summoning_targets[nid] = ((ox, oy), 0.8)
                    
        self.staged_targets.clear()
        
        if not node_ids:
            return
            
        total = len(node_ids)
        spacing_x = 266.0
        # Matching QML properties
        card_height = 170.0
        row_gap = 40.0
        spacing_y = card_height + row_gap
        
        # Determine dynamic columns based on total search match count
        if total <= 4:
            cols = max(1, total)
        elif total in (5, 6):
            cols = 3
        elif total in (7, 8):
            cols = 4
        else:  # total >= 9
            cols = 5 if viewport_w >= 2560 else 4
            
        # We calculate rows to bloom UPWARD from shelf_y
        for i, nid in enumerate(node_ids):
            if nid not in self.staged_origins and nid in node_map:
                self.staged_origins[nid] = (node_map[nid].x, node_map[nid].y)
                
            row = i // cols
            col = i % cols
            
            # Determine how many items are in this specific row to center it individually
            row_items = min(total - row * cols, cols)
            row_grid_width = (row_items - 1) * spacing_x
            row_start_x = (viewport_w / 2.0) - (row_grid_width / 2.0)
            
            # Bloom UPWARD: subtract from shelf_y
            tx = row_start_x + (col * spacing_x)
            ty = shelf_y - (row * spacing_y)
            
            self.staged_targets[nid] = (tx, ty)

    def _recalculate_horizons(self):
        self.box_bound_x = (self.focal_card_w / 2.0) + 520.0
        self.box_bound_y = (self.focal_card_h / 2.0) + 160.0
        self.soft_buffer = 120.0

        diag = math.sqrt(self.box_bound_x**2 + self.box_bound_y**2)
        self.ideal_horizon_radius = diag + (180.0 * max(0.50, self.aperture))

    def _apply_coulomb_repulsion(
        self,
        pos: np.ndarray,
        node_ids: np.ndarray,
        comp_ids: np.ndarray,
        forces: np.ndarray,
        has_active_focus: bool,
        focused_node_id: int,
        first_deg_indices: set[int],
        second_deg_indices: set[int],
        geom_scale: float,
    ) -> None:
        N = len(pos)
        if N <= 1:
            return

        DX = pos[:, 0] - pos[:, 0][:, None]
        DY = pos[:, 1] - pos[:, 1][:, None]
        Dist_sq = DX * DX + DY * DY

        ID1 = node_ids[:, None]
        ID2 = node_ids[None, :]
        Jitter = ((ID1 + ID2) % 17) - 8.0
        Same_Cluster = (comp_ids[:, None] == comp_ids[None, :]) & (comp_ids[:, None] >= 0)

        if has_active_focus:
            focused_idx = np.where(node_ids == focused_node_id)[0]
            focused_idx_val = focused_idx[0] if len(focused_idx) > 0 else -1
            focal_flags = np.array(
                [idx == focused_idx_val or idx in first_deg_indices or idx in second_deg_indices for idx in range(N)]
            )
            n1_focal = focal_flags[:, None]
            n2_focal = focal_flags[None, :]
            is_focused = (node_ids == focused_node_id)
            touch_focused = is_focused[:, None] | is_focused[None, :]

            MIN_SEP = np.where(
                n1_focal != n2_focal,
                0.0,
                np.where(
                    touch_focused,
                    0.0,
                    np.where(
                        n1_focal & n2_focal,
                        120.0,
                        np.where(Same_Cluster, 42.0 + Jitter, 220.0),
                    ),
                ),
            )
        else:
            friend_base = 48.0 + max(0.0, (self.aperture - 0.50) * 150.0)
            friend_sep = friend_base + Jitter
            stranger_sep = 340.0 * geom_scale
            MIN_SEP = np.where(Same_Cluster, friend_sep, stranger_sep)

        mask = (Dist_sq < MIN_SEP**2) & (Dist_sq > 1e-6)
        Dist = np.sqrt(np.where(mask, Dist_sq, 1.0))
        Repulse = (MIN_SEP - Dist) * 8.5
        FX = np.where(mask, (DX / Dist) * Repulse, 0.0)
        FY = np.where(mask, (DY / Dist) * Repulse, 0.0)

        forces[:, 0] -= np.sum(FX, axis=1)
        forces[:, 1] -= np.sum(FY, axis=1)

    def _apply_hooke_springs(
        self,
        edges: list[Edge],
        pos: np.ndarray,
        node_ids: np.ndarray,
        id_to_idx: dict[int, int],
        forces: np.ndarray,
        geom_scale: float,
        has_active_focus: bool,
        focused_node_id: int,
        first_deg_indices: set[int],
        second_deg_indices: set[int],
    ) -> None:
        valid_edges = [e for e in edges if e.sourceId in id_to_idx and e.targetId in id_to_idx]
        if not valid_edges:
            return

        src_idx = np.array([id_to_idx[e.sourceId] for e in valid_edges], dtype=np.int32)
        tgt_idx = np.array([id_to_idx[e.targetId] for e in valid_edges], dtype=np.int32)
        weights = np.array([e.weight for e in valid_edges], dtype=np.float64)
        types = [e.edgeType.lower() for e in valid_edges]

        dx = pos[tgt_idx, 0] - pos[src_idx, 0]
        dy = pos[tgt_idx, 1] - pos[src_idx, 1]
        dist = np.hypot(dx, dy)
        dist_safe = np.where(dist < 1e-6, 1.0, dist)

        rest_len = np.array([150.0 if t == "explicit" else (200.0 if t == "temporal" else 240.0) for t in types]) * geom_scale
        displacement = dist_safe - rest_len

        k_spring = 0.85 * np.minimum(1.0, weights)
        for e_i, (e, t) in enumerate(zip(valid_edges, types)):
            if t == "temporal":
                k_spring[e_i] = 0.0
            else:
                is_cross_desk_temporal = (t == "temporal") and (
                    (e.sourceId in self.recent_node_ids) != (e.targetId in self.recent_node_ids)
                )
                if is_cross_desk_temporal:
                    k_spring[e_i] *= 0.10

            if e.sourceId in self.staged_targets or e.targetId in self.staged_targets:
                k_spring[e_i] = 0.0

        spring_force = displacement * k_spring
        if not has_active_focus:
            mask_cap = spring_force > 150.0
            spring_force = np.where(mask_cap, 150.0 + (spring_force - 150.0) * 0.05, spring_force)

        fx_s = (dx / dist_safe) * spring_force
        fy_s = (dy / dist_safe) * spring_force

        if has_active_focus:
            def get_tier_idx(idx):
                nid = node_ids[idx]
                if nid == focused_node_id:
                    return 0
                if idx in first_deg_indices:
                    return 1
                if idx in second_deg_indices:
                    return 2
                return 3

            for e_i in range(len(valid_edges)):
                s = src_idx[e_i]
                t = tgt_idx[e_i]
                t1 = get_tier_idx(s)
                t2 = get_tier_idx(t)

                if t1 == 0 or t2 == 0:
                    continue
                if t1 == 1 and t2 == 2:
                    forces[t, 0] -= fx_s[e_i] * 0.3
                    forces[t, 1] -= fy_s[e_i] * 0.3
                    continue
                elif t2 == 1 and t1 == 2:
                    forces[s, 0] += fx_s[e_i] * 0.3
                    forces[s, 1] += fy_s[e_i] * 0.3
                    continue
                if (t1 == 2 and t2 >= 3) or (t2 == 2 and t1 >= 3):
                    continue
                if (t1 == 1 and t2 >= 3) or (t2 == 1 and t1 >= 3):
                    continue

                forces[s, 0] += fx_s[e_i]
                forces[s, 1] += fy_s[e_i]
                forces[t, 0] -= fx_s[e_i]
                forces[t, 1] -= fy_s[e_i]
        else:
            np.add.at(forces[:, 0], src_idx, fx_s)
            np.add.at(forces[:, 1], src_idx, fy_s)
            np.add.at(forces[:, 0], tgt_idx, -fx_s)
            np.add.at(forces[:, 1], tgt_idx, -fy_s)

    def _apply_docking_constraints(
        self,
        pos: np.ndarray,
        node_ids: np.ndarray,
        id_to_idx: dict[int, int],
        forces: np.ndarray,
        comp_ids: np.ndarray,
        comp_centroids: dict[int, tuple[float, float, int]],
        has_active_focus: bool,
        focused_node_id: int,
        first_deg_indices: set[int],
        second_degree_parent: dict[int, int],
        geom_scale: float,
    ) -> None:
        self.summoning_targets = {
            nid: (tpos, strength * 0.995)
            for nid, (tpos, strength) in self.summoning_targets.items()
            if strength > 0.01
        }
        bound_x, bound_y = (self.viewport_w / 2.0) * 0.78, (self.viewport_h / 2.0) * 0.65
        N = len(pos)

        for idx in range(N):
            nid = node_ids[idx]
            if nid in self.summoning_targets:
                tpos, strength = self.summoning_targets[nid]
                forces[idx, 0] += (tpos[0] - pos[idx, 0]) * strength * 12.0
                forces[idx, 1] += (tpos[1] - pos[idx, 1]) * strength * 12.0

            if nid in self.staged_targets:
                tx, ty = self.staged_targets[nid]
                forces[idx, 0] = (tx - pos[idx, 0]) * 15.0
                forces[idx, 1] = (ty - pos[idx, 1]) * 15.0
                continue

            dx = pos[idx, 0] - self.center_x
            dy = pos[idx, 1] - self.center_y
            dist_to_center = math.hypot(dx, dy) or 1.0

            if has_active_focus:
                if nid != focused_node_id:
                    if idx in first_deg_indices or nid in second_degree_parent:
                        vp_cx = self.viewport_w / 2.0
                        wb_w = self.focal_card_w
                        wb_x = (self.viewport_w - wb_w) / 2.0
                        target_x = (wb_x - 450.0) if pos[idx, 0] <= vp_cx else (wb_x + wb_w + 450.0)
                        forces[idx, 0] += (target_x - pos[idx, 0]) * self.k_gutter_anchor

                        if nid in second_degree_parent:
                            p_nid = second_degree_parent[nid]
                            p_idx = id_to_idx.get(p_nid)
                            if p_idx is not None:
                                target_sat_y = pos[p_idx, 1] + (((nid % 5) - 2) * 140.0)
                                forces[idx, 1] += (target_sat_y - pos[idx, 1]) * self.k_satellite_drift
                        else:
                            forces[idx, 1] += (self.center_y - pos[idx, 1]) * self.k_horizon_anchor
                    else:
                        c_idx = comp_ids[idx]
                        if c_idx in comp_centroids:
                            ccx, ccy, count = comp_centroids[c_idx]
                            if count >= 3:
                                dx_c = ccx - pos[idx, 0]
                                dy_c = ccy - pos[idx, 1]
                                dist_c = math.hypot(dx_c, dy_c) or 1.0
                                exp_r = min(600.0 * geom_scale, (55.0 + (24.0 * math.sqrt(count))) * geom_scale)
                                k_pull = 1.25 if dist_c < exp_r * 0.8 else min(12.0, 1.25 + ((dist_c - exp_r * 0.8) * 0.25))
                                forces[idx, 0] += dx_c * k_pull
                                forces[idx, 1] += dy_c * k_pull

                        if abs(dx) > bound_x:
                            forces[idx, 0] -= (1.0 if dx > 0 else -1.0) * (abs(dx) - bound_x) * 8.0
                        if abs(dy) > bound_y:
                            forces[idx, 1] -= (1.0 if dy > 0 else -1.0) * (abs(dy) - bound_y) * 8.0
            else:
                if nid in self.custom_anchors:
                    ax, ay = self.custom_anchors[nid]
                    forces[idx, 0] += (ax - pos[idx, 0]) * 4.0
                    forces[idx, 1] += (ay - pos[idx, 1]) * 4.0

                if abs(dx) < 1.0 and abs(dy) < 1.0:
                    dx, dy = 1.0 + (nid % 5), 1.0 + (nid % 7)
                    dist_to_center = math.hypot(dx, dy)

                is_recent = nid in self.recent_node_ids
                void_r = 380.0 if is_recent else 750.0
                if dist_to_center < void_r:
                    ramp = ((void_r - dist_to_center) / void_r) ** 1.5
                    forces[idx, 0] += (dx / dist_to_center) * ramp * 3200.0
                    forces[idx, 1] += (dy / dist_to_center) * ramp * 3200.0

                if is_recent and dist_to_center > 650.0:
                    desk_pull = (dist_to_center - 650.0) * 2.5
                    forces[idx, 0] -= (dx / dist_to_center) * desk_pull
                    forces[idx, 1] -= (dy / dist_to_center) * desk_pull

                if abs(dx) > bound_x:
                    forces[idx, 0] -= (1.0 if dx > 0 else -1.0) * (abs(dx) - bound_x) * 4.5
                if abs(dy) > bound_y:
                    forces[idx, 1] -= (1.0 if dy > 0 else -1.0) * (abs(dy) - bound_y) * 4.5

                c_idx = comp_ids[idx]
                if c_idx in comp_centroids and not is_recent:
                    ccx, ccy, count = comp_centroids[c_idx]
                    if count >= 3:
                        dx_c = ccx - pos[idx, 0]
                        dy_c = ccy - pos[idx, 1]
                        dist_c = math.hypot(dx_c, dy_c) or 1.0
                        exp_r = min(600.0 * geom_scale, (55.0 + (24.0 * math.sqrt(count))) * geom_scale)
                        k_pull = 1.25 if dist_c < exp_r * 0.8 else min(12.0, 1.25 + ((dist_c - exp_r * 0.8) * 0.25))
                        forces[idx, 0] += dx_c * k_pull
                        forces[idx, 1] += dy_c * k_pull

    def _integrate_velocities(
        self,
        nodes: list[Node],
        pos: np.ndarray,
        vel: np.ndarray,
        forces: np.ndarray,
        node_ids: np.ndarray,
        id_to_idx: dict[int, int],
        comp_ids: np.ndarray,
        dt: float,
        has_active_focus: bool,
        focused_node_id: int,
        hovered_node_id: int,
        first_deg_indices: set[int],
        second_degree_parent: dict[int, int],
        focal_weights: dict[int, float],
        first_degree_set: set[int],
    ) -> bool:
        N = len(nodes)
        focused_idx = id_to_idx.get(focused_node_id, -1)

        if has_active_focus:
            vp_cx = self.viewport_w / 2.0
            left_flank = [idx for idx in range(N) if (idx in first_deg_indices or node_ids[idx] in second_degree_parent) and pos[idx, 0] <= vp_cx]
            right_flank = [idx for idx in range(N) if (idx in first_deg_indices or node_ids[idx] in second_degree_parent) and pos[idx, 0] > vp_cx]

            left_flank.sort(key=lambda idx: focal_weights.get(node_ids[idx], 0.0), reverse=True)
            right_flank.sort(key=lambda idx: focal_weights.get(node_ids[idx], 0.0), reverse=True)

            for flank_list in (left_flank, right_flank):
                for i in range(len(flank_list)):
                    for j in range(i + 1, len(flank_list)):
                        na_idx, nb_idx = flank_list[i], flank_list[j]
                        dx = pos[nb_idx, 0] - pos[na_idx, 0]
                        dy = pos[nb_idx, 1] - pos[na_idx, 1]
                        dist_sq = dx * dx + dy * dy
                        if dist_sq < 3600.0 and dist_sq > 0.001:
                            dist = math.sqrt(dist_sq)
                            push = (60.0 - dist) / dist * 0.15
                            vel[na_idx, 1] -= dy * push
                            vel[na_idx, 0] -= dx * push
                            vel[nb_idx, 1] += dy * push
                            vel[nb_idx, 0] += dx * push

        hovered_idx = id_to_idx.get(hovered_node_id, -1)
        pinned_idx = id_to_idx.get(self.pinned_node_id, -1)

        for idx in range(N):
            nid = node_ids[idx]
            if nid in self.staged_targets:
                tx, ty = self.staged_targets[nid]
                pos[idx, 0], pos[idx, 1] = tx, ty
                vel[idx, 0], vel[idx, 1] = 0.0, 0.0
                continue

            if (has_active_focus and idx == focused_idx) or (idx == hovered_idx and nid != self.pinned_node_id):
                vel[idx, 0], vel[idx, 1] = 0.0, 0.0
                continue

            if idx == pinned_idx:
                vel[idx, 0], vel[idx, 1] = 0.0, 0.0
                if has_active_focus and idx in first_deg_indices:
                    self._horizon_bearings[nid] = math.atan2(pos[idx, 1] - self.center_y, pos[idx, 0] - self.center_x)
                continue

            fx, fy = forces[idx, 0], forces[idx, 1]
            speed = math.hypot(vel[idx, 0], vel[idx, 1])
            drag = (5.2 if has_active_focus else 4.0) + (0.045 * speed)

            vel[idx, 0] += ((fx - (drag * vel[idx, 0])) / 1.0) * dt
            vel[idx, 1] += ((fy - (drag * vel[idx, 1])) / 1.0) * dt

            cur_speed = math.hypot(vel[idx, 0], vel[idx, 1])
            max_speed = 340.0 if has_active_focus else 180.0
            if cur_speed > max_speed:
                scale = max_speed / cur_speed
                vel[idx, 0] *= scale
                vel[idx, 1] *= scale

            pos[idx, 0] += vel[idx, 0] * dt
            pos[idx, 1] += vel[idx, 1] * dt

        # Update node coordinates at the end of the step
        for idx, n in enumerate(nodes):
            n.x = float(pos[idx, 0])
            n.y = float(pos[idx, 1])
            n.vx = float(vel[idx, 0])
            n.vy = float(vel[idx, 1])
            n.clusterId = int(comp_ids[idx])
            if has_active_focus and n.id == focused_node_id:
                n.depthZ = 0.0
            else:
                norm_y = max(0.0, min(1.0, 1.0 - (n.y / self.viewport_h)))
                is_wing = has_active_focus and (n.id in first_degree_set or n.id in second_degree_parent)
                n.depthZ = norm_y * 0.25 if is_wing else norm_y * (1.0 - n.focus * 0.5)

        total_velocity = float(np.sum(np.hypot(vel[:, 0], vel[:, 1])))
        return total_velocity >= 0.01 * len(nodes)

    def _find_connected_components(self, nodes: list[Node], edges: list[Edge]) -> list[set[int]]:
        adj: dict[int, set[int]] = {n.id: set() for n in nodes}
        for e in edges:
            if e.edgeType.lower() != "temporal" and e.weight > 0.45:
                if e.sourceId in adj and e.targetId in adj:
                    adj[e.sourceId].add(e.targetId)
                    adj[e.targetId].add(e.sourceId)

        visited: set[int] = set()
        components: list[set[int]] = []

        for n in nodes:
            if n.id not in visited:
                comp: set[int] = set()
                queue = [n.id]
                visited.add(n.id)

                while queue:
                    curr = queue.pop(0)
                    comp.add(curr)
                    for neighbor in adj.get(curr, set()):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

                components.append(comp)

        return components

    def step(
        self,
        nodes: list[Node],
        edges: list[Edge],
        focused_node_id: int,
        hovered_node_id: int = 0,
        dt: float = 0.008,
        first_degree_set: set[int] | None = None,
        second_degree_set: set[int] | None = None,
        second_degree_parent: dict[int, int] | None = None,
        focal_weights: dict[int, float] | None = None,
    ) -> bool:
        """
        Advances the physics simulation by one tick.
        Returns True if the system is still active, False if it has settled and can sleep.
        """
        if not nodes:
            return False

        N = len(nodes)
        id_to_idx = {n.id: i for i, n in enumerate(nodes)}
        node_ids = np.array([n.id for n in nodes], dtype=np.int64)

        pos = np.empty((N, 2), dtype=np.float64)
        vel = np.empty((N, 2), dtype=np.float64)

        for i, n in enumerate(nodes):
            pos[i, 0] = float(n.x)
            pos[i, 1] = float(n.y)
            vel[i, 0] = float(n.vx)
            vel[i, 1] = float(n.vy)

        has_active_focus = (focused_node_id > 0) and (focused_node_id in id_to_idx)

        wing_width = (self.viewport_w - self.focal_card_w) / 2.0
        if has_active_focus:
            self.center_x = (self.viewport_w - wing_width) / 2.0
        else:
            self.center_x = self.viewport_w / 2.0

        first_degree_set = set(first_degree_set) if isinstance(first_degree_set, (set, list, tuple)) else set()
        second_degree_set = set(second_degree_set) if isinstance(second_degree_set, (set, list, tuple)) else set()
        second_degree_parent = second_degree_parent or {}
        focal_weights = focal_weights or {}

        first_deg_indices = {id_to_idx[nid] for nid in first_degree_set if nid in id_to_idx}
        second_deg_indices = {id_to_idx[nid] for nid in second_degree_set if nid in id_to_idx}

        components = self._find_connected_components(nodes, edges)
        comp_ids = np.full(N, -1, dtype=np.int32)
        comp_centroids: dict[int, tuple[float, float, int]] = {}

        for c_idx, comp in enumerate(components):
            if has_active_focus:
                c_nodes_idx = [
                    id_to_idx[nid]
                    for nid in comp
                    if nid in id_to_idx
                    and nid != focused_node_id
                    and nid not in first_degree_set
                    and nid not in second_degree_set
                ]
            else:
                c_nodes_idx = [id_to_idx[nid] for nid in comp if nid in id_to_idx]

            if len(c_nodes_idx) >= 3:
                cx = float(np.mean(pos[c_nodes_idx, 0]))
                cy = float(np.mean(pos[c_nodes_idx, 1]))
                comp_centroids[c_idx] = (cx, cy, len(c_nodes_idx))

                for nid in comp:
                    if nid in id_to_idx:
                        comp_ids[id_to_idx[nid]] = c_idx

        forces = np.zeros((N, 2), dtype=np.float64)

        if not has_active_focus:
            comp_indices = list(comp_centroids.keys())
            recent_indices = {id_to_idx[nid] for nid in self.recent_node_ids if nid in id_to_idx}
            for i in range(len(comp_indices)):
                c1_idx = comp_indices[i]
                c1_x, c1_y, count1 = comp_centroids[c1_idx]
                for j in range(i + 1, len(comp_indices)):
                    c2_idx = comp_indices[j]
                    c2_x, c2_y, count2 = comp_centroids[c2_idx]

                    dx, dy = c2_x - c1_x, c2_y - c1_y
                    dist = math.hypot(dx, dy) or 1.0
                    min_cluster_sep = ((55.0 + (24.0 * math.sqrt(count1))) + (55.0 + (24.0 * math.sqrt(count2)))) * 1.35

                    if dist < min_cluster_sep:
                        push = (min_cluster_sep - dist) * 2.5
                        fx, fy = (dx / dist) * push, (dy / dist) * push

                        for nid in components[c1_idx]:
                            idx = id_to_idx.get(nid)
                            if idx is not None and idx not in recent_indices:
                                forces[idx, 0] -= fx / count1
                                forces[idx, 1] -= fy / count1

                        for nid in components[c2_idx]:
                            idx = id_to_idx.get(nid)
                            if idx is not None and idx not in recent_indices:
                                forces[idx, 0] += fx / count2
                                forces[idx, 1] += fy / count2

        geom_scale = math.sqrt(self.aperture)

        self._apply_coulomb_repulsion(
            pos,
            node_ids,
            comp_ids,
            forces,
            has_active_focus,
            focused_node_id,
            first_deg_indices,
            second_deg_indices,
            geom_scale,
        )

        self._apply_hooke_springs(
            edges,
            pos,
            node_ids,
            id_to_idx,
            forces,
            geom_scale,
            has_active_focus,
            focused_node_id,
            first_deg_indices,
            second_deg_indices,
        )

        self._apply_docking_constraints(
            pos,
            node_ids,
            id_to_idx,
            forces,
            comp_ids,
            comp_centroids,
            has_active_focus,
            focused_node_id,
            first_deg_indices,
            second_degree_parent,
            geom_scale,
        )

        return self._integrate_velocities(
            nodes,
            pos,
            vel,
            forces,
            node_ids,
            id_to_idx,
            comp_ids,
            dt,
            has_active_focus,
            focused_node_id,
            hovered_node_id,
            first_deg_indices,
            second_degree_parent,
            focal_weights,
            first_degree_set,
        )




    def get_cluster_halos(self, nodes: list[Node], edges: list[Edge], focused_id: int,
                          first_degree_set: set[int] | None = None,
                          second_degree_set: set[int] | None = None) -> list[dict]:
        if not nodes:
            return []

        # Geometry scaling for visual halo expansion
        geom_scale = 1.0 + max(0.0, min(1.8, (self.aperture - 0.50) * 1.6))
        
        node_map = {n.id: n for n in nodes}
        components = self._find_connected_components(nodes, edges)
        halos = []
        eff_ap = max(0.35, min(1.0, math.pow(self.aperture, 0.7)))
        active_halo_ids: set[str] = set()

        deg_map: dict[int, int] = {n.id: 0 for n in nodes}
        for e in edges:
            if e.edgeType.lower() != "temporal":
                deg_map[e.sourceId] = deg_map.get(e.sourceId, 0) + 1
                deg_map[e.targetId] = deg_map.get(e.targetId, 0) + 1

        first_deg = first_degree_set or set()
        second_deg = second_degree_set or set()
        workbench_nodes = {focused_id} | first_deg | second_deg

        for comp_idx, comp_ids in enumerate(components):
            # Only generate a cluster halo for connected components with N >= 3 nodes
            if len(comp_ids) < 3:
                continue

            group = [node_map[nid] for nid in comp_ids if nid in node_map and nid not in workbench_nodes]
            if len(group) < 3:
                continue

            halo_id = f"component_{comp_idx}"
            active_halo_ids.add(halo_id)

            # 1. Calculate actual 2D physical footprint bounds
            xs = sorted([n.x for n in group])
            ys = sorted([n.y for n in group])
            
            # 2. Filter outliers (keep inner 90% to ignore rogue runaway nodes)
            p05 = int(len(group) * 0.05)
            p95 = int(len(group) * 0.95)
            
            if len(group) < 5:
                min_x, max_x = xs[0], xs[-1]
                min_y, max_y = ys[0], ys[-1]
            else:
                min_x, max_x = xs[p05], xs[p95]
                min_y, max_y = ys[p05], ys[p95]

            # 3. The exact physical footprint dimensions
            core_w = max_x - min_x
            core_h = max_y - min_y

            # 4. Pad generously to swallow Z-depth parallax projections
            padding = 110.0 * geom_scale
            target_w = core_w + padding
            target_h = core_h + padding

            # Bounding Radius Hard-Cap: Clamp bounding radius between 90.0 and 260.0
            calculated_radius_w = target_w / 2.0
            calculated_radius_h = target_h / 2.0
            radius_w = max(90.0, min(calculated_radius_w, 260.0))
            radius_h = max(90.0, min(calculated_radius_h, 260.0))
            target_w = radius_w * 2.0
            target_h = radius_h * 2.0

            # Density Metric: Calculate cluster dispersion (average distance of nodes to centroid)
            cx = sum(n.x for n in group) / len(group)
            cy = sum(n.y for n in group) / len(group)
            dispersion = sum(math.hypot(n.x - cx, n.y - cy) for n in group) / len(group)
            
            # Scale halo opacity down if dispersion is large (e.g., during startup scatter)
            disp_min = 110.0
            disp_max = 280.0
            if dispersion <= disp_min:
                density_weight = 1.0
            elif dispersion >= disp_max:
                density_weight = 0.0
            else:
                density_weight = (disp_max - dispersion) / (disp_max - disp_min)

            # 5. Shift visual center to the true center of the mass footprint
            target_cx = (min_x + max_x) / 2.0
            target_cy = (min_y + max_y) / 2.0

            # 6. Smooth the dimensions and position
            prev = self._smoothed_halos.get(halo_id)
            curr_cx = prev["centerX"] if prev else target_cx
            curr_cy = prev["centerY"] if prev else target_cy
            curr_w = prev.get("width", target_w) if prev else target_w
            curr_h = prev.get("height", target_h) if prev else target_h

            smooth_cx = curr_cx + (target_cx - curr_cx) * 0.14
            smooth_cy = curr_cy + (target_cy - curr_cy) * 0.14
            smooth_w = curr_w + (target_w - curr_w) * 0.10
            smooth_h = curr_h + (target_h - curr_h) * 0.10

            # Procedural Nebula Identity
            import colorsys
            min_node_id = min(n.id for n in group)
            hue = (min_node_id * 137.508) % 360.0
            # Low saturation, moderate lightness for etched light aesthetic
            r, g, b = colorsys.hls_to_rgb(hue / 360.0, 0.65, 0.35)
            color_hex = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

            is_focal_cluster = any(nid == focused_id for nid in comp_ids) and focused_id > 0

            halo_data = {
                "id": halo_id,
                "centerX": smooth_cx,
                "centerY": smooth_cy,
                "width": smooth_w,     # Replacing 'radius'
                "height": smooth_h,    # Replacing 'radius'
                "color": color_hex,
                "isFocalCluster": is_focal_cluster,
                "nodeCount": len(group),
                "densityWeight": density_weight,
            }

            self._smoothed_halos[halo_id] = halo_data
            halos.append(halo_data)

        # Elastic Cellular Separation Between Distinct Halos
        for i in range(len(halos)):
            for j in range(i + 1, len(halos)):
                h1 = halos[i]
                h2 = halos[j]
                dx = h2["centerX"] - h1["centerX"]
                dy = h2["centerY"] - h1["centerY"]
                dist = math.hypot(dx, dy) or 1.0
                
                # Approximate collision using the average dimension of the pill
                r1 = (h1["width"] + h1["height"]) / 4.0
                r2 = (h2["width"] + h2["height"]) / 4.0
                min_dist = r1 + r2 + 40.0

                if dist < min_dist:
                    overlap = (min_dist - dist) * 0.5
                    push_x = (dx / dist) * overlap
                    push_y = (dy / dist) * overlap
                    h1["centerX"] -= push_x
                    h1["centerY"] -= push_y
                    h2["centerX"] += push_x
                    h2["centerY"] += push_y

        self._smoothed_halos = {hid: hdata for hid, hdata in self._smoothed_halos.items() if hid in active_halo_ids}
        return halos