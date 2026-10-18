"""Unit tests for dynamic viewport capacity, auto-eviction to feed, and selectPlate."""

from controllers.feed_controller import FeedController
from controllers.plate_controller import PlateCanvasController
from plate_engine.bento import BentoAllocator, BentoGridConfig, compute_stage_capacity
from plate_engine.parser import parse_plate_payload


class _Bridge:
    def __init__(self):
        self.feed_ctrl = FeedController(None)


def _make():
    bridge = _Bridge()
    ctrl = PlateCanvasController(bridge)
    return ctrl, bridge.feed_ctrl


def _open(ctrl, nid, epoch):
    ctrl.open_plate({"id": nid, "file_path": f"/d/{nid}.md", "display_title": f"P{nid}"})
    ctrl.get_plate(nid).temporal.touch(epoch)


def test_capacity_formula():
    assert compute_stage_capacity(300) == 1
    assert compute_stage_capacity(1300) == 2
    assert compute_stage_capacity(99999) == 6


def test_open_evicts_oldest_unpinned_to_feed_and_restores():
    ctrl, feed = _make()
    ctrl.setViewportDimensions(1400.0, 800.0)  # capacity 2
    _open(ctrl, 1, 100.0)
    _open(ctrl, 2, 200.0)
    ctrl.pin_plate(1, True)  # pinned plates are exempt and not counted
    _open(ctrl, 3, 300.0)
    ctrl.get_plate(3).temporal.touch(300.0)
    assert {p["node_id"] for p in ctrl.activePlates} == {1, 2, 3}
    _open(ctrl, 4, 400.0)
    ids = {p["node_id"] for p in ctrl.activePlates}
    assert ids == {1, 3, 4}
    assert feed.get_item("plate:2") is not None

    ctrl.open_plate(2)  # restore from feed chip
    assert feed.get_item("plate:2") is None
    assert 2 in {p["node_id"] for p in ctrl.activePlates}
    assert 3 not in {p["node_id"] for p in ctrl.activePlates}
    assert feed.get_item("plate:3") is not None


def test_viewport_shrink_evicts_and_select_plate_touches():
    ctrl, feed = _make()
    ctrl.setViewportDimensions(3900.0, 800.0)
    for i, nid in enumerate((1, 2, 3)):
        _open(ctrl, nid, 100.0 + i)
    ctrl.selectPlate(1)
    assert ctrl.focalPlateId == 1
    ctrl.setViewportDimensions(700.0, 800.0)  # capacity 1
    assert [p["node_id"] for p in ctrl.activePlates] == [1]
    assert feed.get_item("plate:2") is not None and feed.get_item("plate:3") is not None


def test_bento_no_negative_or_overlap_on_narrow_viewports():
    for width in (480.0, 800.0, 1024.0):
        alloc = BentoAllocator(BentoGridConfig(viewport_width=width, viewport_height=700.0))
        plates = [parse_plate_payload({"id": i, "file_path": f"/d/{i}.md"}) for i in range(1, 7)]
        rects = [(a.x, a.y, a.x + a.width, a.y + a.height) for a in alloc.allocate(plates)]
        for x0, y0, x1, y1 in rects:
            assert x0 >= 0 and y0 >= 0 and x1 > x0 and y1 > y0
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                assert a[2] <= b[0] + 1e-6 or b[2] <= a[0] + 1e-6 or a[3] <= b[1] + 1e-6 or b[3] <= a[1] + 1e-6



def _assert_disjoint_in_stage(ctrl, vw, vh):
    rects = [(a.x, a.y, a.x + a.width, a.y + a.height) for a in ctrl._bento_allocations]
    for x0, y0, x1, y1 in rects:
        assert x0 >= -1e-6 and y0 >= -1e-6 and x1 <= vw + 1e-6 and y1 <= vh + 1e-6
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert a[2] <= b[0] + 1e-6 or b[2] <= a[0] + 1e-6 or a[3] <= b[1] + 1e-6 or b[3] <= a[1] + 1e-6


def test_corner_resize_width_evicts_squeezed_neighbour_but_never_pinned():
    ctrl, feed = _make()
    ctrl.setViewportDimensions(3900.0, 1000.0)
    for nid in (1, 2):
        _open(ctrl, nid, 100.0 + nid)
    ctrl.resize_plate_proportional(1, 0.05, 0.0)
    assert {p["node_id"] for p in ctrl.activePlates} == {1, 2}
    ctrl.resize_plate_proportional(1, 0.9, 0.0)
    assert [p["node_id"] for p in ctrl.activePlates] == [1]
    assert feed.get_item("plate:2") is not None

    ctrl2, _ = _make()
    ctrl2.setViewportDimensions(3900.0, 1000.0)
    for nid in (1, 2):
        _open(ctrl2, nid, 100.0 + nid)
    ctrl2.pin_plate(2, True)
    ctrl2.resize_plate_proportional(1, 0.9, 0.0)
    assert {p["node_id"] for p in ctrl2.activePlates} == {1, 2}
    _assert_disjoint_in_stage(ctrl2, 3900.0, 1000.0)


def test_corner_resize_height_pushes_rows_and_evicts_oldest_unpinned_off_stage():
    ctrl, feed = _make()
    ctrl.setViewportDimensions(5000.0, 1000.0)
    for nid in range(1, 6):  # 5 plates -> two rows
        _open(ctrl, nid, 100.0 + nid)
    ctrl.pin_plate(5, True)
    ctrl.resize_plate_proportional(1, 0.0, 0.05)
    _assert_disjoint_in_stage(ctrl, 5000.0, 1000.0)
    ctrl.resize_plate_proportional(1, 0.0, 0.9)
    ids = {p["node_id"] for p in ctrl.activePlates}
    assert 1 in ids and 5 in ids and len(ids) < 5
    assert any(feed.get_item(f"plate:{n}") is not None for n in range(2, 5))
    _assert_disjoint_in_stage(ctrl, 5000.0, 1000.0)


def test_height_override_affects_only_target_plate_in_row():
    alloc = BentoAllocator(BentoGridConfig(viewport_width=2000.0, viewport_height=1000.0))
    plates = [parse_plate_payload({"id": i, "file_path": f"/d/{i}.md"}) for i in (1, 2)]
    base = {a.node_id: a for a in alloc.allocate(plates)}
    assert base[1].height == base[2].height
    assert alloc.adjust_height(plates, 2, 0.1)
    after = {a.node_id: a for a in alloc.allocate(plates)}
    assert set(alloc.height_overrides) == {2}
    assert after[1].height == base[1].height
    assert after[2].height > base[2].height
    assert after[1].y == after[2].y


def test_last_plate_corner_drag_expands_rightward_with_left_edge_anchored():
    ctrl, _ = _make()
    ctrl.setViewportDimensions(3900.0, 1000.0)
    for nid in (1, 2):
        _open(ctrl, nid, 100.0 + nid)
    before = {p.node_id: (p.geometry.x, p.geometry.width) for p in map(ctrl.get_plate, (1, 2))}
    last = max(before, key=lambda n: before[n][0])
    first = min(before, key=lambda n: before[n][0])
    ctrl.resize_plate_proportional(last, 0.02, 0.0)
    after = {n: (ctrl.get_plate(n).geometry.x, ctrl.get_plate(n).geometry.width) for n in before}
    assert after[last][0] == before[last][0]
    assert after[first] == before[first]
    assert after[last][1] > before[last][1]
    assert {p["node_id"] for p in ctrl.activePlates} == {1, 2}


def test_shelve_plate_demotes_to_header_anchor_and_restores():
    ctrl, feed = _make()
    ctrl.setViewportDimensions(3900.0, 800.0)
    _open(ctrl, 1, 100.0)
    _open(ctrl, 2, 200.0)
    ctrl.shelve_plate("1")
    assert 1 not in ctrl._plates
    assert [p["node_id"] for p in ctrl.activePlates] == [2]
    assert "plate:1" in {a["id"] for a in feed.headerAnchors}
    ctrl.shelve_plate("not-an-id")
    ctrl.shelve_plate("99")
    assert [p["node_id"] for p in ctrl.activePlates] == [2]

    ctrl.open_plate(1)  # chip click restores and clears the anchor
    assert "plate:1" not in {a["id"] for a in feed.headerAnchors}
    assert {p["node_id"] for p in ctrl.activePlates} == {1, 2}
