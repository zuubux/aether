import os
import sys
from pathlib import Path
import tempfile
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QGuiApplication, QImage
from PyQt6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlExpression, qmlRegisterType

sys.path.append(str(Path(__file__).parent.parent / "aia_canvas" / "src"))
from aia_intent import IntentEngine
from bridge import CanvasBridge
from content.streamer import MmapTextStreamer
from models import Node

def test_preview_rendering():
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    app = QGuiApplication(sys.argv)
    qmlRegisterType(MmapTextStreamer, "Aether.Content", 1, 0, "MmapTextStreamer")

    # Create temporary dummy image and pdf thumbnail
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_img:
        img_path = f_img.name
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f_pdf:
        pdf_path = f_pdf.name
    with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as f_thumb:
        thumb_path = f_thumb.name

    # Create dummy 100x100 png image
    dummy_img = QImage(100, 100, QImage.Format.Format_RGBA8888)
    dummy_img.fill(0xFF34D399)
    dummy_img.save(img_path)
    dummy_img.save(thumb_path)

    engine = QQmlApplicationEngine()
    bridge = CanvasBridge()
    intent_engine = IntentEngine(bridge)

    # 1. Node 1: PDF with thumbnail
    node_pdf = Node(
        id=1,
        file_path=pdf_path,
        x=100.0,
        y=150.0,
        archetype="document",
        snippet="Sample PDF document snippet",
        size_bytes=2048,
        thumbnail_url=thumb_path
    )
    bridge.store.upsert_node(node_pdf)

    # 2. Node 2: PNG image without thumbnail (direct image preview)
    node_img = Node(
        id=2,
        file_path=img_path,
        x=200.0,
        y=250.0,
        archetype="asset",
        snippet="Sample PNG asset",
        size_bytes=4096,
        thumbnail_url=""
    )
    bridge.store.upsert_node(node_img)

    # 3. Node 3: Markdown doc
    node_md = Node(
        id=3,
        file_path="/test/sample.md",
        x=300.0,
        y=350.0,
        archetype="document",
        snippet="# Hello Markdown",
        size_bytes=512,
        thumbnail_url=""
    )
    bridge.store.upsert_node(node_md)

    print("[TEST 1] Verifying Backend Python Node and Bridge Output...")
    fetched_pdf = bridge.get_node(1)
    assert fetched_pdf is not None, "bridge.get_node(1) returned None"
    assert fetched_pdf.thumbnail == thumb_path, f"Expected thumbnail {thumb_path}, got {fetched_pdf.thumbnail}"
    assert fetched_pdf.thumbnailUrl == thumb_path
    assert fetched_pdf.preview_path == thumb_path
    assert fetched_pdf.previewUrl == thumb_path
    assert fetched_pdf.path == pdf_path
    assert fetched_pdf.archetype == "document"
    assert fetched_pdf["thumbnail"] == thumb_path
    assert fetched_pdf.get("preview_path") == thumb_path

    pdf_dict = bridge.get_node_data(1)
    assert pdf_dict["thumbnail"] == thumb_path
    assert pdf_dict["preview_path"] == thumb_path
    assert pdf_dict["previewUrl"] == thumb_path
    assert pdf_dict["path"] == pdf_path
    assert pdf_dict["archetype"] == "document"

    fetched_img = bridge.get_node(2)
    assert fetched_img.path == img_path
    assert fetched_img.preview_path == img_path
    assert fetched_img.previewUrl == img_path
    assert fetched_img.archetype == "asset"
    print("       -> Backend Node properties and dict outputs verified.")

    # Context setup
    engine.rootContext().setContextProperty("canvasBridge", bridge)
    engine.rootContext().setContextProperty("canvasController", bridge.canvas_ctrl)
    engine.rootContext().setContextProperty("nodeController", bridge.node_ctrl)
    engine.rootContext().setContextProperty("physicsController", bridge.physics_ctrl)
    engine.rootContext().setContextProperty("searchController", bridge.search_ctrl)
    engine.rootContext().setContextProperty("intentEngine", intent_engine)
    engine.rootContext().setContextProperty("targetScreenIdx", 0)
    engine.rootContext().setContextProperty("isFullscreen", False)
    engine.rootContext().setContextProperty("isSpanAll", False)

    print("[TEST 2] Verifying SearchShelf with PDF and Image results...")
    qml_file = Path(__file__).parent.parent / "aia_canvas" / "src" / "qml" / "Canvas.qml"
    engine.load(str(qml_file))
    assert len(engine.rootObjects()) > 0, "Failed to load Canvas.qml"
    root = engine.rootObjects()[0]

    search_shelf = root.findChild(object, "searchShelf")
    assert search_shelf is not None, "searchShelf not found"

    # Emit search result with PDF first
    bridge.searchResultsReceived.emit([1, 2, 3])
    app.processEvents()

    active_data = search_shelf.property("activeNodeData")
    assert active_data is not None, "activeNodeData should not be None"
    assert active_data.property("id") == 1, "Expected focused node 1 (PDF)"
    assert active_data.property("thumbnail") == thumb_path, "PDF thumbnail not present in activeNodeData"

    preview_item = search_shelf.findChild(object, "activePreviewItem")
    assert preview_item is not None, "activePreviewItem not found in SearchShelf"
    assert preview_item.property("previewUrl") == thumb_path, f"Expected previewUrl {thumb_path}, got {preview_item.property('previewUrl')}"
    assert preview_item.property("thumbnail") == thumb_path
    assert preview_item.property("path") == pdf_path
    assert preview_item.property("archetype") == "document"
    assert preview_item.property("isPdf") is True
    print("       -> SearchShelf PDF preview propagation verified.")

    # Navigate to Image (index 1 -> node 2)
    search_shelf.navigateRight()
    app.processEvents()
    assert search_shelf.property("focusedNodeId") == 2
    assert preview_item.property("path") == img_path
    assert preview_item.property("previewUrl") == img_path
    assert preview_item.property("isImage") is True
    print("       -> SearchShelf Image preview propagation verified.")

    print("[TEST 3] Verifying NodePreview component properties & Image formatting...")
    preview_comp = QQmlComponent(engine, "aia_canvas/src/qml/node/NodePreview.qml")
    assert preview_comp.status() == QQmlComponent.Status.Ready, f"NodePreview compilation error: {preview_comp.errors()}"
    
    # Instantiate with PDF node data
    pdf_item = preview_comp.create()
    pdf_item.setProperty("nodeData", node_pdf)
    app.processEvents()

    assert pdf_item.property("isPdf") is True
    assert pdf_item.property("previewUrl") == thumb_path
    assert pdf_item.property("hasThumbnail") is True

    # Check child Image item in NodePreview
    preview_img = pdf_item.findChild(object, "previewImg")
    if preview_img is None:
        # Fallback search by children
        for child in pdf_item.children():
            for subchild in child.children():
                for subsub in subchild.children():
                    if subsub.metaObject().className() == "QQuickImage":
                        preview_img = subsub
                        break

    assert pdf_item.findChild(object, "pdfPaperFrame") is None, "pdfPaperFrame should not exist"
    assert pdf_item.findChild(object, "imageMatFrame") is None, "imageMatFrame should not exist"
    assert pdf_item.findChild(object, "gifMatFrame") is None, "gifMatFrame should not exist"
    assert preview_img is not None, "previewImg not found in NodePreview"
    assert preview_img.property("visible") is True
    assert preview_img.property("asynchronous") is True
    assert preview_img.property("smooth") is True
    assert preview_img.property("clip") is True
    # FillMode: 2 is Image.PreserveAspectCrop, 1 is Image.PreserveAspectFit
    assert QQmlExpression(engine.rootContext(), preview_img, "fillMode").evaluate()[0] == 2
    # AlignTop is 0x0020 (32)
    assert QQmlExpression(engine.rootContext(), preview_img, "verticalAlignment").evaluate()[0] == 32
    # AlignHCenter is 0x0004 (4)
    assert QQmlExpression(engine.rootContext(), preview_img, "horizontalAlignment").evaluate()[0] == 4

    # Instantiate with Image node data
    img_preview_item = preview_comp.create()
    img_preview_item.setProperty("nodeData", node_img)
    app.processEvents()

    assert img_preview_item.property("isStaticImage") is True
    assert img_preview_item.property("isAnimatedGif") is False
    assert img_preview_item.property("isPdf") is False
    assert img_preview_item.property("isImage") is True
    assert img_preview_item.property("previewUrl") == img_path
    assert img_preview_item.property("hasThumbnail") is True

    img_preview_img = img_preview_item.findChild(object, "previewImg")
    if img_preview_img is None:
        for child in img_preview_item.children():
            for subchild in child.children():
                for subsub in subchild.children():
                    if subsub.metaObject().className() == "QQuickImage":
                        img_preview_img = subsub
                        break
    assert img_preview_img is not None
    assert QQmlExpression(engine.rootContext(), img_preview_img, "fillMode").evaluate()[0] == 1
    # AlignVCenter is 0x0080 (128)
    assert QQmlExpression(engine.rootContext(), img_preview_img, "verticalAlignment").evaluate()[0] == 128
    assert QQmlExpression(engine.rootContext(), img_preview_img, "horizontalAlignment").evaluate()[0] == 4

    # Instantiate with Markdown node data (Ensure no image binding)
    md_preview_item = preview_comp.create()
    md_preview_item.setProperty("nodeData", node_md)
    app.processEvents()

    assert md_preview_item.property("isStaticImage") is False
    assert md_preview_item.property("isAnimatedGif") is False
    assert md_preview_item.property("isPdf") is False
    assert md_preview_item.property("previewUrl") == ""
    assert md_preview_item.property("hasThumbnail") is False

    # Instantiate with GIF node data
    node_gif = Node(
        id=4,
        file_path="/test/animation.gif",
        x=400.0,
        y=450.0,
        archetype="media",
        snippet="",
        size_bytes=8192,
        thumbnail_url=""
    )
    gif_preview_item = preview_comp.create()
    gif_preview_item.setProperty("nodeData", node_gif)
    app.processEvents()

    assert gif_preview_item.property("isAnimatedGif") is True
    assert gif_preview_item.property("isPdf") is False
    assert gif_preview_item.property("previewUrl") == "/test/animation.gif"

    print("       -> NodePreview component properties & Image formatting verified.")

    print("[TEST 4] Verifying NodeContent.qml Tier 1.5 preview loader with PDF and Image nodes...")
    node_content_comp = QQmlComponent(engine, "aia_canvas/src/qml/NodeContent.qml")
    assert node_content_comp.status() == QQmlComponent.Status.Ready, f"NodeContent error: {node_content_comp.errors()}"
    
    # Tier 1.5 with PDF nodeData
    nc_item = node_content_comp.create()
    nc_item.setProperty("nodeData", node_pdf)
    nc_item.setProperty("tierState", "TIER_1_5")
    app.processEvents()

    assert nc_item.property("isPreviewMode") is True
    loader = nc_item.property("nodePreviewLoader")
    assert loader is not None
    app.processEvents()
    print("       -> NodeContent Tier 1.5 preview loader verified.")

    # Clean up temp files
    try:
        os.unlink(img_path)
        os.unlink(pdf_path)
        os.unlink(thumb_path)
    except Exception:
        pass

    print("ALL PREVIEW RENDERING TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_preview_rendering()
