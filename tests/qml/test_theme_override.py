import pytest
from PyQt6.QtQml import QQmlComponent

def test_theme_override(qapp, qml_engine, mock_bridge):
    qml_engine.rootContext().setContextProperty("bridge", mock_bridge)
    comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    item = comp.create()
    timers = [c for c in item.children() if "Timer" in c.metaObject().className()]
    for t in timers:
        t.setProperty("interval", 5)
        print("Set interval 5 for timer, interval is now:", t.property("interval"))
