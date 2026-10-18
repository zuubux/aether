"""
Plate Engine - Bento Grid Allocation Subsystem
Translates plate payloads, archetypes, and cognitive mass into harmonious,
editorial bento grid geometries and spatial slot allocations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import PlateArchetype, PlateGeometry, PlateNodePayload


TARGET_PLATE_WIDTH: float = 650.0
MAX_STAGE_CAPACITY: int = 6


def compute_stage_capacity(stage_width: float) -> int:
    """Number of unpinned plates the stage can hold at ~650px per plate (min 1, max 6)."""
    return max(1, min(MAX_STAGE_CAPACITY, int(float(stage_width) // TARGET_PLATE_WIDTH)))


# Layout ratios (all geometry derives from the stage viewport; no pixel constants)
ENVELOPE_HEIGHT_RATIO: float = 0.72        # working height share for a single row of plates
ENVELOPE_HEIGHT_RATIO_MULTI: float = 0.88  # working height share when plates wrap to extra rows
MAX_PLATES_PER_ROW: int = 4
ROW_SPAN_MIN_RATIO: float = 0.70           # active row spans 70% .. 88% of stage width
ROW_SPAN_MAX_RATIO: float = 0.88
MEDIA_MAX_WIDTH_RATIO: float = 0.45
MEDIA_ASPECT: float = 16.0 / 9.0
COMPACT_SNIPPET_BYTES: int = 200
MIN_PLATE_RATIO: float = 0.15              # minimum legible plate share of its row width
MIN_PLATE_HEIGHT_RATIO: float = 0.185      # minimum legible row height share of stage height (~200px on a 1080px stage)
MAX_PLATE_HEIGHT_RATIO: float = 0.88       # maximum row height share of stage height for a user drag

WEIGHT_TABULAR: float = 1.3
WEIGHT_READING: float = 1.0
WEIGHT_COMPACT: float = 0.8

_TABULAR_EXTS = frozenset({"csv", "tsv", "xlsx", "xls", "table"})
_MEDIA_EXTS = frozenset({"video", "mkv", "mp4", "mov", "webm", "image", "png", "jpg", "jpeg", "webp", "gif"})


@dataclass(slots=True)
class BentoGridConfig:
    """
    Layout configuration for viewport-aware bento calculations. Every spatial quantity
    is a ratio of the stage viewport.
    """
    viewport_width: float = 1920.0
    viewport_height: float = 1080.0
    columns: int = 12
    gutter_ratio: float = 0.016  # of min(stage width, stage height)


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


def _plate_ext(plate: PlateNodePayload) -> str:
    return (plate.extension or "").lower().lstrip(".")


def _is_media(plate: PlateNodePayload) -> bool:
    return plate.archetype in (PlateArchetype.IMAGE, PlateArchetype.MEDIA) or _plate_ext(plate) in _MEDIA_EXTS


def plate_weight(plate: PlateNodePayload) -> float:
    """Relative width weight from content archetype, payload size and cognitive mass."""
    if plate.is_preview:
        return WEIGHT_READING  # fixed footprint so swapping preview content never shifts neighbours
    ext = _plate_ext(plate)
    if plate.archetype == PlateArchetype.DATA and ext not in ("json", "yaml", "yml", "toml", "xml", "ini", "env") or ext in _TABULAR_EXTS:
        base = WEIGHT_TABULAR
    else:
        size = plate.size_bytes or len((plate.snippet or "").encode("utf-8"))
        base = WEIGHT_COMPACT if 0 < size < COMPACT_SNIPPET_BYTES else WEIGHT_READING
    mass_factor = max(0.9, min(1.3, 1.0 + 0.1 * (plate.mass - 1.0)))
    return base * mass_factor


def _distribute_widths(
    weights: Sequence[float], caps: Sequence[float], total: float,
) -> list[float]:
    """Splits `total` proportionally to weights, pinning plates at their cap and redistributing the surplus."""
    n = len(weights)
    widths = [0.0] * n
    free = set(range(n))
    remaining = total
    while free:
        wsum = sum(weights[i] for i in free)
        over = [i for i in free if remaining * weights[i] / wsum > caps[i]]
        if not over:
            for i in free:
                widths[i] = remaining * weights[i] / wsum
            break
        for i in over:
            widths[i] = caps[i]
            remaining -= caps[i]
            free.discard(i)
    return widths


class BentoAllocator:
    """
    Allocates plates into archetype-weighted rows that use the stage's vertical working
    envelope. Geometry derives purely from viewport ratios and relative column weights.
    """

    def __init__(self, config: BentoGridConfig | None = None) -> None:
        self.config = config or BentoGridConfig()
        # User-driven column weights (gutter dragging) that supersede archetype weights
        self.weight_overrides: dict[int, float] = {}
        # User-driven per-plate heights (corner dragging) as ratios of stage height; each applies to its plate only
        self.height_overrides: dict[int, float] = {}
        # Left-anchored row extents keyed by the row's LAST plate: (left edge, summed plate widths), both ratios
        # of stage width. Set when the last plate's right edge is dragged outward; replaces row centring.
        self.row_anchors: dict[int, tuple[float, float]] = {}

    def _gutter(self) -> float:
        return max(1.0, min(self.config.viewport_width, self.config.viewport_height) * self.config.gutter_ratio)

    def _row_override(self, row: Sequence[PlateNodePayload]) -> float | None:
        """Pixel height demanded by the tallest height override in the row (None when no plate is overridden)."""
        ratios = [self.height_overrides[p.node_id] for p in row if p.node_id in self.height_overrides]
        return max(ratios) * self.config.viewport_height if ratios else None

    def _resolve_heights(
        self, rows: Sequence[Sequence[PlateNodePayload]], gutter: float,
    ) -> tuple[list[float], list[list[float]], bool]:
        """
        Resolves per-plate heights and the row bands that stack them. A plate uses its own override or
        its row's default height; a row band is its tallest plate, so side-by-side plates share a top
        baseline but end at their own bottoms. Rows with an override keep their demanded band, auto
        rows share what is left of the stage (never more than their default envelope share). The flag
        reports overflow: the stack exceeds the stage or auto rows were squeezed below MIN_PLATE_HEIGHT_RATIO.
        """
        vh = self.config.viewport_height
        count = len(rows)
        envelope = vh * (ENVELOPE_HEIGHT_RATIO if count == 1 else ENVELOPE_HEIGHT_RATIO_MULTI)
        default_h = max(1.0, (envelope - (count - 1) * gutter) / count)
        gutters = (count - 1) * gutter
        own: list[list[float | None]] = [
            [self.height_overrides[p.node_id] * vh if p.node_id in self.height_overrides else None for p in r]
            for r in rows
        ]
        fixed: list[float | None] = []
        for heights in own:
            if all(h is None for h in heights):
                fixed.append(None)
            else:
                fixed.append(max(default_h if h is None else h for h in heights))
        fixed_sum = sum(f for f in fixed if f is not None)
        autos = sum(1 for f in fixed if f is None)
        auto_h = max(1.0, min(default_h, (vh - gutters - fixed_sum) / autos)) if autos else 0.0
        overflow = (autos > 0 and auto_h < vh * MIN_PLATE_HEIGHT_RATIO - 1e-6) or fixed_sum + gutters > vh + 1e-6
        bands = [auto_h if f is None else f for f in fixed]
        plate_heights = [
            [band if f is None else (default_h if h is None else h) for h in heights]
            for band, f, heights in zip(bands, fixed, own)
        ]
        return bands, plate_heights, overflow

    def _row_heights(self, rows: Sequence[Sequence[PlateNodePayload]], gutter: float) -> tuple[list[float], bool]:
        """Row bands (tallest plate per row) and the overflow flag."""
        bands, _, overflow = self._resolve_heights(rows, gutter)
        return bands, overflow

    def rows_overflow(self, plates: Sequence[PlateNodePayload]) -> bool:
        """True when the current row heights do not fit the visible stage."""
        rows = self._split_rows(plates)
        return bool(rows) and self._row_heights(rows, self._gutter())[1]

    def adjust_height(self, plates: Sequence[PlateNodePayload], node_id: int, delta_ratio: float) -> bool:
        """
        Grows (or shrinks) ONLY the target plate by `delta_ratio` of stage height, clamped between
        MIN_PLATE_HEIGHT_RATIO and MAX_PLATE_HEIGHT_RATIO. Row neighbours keep their own heights.
        Rows are not re-fitted here; see rows_overflow/fit_height.
        """
        rows = self._split_rows(plates)
        if not rows:
            return False
        _, plate_heights, _ = self._resolve_heights(rows, self._gutter())
        vh = self.config.viewport_height
        for row, heights in zip(rows, plate_heights):
            for p, height in zip(row, heights):
                if p.node_id == node_id:
                    self.height_overrides[node_id] = max(
                        MIN_PLATE_HEIGHT_RATIO, min(MAX_PLATE_HEIGHT_RATIO, height / vh + delta_ratio))
                    return True
        return False

    def fit_height(self, plates: Sequence[PlateNodePayload], node_id: int) -> None:
        """Caps the target row's height so the stack fits the stage (other rows keep their share or floor)."""
        rows = self._split_rows(plates)
        gutter = self._gutter()
        vh = self.config.viewport_height
        floor_h = vh * MIN_PLATE_HEIGHT_RATIO
        others = 0.0
        target: Sequence[PlateNodePayload] = ()
        for row in rows:
            if node_id in [p.node_id for p in row]:
                target = row
                continue
            override = self._row_override(row)
            others += floor_h if override is None else override
        if not target:
            return
        max_ratio = max(MIN_PLATE_HEIGHT_RATIO, min(MAX_PLATE_HEIGHT_RATIO, (vh - (len(rows) - 1) * gutter - others) / vh))
        if node_id in self.height_overrides:
            self.height_overrides[node_id] = min(self.height_overrides[node_id], max_ratio)

    def _weight(self, plate: PlateNodePayload) -> float:
        return self.weight_overrides.get(plate.node_id, plate_weight(plate))

    @staticmethod
    def _split_rows(plates: Sequence[PlateNodePayload]) -> list[list[PlateNodePayload]]:
        """Mass-ordered, balanced row split (at most MAX_PLATES_PER_ROW plates per row)."""
        sorted_plates = sorted(plates, key=lambda p: (p.is_preview, -p.mass))
        n = len(sorted_plates)
        if n == 0:
            return []
        row_count = -(-n // MAX_PLATES_PER_ROW)
        base, extra = divmod(n, row_count)
        rows: list[list[PlateNodePayload]] = []
        idx = 0
        for r in range(row_count):
            k = base + (1 if r < extra else 0)
            rows.append(sorted_plates[idx:idx + k])
            idx += k
        return rows

    def _row_frame(
        self, row: Sequence[PlateNodePayload], heights: Sequence[float], gutter: float,
    ) -> tuple[list[float], float]:
        """Plate widths and left edge of a row: left-anchored when the last plate was dragged, else centred."""
        vw = self.config.viewport_width
        k = len(row)
        anchor = self.row_anchors.get(row[-1].node_id)
        if anchor:
            left, avail = anchor[0] * vw, anchor[1] * vw
        else:
            span_ratio = min(ROW_SPAN_MAX_RATIO, ROW_SPAN_MIN_RATIO + 0.06 * (k - 1))
            left, avail = None, max(float(k), vw * span_ratio - (k - 1) * gutter)
        weights = [self._weight(p) for p in row]
        caps = [
            min(vw * MEDIA_MAX_WIDTH_RATIO, h * MEDIA_ASPECT) if (_is_media(p) and not p.is_preview) else float("inf")
            for p, h in zip(row, heights)
        ]
        widths = _distribute_widths(weights, caps, avail)
        if left is None:
            left = (vw - (sum(widths) + (k - 1) * gutter)) / 2.0
        return widths, left

    def _expand_last(
        self, row: Sequence[PlateNodePayload], heights: Sequence[float], gutter: float,
        delta_ratio: float, min_ratio: float,
    ) -> float:
        """
        Moves the row's right edge by `delta_ratio` of stage width with the left edge anchored. Growth is
        limited by the stage's right margin (symmetric to ROW_SPAN_MAX_RATIO); shrinking is floored at
        `min_ratio` of the row. Other plates keep their widths. Returns the growth left over after the
        margin was reached (to be taken from the left neighbour), or 0.0.
        """
        vw = self.config.viewport_width
        k = len(row)
        widths, left = self._row_frame(row, heights, gutter)
        row_w = sum(widths)
        grow = delta_ratio * vw
        max_right = vw * (1.0 - (1.0 - ROW_SPAN_MAX_RATIO) / 2.0)
        if grow > 0.0:
            take = max(0.0, min(grow, max_right - (left + row_w + (k - 1) * gutter)))
        else:
            take = min(0.0, max(grow, min_ratio * row_w - widths[-1]))
        if take != 0.0:
            widths[-1] += take
            for p, w in zip(row, widths):
                self.weight_overrides[p.node_id] = w / vw
            self.row_anchors[row[-1].node_id] = (left / vw, sum(widths) / vw)
        return (grow - take) / sum(widths) if grow > take else 0.0

    def adjust_weight(
        self, plates: Sequence[PlateNodePayload], node_id: int, delta_ratio: float,
        min_ratio: float = MIN_PLATE_RATIO, protected: Sequence[int] = (),
    ) -> int | None:
        """
        Moves `delta_ratio` of row width from the right neighbour to the target plate (negative
        shrinks the target). The last plate in a row first expands rightward into the stage margin
        with its left edge anchored (`_expand_last`); only the overflow past the margin compresses
        its left neighbour.
        The target is clamped at `min_ratio`; a neighbour compressed below `min_ratio` is
        returned as the node id to evict, and the target absorbs its share. A neighbour listed in
        `protected` (pinned) is never evicted: the target is clamped so the neighbour keeps `min_ratio`.
        Returns None when nothing needs eviction (or the plate is alone in its row).
        """
        rows = self._split_rows(plates)
        gutter = self._gutter()
        _, plate_heights, _ = self._resolve_heights(rows, gutter)
        for row, heights in zip(rows, plate_heights):
            ids = [p.node_id for p in row]
            if node_id not in ids:
                continue
            pos = ids.index(node_id)
            if pos == len(row) - 1:
                delta_ratio = self._expand_last(row, heights, gutter, delta_ratio, min_ratio)
            if len(row) < 2 or delta_ratio <= 0.0 and pos == len(row) - 1:
                return None
            npos = pos + 1 if pos + 1 < len(row) else pos - 1
            neighbour = row[npos]
            weights = [self._weight(p) for p in row]
            total = sum(weights)
            frac_t = weights[pos] / total
            frac_n = weights[npos] / total
            new_t = max(min_ratio, frac_t + delta_ratio)
            new_n = frac_n + frac_t - new_t
            if new_n < min_ratio and neighbour.node_id in protected:
                new_n = min_ratio
                new_t = frac_t + frac_n - min_ratio
            if new_n < min_ratio:
                self.weight_overrides.pop(neighbour.node_id, None)
                self.weight_overrides[node_id] = (frac_t + frac_n) * total
                return neighbour.node_id
            self.weight_overrides[node_id] = new_t * total
            self.weight_overrides[neighbour.node_id] = new_n * total
            return None
        return None

    @property
    def capacity(self) -> int:
        """Dynamic stage capacity derived from the current viewport width."""
        return compute_stage_capacity(self.config.viewport_width)

    def _fill(self, plate: PlateNodePayload, x: float, y: float, w: float, h: float, row: int, row_count: int = 1) -> BentoAllocation:
        """Writes geometry onto the plate and returns its allocation record."""
        vw = self.config.viewport_width
        cols = self.config.columns
        c_span = max(1, min(cols, round(w / vw * cols)))
        c_start = max(0, min(cols - c_span, round(x / vw * cols)))
        plate.geometry.x = round(x, 2)
        plate.geometry.y = round(y, 2)
        plate.geometry.width = round(w, 2)
        plate.geometry.height = round(h, 2)
        plate.geometry.col_span = c_span
        plate.geometry.row_span = row_count
        return BentoAllocation(
            node_id=plate.node_id, col_start=c_start, col_span=c_span,
            row_start=row, row_span=row_count, x=x, y=y, width=w, height=h,
        )

    def _allocate_centered_preview(self, plate: PlateNodePayload) -> BentoAllocation:
        """Centers a Stage 0 preview at ~60% stage width across the vertical working envelope."""
        vw = self.config.viewport_width
        vh = self.config.viewport_height
        px_w = vw * 0.6
        px_h = vh * ENVELOPE_HEIGHT_RATIO
        return self._fill(plate, (vw - px_w) / 2.0, (vh - px_h) / 2.0, px_w, px_h, 0)

    def allocate(
        self,
        plates: Sequence[PlateNodePayload],
    ) -> list[BentoAllocation]:
        """
        Lays plates out in centered, weight-proportional rows (most massive first).
        Updates plate.geometry in-place and returns allocation records.
        """
        if not plates:
            return []

        # Stage 0: a lone transient preview is centered rather than clamped to the margins
        if len(plates) == 1 and plates[0].is_preview:
            return [self._allocate_centered_preview(plates[0])]

        vw = self.config.viewport_width
        vh = self.config.viewport_height
        gutter = self._gutter()

        # Balanced row split: at most MAX_PLATES_PER_ROW plates per row
        # Committed plates by descending mass; transient previews pack last
        rows = self._split_rows(plates)
        row_count = len(rows)
        row_heights, plate_heights, _ = self._resolve_heights(rows, gutter)
        top = max(0.0, (vh - (sum(row_heights) + (row_count - 1) * gutter)) / 2.0)

        allocations: list[BentoAllocation] = []
        y = top
        for r, row_plates in enumerate(rows):
            row_h = row_heights[r]
            heights = plate_heights[r]
            widths, x = self._row_frame(row_plates, heights, gutter)
            for plate, w, h in zip(row_plates, widths, heights):
                allocations.append(self._fill(plate, x, y, w, h, r))
                x += w + gutter
            y += row_h + gutter

        return allocations
