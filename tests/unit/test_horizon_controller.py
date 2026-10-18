"""
Unit tests for HorizonController.
Verifies dynamic identity resolution, ambient status management, and signal emissions.
"""

import getpass
import platform
import pytest
from PyQt6.QtCore import QObject

from aia_canvas.src.controllers.horizon_controller import HorizonController


def test_horizon_controller_dynamic_identity(qapp):
    controller = HorizonController()
    expected_identity = f"{getpass.getuser().upper()} · {platform.node().split('.')[0].upper()}"
    assert controller.identity == expected_identity
    assert len(controller.identity) > 0


def test_horizon_controller_ambient_status_default_and_custom(qapp):
    # Default
    controller_default = HorizonController()
    assert controller_default.ambientStatus == "South Jordan · Fair"

    # Custom
    controller_custom = HorizonController(ambient_status="Salt Lake City · Clear")
    assert controller_custom.ambientStatus == "Salt Lake City · Clear"


def test_horizon_controller_signals_and_mutators(qapp):
    controller = HorizonController()

    identity_emissions = []
    ambient_emissions = []

    controller.identityChanged.connect(lambda val: identity_emissions.append(val))
    controller.ambientStatusChanged.connect(lambda val: ambient_emissions.append(val))

    # Mutate identity
    controller.setIdentity("AGENT · ATLAS")
    assert controller.identity == "AGENT · ATLAS"
    assert identity_emissions == ["AGENT · ATLAS"]

    # Setting same value does not emit
    controller.setIdentity("AGENT · ATLAS")
    assert len(identity_emissions) == 1

    # Mutate ambient status
    controller.setAmbientStatus("Moab · Sunny")
    assert controller.ambientStatus == "Moab · Sunny"
    assert ambient_emissions == ["Moab · Sunny"]

    # Setting same ambient status does not emit
    controller.setAmbientStatus("Moab · Sunny")
    assert len(ambient_emissions) == 1


def test_horizon_controller_refresh_identity(qapp):
    controller = HorizonController()
    controller.setIdentity("OVERRIDDEN · IDENTITY")
    assert controller.identity == "OVERRIDDEN · IDENTITY"

    controller.refresh_identity()
    expected_identity = f"{getpass.getuser().upper()} · {platform.node().split('.')[0].upper()}"
    assert controller.identity == expected_identity


def test_horizon_controller_refresh_diagnostics(qapp, tmp_path, monkeypatch):
    import sqlite3
    from types import SimpleNamespace

    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    db_dir = tmp_path / ".config" / "aether"
    db_dir.mkdir(parents=True)
    conn = sqlite3.connect(str(db_dir / "weaver_graph.db"))
    conn.execute("CREATE TABLE nodes (id INTEGER PRIMARY KEY)")
    conn.executemany("INSERT INTO nodes (id) VALUES (?)", [(1,), (2,), (3,)])
    conn.commit()
    conn.close()

    bridge = SimpleNamespace(plate_controller=SimpleNamespace(plateCount=2, capacity=4))
    controller = HorizonController(bridge=bridge)
    emissions = []
    controller.diagnosticsChanged.connect(lambda: emissions.append(True))
    controller.refresh_diagnostics()

    assert emissions == [True]
    assert controller.hostname == platform.node().split(".")[0].upper()
    assert controller.username == getpass.getuser().upper()
    assert controller.osKernel == f"{platform.system()} {platform.release()}"
    assert controller.memoryRss > 0
    assert controller.weaverStatus == {
        "is_connected": True,
        "entity_count": 3,
        "db_path": str(db_dir / "weaver_graph.db"),
    }
    assert controller.stageMetrics == {"active_count": 2, "capacity": 4}
