"""
Plate Engine - Weight & Mass Calculation Subsystem
Calculates dynamic cognitive mass, recency decay, and topological centrality
for plate prioritizing and layout sizing based on Weaver's established decay math
and elastic density rules.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Sequence

from .models import PlateArchetype, PlateNodePayload, TemporalState


@dataclass(init=False)
class PlateWeightConfig:
    """
    Configuration parameters for plate cognitive mass calculations.
    """

    half_life_minutes: float = 25.0
    weight_temporal: float = 0.40
    weight_semantic: float = 0.40
    weight_topological: float = 0.20
    pin_override: bool = True
    pin_temporal_score: float = 1.0
    min_temporal_decay: float = 0.10
    max_temporal_decay: float = 1.00
    min_mass: float = 0.10
    max_mass: float = 5.00
    default_semantic_score: float = 0.50
    degree_saturation: float = 8.0
    archetype_base_mass: dict[PlateArchetype, float] = field(default_factory=dict)
    pinned_multiplier: float = 1.0
    user_placed_multiplier: float = 1.0

    def __init__(
        self,
        half_life_minutes: float = 25.0,
        weight_temporal: float = 0.40,
        weight_semantic: float = 0.40,
        weight_topological: float = 0.20,
        pin_override: bool = True,
        pin_temporal_score: float = 1.0,
        min_temporal_decay: float = 0.10,
        max_temporal_decay: float = 1.00,
        min_mass: float = 0.10,
        max_mass: float = 5.00,
        default_semantic_score: float = 0.50,
        degree_saturation: float = 8.0,
        archetype_base_mass: dict[PlateArchetype, float] | None = None,
        pinned_multiplier: float = 1.0,
        user_placed_multiplier: float = 1.0,
        *,
        t_half: float | None = None,
        t_half_minutes: float | None = None,
        recency_weight: float | None = None,
        temporal_weight: float | None = None,
        semantic_weight: float | None = None,
        topological_weight: float | None = None,
        pin_temporal_override: bool | None = None,
        recency_half_life_hours: float | None = None,
        **kwargs: Any,
    ) -> None:
        if t_half is not None:
            half_life_minutes = t_half
        elif t_half_minutes is not None:
            half_life_minutes = t_half_minutes
        elif recency_half_life_hours is not None:
            half_life_minutes = recency_half_life_hours * 60.0

        if temporal_weight is not None:
            weight_temporal = temporal_weight
        elif recency_weight is not None:
            weight_temporal = recency_weight

        if semantic_weight is not None:
            weight_semantic = semantic_weight

        if topological_weight is not None:
            weight_topological = topological_weight

        if pin_temporal_override is not None:
            pin_override = pin_temporal_override

        self.half_life_minutes = float(half_life_minutes)
        self.weight_temporal = float(weight_temporal)
        self.weight_semantic = float(weight_semantic)
        self.weight_topological = float(weight_topological)
        self.pin_override = bool(pin_override)
        self.pin_temporal_score = float(pin_temporal_score)
        self.min_temporal_decay = float(min_temporal_decay)
        self.max_temporal_decay = float(max_temporal_decay)
        self.min_mass = float(min_mass)
        self.max_mass = float(max_mass)
        self.default_semantic_score = float(default_semantic_score)
        self.degree_saturation = float(degree_saturation)
        self.pinned_multiplier = float(pinned_multiplier)
        self.user_placed_multiplier = float(user_placed_multiplier)

        if archetype_base_mass is not None:
            self.archetype_base_mass = dict(archetype_base_mass)
        else:
            self.archetype_base_mass = {
                PlateArchetype.IMAGE: 1.4,
                PlateArchetype.MEDIA: 1.5,
                PlateArchetype.MODEL: 1.4,
                PlateArchetype.DOCUMENT: 1.0,
                PlateArchetype.CODE: 1.0,
                PlateArchetype.DATA: 1.1,
                PlateArchetype.ARCHIVE: 0.8,
                PlateArchetype.UNKNOWN: 0.7,
            }

        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def t_half(self) -> float:
        return self.half_life_minutes

    @t_half.setter
    def t_half(self, val: float) -> None:
        self.half_life_minutes = val

    @property
    def t_half_minutes(self) -> float:
        return self.half_life_minutes

    @t_half_minutes.setter
    def t_half_minutes(self, val: float) -> None:
        self.half_life_minutes = val

    @property
    def recency_weight(self) -> float:
        return self.weight_temporal

    @recency_weight.setter
    def recency_weight(self, val: float) -> None:
        self.weight_temporal = val

    @property
    def temporal_weight(self) -> float:
        return self.weight_temporal

    @temporal_weight.setter
    def temporal_weight(self, val: float) -> None:
        self.weight_temporal = val

    @property
    def semantic_weight(self) -> float:
        return self.weight_semantic

    @semantic_weight.setter
    def semantic_weight(self, val: float) -> None:
        self.weight_semantic = val

    @property
    def topological_weight(self) -> float:
        return self.weight_topological

    @topological_weight.setter
    def topological_weight(self, val: float) -> None:
        self.weight_topological = val

    @property
    def pin_temporal_override(self) -> bool:
        return self.pin_override

    @pin_temporal_override.setter
    def pin_temporal_override(self, val: bool) -> None:
        self.pin_override = val


class PlateWeightCalculator:
    """
    Computes normalized Cognitive Mass combining temporal recency decay, user intent (pinning),
    sub-linear topological degree centrality, and archetype elastic density.
    """

    def __init__(self, config: PlateWeightConfig | None = None) -> None:
        self.config = config or PlateWeightConfig()

    def compute_recency_decay(
        self,
        last_interaction_epoch: float,
        now: float | None = None,
    ) -> float:
        """
        Computes an exponential half-life decay factor matching Weaver's formulation:
        W(t) = 2^(-delta_t / t_half), clamped between [min_temporal_decay, max_temporal_decay].
        """
        current_time = now if now is not None else time.time()
        delta_seconds = max(0.0, current_time - last_interaction_epoch)
        delta_minutes = delta_seconds / 60.0
        t_half = max(1e-6, self.config.half_life_minutes)
        decay = 2.0 ** (-delta_minutes / t_half)
        return max(self.config.min_temporal_decay, min(self.config.max_temporal_decay, decay))

    def compute_temporal_factor(
        self,
        plate: PlateNodePayload,
        now: float | None = None,
    ) -> float:
        """
        Calculates the temporal score component for a plate.
        
        If plate is pinned (checked via plate.temporal_state.is_pinned, plate.temporal.is_pinned,
        or plate.is_pinned), bypasses temporal decay and locks the score to 1.0 (or pin_temporal_score).
        Updates recency_score on plate temporal state in-place.
        """
        temporal_state = getattr(plate, "temporal_state", None) or getattr(plate, "temporal", None)
        is_pinned = (
            getattr(plate, "is_pinned", False)
            or (temporal_state is not None and getattr(temporal_state, "is_pinned", False))
        )

        if self.config.pin_override and is_pinned:
            score = self.config.pin_temporal_score
        else:
            current_time = now if now is not None else time.time()
            epoch = (
                getattr(temporal_state, "last_interaction_epoch", current_time)
                if temporal_state is not None
                else current_time
            )
            score = self.compute_recency_decay(epoch, current_time)

        if temporal_state is not None:
            temporal_state.recency_score = score
        if getattr(plate, "temporal", None) is not None:
            plate.temporal.recency_score = score

        return score

    def compute_degree_centrality(self, plate: PlateNodePayload) -> float:
        """
        Calculates sub-linear degree centrality from plate relationship edges.
        Uses logarithmic scaling: ln(1 + degree) / ln(1 + saturation), clamped to [0.0, 1.0].
        """
        relationships = getattr(plate, "relationships", None)
        if relationships is None:
            return 0.0

        edges = getattr(relationships, "edges", [])
        if edges:
            raw_degree = sum(float(getattr(e, "weight", 1.0)) for e in edges)
        else:
            neighbor_ids = getattr(relationships, "neighbor_ids", None)
            if neighbor_ids:
                raw_degree = float(len(neighbor_ids))
            else:
                inc = getattr(relationships, "incoming_count", 0)
                out = getattr(relationships, "outgoing_count", 0)
                raw_degree = float(inc + out)

        if raw_degree <= 0.0:
            return 0.0

        sat = max(1.0, self.config.degree_saturation)
        centrality = math.log1p(raw_degree) / math.log1p(sat)
        return max(0.0, min(1.0, centrality))

    def compute_centrality_factor(self, degree: int | float) -> float:
        """
        Legacy sub-linear degree centrality helper returning a scaling multiplier >= 1.0.
        Maintained for backwards compatibility.
        """
        if degree <= 0:
            return 1.0
        bonus = math.log1p(float(degree)) * 0.25
        max_bonus = getattr(self.config, "max_degree_bonus", 1.5)
        return min(max_bonus, 1.0 + bonus)

    def resolve_semantic_score(
        self,
        plate: PlateNodePayload,
        explicit_score: float | None = None,
    ) -> float:
        """
        Resolves the relevance / semantic intent component score in [0.0, 1.0].
        Prefers explicit override, then plate metadata, then semantic graph edges / neighbors,
        falling back to default_semantic_score.
        """
        if explicit_score is not None:
            return max(0.0, min(1.0, float(explicit_score)))

        metadata = getattr(plate, "metadata", {})
        if isinstance(metadata, dict):
            for key in ("relevance", "semantic_score", "semantic_intent", "relevance_score", "intent_score"):
                val = metadata.get(key)
                if val is not None:
                    try:
                        return max(0.0, min(1.0, float(val)))
                    except (ValueError, TypeError):
                        pass

        relationships = getattr(plate, "relationships", None)
        if relationships is not None:
            semantic_neighbors = getattr(relationships, "semantic_neighbors", [])
            if semantic_neighbors:
                scores = [float(s) for _, s in semantic_neighbors]
                if scores:
                    return max(0.0, min(1.0, max(scores)))

            edges = getattr(relationships, "edges", [])
            semantic_weights = [
                float(getattr(e, "weight", 1.0))
                for e in edges
                if getattr(e, "category", "") == "semantic" or getattr(e, "edge_type", "") == "semantic"
            ]
            if semantic_weights:
                return max(0.0, min(1.0, max(semantic_weights)))

        return max(0.0, min(1.0, self.config.default_semantic_score))

    def calculate_mass(
        self,
        plate: PlateNodePayload,
        semantic_score: float | None = None,
        now: float | None = None,
    ) -> float:
        """
        Calculates and returns aggregate Cognitive Mass for a single plate.
        
        Combines Recency/Temporal decay (0.40), Relevance/Semantic Intent (0.40),
        and Topological Degree Centrality (0.20) modulated by archetype elastic density.
        Updates plate.mass in-place.
        """
        # 1. Temporal score (with pin override)
        s_temporal = self.compute_temporal_factor(plate, now)

        # 2. Semantic intent / relevance score
        s_semantic = self.resolve_semantic_score(plate, semantic_score)

        # 3. Topological degree centrality
        s_topological = self.compute_degree_centrality(plate)

        # 4. Weighted combination
        w_t = self.config.weight_temporal
        w_s = self.config.weight_semantic
        w_d = self.config.weight_topological
        w_total = w_t + w_s + w_d
        if w_total > 0:
            composite = (w_t * s_temporal + w_s * s_semantic + w_d * s_topological) / w_total
        else:
            composite = 1.0

        # 5. Archetype elastic density footprint
        base_density = self.config.archetype_base_mass.get(plate.archetype, 1.0)
        mass = composite * base_density

        # 6. Intent multipliers
        temporal_state = getattr(plate, "temporal_state", None) or getattr(plate, "temporal", None)
        is_pinned = (
            getattr(plate, "is_pinned", False)
            or (temporal_state is not None and getattr(temporal_state, "is_pinned", False))
        )
        is_user_placed = (
            getattr(plate, "is_user_placed", False)
            or (temporal_state is not None and getattr(temporal_state, "is_user_placed", False))
        )

        if is_pinned and self.config.pinned_multiplier != 1.0:
            mass *= self.config.pinned_multiplier
        elif is_user_placed and self.config.user_placed_multiplier != 1.0:
            mass *= self.config.user_placed_multiplier

        # 7. Mass clamping & in-place assignment
        clamped_mass = max(self.config.min_mass, min(self.config.max_mass, mass))
        final_mass = round(clamped_mass, 4)
        plate.mass = final_mass
        return final_mass

    def calculate_plate_mass(
        self,
        plate: PlateNodePayload,
        now: float | None = None,
        semantic_score: float | None = None,
    ) -> float:
        """Alias for calculate_mass for backwards compatibility."""
        return self.calculate_mass(plate, semantic_score=semantic_score, now=now)

    def calculate_mass_batch(
        self,
        plates: Sequence[PlateNodePayload],
        semantic_scores: dict[int, float] | None = None,
        now: float | None = None,
        sort: bool = True,
        reverse: bool = True,
    ) -> list[PlateNodePayload]:
        """
        Updates plate mass in-place for a sequence of plates and returns
        the list, optionally sorted descending by Cognitive Mass.
        """
        current_time = now if now is not None else time.time()
        scores_map = semantic_scores or {}

        for p in plates:
            s_score = scores_map.get(p.node_id)
            self.calculate_mass(p, semantic_score=s_score, now=current_time)

        plate_list = list(plates)
        if sort:
            plate_list.sort(key=lambda p: p.mass, reverse=reverse)
        return plate_list

    def recalculate_batch(
        self,
        plates: Sequence[PlateNodePayload],
        now: float | None = None,
    ) -> None:
        """Recalculates mass for a batch of plates in-place."""
        self.calculate_mass_batch(plates, now=now, sort=False)
