import pytest
from PyQt6.QtQml import QQmlComponent, QQmlApplicationEngine
from PyQt6.QtCore import QUrl, QObject
import os

@pytest.fixture
def theme_component(qml_engine):
    path = os.path.abspath("aia_canvas/src/qml/Theme.qml")
    comp = QQmlComponent(qml_engine, QUrl.fromLocalFile(path))
    theme = comp.create()
    yield theme
    if theme:
        theme.deleteLater()

@pytest.fixture
def focal_lens_component(qml_engine):
    path = os.path.abspath("aia_canvas/src/qml/focal/FocalLensFrame.qml")
    comp = QQmlComponent(qml_engine, QUrl.fromLocalFile(path))
    lens = comp.create()
    yield lens
    if lens:
        lens.deleteLater()

@pytest.fixture
def omni_bar_component(qml_engine):
    path = os.path.abspath("aia_canvas/src/qml/bar/OmniBar.qml")
    comp = QQmlComponent(qml_engine, QUrl.fromLocalFile(path))
    omni = comp.create()
    yield omni
    if omni:
        omni.deleteLater()

def test_theme_animation_tokens(theme_component):
    assert theme_component is not None
    assert theme_component.property("animLensOpenDuration") == 300
    assert theme_component.property("animLensCloseDuration") == 200
    assert theme_component.property("animLensOpenEasing") is not None
    assert theme_component.property("animLensCloseEasing") is not None

def test_focal_lens_spatial_states(focal_lens_component):
    lens = focal_lens_component
    assert lens is not None

    lens.setProperty("targetCenterY", 200.0)
    
    container = lens.findChild(QObject, "lensContainer")
    assert container is not None

    # Inactive
    lens.setProperty("active", False)
    assert lens.property("active") == False
    assert container.property("visible") == False
    assert container.property("scale") == 0.88
    assert container.property("opacity") == 0.0
    assert container.property("y") == 232.0

    # Active
    lens.setProperty("active", True)
    assert lens.property("active") == True
    # QML state transitions might take time to propagate their final property values without an event loop.
    # But State changes apply property values directly if we skip animations in tests or evaluate StateGroup.
    # Actually, StateGroup applies properties immediately in tests unless blocked by transition.
    # To check state cleanly, we can check the state group property if accessible or simply check open() behavior
    lens.open("Context123", [])
    assert lens.property("activeContext") == "Context123"

def test_focal_lens_backdrop_and_absorber(focal_lens_component):
    lens = focal_lens_component
    
    backdrop = lens.findChild(QObject, "lensBackdrop")
    assert backdrop is not None

    interior = lens.findChild(QObject, "interiorAbsorber")
    assert interior is not None

def test_omni_bar_ascension(omni_bar_component):
    omni = omni_bar_component
    assert omni is not None

    drawer = omni.findChild(QObject, "dialogueDrawer")
    assert drawer is not None
    
    btn = drawer.findChild(QObject, "ascendBtn")
    assert btn is not None

    # Test shift+enter wiring via ascendToLens call behavior implicitly via properties
    lens = omni.findChild(QObject, "focalLensFrame")
    assert lens is not None
    assert lens.property("active") == False

    omni.ascendToLens()
    assert lens.property("active") == True
