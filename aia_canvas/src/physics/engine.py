"""
Aether Canvas - Physics Engine
Topological cluster encapsulation, non-linear covalent spring mechanics,
working memory desk queue with horseshoe staging arc, and zero-mass temporal tendrils.
"""

import math
import time
from typing import Dict, List, Optional, Tuple, Set
from models import Node, Edge


class PhysicsEngine:
    def __init__(self):
        # Viewport Dimensions (Dual-Monitor Canvas)
        self.width = 3840.0
        self.height = 2160.0
        self.center_x = self.width / 2.0
        self.center_y = self.height / 2.0

        # Cognitive Aperture
        self.aperture = 1.0

        # Workbench Footprint
        self.focal_card_w = 1600.0
        self.focal_card_h = 1000.0
        self._recalculate_horizons()

        # Viscous Spring Constants
        self.k_horizon_anchor = 7.5
        self.k_satellite_drift = 4.0

        # Bearing & Anchor State
        self.pinned_node_id: Optional[int] = None
        self.custom_anchors: Dict[int, Tuple[float, float]] = {}
        self._horizon_bearings: Dict[int, float] = {}
        self._last_focused_id: int = -1
        self._start_time = time.time()

        # Working Memory Session Queue (LRU Stack)
        self.recent_node_ids: List[int] = []

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

    def set_recent_nodes(self, recent_ids: List[int]):
        self.recent_node_ids = recent_ids

    def _recalculate_horizons(self):
        self.box_bound_x = (self.focal_card_w / 2.0) + 180.0
        self.box_bound_y = (self.focal_card_h / 2.0) + 135.0
        self.soft_buffer = 105.0

        diag = math.sqrt(self.box_bound_x**2 + self.box_bound_y**2)
        self.ideal_horizon_radius = diag + (180.0 * max(0.50, self.aperture))

    def pin_node(self, node_id: int):
        self.pinned_node_id = node_id
        if node_id in self.custom_anchors:
            del self.custom_anchors[node_id]

    def unpin_node(self):
        self.pinned_node_id = None

    def set_custom_anchor(self, node_id: int, x: float, y: float):
        self.custom_anchors[node_id] = (x, y)
        self._horizon_bearings[node_id] = math.atan2(y - self.center_y, x - self.center_x)

    def _find_connected_components(self, nodes: List[Node], edges: List[Edge]) -> List[List[int]]:
        """
        Partition graph strictly on structural relationships:
        - Explicit [[WikiLinks]]: 100% Covalent Bond
        - Semantic Embeddings: High confidence (Weight >= 0.72)
        - Temporal: Excluded (0% Clustering influence)
        """
        adj: Dict[int, Set[int]] = {n.id: set() for n in nodes}
        for e in edges:
            e_type = e.edgeType.lower()
            if e_type == "explicit" or (e_type == "semantic" and e.weight >= 0.72):
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
        active_halo_ids: Set[str] = set()

        deg_map: Dict[int, int] = {n.id: 0 for n in nodes}
        for e in edges:
            if e.edgeType.lower() != "temporal":
                deg_map[e.sourceId] = deg_map.get(e.sourceId, 0) + 1
                deg_map[e.targetId] = deg_map.get(e.targetId, 0) + 1

        for comp_idx, comp_ids in enumerate(components):
            group = [node_map[nid] for nid in comp_ids if nid in node_map]
            # Dyad Rule: Suppress halos for components under 3 nodes
            if len(group) < 3:
                continue

            halo_id = f"component_{comp_idx}"
            active_halo_ids.add(halo_id)

            seed_node = max(group, key=lambda n: deg_map.get(n.id, 0))

            prev = self._smoothed_halos.get(halo_id)
            if prev is None:
                curr_cx = seed_node.x
                curr_cy = seed_node.y
                curr_r = 45.0
            else:
                curr_cx = prev["centerX"]
                curr_cy = prev["centerY"]
                curr_r = prev["radius"]

            capture_margin = max(45.0, curr_r * 1.15)
            absorbed_nodes = [
                n for n in group 
                if math.hypot(n.x - curr_cx, n.y - curr_cy) <= capture_margin
            ]
            if not absorbed_nodes:
                absorbed_nodes = [seed_node]

            target_cx = sum(n.x for n in absorbed_nodes) / len(absorbed_nodes)
            target_cy = sum(n.y for n in absorbed_nodes) / len(absorbed_nodes)

            absorbed_dists = [math.hypot(n.x - target_cx, n.y - target_cy) for n in absorbed_nodes]
            max_absorbed_d = max(absorbed_dists) if absorbed_dists else 35.0
            base_r = 40.0 + (16.0 * math.sqrt(len(absorbed_nodes)))
            target_radius = max(base_r, min(360.0, max_absorbed_d + (28.0 * eff_ap)))

            smooth_cx = curr_cx + (target_cx - curr_cx) * 0.12
            smooth_cy = curr_cy + (target_cy - curr_cy) * 0.12
            smooth_r = curr_r + (target_radius - curr_r) * 0.08

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
                "radius": smooth_r,
                "color": color_hex,
                "isFocalCluster": is_focal_cluster,
                "nodeCount": len(absorbed_nodes)
            }

            self._smoothed_halos[halo_id] = halo_data
            halos.append(halo_data)

        # Elastic Cellular Buffering between Distinct Halos
        for i in range(len(halos)):
            for j in range(i + 1, len(halos)):
                h1 = halos[i]
                h2 = halos[j]
                dx = h2["centerX"] - h1["centerX"]
                dy = h2["centerY"] - h1["centerY"]
                dist = math.hypot(dx, dy) or 1.0
                min_dist = h1["radius"] + h2["radius"] + 40.0

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

    def _get_edge_mechanics(self, edge: Edge, has_active_focus: bool, desk_pass_nodes: Dict[int, float]) -> Tuple[float, float, bool]:
        """Returns: (spring_k, rest_span, is_nonlinear_ramp)"""
        edge_type = edge.edgeType.lower()
        w = max(0.05, min(1.0, edge.weight))
        eff_ap = math.pow(self.aperture, 1.4)

        # Zero-Mass Temporal Links: Never exert physical spring forces
        if edge_type == "temporal":
            return 0.0, 400.0, False

        # Check for working memory desk pass attenuation
        src_desk_w = desk_pass_nodes.get(edge.sourceId, 0.0)
        tgt_desk_w = desk_pass_nodes.get(edge.targetId, 0.0)
        max_desk_w = max(src_desk_w, tgt_desk_w)

        # Explicit [[WikiLinks]]: High covalent tension with non-linear stretch ramp
        if edge_type == "explicit":
            k = 13.0 if not has_active_focus else 10.5
            span = 145.0 * eff_ap
            is_ramp = True
        elif edge_type == "semantic":
            if w >= 0.72:
                k = 7.5 * math.pow(w, 1.2)
                span = 190.0 * eff_ap
            else:
                k = 3.2 * max(0.35, w)
                span = 260.0 * eff_ap
            is_ramp = False
        else:
            k = 4.0
            span = 220.0 * eff_ap
            is_ramp = False

        # Slack Tether: Attenuate spring pull if one of the nodes is parked on the desk
        if max_desk_w > 0.0 and not has_active_focus:
            k *= (1.0 - 0.85 * max_desk_w)
            span += (600.0 * max_desk_w)
            is_ramp = False

        return k, max(30.0, span), is_ramp

    def _get_node_radial_band(self, node: Node, has_focus: bool, focused_id: int) -> Tuple[float, float, float]:
        dx = node.x - self.center_x
        dy = node.y - self.center_y
        dist = math.sqrt(dx * dx + dy * dy)

        if has_focus and node.id == focused_id:
            return (self.focal_card_w / 2.0), (self.focal_card_h / 2.0), 3.0

        aperture_scale = max(0.28, min(1.0, math.pow(self.aperture, 0.8)))

        if dist < (self.ideal_horizon_radius + 180.0):
            return (150.0 * aperture_scale), (65.0 * aperture_scale), 1.0
        else:
            return (105.0 * aperture_scale), (35.0 * aperture_scale), 0.40

    def step(self, nodes: List[Node], edges: List[Edge], focused_node_id: int, dt: float = 0.008):
        if not nodes:
            return

        node_map: Dict[int, Node] = {n.id: n for n in nodes}
        forces: Dict[int, List[float]] = {n.id: [0.0, 0.0] for n in nodes}
        elapsed = time.time() - self._start_time
        has_active_focus = (focused_node_id > 0 and focused_node_id in node_map)

        # 1. Structural Component & Centroid Mapping
        components = self._find_connected_components(nodes, edges)
        node_comp_map: Dict[int, int] = {}
        comp_centroids: Dict[int, Tuple[float, float, int]] = {}

        for c_idx, c_ids in enumerate(components):
            # Only assign valid cluster IDs to clusters of 3+ nodes
            assigned_cluster_id = c_idx if len(c_ids) >= 3 else -1
            
            c_nodes = [node_map[nid] for nid in c_ids if nid in node_map]
            if len(c_ids) >= 3 and c_nodes:
                cx = sum(n.x for n in c_nodes) / len(c_nodes)
                cy = sum(n.y for n in c_nodes) / len(c_nodes)
                comp_centroids[c_idx] = (cx, cy, len(c_nodes))
                
            for nid in c_ids:
                node_comp_map[nid] = c_idx
                if nid in node_map:
                    node_map[nid].clusterId = assigned_cluster_id

        # 2. Working Memory Desk Queue & Staging Arc Slots
        # Capacity throttles with aperture zoom and screen width (Max 5)
        max_desk_slots = max(2, min(5, round(5.0 * min(1.0, self.aperture) * (self.width / 2560.0))))
        active_desk_ids = [nid for nid in self.recent_node_ids if nid in node_map and nid != focused_node_id][:max_desk_slots]
        num_desk = len(active_desk_ids)

        desk_pass_nodes: Dict[int, float] = {}   # node_id -> desk_weight in [0.6, 1.0]
        desk_slot_targets: Dict[int, Tuple[float, float]] = {}

        if num_desk > 0:
            # Elliptical Horseshoe Tray below the focal center
            arc_rx = 450.0 * min(1.0, math.pow(self.aperture, 0.8))
            arc_ry = 260.0 * min(1.0, math.pow(self.aperture, 0.8))
            delta_theta = 0.38  # ~21 degrees per slot separation

            for idx, nid in enumerate(active_desk_ids):
                weight = 1.0 - (idx / float(max_desk_slots)) * 0.35
                desk_pass_nodes[nid] = weight

                # Inverted arc hanging below workbench
                slot_offset = (idx - (num_desk - 1) / 2.0) * delta_theta
                slot_x = self.center_x - math.sin(slot_offset) * arc_rx
                slot_y = self.center_y + math.cos(slot_offset) * arc_ry + 60.0
                desk_slot_targets[nid] = (slot_x, slot_y)

        node_mass: Dict[int, float] = {}
        for n in nodes:
            deg = sum(1 for e in edges if e.sourceId == n.id or e.targetId == n.id)
            node_mass[n.id] = 1.0 + (0.45 * deg)

        # 3. Focus Transition & Horizon Bearing Latching
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
        aperture_rep_mod = math.pow(self.aperture, 1.2)

        # 4. Decoupled Repulsion: Universal Box Separation vs Cluster Barriers
        for i in range(num_nodes):
            n1 = nodes[i]
            if has_active_focus and n1.id == focused_node_id:
                continue

            hw1, hh1, rep_mult1 = self._get_node_radial_band(n1, has_active_focus, focused_node_id)
            c1 = node_comp_map.get(n1.id, -1)

            for j in range(i + 1, num_nodes):
                n2 = nodes[j]
                if has_active_focus and n2.id == focused_node_id:
                    continue

                hw2, hh2, rep_mult2 = self._get_node_radial_band(n2, has_active_focus, focused_node_id)
                c2 = node_comp_map.get(n2.id, -2)
                is_same_component = (c1 == c2 and c1 >= 0)

                dx = n2.x - n1.x
                dy = n2.y - n1.y
                abs_dx = abs(dx)
                abs_dy = abs(dy)

                req_sep_x = hw1 + hw2 + (24.0 * aperture_rep_mod)
                req_sep_y = hh1 + hh2 + (18.0 * aperture_rep_mod)

                overlap_x = req_sep_x - abs_dx
                overlap_y = req_sep_y - abs_dy

                # Box Non-Overlap Push (Applies universally for legibility)
                if overlap_x > 0.0 and overlap_y > 0.0:
                    dist = math.sqrt(dx * dx + dy * dy) + 0.1
                    dir_x = (dx / dist) if dist > 0.1 else 1.0
                    dir_y = (dy / dist) if dist > 0.1 else 0.0

                    penetration = min(overlap_x / req_sep_x, overlap_y / req_sep_y)
                    box_push = penetration * 1500.0 * max(rep_mult1, rep_mult2)

                    forces[n1.id][0] -= dir_x * box_push
                    forces[n1.id][1] -= dir_y * box_push
                    forces[n2.id][0] += dir_x * box_push
                    forces[n2.id][1] += dir_y * box_push

                # Inter-Component Coulomb Repulsion (Strictly between different clusters)
                elif not is_same_component:
                    dist_sq = (dx * dx) + (dy * dy * 2.0) + 400.0
                    dist = math.sqrt(dist_sq)
                    ambient_charge = 260000.0 * min(rep_mult1, rep_mult2) * aperture_rep_mod
                    rep_force = ambient_charge / dist_sq

                    fx = (dx / dist) * rep_force
                    fy = (dy / dist) * rep_force

                    forces[n1.id][0] -= fx
                    forces[n1.id][1] -= fy
                    forces[n2.id][0] += fx
                    forces[n2.id][1] += fy

        # 5. Tendril Elasticity with Slack Tether Attenuation
        for edge in edges:
            src = node_map.get(edge.sourceId)
            dst = node_map.get(edge.targetId)
            if not src or not dst:
                continue

            if has_active_focus and (edge.sourceId == focused_node_id or edge.targetId == focused_node_id):
                continue

            spring_k, target_span, is_nonlinear = self._get_edge_mechanics(edge, has_active_focus, desk_pass_nodes)
            if spring_k <= 0.0:
                continue

            dx = dst.x - src.x
            dy = dst.y - src.y
            dist = math.sqrt(dx * dx + dy * dy) + 0.1
            delta = dist - target_span

            if delta > 0.0:
                stretch_ramp = (1.0 + (delta / 150.0)) if is_nonlinear else min(2.0, 1.0 + (delta / 400.0))
                spring_force = delta * spring_k * stretch_ramp
            else:
                spring_force = delta * spring_k

            fx = (dx / dist) * spring_force
            fy = (dy / dist) * spring_force

            forces[src.id][0] += fx
            forces[src.id][1] += fy
            forces[dst.id][0] -= fx
            forces[dst.id][1] -= fy

        # 6. Ambient Void, Desk Staging Slots, and Intra-Cluster Cohesion
        soft_hull_x = self.box_bound_x + self.soft_buffer
        soft_hull_y = self.box_bound_y + self.soft_buffer

        for node in nodes:
            if has_active_focus and node.id == focused_node_id:
                node.x = self.center_x
                node.y = self.center_y
                node.vx = 0.0
                node.vy = 0.0
                continue

            dx = node.x - self.center_x
            dy = node.y - self.center_y
            abs_dx = abs(dx)
            abs_dy = abs(dy)
            dist_to_center = math.sqrt(dx * dx + dy * dy) + 0.1

            if has_active_focus:
                if node.id in first_degree_set:
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
                        sat_span = 200.0 * math.pow(self.aperture, 1.2)
                        target_sat_x = parent_node.x + (math.cos(p_theta) * sat_span)
                        target_sat_y = parent_node.y + (math.sin(p_theta) * sat_span)

                        forces[node.id][0] += (target_sat_x - node.x) * self.k_satellite_drift
                        forces[node.id][1] += (target_sat_y - node.y) * self.k_satellite_drift

                else:
                    if abs_dx < soft_hull_x and abs_dy < soft_hull_y:
                        pen_x = max(0.0, soft_hull_x - abs_dx) / self.soft_buffer
                        pen_y = max(0.0, soft_hull_y - abs_dy) / self.soft_buffer
                        ramp = min(1.0, max(pen_x, pen_y))

                        dir_x = (dx / dist_to_center) if dist_to_center > 1.0 else 1.0
                        dir_y = (dy / dist_to_center) if dist_to_center > 1.0 else 0.0

                        forces[node.id][0] += dir_x * ramp * 600.0
                        forces[node.id][1] += dir_y * ramp * 600.0

            else:
                # AMBIENT MODE: Working Memory Desk Slot vs Central Void Shove
                if node.id in desk_slot_targets:
                    slot_x, slot_y = desk_slot_targets[node.id]
                    desk_w = desk_pass_nodes.get(node.id, 1.0)
                    forces[node.id][0] += (slot_x - node.x) * (6.5 * desk_w)
                    forces[node.id][1] += (slot_y - node.y) * (6.5 * desk_w)

                else:
                    # Standard Ambient Void Clearing Field
                    void_radius_x = 1000.0
                    void_radius_y = 675.0
                    normalized_dist = math.sqrt((dx / void_radius_x)**2 + (dy / void_radius_y)**2)

                    if normalized_dist < 1.0:
                        push_intensity = (1.0 - normalized_dist) * 750.0
                        dir_x = (dx / dist_to_center) if dist_to_center > 1.0 else 1.0
                        dir_y = (dy / dist_to_center) if dist_to_center > 1.0 else 0.0

                        forces[node.id][0] += dir_x * push_intensity
                        forces[node.id][1] += dir_y * push_intensity

                    # Ambient Landscape Orbit
                    ideal_ring_x = 1500.0
                    ideal_ring_y = 900.0
                    current_ring_dist = math.sqrt((dx / ideal_ring_x)**2 + (dy / ideal_ring_y)**2)
                    ring_delta = 1.0 - current_ring_dist
                    forces[node.id][0] += (dx / dist_to_center) * ring_delta * 12.0
                    forces[node.id][1] += (dy / dist_to_center) * ring_delta * 12.0

                    # Intra-Cluster Centroid Cohesion
                    c_idx = node_comp_map.get(node.id, -1)
                    if c_idx in comp_centroids:
                        ccx, ccy, count = comp_centroids[c_idx]
                        if count >= 3:
                            forces[node.id][0] += (ccx - node.x) * 1.8
                            forces[node.id][1] += (ccy - node.y) * 1.8

            if node.id in self.custom_anchors:
                c_x, c_y = self.custom_anchors[node.id]
                forces[node.id][0] += (c_x - node.x) * 40.0
                forces[node.id][1] += (c_y - node.y) * 40.0

            # Harmonic Biological Respiration
            phase = node.id * 1.618033
            drift_x = math.sin(elapsed * 0.22 + phase) + (0.35 * math.sin(elapsed * 0.10 + phase * 2.1))
            drift_y = math.cos(elapsed * 0.18 + phase * 1.3) + (0.35 * math.cos(elapsed * 0.08 + phase * 0.7))

            drift_amp = (20.0 if has_active_focus else 16.0) * math.pow(self.aperture, 0.7)
            forces[node.id][0] += drift_x * drift_amp
            forces[node.id][1] += drift_y * (drift_amp * 0.75)

        # 7. Stokes Fluid Drag & Velocity Limits
        for node in nodes:
            if has_active_focus and node.id == focused_node_id:
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
            drag_linear = 8.5 if has_active_focus else 5.5
            drag_quadratic = 0.045 * speed

            total_drag_x = (drag_linear + drag_quadratic) * node.vx
            total_drag_y = (drag_linear + drag_quadratic) * node.vy

            ax = (fx - total_drag_x) / mass
            ay = (fy - total_drag_y) / mass

            node.vx += ax * dt
            node.vy += ay * dt

            cur_speed = math.sqrt(node.vx * node.vx + node.vy * node.vy)
            max_speed = 35.0 if has_active_focus else 28.0
            if cur_speed > max_speed:
                scale = max_speed / cur_speed
                node.vx *= scale
                node.vy *= scale

            node.x += node.vx * dt
            node.y += node.vy * dt

        # 8. Perimeter Buffer Retention
        margin_pad_x = max(80.0, self.width * 0.04)
        margin_pad_y = max(60.0, self.height * 0.04)

        for node in nodes:
            if node.id == self.pinned_node_id or (has_active_focus and node.id == focused_node_id):
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