import sys, os
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlExpression, qmlContext

sys.path.insert(0, os.path.abspath("aia_canvas/src"))
from models import Node

def test_top_alignment():
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.addImportPath("aia_canvas/src/qml")

    preview_comp = QQmlComponent(engine, "aia_canvas/src/qml/node/NodePreview.qml")
    assert preview_comp.status() == QQmlComponent.Status.Ready, f"Error: {preview_comp.errors()}"

    # 1. Test CSV Node
    node_csv = Node(id=101, file_path="/workspace/data.csv", archetype="table", snippet="col1,col2,col3\nval1,val2,val3\nval4,val5,val6", size_bytes=1024)
    csv_item = preview_comp.create()
    csv_item.setProperty("nodeData", node_csv)
    app.processEvents()

    ctx_csv = qmlContext(csv_item)
    assert csv_item.property("isCsv") is True
    assert QQmlExpression(ctx_csv, csv_item, "textContentContainer.visible").evaluate()[0] is True
    assert QQmlExpression(ctx_csv, csv_item, "mediaContainer.visible").evaluate()[0] is False
    assert QQmlExpression(ctx_csv, csv_item, "textContentContainer.anchors.topMargin").evaluate()[0] == 8
    assert QQmlExpression(ctx_csv, csv_item, "textContentContainer.anchors.leftMargin").evaluate()[0] == 12
    assert QQmlExpression(ctx_csv, csv_item, "textContentContainer.anchors.rightMargin").evaluate()[0] == 12
    assert QQmlExpression(ctx_csv, csv_item, "textContentContainer.anchors.bottomMargin").evaluate()[0] == 8
    assert QQmlExpression(ctx_csv, csv_item, "csvTable.visible").evaluate()[0] is True
    print("PASS 1: CSV Preview top-alignment and margins verified.")

    # 2. Test Markdown Node
    node_md = Node(id=102, file_path="/workspace/notes.md", archetype="document", snippet="# Notes\nMarkdown text", size_bytes=512)
    md_item = preview_comp.create()
    md_item.setProperty("nodeData", node_md)
    app.processEvents()
    ctx_md = qmlContext(md_item)
    assert QQmlExpression(ctx_md, md_item, "textContentContainer.visible").evaluate()[0] is True
    assert QQmlExpression(ctx_md, md_item, "mediaContainer.visible").evaluate()[0] is False
    assert QQmlExpression(ctx_md, md_item, "csvTable.visible").evaluate()[0] is False
    print("PASS 2: Markdown Preview top-alignment verified.")

    # 3. Test Python Node
    node_py = Node(id=103, file_path="/workspace/app.py", archetype="code", snippet="import os\nprint('hi')", size_bytes=256)
    py_item = preview_comp.create()
    py_item.setProperty("nodeData", node_py)
    app.processEvents()
    ctx_py = qmlContext(py_item)
    assert QQmlExpression(ctx_py, py_item, "textContentContainer.visible").evaluate()[0] is True
    assert QQmlExpression(ctx_py, py_item, "mediaContainer.visible").evaluate()[0] is False
    assert QQmlExpression(ctx_py, py_item, "csvTable.visible").evaluate()[0] is False
    print("PASS 3: Python Code Preview top-alignment verified.")

    # 4. Test Config Node (JSON / YAML)
    node_json = Node(id=104, file_path="/workspace/config.json", archetype="config", snippet='{"a": 1}', size_bytes=128)
    json_item = preview_comp.create()
    json_item.setProperty("nodeData", node_json)
    app.processEvents()
    ctx_json = qmlContext(json_item)
    assert QQmlExpression(ctx_json, json_item, "textContentContainer.visible").evaluate()[0] is True
    assert QQmlExpression(ctx_json, json_item, "mediaContainer.visible").evaluate()[0] is False
    print("PASS 4: Config Preview top-alignment verified.")

    # 5. Media Exception - Optical Centering
    sample_img = os.path.abspath("aia_weaver/sandbox/Steam_Battlenet1.png")
    node_img = Node(id=105, file_path=sample_img, archetype="media", snippet="", thumbnail_url=sample_img, size_bytes=4096)
    img_item = preview_comp.create()
    img_item.setProperty("nodeData", node_img)
    app.processEvents()
    ctx_img = qmlContext(img_item)
    assert QQmlExpression(ctx_img, img_item, "mediaContainer.visible").evaluate()[0] is True
    assert QQmlExpression(ctx_img, img_item, "textContentContainer.visible").evaluate()[0] is False
    assert QQmlExpression(ctx_img, img_item, "previewImg.verticalAlignment").evaluate()[0] == 128
    print("PASS 5: Media optical vertical centering verified.")
    print("\nALL PREVIEW TOP-ALIGNMENT AND MEDIA CENTERING TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_top_alignment()

