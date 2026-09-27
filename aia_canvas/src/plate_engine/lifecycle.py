"""
Plate Engine - 5-Tier Plate Lifecycle Subsystem
Manages temporal decay, inactivity progression (ACTIVE -> WING -> SUMMARY -> MICRO -> RAIL),
pin protection locks, manual size override timeouts, and workspace desktop sweeps.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence

from .models import PlateArchetype, PlateNodePayload


class PlateLifecycleTier(str, Enum):
    """
    Five-tier lifecycle hierarchy for interactive plates in the Aether Canvas.
    """
    ACTIVE = "ACTIVE"       # Hero / Focus active plate
    WING = "WING"           # Standard active / default spawn plate
    SUMMARY = "SUMMARY"     # 30+ min idle AI summary cell
    MICRO = "MICRO"         # 45+ min extended idle pre-rail micro-tile
    RAIL = "RAIL"           # 60+ min 0Hz stack rail pill

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.value.upper() == other.strip().upper()
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def _missing_(cls, value: object) -> PlateLifecycleTier | None:
        if isinstance(value, str):
            val_norm = value.strip().upper()
            for member in cls:
                if member.name == val_norm or member.value == val_norm:
                    return member
        return None

    @classmethod
    def from_str(cls, val: str | PlateLifecycleTier | None) -> PlateLifecycleTier:
        """
        Safely resolves a string or member to a PlateLifecycleTier enum.
        """
        if isinstance(val, cls):
            return val
        if not val:
            return cls.WING

        norm = str(val).strip().upper()
        mapping: dict[str, PlateLifecycleTier] = {
            "ACTIVE": cls.ACTIVE,
            "HERO": cls.ACTIVE,
            "FOCUS": cls.ACTIVE,
            "WING": cls.WING,
            "STANDARD": cls.WING,
            "DEFAULT": cls.WING,
            "SUMMARY": cls.SUMMARY,
            "MICRO": cls.MICRO,
            "RAIL": cls.RAIL,
            "DOCK": cls.RAIL,
            "STACK": cls.RAIL,
        }
        return mapping.get(norm, cls.WING)

    @property
    def is_active(self) -> bool:
        return self == PlateLifecycleTier.ACTIVE

    @property
    def is_wing(self) -> bool:
        return self == PlateLifecycleTier.WING

    @property
    def is_summary(self) -> bool:
        return self == PlateLifecycleTier.SUMMARY

    @property
    def is_micro(self) -> bool:
        return self == PlateLifecycleTier.MICRO

    @property
    def is_rail(self) -> bool:
        return self == PlateLifecycleTier.RAIL


DEFAULT_ARCHETYPE_DIMENSIONS: dict[PlateArchetype, tuple[float, float]] = {
    PlateArchetype.DOCUMENT: (440.0, 280.0),
    PlateArchetype.CODE: (480.0, 320.0),
    PlateArchetype.IMAGE: (400.0, 400.0),
    PlateArchetype.MEDIA: (480.0, 360.0),
    PlateArchetype.DATA: (440.0, 300.0),
    PlateArchetype.ARCHIVE: (380.0, 240.0),
    PlateArchetype.MODEL: (420.0, 420.0),
    PlateArchetype.UNKNOWN: (400.0, 260.0),
}

DEFAULT_ARCHETYPE_SPANS: dict[PlateArchetype, tuple[int, int]] = {
    PlateArchetype.DOCUMENT: (3, 2),
    PlateArchetype.CODE: (3, 2),
    PlateArchetype.IMAGE: (3, 3),
    PlateArchetype.MEDIA: (3, 3),
    PlateArchetype.DATA: (3, 2),
    PlateArchetype.ARCHIVE: (2, 2),
    PlateArchetype.MODEL: (3, 3),
    PlateArchetype.UNKNOWN: (3, 2),
}


@dataclass(slots=True)
class PlateLifecycleConfig:
    """
    Temporal decay thresholds and configuration for the Plate lifecycle manager.
    All temporal durations are expressed in minutes.
    """
    manual_override_timeout_mins: float = 20.0  # Time before manual size overrides revert to WING default
    summary_threshold_mins: float = 30.0        # Time before shifting to SUMMARY tier
    micro_threshold_mins: float = 45.0          # Time before shifting to MICRO tier
    rail_threshold_mins: float = 60.0           # Time before eviction to RAIL tier
    archetype_default_dimensions: dict[PlateArchetype, tuple[float, float]] = field(
        default_factory=lambda: dict(DEFAULT_ARCHETYPE_DIMENSIONS)
    )


class LifecycleBatchResult(dict[int, PlateLifecycleTier]):
    """
    Convenience result mapping (node_id -> PlateLifecycleTier) supporting index and list property access.
    """
    def __init__(
        self,
        mapping: dict[int, PlateLifecycleTier],
        tiers: list[PlateLifecycleTier],
        plates: list[Any],
    ) -> None:
        super().__init__(mapping)
        self._tiers = tiers
        self._plates = plates

    @property
    def tiers(self) -> list[PlateLifecycleTier]:
        return self._tiers

    @property
    def plates(self) -> list[Any]:
        return self._plates

    def __getitem__(self, key: Any) -> PlateLifecycleTier:
        if isinstance(key, int) and key not in self and 0 <= key < len(self._tiers):
            return self._tiers[key]
        return super().__getitem__(key)


class PlateLifecycleManager:
    """
    Authoritative lifecycle coordinator for Plates on the Aether Canvas.
    Evaluates temporal inactivity decay, enforces pin protection guards,
    reverts expired manual resize overrides, and executes desktop sweeps.
    """

    def __init__(self, config: PlateLifecycleConfig | None = None) -> None:
        self.config = config or PlateLifecycleConfig()

    def is_pinned(self, plate: Any) -> bool:
        """
        Returns True if plate is pinned either via temporal state, direct attribute, or metadata.
        """
        temporal = getattr(plate, "temporal_state", None) or getattr(plate, "temporal", None)
        if temporal is not None and getattr(temporal, "is_pinned", False):
            return True
        if getattr(plate, "is_pinned", False):
            return True
        meta = getattr(plate, "metadata", None)
        if isinstance(meta, dict) and (meta.get("is_pinned") or meta.get("isPinned")):
            return True
        return False

    def has_manual_size_override(self, plate: Any) -> bool:
        """
        Determines whether the plate carries an active manual size/dimension override.
        """
        for attr in (
            "is_manually_resized",
            "has_size_override",
            "manual_override",
            "is_size_overridden",
            "has_manual_override",
        ):
            if getattr(plate, attr, False):
                return True

        meta = getattr(plate, "metadata", None)
        if isinstance(meta, dict):
            for key in (
                "manual_override",
                "has_manual_override",
                "is_manually_resized",
                "user_size_override",
                "manual_resize",
                "size_override",
                "custom_dimensions",
            ):
                if meta.get(key):
                    return True

        geom = getattr(plate, "geometry", None)
        if geom is not None:
            for attr in ("is_manual_override", "has_override", "manual_override"):
                if getattr(geom, attr, False):
                    return True

        return False

    def clear_manual_size_override(self, plate: Any) -> None:
        """
        Clears all manual size override flags on a plate.
        """
        for attr in (
            "is_manually_resized",
            "has_size_override",
            "manual_override",
            "is_size_overridden",
            "has_manual_override",
        ):
            if hasattr(plate, attr):
                try:
                    setattr(plate, attr, False)
                except (AttributeError, TypeError):
                    pass

        meta = getattr(plate, "metadata", None)
        if isinstance(meta, dict):
            for key in (
                "manual_override",
                "has_manual_override",
                "is_manually_resized",
                "user_size_override",
                "manual_resize",
                "size_override",
                "custom_dimensions",
            ):
                meta.pop(key, None)

        geom = getattr(plate, "geometry", None)
        if geom is not None:
            for attr in ("is_manual_override", "has_override", "manual_override"):
                if hasattr(geom, attr):
                    try:
                        setattr(geom, attr, False)
                    except (AttributeError, TypeError):
                        pass

    def mark_manual_size_override(
        self,
        plate: Any,
        width: float | None = None,
        height: float | None = None,
    ) -> None:
        """
        Marks a plate as having an active user size override, optionally setting custom dimensions.
        """
        if width is not None and hasattr(plate, "geometry") and plate.geometry is not None:
            plate.geometry.width = float(width)
        if height is not None and hasattr(plate, "geometry") and plate.geometry is not None:
            plate.geometry.height = float(height)

        try:
            plate.is_manually_resized = True
        except (AttributeError, TypeError):
            pass

        meta = getattr(plate, "metadata", None)
        if isinstance(meta, dict):
            meta["manual_override"] = True
            meta["is_manually_resized"] = True


    def reset_to_archetype_default(self, plate: Any) -> None:
        """
        Resets plate geometry dimensions and spans back to archetype WING defaults.
        """
        arch = getattr(plate, "archetype", PlateArchetype.DOCUMENT)
        if not isinstance(arch, PlateArchetype):
            try:
                arch = PlateArchetype.from_str(str(arch))
            except Exception:
                arch = PlateArchetype.DOCUMENT

        default_dims = self.config.archetype_default_dimensions.get(arch) or DEFAULT_ARCHETYPE_DIMENSIONS.get(
            arch, (440.0, 280.0)
        )
        default_spans = DEFAULT_ARCHETYPE_SPANS.get(arch, (3, 2))

        geom = getattr(plate, "geometry", None)
        if geom is not None:
            geom.width = default_dims[0]
            geom.height = default_dims[1]
            if hasattr(geom, "col_span"):
                geom.col_span = default_spans[0]
            if hasattr(geom, "row_span"):
                geom.row_span = default_spans[1]

        if hasattr(plate, "width"):
            try:
                plate.width = default_dims[0]
            except (AttributeError, TypeError):
                pass
        if hasattr(plate, "height"):
            try:
                plate.height = default_dims[1]
            except (AttributeError, TypeError):
                pass

    def get_plate_tier(self, plate: Any) -> PlateLifecycleTier:
        """Returns the current lifecycle tier assigned to a plate."""
        return self._get_current_tier(plate)

    def set_plate_tier(self, plate: Any, tier: PlateLifecycleTier | str) -> None:
        """Explicitly sets a plate's lifecycle tier."""
        resolved = PlateLifecycleTier.from_str(tier)
        self._apply_tier(plate, resolved)

    def _get_last_interaction(self, plate: Any, default_time: float) -> float:
        temporal = getattr(plate, "temporal_state", None) or getattr(plate, "temporal", None)
        if temporal is not None and hasattr(temporal, "last_interaction_epoch"):
            epoch = float(temporal.last_interaction_epoch)
            if epoch > 0:
                return epoch

        if hasattr(plate, "last_interaction_epoch"):
            epoch = float(plate.last_interaction_epoch)
            if epoch > 0:
                return epoch

        meta = getattr(plate, "metadata", None)
        if isinstance(meta, dict):
            raw = meta.get("last_interaction_epoch") or meta.get("lastInteractionEpoch")
            if raw is not None:
                try:
                    epoch = float(raw)
                    if epoch > 0:
                        return epoch
                except (ValueError, TypeError):
                    pass

        return default_time

    def _get_current_tier(self, plate: Any) -> PlateLifecycleTier:
        raw = getattr(plate, "lifecycle_tier", None)
        if raw is not None:
            return PlateLifecycleTier.from_str(raw)

        meta = getattr(plate, "metadata", None)
        if isinstance(meta, dict):
            raw = meta.get("lifecycle_tier") or meta.get("tier")
            if raw is not None:
                try:
                    return PlateLifecycleTier.from_str(raw)
                except Exception:
                    pass

        return PlateLifecycleTier.WING

    def _apply_tier(self, plate: Any, tier: PlateLifecycleTier) -> None:
        try:
            plate.lifecycle_tier = tier
        except (AttributeError, TypeError):
            pass

        meta = getattr(plate, "metadata", None)
        if isinstance(meta, dict):
            meta["lifecycle_tier"] = tier.value

        geom = getattr(plate, "geometry", None)
        if geom is not None:
            tier_float_map = {
                PlateLifecycleTier.ACTIVE: 1.0,
                PlateLifecycleTier.WING: 2.0,
                PlateLifecycleTier.SUMMARY: 3.0,
                PlateLifecycleTier.MICRO: 4.0,
                PlateLifecycleTier.RAIL: 4.5,
            }
            zone_map = {
                PlateLifecycleTier.ACTIVE: 0,
                PlateLifecycleTier.WING: 0,
                PlateLifecycleTier.SUMMARY: 1,
                PlateLifecycleTier.MICRO: 2,
                PlateLifecycleTier.RAIL: 2,
            }
            if hasattr(geom, "tier"):
                try:
                    geom.tier = tier_float_map.get(tier, geom.tier)
                except (AttributeError, TypeError):
                    pass
            if hasattr(geom, "zone"):
                try:
                    geom.zone = zone_map.get(tier, geom.zone)
                except (AttributeError, TypeError):
                    pass


    def evaluate_tier(self, plate: Any, now: float | None = None) -> PlateLifecycleTier:
        """
        Evaluates a plate's last interaction delta against temporal thresholds.

        1. Pin Guard: If plate.temporal_state.is_pinned or plate.is_pinned is True,
           locks tier to WING (or ACTIVE if already active) and ignores decay thresholds.
        2. Manual Override Expiry: If delta >= manual_override_timeout_mins and a user
           size override exists, clears the override, resets dimensions to archetype default,
           and ensures tier is WING.
        3. Standard Progression: Transitions to SUMMARY, MICRO, and RAIL based on inactivity deltas.
        """
        current_time = float(now) if now is not None else time.time()
        last_interaction = self._get_last_interaction(plate, default_time=current_time)
        delta_seconds = max(0.0, current_time - last_interaction)
        delta_mins = delta_seconds / 60.0

        current_tier = self._get_current_tier(plate)

        # 1. Pin Guard
        if self.is_pinned(plate):
            locked_tier = (
                PlateLifecycleTier.ACTIVE
                if current_tier == PlateLifecycleTier.ACTIVE
                else PlateLifecycleTier.WING
            )
            self._apply_tier(plate, locked_tier)
            return locked_tier

        # 2. Manual Override Expiry
        override_cleared = False
        if delta_mins >= self.config.manual_override_timeout_mins:
            if self.has_manual_size_override(plate):
                self.clear_manual_size_override(plate)
                self.reset_to_archetype_default(plate)
                override_cleared = True

        # 3. Standard Progression
        if delta_mins >= self.config.rail_threshold_mins:
            tier = PlateLifecycleTier.RAIL
        elif delta_mins >= self.config.micro_threshold_mins:
            tier = PlateLifecycleTier.MICRO
        elif delta_mins >= self.config.summary_threshold_mins:
            tier = PlateLifecycleTier.SUMMARY
        elif delta_mins >= self.config.manual_override_timeout_mins or override_cleared:
            tier = PlateLifecycleTier.WING
        else:
            # Under manual_override_timeout_mins (< 20 mins)
            tier = (
                PlateLifecycleTier.ACTIVE
                if current_tier == PlateLifecycleTier.ACTIVE
                else PlateLifecycleTier.WING
            )

        self._apply_tier(plate, tier)
        return tier

    def desktop_sweep(self, plates: Sequence[Any]) -> list[Any]:
        """
        Global sweep method that forces all plates (bypassing pin guards)
        into the RAIL tier to clean the workspace.
        """
        swept: list[Any] = []
        for plate in plates:
            if self.has_manual_size_override(plate):
                self.clear_manual_size_override(plate)
                self.reset_to_archetype_default(plate)
            self._apply_tier(plate, PlateLifecycleTier.RAIL)
            swept.append(plate)
        return swept

    def evaluate_lifecycle_batch(
        self,
        plates: Sequence[Any],
        now: float | None = None,
    ) -> LifecycleBatchResult:
        """
        Batch evaluation helper updating lifecycle tiers across a sequence of plates.
        Updates each plate in-place and returns a LifecycleBatchResult mapping.
        """
        current_time = float(now) if now is not None else time.time()
        mapping: dict[int, PlateLifecycleTier] = {}
        tiers: list[PlateLifecycleTier] = []
        plate_list: list[Any] = []

        for idx, plate in enumerate(plates):
            tier = self.evaluate_tier(plate, now=current_time)
            tiers.append(tier)
            plate_list.append(plate)

            node_id = getattr(plate, "node_id", None)
            if node_id is None and hasattr(plate, "id"):
                node_id = getattr(plate, "id")
            if node_id is None:
                node_id = idx

            try:
                mapping[int(node_id)] = tier
            except (ValueError, TypeError):
                mapping[idx] = tier

        return LifecycleBatchResult(mapping=mapping, tiers=tiers, plates=plate_list)

