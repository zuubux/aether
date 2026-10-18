"""
Unit tests for FuzzySearchEngine.
Tests multi-tier ranking, stem matching, snippet extraction math, and search scoring.
"""

import asyncio
from omni import FuzzySearchEngine, OmniContext
from models import Node


class MockStore:
    def __init__(self, nodes=None):
        self._nodes = nodes or []

    def get_all_nodes(self):
        return self._nodes


def test_fuzzy_search_engine_can_handle():
    store = MockStore()
    engine = FuzzySearchEngine(store=store)

    ctx = OmniContext(raw_query="restomod")
    assert engine.can_handle("restomod", ctx) == 0.8
    assert engine.can_handle("> restomod", ctx) == 0.0


def test_fuzzy_search_ranking_and_scoring(mock_bridge):
    n1 = Node(id=1, file_path="/test/report.pdf", x=1280.0, y=720.0, archetype="document", snippet="Quarterly earnings summary report line", size_bytes=2048)
    n2 = Node(id=2, file_path="/test/analytics.py", x=3000.0, y=3000.0, archetype="code", snippet="Data pipeline engine execution", size_bytes=4096)
    n3 = Node(id=3, file_path="/test/dataset.csv", x=100.0, y=100.0, archetype="table", snippet="Row data entries for ML model", size_bytes=8192)

    mock_bridge.store.upsert_node(n1)
    mock_bridge.store.upsert_node(n2)
    mock_bridge.store.upsert_node(n3)

    engine = FuzzySearchEngine(store=mock_bridge.store)
    ctx1 = OmniContext(raw_query="report")

    res1 = asyncio.run(engine.execute("report", ctx1))
    assert len(res1) > 0
    assert res1[0].id == "1"
    assert res1[0].score >= 0.85
    assert "report" in res1[0].title.lower() or "report" in res1[0].snippet.lower()


def test_fuzzy_search_empty_store():
    store = MockStore([])
    engine = FuzzySearchEngine(store=store)

    ctx = OmniContext(raw_query="nonexistent")
    res = asyncio.run(engine.execute("nonexistent", ctx))
    assert len(res) == 0

def test_fuzzy_search_sqlite_direct_fallback(tmp_path):
    import sqlite3

    db_path = tmp_path / "weaver_graph.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            file_hash TEXT,
            extension TEXT,
            size_bytes INTEGER,
            archetype TEXT,
            snippet TEXT,
            thumbnail_url TEXT
        );
    """)
    cursor.execute(
        "INSERT INTO nodes VALUES (10, '/workspace/src/financial_summary.csv', 'hash1', '.csv', 1024, 'document', '<span class=\"label\">Header</span><br/><pre>Revenue: 500000</pre>', '');"
    )
    cursor.execute(
        "INSERT INTO nodes VALUES (11, '/workspace/docs/architecture.md', 'hash2', '.md', 2048, 'document', '<h1>Architecture</h1><p>Post-WIMP canvas design</p>', '');"
    )
    cursor.execute(
        "INSERT INTO nodes VALUES (12, '/workspace/scripts/deploy.sh', 'hash3', '.sh', 512, 'code', 'echo \"deploying stack\"', '');"
    )
    conn.commit()
    conn.close()

    # Empty store, should fall back to SQLite
    engine = FuzzySearchEngine(store=None, db_path=db_path)

    # 1. Exact match by file name stem
    ctx = OmniContext(raw_query="financial_summary.csv")
    results = asyncio.run(engine.execute("financial_summary.csv", ctx))
    assert len(results) > 0
    assert results[0].id == "10"
    assert results[0].title == "financial_summary.csv"
    assert results[0].score == 1.0
    # Verify HTML tags were stripped
    assert "<span" not in results[0].metadata["snippet"]
    assert "Revenue: 500000" in results[0].metadata["snippet"] or "Header" in results[0].metadata["snippet"]

    # 2. Match by clean snippet text
    ctx2 = OmniContext(raw_query="post-wimp")
    results2 = asyncio.run(engine.execute("post-wimp", ctx2))
    assert len(results2) > 0
    assert results2[0].id == "11"
    assert results2[0].title == "architecture.md"
    assert "Post-WIMP canvas design" in results2[0].metadata["snippet"]
    assert "<p>" not in results2[0].metadata["snippet"]

    # 3. Sorted by score descending
    ctx3 = OmniContext(raw_query="deploy")
    results3 = asyncio.run(engine.execute("deploy", ctx3))
    assert len(results3) > 0
    assert results3[0].id == "12"
    # Filename match (deploy.sh starts with deploy) scores 0.95 vs snippet match (0.70)
    assert results3[0].score >= 0.85


def test_plate_canvas_controller_open_plate():
    from controllers.plate_controller import PlateCanvasController

    ctrl = PlateCanvasController()
    ctrl.setViewportDimensions(3900.0, 1000.0)  # capacity 6: no auto-eviction in this scenario
    opened_ids = []
    ctrl.plateOpened.connect(lambda nid: opened_ids.append(nid))

    # 1. Open by ID
    nid1 = ctrl.open_plate(1)
    assert nid1 == 1
    assert nid1 in opened_ids
    assert len(ctrl.activePlates) == 1
    assert ctrl.activePlates[0]["node_id"] == 1

    # 2. Open by file path
    nid2 = ctrl.open_plate("/workspace/test_script.py")
    assert nid2 > 0
    assert len(ctrl.activePlates) == 2

    # 3. Open by dict payload
    payload = {"id": 99, "file_path": "/test/doc.md", "display_title": "Custom Doc"}
    nid3 = ctrl.openPlate(payload)
    assert nid3 == 99
    assert len(ctrl.activePlates) == 3
    assert ctrl.focalPlateId == 99


def test_plate_canvas_controller_preview_and_dwell_commit():
    from controllers.plate_controller import PlateCanvasController

    ctrl = PlateCanvasController()

    # 1. Preview a plate
    nid1 = ctrl.preview_plate({"id": 10, "file_path": "/docs/spec1.md", "display_title": "Spec 1"})
    assert nid1 == 10
    assert len(ctrl.activePlates) == 1
    assert ctrl.activePlates[0]["is_preview"] is True
    assert ctrl.activePlates[0]["isPreview"] is True

    # 2. Preview another plate -> replaces rather than stacking duplicates
    nid2 = ctrl.preview_plate({"id": 20, "file_path": "/docs/spec2.md", "display_title": "Spec 2"})
    assert nid2 == 20
    assert len(ctrl.activePlates) == 1
    assert ctrl.activePlates[0]["node_id"] == 20
    assert ctrl.activePlates[0]["is_preview"] is True

    # 3. Clear preview
    ctrl.clear_preview()
    assert len(ctrl.activePlates) == 0

    # 4. Committed plate + transient preview
    ctrl.open_plate({"id": 100, "file_path": "/docs/committed.md", "display_title": "Committed"})
    assert len(ctrl.activePlates) == 1
    assert ctrl.activePlates[0]["is_preview"] is False

    ctrl.preview_plate({"id": 200, "file_path": "/docs/transient.md", "display_title": "Transient"})
    assert len(ctrl.activePlates) == 2
    preview_plates = [p for p in ctrl.activePlates if p["is_preview"]]
    assert len(preview_plates) == 1
    assert preview_plates[0]["node_id"] == 200

    # 5. Clear preview keeps committed plate
    ctrl.clear_preview()
    assert len(ctrl.activePlates) == 1
    assert ctrl.activePlates[0]["node_id"] == 100

    # 6. Dwell commit: Preview then open_plate commits it
    ctrl.preview_plate({"id": 300, "file_path": "/docs/dwell.md", "display_title": "Dwell"})
    assert len(ctrl.activePlates) == 2
    plate300 = next(p for p in ctrl.activePlates if p["node_id"] == 300)
    assert plate300["is_preview"] is True

    committed_id = ctrl.open_plate(300)
    assert committed_id == 300
    assert len(ctrl.activePlates) == 2
    committed_plate = next(p for p in ctrl.activePlates if p["node_id"] == 300)
    assert committed_plate["is_preview"] is False
    assert committed_plate["isPreview"] is False


def test_plate_canvas_controller_snippet_1kb_fallback(tmp_path):
    from controllers.plate_controller import PlateCanvasController

    ctrl = PlateCanvasController()
    test_file = tmp_path / "long_doc.txt"
    sample_text = "Aether post-WIMP spatial environment. " * 100  # >2KB
    test_file.write_text(sample_text, encoding="utf-8")

    # Ingest without snippet -> should hydrate ~2KB head buffer
    nid = ctrl.add_plate({
        "id": 55,
        "file_path": str(test_file),
        "snippet": "",
    })
    assert nid == 55
    plate = ctrl.get_plate(55)
    assert plate is not None
    assert len(plate.snippet) > 0
    assert len(plate.snippet) <= 2048
    assert "Aether post-WIMP" in plate.snippet


