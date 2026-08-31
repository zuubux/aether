"""
Unit tests for Procedural Spatial Background (CanvasAtmosphere.qml).
Verifies component initialization, geometry binding, color gradient tokens,
and camera parallax tracking.
"""

import pytest
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtQml import QQmlComponent
from PyQt6.QtGui import QColor


def test_canvas_atmosphere_standalone_initialization(qapp, qml_engine):
    """Verify CanvasAtmosphere.qml instantiates, exposes expected properties and defaults."""
    comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/background/CanvasAtmosphere.qml")
    assert comp.status() == QQmlComponent.Status.Ready, f"CanvasAtmosphere.qml compilation failed: {comp.errors()}"

    atmosphere = comp.create()
    assert atmosphere is not None
    assert atmosphere.property("objectName") == "canvasAtmosphere"
    assert atmosphere.property("z") == -100.0

    # Default color tokens
    center_color = atmosphere.property("centerColor")
    mid_color = atmosphere.property("midColor")
    outer_color = atmosphere.property("outerColor")

    assert isinstance(center_color, QColor)
    assert center_color.name().lower() == "#07111e"
    assert mid_color.name().lower() == "#030712"
    assert outer_color.name().lower() == "#000000"

    # Default camera parallax properties
    assert atmosphere.property("cameraX") == 0.0
    assert atmosphere.property("cameraY") == 0.0
    assert abs(atmosphere.property("parallaxFactor") - 0.12) < 1e-5

    # Child ShaderEffect presence
    shader = atmosphere.findChild(object, "atmosphereShader")
    assert shader is not None
    assert shader.property("parallaxFactor") == atmosphere.property("parallaxFactor")
    assert shader.property("_pad") == 0.0


def test_canvas_atmosphere_root_integration_and_parallax_binding(qapp, qml_engine, canvas_qml_root):
    """Verify CanvasAtmosphere integration inside Canvas.qml root window and camera binding."""
    import time
    atmosphere = canvas_qml_root.findChild(object, "canvasAtmosphere")
    assert atmosphere is not None
    assert atmosphere.property("z") == -100.0

    # Verify geometry binding to canvas root window
    assert atmosphere.property("width") == canvas_qml_root.property("width")
    assert atmosphere.property("height") == canvas_qml_root.property("height")

    # Verify initial camera positions
    viewport = canvas_qml_root.findChild(object, "canvasViewport")
    assert viewport is not None

    # Simulate camera viewport movement
    viewport.setProperty("targetX", 150.0)
    viewport.setProperty("targetY", -80.0)

    # Process events to allow NumberAnimation on viewport x/y to complete
    start_time = time.time()
    while time.time() - start_time < 0.35:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert abs(viewport.property("x") - 150.0) < 1.0
    assert abs(viewport.property("y") - (-80.0)) < 1.0
    assert abs(atmosphere.property("cameraX") - viewport.property("x")) < 1e-5
    assert abs(atmosphere.property("cameraY") - viewport.property("y")) < 1e-5



def test_canvas_atmosphere_property_overrides(qapp, qml_engine):
    """Verify property overrides on CanvasAtmosphere update shader properties."""
    comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/background/CanvasAtmosphere.qml")
    atmosphere = comp.create()
    assert atmosphere is not None

    atmosphere.setProperty("cameraX", 320.0)
    atmosphere.setProperty("cameraY", 240.0)
    atmosphere.setProperty("parallaxFactor", 0.18)
    atmosphere.setProperty("centerColor", QColor("#0a192f"))

    assert atmosphere.property("cameraX") == 320.0
    assert atmosphere.property("cameraY") == 240.0
    assert abs(atmosphere.property("parallaxFactor") - 0.18) < 1e-5
    assert atmosphere.property("centerColor").name().lower() == "#0a192f"

    shader = atmosphere.findChild(object, "atmosphereShader")
    assert shader is not None
    assert shader.property("cameraX") == 320.0
    assert shader.property("cameraY") == 240.0
    assert abs(shader.property("parallaxFactor") - 0.18) < 1e-5
    assert shader.property("centerColor").name().lower() == "#0a192f"
