"""
Plate Engine - Bento Grid Allocation Subsystem
Translates plate payloads, archetypes, and cognitive mass into harmonious,
editorial bento grid geometries and spatial slot allocations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import PlateArchetype, PlateGeometry, PlateNodePayload


@dataclass(slots=True)
class BentoGridConfig:
    """
    Layout configuration for viewport-aware bento grid calculations.
    """
    viewport_width: float = 1920.0
    viewport_height: float = 1080.0
    columns: int = 12
    gutter: float = 24.0
    margin_x: float = 48.0
    margin_y: float = 48.0
    base_row_height: float = 120.0


@dataclass(slots=True)
class BentoAllocation:
    """
    Resolved geometric slot allocation for an individual plate.
    """
    node_id: int
    col_start: int
    col_span: int
    row_start: int
    row_span: int
    x: float
    y: float
    width: float
    height: float


class BentoAllocator:
    """
    Allocates plates into balanced bento grid configurations based on cognitive mass,
    archetype footprint needs, and viewport bounds.
    """

    def __init__(self, config: BentoGridConfig | None = None) -> None:
        self.config = config or BentoGridConfig()

    def determine_spans(self, plate: PlateNodePayload) -> tuple[int, int]:
        """
        Determines appropriate (col_span, row_span) for a plate given its archetype and mass.
        """
        mass = plate.mass
        arch = plate.archetype

        # Default standard 12-column subdivisions
        if mass >= 3.0:
            # Focal hero plate
            if arch.is_visual:
                return (6, 4)
            return (6, 3)
        elif mass >= 2.0:
            # Significant companion plate
            if arch.is_visual:
                return (4, 3)
            return (4, 2)
        elif mass >= 1.2:
            # Standard active plate
            if arch == PlateArchetype.MEDIA or arch == PlateArchetype.IMAGE:
                return (3, 3)
            return (3, 2)
        else:
            # Compact / peripheral plate
            return (2, 2)

    def allocate(
        self,
        plates: Sequence[PlateNodePayload],
    ) -> list[BentoAllocation]:
        """
        Performs grid placement packing plates in order of importance (mass).
        Updates plate.geometry in-place and returns allocation records.
        """
        if not plates:
            return []

        # Sort plates descending by mass
        sorted_plates = sorted(plates, key=lambda p: p.mass, reverse=True)

        cols = self.config.columns
        gutter = self.config.gutter
        margin_x = self.config.margin_x
        margin_y = self.config.margin_y
        row_h = self.config.base_row_height

        # Usable width for columns
        usable_width = self.config.viewport_width - (2.0 * margin_x)
        col_width = (usable_width - ((cols - 1) * gutter)) / cols

        # Simple 2D occupancy grid tracking (col, row)
        occupied: set[tuple[int, int]] = set()
        allocations: list[BentoAllocation] = []

        def is_available(c_start: int, r_start: int, c_span: int, r_span: int) -> bool:
            if c_start + c_span > cols:
                return False
            for r in range(r_start, r_start + r_span):
                for c in range(c_start, c_start + c_span):
                    if (c, r) in occupied:
                        return False
            return True

        def mark_occupied(c_start: int, r_start: int, c_span: int, r_span: int) -> None:
            for r in range(r_start, r_start + r_span):
                for c in range(c_start, c_start + c_span):
                    occupied.add((c, r))

        for plate in sorted_plates:
            c_span, r_span = self.determine_spans(plate)
            # Ensure span fits grid width
            c_span = min(cols, max(1, c_span))

            placed = False
            r_candidate = 0
            while not placed:
                for c_candidate in range(cols - c_span + 1):
                    if is_available(c_candidate, r_candidate, c_span, r_span):
                        mark_occupied(c_candidate, r_candidate, c_span, r_span)

                        # Calculate pixel geometry
                        px_x = margin_x + c_candidate * (col_width + gutter)
                        px_y = margin_y + r_candidate * (row_h + gutter)
                        px_w = c_span * col_width + (c_span - 1) * gutter
                        px_h = r_span * row_h + (r_span - 1) * gutter

                        # Update plate geometry
                        plate.geometry.x = round(px_x, 2)
                        plate.geometry.y = round(px_y, 2)
                        plate.geometry.width = round(px_w, 2)
                        plate.geometry.height = round(px_h, 2)
                        plate.geometry.col_span = c_span
                        plate.geometry.row_span = r_span

                        alloc = BentoAllocation(
                            node_id=plate.node_id,
                            col_start=c_candidate,
                            col_span=c_span,
                            row_start=r_candidate,
                            row_span=r_span,
                            x=px_x,
                            y=px_y,
                            width=px_w,
                            height=px_h,
                        )
                        allocations.append(alloc)
                        placed = True
                        break
                r_candidate += 1

        return allocations
