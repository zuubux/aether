import os, sys, io, tempfile, zipfile, tarfile
from pathlib import Path

sys.path.insert(0, os.path.abspath("aia_weaver/src"))
from extractors.archive import extract_archive_manifest, is_archive_file, get_archive_type
from indexer.parser import extract_archetype_and_snippet

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlExpression, qmlContext

sys.path.insert(0, os.path.abspath("aia_canvas/src"))
from models import Node


def test_archive_extractor():
    print("[TEST 1] Verifying Archive Extractor on ZIP and TAR...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        zip_path = tmp_path / "test_package.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("src/", "")
            zf.writestr("src/index.ts", "console.log('index');\n")
            zf.writestr("src/utils.ts", "export const foo = 1;\n")
            for i in range(12):
                zf.writestr(f"docs/doc_{i}.md", f"# Doc {i}\n")
            zf.writestr("package.json", '{"name": "test-pkg"}\n')

        assert is_archive_file(zip_path) is True
        assert get_archive_type(zip_path) == "ZIP"
        zip_info = extract_archive_manifest(zip_path)
        assert zip_info["file_count"] == 16, f"Expected 16 files, got {zip_info['file_count']}"
        assert zip_info["uncompressed_size"] > 0
        assert "src/" in zip_info["manifest"]
        assert "16 items •" in zip_info["summary"]

        targz_path = tmp_path / "archive_data.tar.gz"
        with tarfile.open(targz_path, "w:gz") as tf:
            for name, data in [("README.md", b"# Test\n"), ("lib/mod.py", b"def run(): pass\n")]:
                ti = tarfile.TarInfo(name=name)
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))

        assert is_archive_file(targz_path) is True
        assert get_archive_type(targz_path) == "TAR"
        targz_info = extract_archive_manifest(targz_path)
        assert targz_info["file_count"] == 2
        assert "README.md" in targz_info["manifest"]

        arch_type, snippet = extract_archetype_and_snippet(zip_path, b"")
        assert arch_type == "ARCHIVE"
        assert "16 items •" in snippet
        print(" -> Archive extractor (ZIP/TAR) and parser integration verified.")


def test_qml_rendering():
    print("[TEST 2] Verifying QML Theme badges and NodePreview rendering...")
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.addImportPath("aia_canvas/src/qml")

    preview_comp = QQmlComponent(engine, "aia_canvas/src/qml/node/NodePreview.qml")
    assert preview_comp.status() == QQmlComponent.Status.Ready, f"NodePreview error: {preview_comp.errors()}"

    node_zip = Node(
        id=201, file_path="/workspace/build.zip", archetype="ARCHIVE",
        snippet="16 items • 42.5 KB uncompressed\nsrc/\nsrc/index.ts\n... (+14 more)", size_bytes=14200
    )
    zip_item = preview_comp.create()
    zip_item.setProperty("nodeData", node_zip)
    app.processEvents()
    ctx = qmlContext(zip_item)

    assert zip_item.property("isArchive") is True
    assert QQmlExpression(ctx, zip_item, "textContentContainer.visible").evaluate()[0] is True
    assert QQmlExpression(ctx, zip_item, "mediaContainer.visible").evaluate()[0] is False
    assert QQmlExpression(ctx, zip_item, "archiveLayout.visible").evaluate()[0] is True
    assert QQmlExpression(ctx, zip_item, "archiveSummaryText.text").evaluate()[0] == "16 items • 42.5 KB uncompressed"
    assert "src/index.ts" in QQmlExpression(ctx, zip_item, "archiveManifestText.text").evaluate()[0]

    node_tar = Node(
        id=202, file_path="/workspace/data.tar.gz", archetype="ARCHIVE",
        snippet="50 items • 1.2 MB uncompressed\nREADME.md\nlib/\n... (+48 more)", size_bytes=150000
    )
    tar_item = preview_comp.create()
    tar_item.setProperty("nodeData", node_tar)
    app.processEvents()
    ctx_tar = qmlContext(tar_item)

    assert tar_item.property("isArchive") is True
    assert QQmlExpression(ctx_tar, tar_item, "badgeText.text").evaluate()[0] == "TAR"
    assert QQmlExpression(ctx, zip_item, "badgeText.text").evaluate()[0] == "ZIP"
    print(" -> Archive QML scene graph properties (summary pill, tree, badge) verified.")


if __name__ == "__main__":
    test_archive_extractor()
    test_qml_rendering()
    print("ALL ARCHIVE INSPECTION TESTS PASSED SUCCESSFULLY!")
