"""
Plate Canvas Controller Implementation
Forwarding module re-exporting PlateCanvasController from plate_controller.
"""

from .plate_controller import (  # noqa: F401
    PlateCanvasController,
    parse_plate_payload,
)

__all__ = ["PlateCanvasController", "parse_plate_payload"]
