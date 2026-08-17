"""
Aether Physics Engine - 2.5D Organic Force-Directed & Conformal Horizon Integrator
Handles multi-cluster galaxy dispersion, fluid splines, and wing companion slotting.
"""

import math
import logging
from typing import List, Dict, Tuple, Set, Optional

from models import Node, Edge

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
        self.custom_anchors: Dict[int, Tuple[float, float]] = {}
        self.recent_node_ids: List[int] = []

        # Smoothing & Geometry Cache
        self._smoothed_halos: Dict[str, dict] = {}
        self._horizon_bearings: Dict[int, float] = {}

        # Spring & Field Constants
        self.k_horizon_anchor: float = 9.5
        self.k_gutter_anchor: float = 8.5
        self.k_satellite_drift: float = 5.5

        self.box_bound_x: float = 0.0
        self.box_bound_y: float = 0.0
        self.soft_buffer: float = 120.0
        self.ideal_horizon_radius: float = 1200.0

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

    def _recalculate_horizons(self):
        self.box_bound_x = (self.focal_card_w / 2.0) + 520.0
        self.box_bound_y = (self.focal_card_h / 2.0) + 160.0
        self.soft_buffer = 120.0

        diag = math.sqrt(self.box_bound_x**2 + self.box_bound_y**2)
        self.ideal_horizon_radius = diag + (180.0 * max(0.50, self.aperture))

    def _get_conformal_horizon_radius(self, theta: float) -> float:
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        n = 2.8
        denom = (abs(cos_t) / (self.box_bound_x + 40.0)) ** n + (abs(sin_t) / (self.box_bound_y + 40.0)) ** n
        if denom <= 0:
            return self.ideal_horizon_radius
        return (1.0 / denom) ** (1.0 / n)

    def _find_connected_components(self, nodes: List[Node], edges: List[Edge]) -> List[Set[int]]:
        adj: Dict[int, Set[int]] = {n.id: set() for n in nodes}
        for e in edges:
            if e.edgeType.lower() != "temporal" and e.weight > 0.45:
                if e.sourceId in adj and e.targetId in adj:
                    adj[e.sourceId].add(e.targetId)
                    adj[e.targetId].add(e.sourceId)

        visited: Set[int] = set()
        components: List[Set[int]] = []

        for n in nodes:
            if n.id not in visited:
                comp: Set[int] = set()
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

    def step(self, nodes: List[Node], edges: List[Edge], focused_node_id: int, dt: float = 0.008):
        if not nodes:
            return

        node_map = {n.id: n for n in nodes}
        has_active_focus = (focused_node_id > 0) and (focused_node_id in node_map)

        # 0. Reset all nodes to independent status at the start of the tick
        for node in nodes:
            node.clusterId = -1

        # 1. Structural Component & Centroid Resolution
        components = self._find_connected_components(nodes, edges)
        node_comp_map: Dict[int, int] = {}
        comp_centroids: Dict[int, Tuple[float, float, int]] = {}

        for c_idx, comp in enumerate(components):
            c_nodes = [node_map[nid] for nid in comp if nid in node_map]
            
            # ONLY form a mathematical cluster if there are 3 or more nodes
            if len(c_nodes) >= 3:
                cx = sum(n.x for n in c_nodes) / len(c_nodes)
                cy = sum(n.y for n in c_nodes) / len(c_nodes)
                comp_centroids[c_idx] = (cx, cy, len(c_nodes))
                
                for nid in comp:
                    node_comp_map[nid] = c_idx
                    if nid in node_map:
                        node_map[nid].clusterId = c_idx

        # 2. Relational Hierarchy for Active Focus
        first_degree_set: Set[int] = set()
        second_degree_set: Set[int] = set()
        second_degree_parent: Dict[int, int] = {}
        focal_weights: Dict[int, float] = {}

        if has_active_focus:
            for e in edges:
                if e.sourceId == focused_node_id:
                    first_degree_set.add(e.targetId)
                    focal_weights[e.targetId] = max(focal_weights.get(e.targetId, 0.0), e.weight)
                elif e.targetId == focused_node_id:
                    first_degree_set.add(e.sourceId)
                    focal_weights[e.sourceId] = max(focal_weights.get(e.sourceId, 0.0), e.weight)

            for e in edges:
                if e.sourceId in first_degree_set and e.targetId != focused_node_id and e.targetId not in first_degree_set:
                    second_degree_set.add(e.targetId)
                    second_degree_parent[e.targetId] = e.sourceId
                elif e.targetId in first_degree_set and e.sourceId != focused_node_id and e.sourceId not in first_degree_set:
                    second_degree_set.add(e.sourceId)
                    second_degree_parent[e.sourceId] = e.targetId

        # 3. Wing Target Allocation (Top 4 Companions Flanked Left / Right)
        wing_targets: Dict[int, Tuple[float, float]] = {}
        if has_active_focus:
            sorted_companions = sorted(list(first_degree_set), key=lambda nid: focal_weights.get(nid, 0.0), reverse=True)
            top_companions = sorted_companions[:4]
            left_wing = [nid for idx, nid in enumerate(top_companions) if idx % 2 == 0]
            right_wing = [nid for idx, nid in enumerate(top_companions) if idx % 2 != 0]

            def compute_wing_slots(c_ids: List[int], is_left: bool):
                total = len(c_ids)
                sign = -1.0 if is_left else 1.0
                target_x = self.center_x + sign * ((self.focal_card_w / 2.0) + 480.0)
                for idx, nid in enumerate(c_ids):
                    y_offset = (idx - (total - 1) / 2.0) * 110.0
                    wing_targets[nid] = (target_x, self.center_y + y_offset)

            compute_wing_slots(left_wing, is_left=True)
            compute_wing_slots(right_wing, is_left=False)

        # 4. Initialize Forces
        forces: Dict[int, List[float]] = {n.id: [0.0, 0.0] for n in nodes}
        node_mass: Dict[int, float] = {n.id: 1.0 for n in nodes}

        # 5. Inter-Cluster Centroid Separation (Gentle Galaxy Drift)
        if not has_active_focus:
            comp_indices = list(comp_centroids.keys())
            for i in range(len(comp_indices)):
                c1_idx = comp_indices[i]
                c1_x, c1_y, count1 = comp_centroids[c1_idx]
                for j in range(i + 1, len(comp_indices)):
                    c2_idx = comp_indices[j]
                    c2_x, c2_y, count2 = comp_centroids[c2_idx]

                    cdx = c2_x - c1_x
                    cdy = c2_y - c1_y
                    cdist = math.hypot(cdx, cdy) or 1.0

                    min_cluster_sep = 500.0 + (math.sqrt(count1) + math.sqrt(count2)) * 40.0
                    if cdist < min_cluster_sep:
                        # Soft centroid nudge distributed lightly across group members
                        c_repulse = (min_cluster_sep - cdist) * 0.12
                        push_x = (cdx / cdist) * c_repulse
                        push_y = (cdy / cdist) * c_repulse

                        for nid in components[c1_idx]:
                            forces[nid][0] -= push_x / math.sqrt(count1)
                            forces[nid][1] -= push_y / math.sqrt(count1)
                        for nid in components[c2_idx]:
                            forces[nid][0] += push_x / math.sqrt(count2)
                            forces[nid][1] += push_y / math.sqrt(count2)

        # 6. Pairwise Node Repulsion (Aperture-Aware Physical Scaling)
        # Scales geometry from 1.0x (dots) up to ~2.8x (full cards) based on zoom
        geom_scale = 1.0 + max(0.0, min(1.8, (self.aperture - 0.35) * 2.4))
        
        node_list = list(nodes)
        num_nodes = len(node_list)
        for i in range(num_nodes):
            n1 = node_list[i]
            for j in range(i + 1, num_nodes):
                n2 = node_list[j]
                dx = n2.x - n1.x
                dy = n2.y - n1.y
                dist_sq = dx * dx + dy * dy
                dist = math.sqrt(dist_sq) or 1.0

                same_cluster = (node_comp_map.get(n1.id) == node_comp_map.get(n2.id)) and (node_comp_map.get(n1.id) is not None)

                if has_active_focus:
                    min_sep = 160.0 * (1.0 + max(0.0, geom_scale - 1.0) * 0.5)
                else:
                    # Inject organic noise (+/- 8px) so they don't form a perfect uniform grid
                    organic_jitter = ((n1.id + n2.id) % 17) - 8.0 
                    
                    # Dynamically expand to make room for pill and full-card geometry
                    friend_sep = (42.0 + organic_jitter) * geom_scale
                    stranger_sep = 340.0 * (1.0 + max(0.0, geom_scale - 1.0) * 0.6)
                    min_sep = friend_sep if same_cluster else stranger_sep

                if dist < min_sep:
                    repulse = (min_sep - dist) * 8.5
                    fx = (dx / dist) * repulse
                    fy = (dy / dist) * repulse
                    forces[n1.id][0] -= fx
                    forces[n1.id][1] -= fy
                    forces[n2.id][0] += fx
                    forces[n2.id][1] += fy

        # 7. Edge Spring Tension
        for e in edges:
            n1 = node_map.get(e.sourceId)
            n2 = node_map.get(e.targetId)
            if not n1 or not n2:
                continue

            dx = n2.x - n1.x
            dy = n2.y - n1.y
            dist = math.sqrt(dx * dx + dy * dy) or 1.0

            rest_len = 150.0 if e.edgeType == "explicit" else (200.0 if e.edgeType == "temporal" else 240.0)
            displacement = dist - rest_len
            k_spring = 0.85 * min(1.0, e.weight)

            spring_force = displacement * k_spring

            # Anti-Rubberband Clamp: Prevents springs from acting like steel cables across the void
            if not has_active_focus and spring_force > 150.0:
                spring_force = 150.0 + (spring_force - 150.0) * 0.05

            fx = (dx / dist) * spring_force
            fy = (dy / dist) * spring_force

            forces[n1.id][0] += fx
            forces[n1.id][1] += fy
            forces[n2.id][0] -= fx
            forces[n2.id][1] -= fy

        # 8. Horizon, Centroid Spring & Viewport Gravitational Anchor
        max_canvas_r = max(self.viewport_w, self.viewport_h) * 0.70

        for node in nodes:
            dx = node.x - self.center_x
            dy = node.y - self.center_y
            dist_to_center = math.hypot(dx, dy) or 1.0

            if has_active_focus:
                if node.id == focused_node_id:
                    forces[node.id][0] += (self.center_x - node.x) * 18.0
                    forces[node.id][1] += (self.center_y - node.y) * 18.0

                elif node.id in wing_targets:
                    wx, wy = wing_targets[node.id]
                    forces[node.id][0] += (wx - node.x) * self.k_gutter_anchor
                    forces[node.id][1] += (wy - node.y) * self.k_gutter_anchor

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
                        p_dx = parent_node.x - self.center_x
                        p_dy = parent_node.y - self.center_y
                        p_theta = math.atan2(p_dy, p_dx)

                        sat_span = 180.0 * math.pow(self.aperture, 1.2)
                        target_sat_x = parent_node.x + (math.cos(p_theta) * sat_span)
                        target_sat_y = parent_node.y + (math.sin(p_theta) * sat_span)

                        forces[node.id][0] += (target_sat_x - node.x) * self.k_satellite_drift
                        forces[node.id][1] += (target_sat_y - node.y) * self.k_satellite_drift

                # Unfocused Background Clusters: Stay Put with Moderate Cohesion
                else:
                    c_idx = node_comp_map.get(node.id, -1)
                    if c_idx in comp_centroids:
                        ccx, ccy, count = comp_centroids[c_idx]
                        if count >= 3:
                            forces[node.id][0] += (ccx - node.x) * 0.45
                            forces[node.id][1] += (ccy - node.y) * 0.45

            # Ambient Void Mode
            else:
                if node.id in self.custom_anchors:
                    ax, ay = self.custom_anchors[node.id]
                    forces[node.id][0] += (ax - node.x) * 4.0
                    forces[node.id][1] += (ay - node.y) * 4.0

                # 1. Break dead-center symmetry lock (so nodes don't get stuck perfectly at 0,0)
                if abs(dx) < 1.0 and abs(dy) < 1.0:
                    dx = 1.0 + (node.id % 5)
                    dy = 1.0 + (node.id % 7)
                    dist_to_center = math.hypot(dx, dy)

                # 2. The Donut Hole (Absolute Center Void)
                void_radius = 750.0
                if dist_to_center < void_radius:
                    # Exponential ramp makes the very center violently repulsive
                    ramp = ((void_radius - dist_to_center) / void_radius) ** 1.5
                    forces[node.id][0] += (dx / dist_to_center) * ramp * 3200.0
                    forces[node.id][1] += (dy / dist_to_center) * ramp * 3200.0

                # 3. Outer Viewport Containment Belt
                containment_radius = 1250.0
                if dist_to_center > containment_radius:
                    pull_ramp = dist_to_center - containment_radius
                    forces[node.id][0] -= (dx / dist_to_center) * pull_ramp * 3.5
                    forces[node.id][1] -= (dy / dist_to_center) * pull_ramp * 3.5

                # 4. Progressive Intra-Cluster Cohesion (Aperture-Aware Membrane)
                c_idx = node_comp_map.get(node.id, -1)
                if c_idx in comp_centroids:
                    ccx, ccy, count = comp_centroids[c_idx]
                    if count >= 3:
                        dx_c = ccx - node.x
                        dy_c = ccy - node.y
                        dist_c = math.hypot(dx_c, dy_c) or 1.0

                        # Generously expanded natural cluster radius
                        base_radius = (55.0 + (24.0 * math.sqrt(count))) * geom_scale
                        expected_radius = min(600.0 * geom_scale, base_radius)

                        if dist_c < expected_radius * 0.8:
                            k_pull = 1.25
                        else:
                            escape_dist = dist_c - (expected_radius * 0.8)
                            k_pull = min(12.0, 1.25 + (escape_dist * 0.25))

                        forces[node.id][0] += dx_c * k_pull
                        forces[node.id][1] += dy_c * k_pull

        # 9. Viscous Fluid Drag & Integration
        for node in nodes:
            if has_active_focus and node.id == focused_node_id:
                node.vx = 0.0
                node.vy = 0.0
                node.x = self.center_x
                node.y = self.center_y
                continue

            if node.id == self.pinned_node_id:
                node.vx = 0.0
                node.vy = 0.0
                if has_active_focus and node.id in first_degree_set:
                    self._horizon_bearings[node.id] = math.atan2(node.y - self.center_y, node.x - self.center_x)
                continue

            mass = node_mass.get(node.id, 1.0)
            fx, fy = forces[node.id]

            speed = math.sqrt(node.vx * node.vx + node.vy * node.vy)

            drag_linear = 5.2 if has_active_focus else 4.0
            drag_quadratic = 0.045 * speed

            total_drag_x = (drag_linear + drag_quadratic) * node.vx
            total_drag_y = (drag_linear + drag_quadratic) * node.vy

            ax = (fx - total_drag_x) / mass
            ay = (fy - total_drag_y) / mass

            node.vx += ax * dt
            node.vy += ay * dt

            cur_speed = math.sqrt(node.vx * node.vx + node.vy * node.vy)
            max_speed = 280.0 if has_active_focus else 180.0
            if cur_speed > max_speed:
                scale = max_speed / cur_speed
                node.vx *= scale
                node.vy *= scale

            node.x += node.vx * dt
            node.y += node.vy * dt

    def get_cluster_halos(self, nodes: List[Node], edges: List[Edge], focused_id: int) -> List[dict]:
        if not nodes:
            return []

        # Geometry scaling for visual halo expansion
        geom_scale = 1.0 + max(0.0, min(1.8, (self.aperture - 0.35) * 2.4))
        
        node_map = {n.id: n for n in nodes}
        components = self._find_connected_components(nodes, edges)
        halos = []
        eff_ap = max(0.35, min(1.0, math.pow(self.aperture, 0.7)))
        active_halo_ids: Set[str] = set()

        deg_map: Dict[int, int] = {n.id: 0 for n in nodes}
        for e in edges:
            if e.edgeType.lower() != "temporal":
                deg_map[e.sourceId] = deg_map.get(e.sourceId, 0) + 1
                deg_map[e.targetId] = deg_map.get(e.targetId, 0) + 1

        for comp_idx, comp_ids in enumerate(components):
            group = [node_map[nid] for nid in comp_ids if nid in node_map]
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

            # Minimum size clamp so small clusters don't shrink into tiny dots
            min_size = 140.0 * geom_scale
            target_w = max(min_size, target_w)
            target_h = max(min_size, target_h)

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

            # Color extraction
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

            is_focal_cluster = any(n.id == focused_id for n in group) and focused_id > 0

            halo_data = {
                "id": halo_id,
                "centerX": smooth_cx,
                "centerY": smooth_cy,
                "width": smooth_w,     # Replacing 'radius'
                "height": smooth_h,    # Replacing 'radius'
                "color": color_hex,
                "isFocalCluster": is_focal_cluster,
                "nodeCount": len(group),
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