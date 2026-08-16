"""
Aether Canvas - Physics Engine
Viscous orbital horizons (calm, non-distracting drift), zero position-clamp chatter,
Stokes fluid drag, and elastic shield membranes.
"""

import math
import time
from typing import Dict, List, Optional, Tuple, Set
from models import Node, Edge


class PhysicsEngine:
    def __init__(self):
        # Viewport Dimensions
        self.width = 3840.0
        self.height = 2160.0
        self.center_x = self.width / 2.0
        self.center_y = self.height / 2.0

        # Cognitive Aperture
        self.aperture = 1.0

        # Workbench Footprint & Non-Penetration Boundaries
        self.focal_card_w = 1400.0
        self.focal_card_h = 900.0
        self._recalculate_horizons()

        # Viscous Spring Constants (Calm, biological orbital movement)
        self.k_focus = 32.0
        self.k_horizon_anchor = 18.0
        self.k_satellite_drift = 12.0

        # Gentle Repulsion & Clearance
        self.focal_repulsion_charge = 1200000.0
        self.spotlight_clearing_force = 650.0

        # Bearing & Anchor State
        self.pinned_node_id: Optional[int] = None
        self.custom_anchors: Dict[int, Tuple[float, float]] = {}
        self._horizon_bearings: Dict[int, float] = {}
        self._last_focused_id: int = -1
        self._start_time = time.time()

        # Low-Pass Filtered Halo Memory
        self._smoothed_halos: Dict[str, dict] = {}

    def set_aperture(self, aperture_val: float):
        self.aperture = max(0.20, min(2.20, aperture_val))
        self._recalculate_horizons()

    def set_focal_card_dimensions(self, w: float, h: float):
        self.focal_card_w = w
        self.focal_card_h = h
        self._recalculate_horizons()

    def set_viewport_dimensions(self, w: float, h: float):
        if w <= 0 or h <= 0:
            return
        self.width = w
        self.height = h
        self.center_x = w / 2.0
        self.center_y = h / 2.0
        self._recalculate_horizons()

    def _recalculate_horizons(self):
        self.box_bound_x = (self.focal_card_w / 2.0) + 110.0
        self.box_bound_y = (self.focal_card_h / 2.0) + 85.0
        self.soft_buffer = 65.0

        diag = math.sqrt(self.box_bound_x**2 + self.box_bound_y**2)
        self.ideal_horizon_radius = diag + (160.0 * max(0.50, self.aperture))

    def pin_node(self, node_id: int):
        self.pinned_node_id = node_id
        if node_id in self.custom_anchors:
            del self.custom_anchors[node_id]

    def unpin_node(self):
        self.pinned_node_id = None

    def set_custom_anchor(self, node_id: int, x: float, y: float):
        self.custom_anchors[node_id] = (x, y)
        self._horizon_bearings[node_id] = math.atan2(y - self.center_y, x - self.center_x)

    def _find_connected_components(
        self, nodes: List[Node], edges: List[Edge]
    ) -> List[List[int]]:
        adj: Dict[int, Set[int]] = {n.id: set() for n in nodes}
        for e in edges:
            adj[e.sourceId].add(e.targetId)
            adj[e.targetId].add(e.sourceId)

        visited: Set[int] = set()
        components: List[List[int]] = []

        for node in nodes:
            if node.id not in visited:
                comp: List[int] = []
                queue = [node.id]
                visited.add(node.id)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for neighbor in adj.get(curr, set()):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                components.append(comp)
        return components

    def get_cluster_halos(self, nodes: List[Node], edges: List[Edge], focused_id: int) -> List[dict]:
        if not nodes:
            return []

        node_map = {n.id: n for n in nodes}
        components = self._find_connected_components(nodes, edges)
        halos = []

        eff_ap = max(0.35, min(1.0, math.pow(self.aperture, 0.7)))
        proximity_threshold = 300.0 * eff_ap

        active_halo_ids: Set[str] = set()

        for comp_idx, comp_ids in enumerate(components):
            comp_nodes = [node_map[nid] for nid in comp_ids if nid in node_map]
            if len(comp_nodes) < 2:
                continue

            dense_groups: List[List[Node]] = []
            visited_nodes: Set[int] = set()

            for n in comp_nodes:
                if n.id in visited_nodes:
                    continue

                group = [n]
                visited_nodes.add(n.id)
                queue = [n]

                while queue:
                    curr = queue.pop(0)
                    for other in comp_nodes:
                        if other.id not in visited_nodes:
                            dist = math.hypot(curr.x - other.x, curr.y - other.y)
                            if dist <= proximity_threshold:
                                visited_nodes.add(other.id)
                                group.append(other)
                                queue.append(other)

                if len(group) >= 2:
                    dense_groups.append(group)

            for g_idx, group in enumerate(dense_groups):
                halo_id = f"c_{comp_idx}_g_{g_idx}"
                active_halo_ids.add(halo_id)

                target_cx = sum(n.x for n in group) / len(group)
                target_cy = sum(n.y for n in group) / len(group)

                dists = [math.hypot(n.x - target_cx, n.y - target_cy) for n in group]
                max_d = max(dists)

                ext_counts: Dict[str, int] = {}
                for n in group:
                    ext = n.extension.lower() if hasattr(n, "extension") else ".txt"
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1

                top_ext = max(ext_counts, key=ext_counts.get) if ext_counts else ".md"
                if top_ext == ".py":
                    color_hex = "#38bdf8"
                elif top_ext in [".sh", ".bash", ".zsh"]:
                    color_hex = "#fbbf24"
                elif top_ext in [".md", ".org", ".txt"]:
                    color_hex = "#a78bfa"
                else:
                    color_hex = "#34d399"

                target_radius = max(70.0, min(240.0, max_d + (55.0 * eff_ap)))
                is_focal_cluster = any(n.id == focused_id for n in group) and focused_id > 0

                if halo_id in self._smoothed_halos:
                    prev = self._smoothed_halos[halo_id]
                    smooth_cx = prev["centerX"] + (target_cx - prev["centerX"]) * 0.14
                    smooth_cy = prev["centerY"] + (target_cy - prev["centerY"]) * 0.14
                    smooth_r = prev["radius"] + (target_radius - prev["radius"]) * 0.14
                else:
                    smooth_cx = target_cx
                    smooth_cy = target_cy
                    smooth_r = target_radius

                halo_data = {
                    "id": halo_id,
                    "centerX": smooth_cx,
                    "centerY": smooth_cy,
                    "radius": smooth_r,
                    "color": color_hex,
                    "isFocalCluster": is_focal_cluster,
                    "nodeCount": len(group)
                }

                self._smoothed_halos[halo_id] = halo_data
                halos.append(halo_data)

        self._smoothed_halos = {hid: hdata for hid, hdata in self._smoothed_halos.items() if hid in active_halo_ids}
        return halos

    def _get_conformal_horizon_radius(self, theta: float) -> float:
        u_x = math.cos(theta)
        u_y = math.sin(theta)

        pad_x = max(110.0, self.width * 0.05)
        pad_y = max(80.0, self.height * 0.05)

        max_span_x = ((self.width / 2.0) - pad_x) / (abs(u_x) + 0.0001)
        max_span_y = ((self.height / 2.0) - pad_y) / (abs(u_y) + 0.0001)
        max_allowed_radius = min(max_span_x, max_span_y)

        min_clear_x = self.box_bound_x / (abs(u_x) + 0.0001)
        min_clear_y = self.box_bound_y / (abs(u_y) + 0.0001)
        min_hull_radius = min(min_clear_x, min_clear_y) + 40.0

        target_r = min(self.ideal_horizon_radius, max_allowed_radius - 20.0)
        return max(min_hull_radius, target_r)

    def _get_edge_mechanics(self, edge: Edge, has_active_focus: bool) -> Tuple[float, float]:
        edge_type = edge.edgeType.lower()
        w = max(0.05, min(1.0, edge.weight))
        eff_ap = math.pow(self.aperture, 1.4)

        if has_active_focus:
            # Relaxed active spring tension (calm horizon anchors)
            if edge_type == "explicit" or w >= 0.80:
                k = 18.0 * math.pow(w, 1.4)
                span = 175.0 * eff_ap
            elif edge_type == "temporal" or w <= 0.25:
                k = 6.0 * max(0.35, w)
                span = 280.0 * eff_ap
            else:
                k = 11.0 * math.pow(w, 1.2)
                span = (210.0 + (1.0 - w) * 90.0) * eff_ap
        else:
            if edge_type == "explicit" or w >= 0.80:
                k = 14.0 * math.pow(w, 1.4)
                span = 140.0 * eff_ap
            elif edge_type == "temporal" or w <= 0.25:
                k = 4.2 * max(0.35, w)
                span = 230.0 * eff_ap
            else:
                k = 8.5 * math.pow(w, 1.2)
                span = (175.0 + (1.0 - w) * 60.0) * eff_ap

        return k, max(26.0, span)

    def _get_node_radial_band(self, node: Node, has_focus: bool, focused_id: int) -> Tuple[float, float, float]:
        dx = node.x - self.center_x
        dy = node.y - self.center_y
        dist = math.sqrt(dx * dx + dy * dy)

        if has_focus and node.id == focused_id:
            return (self.focal_card_w / 2.0), (self.focal_card_h / 2.0), 3.0

        aperture_scale = max(0.28, min(1.0, math.pow(self.aperture, 0.8)))

        if dist < (self.ideal_horizon_radius + 180.0):
            return (145.0 * aperture_scale), (60.0 * aperture_scale), 1.0
        else:
            return (95.0 * aperture_scale), (30.0 * aperture_scale), 0.40

    def step(self, nodes: List[Node], edges: List[Edge], focused_node_id: int, dt: float = 0.008):
        """Execute 120Hz simulation frame."""
        if not nodes:
            return

        node_map: Dict[int, Node] = {n.id: n for n in nodes}
        forces: Dict[int, List[float]] = {n.id: [0.0, 0.0] for n in nodes}
        elapsed = time.time() - self._start_time

        has_active_focus = (focused_node_id > 0 and focused_node_id in node_map)

        # 1. Inertial Mass & Component Mapping
        components = self._find_connected_components(nodes, edges)
        node_comp_map: Dict[int, int] = {}
        for c_idx, c_ids in enumerate(components):
            for nid in c_ids:
                node_comp_map[nid] = c_idx

        node_mass: Dict[int, float] = {}
        for n in nodes:
            deg = sum(1 for e in edges if e.sourceId == n.id or e.targetId == n.id)
            node_mass[n.id] = 1.0 + (0.55 * deg)

        # 2. Focus Transition & Horizon Bearing Latching
        first_degree_set: Set[int] = set()
        second_degree_parent: Dict[int, int] = {}

        if has_active_focus:
            for e in edges:
                if e.sourceId == focused_node_id:
                    first_degree_set.add(e.targetId)
                elif e.targetId == focused_node_id:
                    first_degree_set.add(e.sourceId)

            for e in edges:
                src, tgt = e.sourceId, e.targetId
                if src in first_degree_set and tgt != focused_node_id and tgt not in first_degree_set:
                    second_degree_parent[tgt] = src
                elif tgt in first_degree_set and src != focused_node_id and src not in first_degree_set:
                    second_degree_parent[src] = tgt

            if focused_node_id != self._last_focused_id:
                self._last_focused_id = focused_node_id
                self._horizon_bearings.clear()

            for n_id in first_degree_set:
                if n_id not in self._horizon_bearings and n_id in node_map:
                    n = node_map[n_id]
                    self._horizon_bearings[n_id] = math.atan2(n.y - self.center_y, n.x - self.center_x)
        else:
            self._last_focused_id = -1
            self._horizon_bearings.clear()

        num_nodes = len(nodes)

        # 3. Dynamic Box Repulsion
        aperture_rep_mod = math.pow(self.aperture, 1.2)

        for i in range(num_nodes):
            n1 = nodes[i]
            hw1, hh1, rep_mult1 = self._get_node_radial_band(n1, has_active_focus, focused_node_id)
            c1 = node_comp_map.get(n1.id, -1)

            for j in range(i + 1, num_nodes):
                n2 = nodes[j]
                hw2, hh2, rep_mult2 = self._get_node_radial_band(n2, has_active_focus, focused_node_id)
                c2 = node_comp_map.get(n2.id, -2)
                same_project_component = (c1 == c2 and c1 >= 0)

                dx = n2.x - n1.x
                dy = n2.y - n1.y
                abs_dx = abs(dx)
                abs_dy = abs(dy)

                req_sep_x = hw1 + hw2 + (20.0 * aperture_rep_mod)
                req_sep_y = hh1 + hh2 + (16.0 * aperture_rep_mod)

                overlap_x = req_sep_x - abs_dx
                overlap_y = req_sep_y - abs_dy

                if overlap_x > 0.0 and overlap_y > 0.0:
                    dist = math.sqrt(dx * dx + dy * dy) + 0.1
                    dir_x = (dx / dist) if dist > 0.1 else 1.0
                    dir_y = (dy / dist) if dist > 0.1 else 0.0

                    penetration = min(overlap_x / req_sep_x, overlap_y / req_sep_y)
                    box_push = penetration * (1800.0 if has_active_focus else 1100.0) * max(rep_mult1, rep_mult2)

                    forces[n1.id][0] -= dir_x * box_push
                    forces[n1.id][1] -= dir_y * box_push
                    forces[n2.id][0] += dir_x * box_push
                    forces[n2.id][1] += dir_y * box_push
                else:
                    if not same_project_component:
                        dist_sq = (dx * dx) + (dy * dy * 2.2) + 350.0
                        dist = math.sqrt(dist_sq)
                        ambient_charge = (450000.0 if has_active_focus else 250000.0) * min(rep_mult1, rep_mult2) * aperture_rep_mod
                        rep_force = ambient_charge / dist_sq

                        fx = (dx / dist) * rep_force
                        fy = (dy / dist) * rep_force

                        forces[n1.id][0] -= fx
                        forces[n1.id][1] -= fy
                        forces[n2.id][0] += fx
                        forces[n2.id][1] += fy

        # 4. Tendril Elasticity
        for edge in edges:
            src = node_map.get(edge.sourceId)
            dst = node_map.get(edge.targetId)
            if not src or not dst:
                continue

            if has_active_focus and (edge.sourceId == focused_node_id or edge.targetId == focused_node_id):
                continue

            dx = dst.x - src.x
            dy = dst.y - src.y
            dist = math.sqrt(dx * dx + dy * dy) + 0.1

            spring_k, target_span = self._get_edge_mechanics(edge, has_active_focus)

            delta = dist - target_span
            if delta > 0.0:
                stretch_ramp = min(2.0, 1.0 + (delta / 450.0))
                spring_force = delta * spring_k * stretch_ramp
            else:
                spring_force = delta * spring_k

            fx = (dx / dist) * spring_force
            fy = (dy / dist) * spring_force

            forces[src.id][0] += fx
            forces[src.id][1] += fy
            forces[dst.id][0] -= fx
            forces[dst.id][1] -= fy

        # 5. Viscous Horizon Anchors & Potential Barrier Clearance
        soft_hull_x = self.box_bound_x + self.soft_buffer
        soft_hull_y = self.box_bound_y + self.soft_buffer

        for node in nodes:
            dx = node.x - self.center_x
            dy = node.y - self.center_y
            abs_dx = abs(dx)
            abs_dy = abs(dy)
            dist_to_center = math.sqrt(dx * dx + dy * dy) + 0.1

            if has_active_focus:
                if node.id == focused_node_id:
                    forces[node.id][0] += (self.center_x - node.x) * self.k_focus
                    forces[node.id][1] += (self.center_y - node.y) * self.k_focus

                elif node.id in first_degree_set:
                    theta = self._horizon_bearings.get(node.id, math.atan2(dy, dx))
                    target_r = self._get_conformal_horizon_radius(theta)
                    target_x = self.center_x + math.cos(theta) * target_r
                    target_y = self.center_y + math.sin(theta) * target_r

                    forces[node.id][0] += (target_x - node.x) * self.k_horizon_anchor
                    forces[node.id][1] += (target_y - node.y) * self.k_horizon_anchor

                elif node.id in second_degree_parent:
                    parent_node = node_map.get(second_degree_parent[node.id])
                    if parent_node:
                        p_theta = self._horizon_bearings.get(
                            parent_node.id,
                            math.atan2(parent_node.y - self.center_y, parent_node.x - self.center_x)
                        )
                        sat_span = 190.0 * math.pow(self.aperture, 1.2)
                        target_sat_x = parent_node.x + (math.cos(p_theta) * sat_span)
                        target_sat_y = parent_node.y + (math.sin(p_theta) * sat_span)

                        forces[node.id][0] += (target_sat_x - node.x) * self.k_satellite_drift
                        forces[node.id][1] += (target_sat_y - node.y) * self.k_satellite_drift

                else:
                    # Smooth potential barrier around active workbench (no hard clamping chatter)
                    if abs_dx < soft_hull_x and abs_dy < soft_hull_y:
                        pen_x = max(0.0, soft_hull_x - abs_dx) / self.soft_buffer
                        pen_y = max(0.0, soft_hull_y - abs_dy) / self.soft_buffer
                        ramp = min(1.0, max(pen_x, pen_y))

                        dir_x = (dx / dist_to_center) if dist_to_center > 1.0 else 1.0
                        dir_y = (dy / dist_to_center) if dist_to_center > 1.0 else 0.0

                        forces[node.id][0] += dir_x * ramp * self.spotlight_clearing_force
                        forces[node.id][1] += dir_y * ramp * self.spotlight_clearing_force

            if node.id in self.custom_anchors:
                c_x, c_y = self.custom_anchors[node.id]
                forces[node.id][0] += (c_x - node.x) * 40.0
                forces[node.id][1] += (c_y - node.y) * 40.0

            # Biological Multi-Harmonic Respiration
            phase = node.id * 1.618033
            drift_x = math.sin(elapsed * 0.18 + phase) + (0.35 * math.sin(elapsed * 0.07 + phase * 2.1))
            drift_y = math.cos(elapsed * 0.14 + phase * 1.3) + (0.35 * math.cos(elapsed * 0.05 + phase * 0.7))

            if not (has_active_focus and node.id == focused_node_id):
                drift_amp = (18.0 if has_active_focus else 14.0) * math.pow(self.aperture, 0.7)
                forces[node.id][0] += drift_x * drift_amp
                forces[node.id][1] += drift_y * (drift_amp * 0.75)

        # 6. Stokes Fluid Drag & Velocity Clamping
        for node in nodes:
            if node.id == self.pinned_node_id:
                node.vx = 0.0
                node.vy = 0.0
                if has_active_focus and node.id in first_degree_set:
                    self._horizon_bearings[node.id] = math.atan2(node.y - self.center_y, node.x - self.center_x)
                continue

            mass = node_mass.get(node.id, 1.0)
            fx, fy = forces[node.id]

            speed = math.sqrt(node.vx * node.vx + node.vy * node.vy)
            drag_linear = 14.0 if has_active_focus else 9.0
            drag_quadratic = 0.075 * speed

            total_drag_x = (drag_linear + drag_quadratic) * node.vx
            total_drag_y = (drag_linear + drag_quadratic) * node.vy

            ax = (fx - total_drag_x) / mass
            ay = (fy - total_drag_y) / mass

            node.vx += ax * dt
            node.vy += ay * dt

            # Calm, intentional speed caps across both modes
            if not (has_active_focus and node.id == focused_node_id):
                cur_speed = math.sqrt(node.vx * node.vx + node.vy * node.vy)
                max_speed = 24.0 if has_active_focus else 20.0
                if cur_speed > max_speed:
                    scale = max_speed / cur_speed
                    node.vx *= scale
                    node.vy *= scale

            node.x += node.vx * dt
            node.y += node.vy * dt

        # 7. Soft Perimeter Buffer Margin Retention
        margin_pad_x = max(80.0, self.width * 0.04)
        margin_pad_y = max(60.0, self.height * 0.04)

        for node in nodes:
            if node.id == self.pinned_node_id:
                continue

            if node.x < margin_pad_x:
                node.x = margin_pad_x
                node.vx = max(0.0, node.vx)
            elif node.x > self.width - margin_pad_x:
                node.x = self.width - margin_pad_x
                node.vx = min(0.0, node.vx)

            if node.y < margin_pad_y:
                node.y = margin_pad_y
                node.vy = max(0.0, node.vy)
            elif node.y > self.height - margin_pad_y:
                node.y = self.height - margin_pad_y
                node.vy = min(0.0, node.vy)