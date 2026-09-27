"""
Plate Engine Package
Post-WIMP spatial layout, editorial bento allocation, canonical data models,
and temporal lifecycle progression.
"""

from .models import (
    PlateArchetype,
    PlateEdge,
    PlateEdgeCategory,
    PlateEdgeType,
    PlateGeometry,
    PlateNodePayload,
    TemporalState,
    NodeRelationships,
)
from .parser import (
    PlatePayloadParser,
    hydrate_relationships,
    parse_plate_edge,
    parse_plate_edges_batch,
    parse_plate_payload,
    parse_plate_payloads_batch,
)
from .weights import (
    PlateWeightCalculator,
    PlateWeightConfig,
)
from .bento import (
    BentoAllocation,
    BentoAllocator,
    BentoGridConfig,
)
from .lifecycle import (
    LifecycleBatchResult,
    PlateLifecycleConfig,
    PlateLifecycleManager,
    PlateLifecycleTier,
)

__version__ = "0.1.0"

__all__ = [
    # Models & Enums
    "PlateArchetype",
    "PlateEdgeCategory",
    "PlateEdgeType",
    "PlateEdge",
    "TemporalState",
    "NodeRelationships",
    "PlateGeometry",
    "PlateNodePayload",
    # Ingestion & Parsing
    "PlatePayloadParser",
    "parse_plate_payload",
    "parse_plate_payloads_batch",
    "parse_plate_edge",
    "parse_plate_edges_batch",
    "hydrate_relationships",
    # Weights & Sizing
    "PlateWeightConfig",
    "PlateWeightCalculator",
    # Bento Layout
    "BentoGridConfig",
    "BentoAllocation",
    "BentoAllocator",
    # Lifecycle Management
    "PlateLifecycleTier",
    "PlateLifecycleConfig",
    "PlateLifecycleManager",
    "LifecycleBatchResult",
]

