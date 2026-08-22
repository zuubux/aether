"""
Aether Physics Engine - 2.5D Organic Force-Directed & Conformal Horizon Integrator
Handles multi-cluster galaxy dispersion, fluid splines, and wing companion slotting.
"""

import logging
import math

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
        spacing = 300.0
        total_width = (total - 1) * spacing
        start_x = (viewport_w / 2.0) - (total_width / 2.0)
        
        for i, nid in enumerate(node_ids):
            if nid not in self.staged_origins and nid in node_map:
                self.staged_origins[nid] = (node_map[nid].x, node_map[nid].y)
            self.staged_targets[nid] = (start_x + (i * spacing), shelf_y)

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

    def step(self, nodes: list[Node], edges: list[Edge], focused_node_id: int, hovered_node_id: int = 0, dt: float = 0.008,
             first_degree_set: set[int] | None = None,
             second_degree_set: set[int] | None = None,
             second_degree_parent: dict[int, int] | None = None,
             focal_weights: dict[int, float] | None = None) -> bool:
        """
        Advances the physics simulation by one tick.
        Returns True if the system is still active, False if it has settled and can sleep.
        """
        if not nodes:
            return False

        node_map = {n.id: n for n in nodes}
        has_active_focus = (focused_node_id > 0) and (focused_node_id in node_map)

        # Viewport-Aware Zoom/Aperture Center update
        wing_width = (self.viewport_w - self.focal_card_w) / 2.0
        if has_active_focus:
            self.center_x = (self.viewport_w - wing_width) / 2.0
        else:
            self.center_x = self.viewport_w / 2.0

        first_degree_set = first_degree_set or set()
        second_degree_set = second_degree_set or set()
        second_degree_parent = second_degree_parent or {}
        focal_weights = focal_weights or {}

        # 0. Reset all nodes to independent status at the start of the tick
        for node in nodes:
            node.clusterId = -1

        # 1. Structural Component & Centroid Resolution
        components = self._find_connected_components(nodes, edges)
        node_comp_map: dict[int, int] = {}
        comp_centroids: dict[int, tuple[float, float, int]] = {}

        for c_idx, comp in enumerate(components):
            # Exclude focused and docked wing nodes from the centroid calculation of background clusters
            if has_active_focus:
                c_nodes = [node_map[nid] for nid in comp if nid in node_map and nid != focused_node_id and nid not in first_degree_set and nid not in second_degree_set]
            else:
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

        # 3. Wing Target Allocation (Top 8 Companions Flanked Left / Right)
        wing_targets: dict[int, tuple[float, float]] = {}
        if has_active_focus:
            sorted_companions = sorted(list(first_degree_set), key=lambda nid: focal_weights.get(nid, 0.0), reverse=True)
            top_companions = sorted_companions[:8]
            
            left_wing = [nid for idx, nid in enumerate(top_companions) if idx % 2 == 0]
            right_wing = [nid for idx, nid in enumerate(top_companions) if idx % 2 != 0]

            def compute_wing_slots(c_ids: list[int], is_left: bool):
                total = len(c_ids)
                sign = -1.0 if is_left else 1.0
                # Bring wings closer to the card (was 480.0, putting them off-screen)
                target_x = self.center_x + sign * ((self.focal_card_w / 2.0) + 450.0) 
                for idx, nid in enumerate(c_ids):
                    y_offset = (idx - (total - 1) / 2.0) * 160.0 
                    wing_targets[nid] = (target_x, self.center_y + y_offset)

            compute_wing_slots(left_wing, is_left=True)
            compute_wing_slots(right_wing, is_left=False)

        # 4. Initialize Forces
        forces: dict[int, list[float]] = {n.id: [0.0, 0.0] for n in nodes}
        node_mass: dict[int, float] = {n.id: 1.0 for n in nodes}

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
        # Smoothly scales from 1.0x at 0.50 zoom up to ~2.7x at 2.20 zoom, clamping at 1.0x for low aperture
        geom_scale = 1.0 + max(0.0, (self.aperture - 0.50) * 1.0)
        
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
                
                # NEW: Check if these nodes are actively participating in the Focal Lens (1st OR 2nd degree)
                n1_focal = has_active_focus and (n1.id == focused_node_id or n1.id in first_degree_set or n1.id in second_degree_set)
                n2_focal = has_active_focus and (n2.id == focused_node_id or n2.id in first_degree_set or n2.id in second_degree_set)

                if has_active_focus:
                    if n1_focal != n2_focal:
                        # Ethereal: Active focal hierarchy completely ignores background nodes
                        min_sep = 0.0
                    elif n1.id == focused_node_id or n2.id == focused_node_id:
                        # Center card ignores its own wings
                        min_sep = 0.0
                    elif n1_focal and n2_focal:
                        # Wingmen and Satellites just need a tiny bit of personal space from each other
                        min_sep = 120.0
                    else:
                        organic_jitter = ((n1.id + n2.id) % 17) - 8.0 
                        min_sep = 42.0 + organic_jitter if same_cluster else 220.0
                else:
                    organic_jitter = ((n1.id + n2.id) % 17) - 8.0 
                    
                    # PROGRESSIVE SPREAD: 48px at 50% zoom, 123px at 100% zoom, 303px at 220% zoom
                    friend_base = 48.0 + max(0.0, (self.aperture - 0.50) * 150.0)
                    friend_sep = friend_base + organic_jitter
                    stranger_sep = 340.0 * geom_scale
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
            rest_len *= geom_scale
            displacement = dist - rest_len
            
            k_spring = 0.85 * min(1.0, e.weight)
            
            if e.edgeType.lower() == "temporal":
                k_spring = 0.0
            else:
                # Soften cross-desk temporal springs
                is_cross_desk_temporal = (e.edgeType == "temporal") and (
                    (n1.id in self.recent_node_ids) != (n2.id in self.recent_node_ids)
                )
                if is_cross_desk_temporal:
                    k_spring *= 0.10
                
            # --- FOCAL DECOUPLING FIX ---
            # Temporarily disable or zero out spring forces (k = 0) between docked wing nodes and non-focused peripheral nodes.
            if has_active_focus:
                n1_docked = (n1.id in first_degree_set or n1.id in second_degree_set)
                n2_docked = (n2.id in first_degree_set or n2.id in second_degree_set)
                n1_peripheral = (n1.id != focused_node_id and not n1_docked)
                n2_peripheral = (n2.id != focused_node_id and not n2_docked)
                
                if (n1_docked and n2_peripheral) or (n2_docked and n1_peripheral) or (n1.id == focused_node_id and n2_peripheral) or (n2.id == focused_node_id and n1_peripheral):
                    k_spring = 0.0

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
        
        # Maintain/Decay summoning targets
        active_summoning = {}
        for nid, (tpos, strength) in list(self.summoning_targets.items()):
            if strength > 0.01:
                # Slight decay so they settle nicely without oscillating forever
                active_summoning[nid] = (tpos, strength * 0.995)
        self.summoning_targets = active_summoning

        for node in nodes:
            # Override forces heavily for summoned nodes
            if node.id in self.summoning_targets:
                tpos, strength = self.summoning_targets[node.id]
                forces[node.id][0] += (tpos[0] - node.x) * strength * 12.0
                forces[node.id][1] += (tpos[1] - node.y) * strength * 12.0

            if node.id in self.staged_targets:
                tx, ty = self.staged_targets[node.id]
                forces[node.id][0] = (tx - node.x) * 15.0
                forces[node.id][1] = (ty - node.y) * 15.0
                continue

            dx = node.x - self.center_x
            dy = node.y - self.center_y
            dist_to_center = math.hypot(dx, dy) or 1.0

            if has_active_focus:
                if node.id == focused_node_id:
                    forces[node.id][0] += (self.center_x - node.x) * 18.0
                    forces[node.id][1] += (self.center_y - node.y) * 18.0

                elif node.id in first_degree_set or node.id in second_degree_parent:
                    viewport_center_x = self.viewport_w / 2.0
                    workbench_width = self.focal_card_w
                    workbench_x = (self.viewport_w - workbench_width) / 2.0
                    margin = 450.0
                    left_shelf_x = workbench_x - margin
                    right_shelf_x = workbench_x + workbench_width + margin

                    if node.x <= viewport_center_x:
                        target_x = left_shelf_x
                    else:
                        target_x = right_shelf_x

                    forces[node.id][0] += (target_x - node.x) * self.k_gutter_anchor

                    if node.id in wing_targets:
                        _, wy = wing_targets[node.id]
                        forces[node.id][1] += (wy - node.y) * self.k_gutter_anchor
                    elif node.id in second_degree_parent:
                        parent_node = node_map.get(second_degree_parent[node.id])
                        if parent_node:
                            y_spread = ((node.id % 5) - 2) * 140.0
                            target_sat_y = parent_node.y + y_spread
                            forces[node.id][1] += (target_sat_y - node.y) * self.k_satellite_drift
                    else:
                        forces[node.id][1] += (self.center_y - node.y) * self.k_horizon_anchor
                # Unfocused Background Clusters: Full Progressive Cohesion & Strict Boundary
                else:
                    c_idx = node_comp_map.get(node.id, -1)
                    if c_idx in comp_centroids:
                        ccx, ccy, count = comp_centroids[c_idx]
                        if count >= 3:
                            dx_c = ccx - node.x
                            dy_c = ccy - node.y
                            dist_c = math.hypot(dx_c, dy_c) or 1.0

                            # RESTORE FULL PROGRESSIVE COHESION: Prevents clusters from ripping apart
                            base_radius = (55.0 + (24.0 * math.sqrt(count))) * geom_scale
                            expected_radius = min(600.0 * geom_scale, base_radius)

                            if dist_c < expected_radius * 0.8:
                                k_pull = 1.25
                            else:
                                escape_dist = dist_c - (expected_radius * 0.8)
                                k_pull = min(12.0, 1.25 + (escape_dist * 0.25))

                            forces[node.id][0] += dx_c * k_pull
                            forces[node.id][1] += dy_c * k_pull

                    # Aspect & Card-Height Aware Boundary (Prevents cards hanging off the bottom)
                    bound_x = (self.viewport_w / 2.0) * 0.78
                    bound_y = (self.viewport_h / 2.0) * 0.65  # Padded to fit full card height

                    if abs(dx) > bound_x:
                        pull_ramp_x = abs(dx) - bound_x
                        sign_x = 1.0 if dx > 0 else -1.0
                        forces[node.id][0] -= sign_x * pull_ramp_x * 8.0

                    if abs(dy) > bound_y:
                        pull_ramp_y = abs(dy) - bound_y
                        sign_y = 1.0 if dy > 0 else -1.0
                        forces[node.id][1] -= sign_y * pull_ramp_y * 8.0

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

                # --- NEW WORKBENCH LOGIC START ---
                is_recent = node.id in self.recent_node_ids

                # 2. The Donut Hole (Softened for Recent Nodes)
                # Recent nodes get an inner working ring (380px) instead of the deep void (750px)
                void_radius = 380.0 if is_recent else 750.0
                if dist_to_center < void_radius:
                    # Exponential ramp makes the very center violently repulsive
                    ramp = ((void_radius - dist_to_center) / void_radius) ** 1.5
                    forces[node.id][0] += (dx / dist_to_center) * ramp * 3200.0
                    forces[node.id][1] += (dy / dist_to_center) * ramp * 3200.0

                # If it's a recent node drifting too far out, gently tug it to stay on the desk
                if is_recent and dist_to_center > 650.0:
                    desk_pull = (dist_to_center - 650.0) * 2.5
                    forces[node.id][0] -= (dx / dist_to_center) * desk_pull
                    forces[node.id][1] -= (dy / dist_to_center) * desk_pull

                # 3. Outer Viewport Containment Belt (Card-Height Aware)
                bound_x = (self.viewport_w / 2.0) * 0.78
                bound_y = (self.viewport_h / 2.0) * 0.65

                if abs(dx) > bound_x:
                    pull_ramp_x = abs(dx) - bound_x
                    sign_x = 1.0 if dx > 0 else -1.0
                    forces[node.id][0] -= sign_x * pull_ramp_x * 4.5
                
                if abs(dy) > bound_y:
                    pull_ramp_y = abs(dy) - bound_y
                    sign_y = 1.0 if dy > 0 else -1.0
                    forces[node.id][1] -= sign_y * pull_ramp_y * 4.5

                # 4. Progressive Intra-Cluster Cohesion (Aperture-Aware Membrane)
                c_idx = node_comp_map.get(node.id, -1)
                
                # NEW: Exempt recent nodes from being dragged back into the cluster
                if c_idx in comp_centroids and not is_recent:
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

        # --- Elastic Boundary Cushion (32px inner boundary zone) ---
        cushion_zone = 32.0
        k_cushion = 25.0
        for node in nodes:
            if has_active_focus and node.id == focused_node_id:
                continue
            if node.id in getattr(self, 'staged_targets', {}):
                continue

            # Left border
            if node.x < cushion_zone:
                penetration = cushion_zone - node.x
                forces[node.id][0] += k_cushion * (penetration ** 1.8)
            # Right border
            elif node.x > self.viewport_w - cushion_zone:
                penetration = node.x - (self.viewport_w - cushion_zone)
                forces[node.id][0] -= k_cushion * (penetration ** 1.8)

            # Top border
            if node.y < cushion_zone:
                penetration = cushion_zone - node.y
                forces[node.id][1] += k_cushion * (penetration ** 1.8)
            # Bottom border
            elif node.y > self.viewport_h - cushion_zone:
                penetration = node.y - (self.viewport_h - cushion_zone)
                forces[node.id][1] -= k_cushion * (penetration ** 1.8)

        # 9. Viscous Fluid Drag & Integration
        for node in nodes:
            if node.id in self.staged_targets:
                tx, ty = self.staged_targets[node.id]
                node.x = tx
                node.y = ty
                node.vx = 0.0
                node.vy = 0.0
                continue

            if has_active_focus and node.id == focused_node_id:
                node.vx = 0.0
                node.vy = 0.0
                node.x = self.center_x
                node.y = self.center_y
                continue

            # NEW: Freeze hovered node under mouse in ambient mode
            if not has_active_focus and node.id == hovered_node_id and node.id != self.pinned_node_id:
                node.vx = 0.0
                node.vy = 0.0
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
            max_speed = 340.0 if has_active_focus else 180.0
            if cur_speed > max_speed:
                scale = max_speed / cur_speed
                node.vx *= scale
                node.vy *= scale

            node.x += node.vx * dt
            node.y += node.vy * dt

        # Update depthZ for all nodes (lateral separation forces are already integrated into node.x / node.y)
        for node in nodes:
            if has_active_focus and node.id == focused_node_id:
                node.depthZ = 0.0
            else:
                normalized_y = max(0.0, min(1.0, 1.0 - (node.y / self.viewport_h)))
                is_wing_node = has_active_focus and (node.id in first_degree_set or node.id in second_degree_parent)
                if is_wing_node:
                    node.depthZ = normalized_y * 0.25
                else:
                    node.depthZ = normalized_y * (1.0 - node.focus * 0.5)

        # Kinetic Energy Cutoff
        total_velocity = sum(math.sqrt(n.vx**2 + n.vy**2) for n in nodes)
        if total_velocity < 0.01 * len(nodes):
            return False

        return True

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