"""Unit tests for ProfileManager."""

import json
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from aia_canvas.src.memory.profile_manager import (
        DEFAULT_IDENTITY,
        DEFAULT_WORKING_STATE,
        ProfileManager,
    )
except ModuleNotFoundError:
    from memory.profile_manager import (
        DEFAULT_IDENTITY,
        DEFAULT_WORKING_STATE,
        ProfileManager,
    )


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return tmp_path / "config"


def test_initializes_default_files(config_dir: Path):
    assert not config_dir.exists()
    pm = ProfileManager(config_dir)

    identity_file = config_dir / "identity.json"
    working_state_file = config_dir / "working_state.json"

    assert identity_file.exists()
    assert working_state_file.exists()

    with open(identity_file, "r", encoding="utf-8") as f:
        identity_data = json.load(f)
    assert identity_data == DEFAULT_IDENTITY

    with open(working_state_file, "r", encoding="utf-8") as f:
        working_state_data = json.load(f)
    assert working_state_data == DEFAULT_WORKING_STATE

    # Test load fallback when file is deleted or corrupt
    identity_file.write_text("invalid json content {{{", encoding="utf-8")
    loaded_fallback = pm.get_identity()
    assert loaded_fallback == DEFAULT_IDENTITY


def test_atomic_write_safety(config_dir: Path):
    pm = ProfileManager(config_dir)

    test_data = {"custom_key": "valid_value", "number": 12345}
    pm.save_identity(test_data)

    identity_file = config_dir / "identity.json"
    with open(identity_file, "r", encoding="utf-8") as f:
        saved = json.load(f)

    assert saved == test_data

    # Verify no temporary files remain in config_dir
    tmp_files = list(config_dir.glob("*.tmp"))
    assert len(tmp_files) == 0


def test_update_identity(config_dir: Path):
    pm = ProfileManager(config_dir)

    # Merging persistent fact at top level without wiping defaults
    pm.update_identity("preferred_language", "en-US")
    identity = pm.get_identity()
    assert identity["preferred_language"] == "en-US"
    assert "system_environment" in identity
    assert identity["system_environment"]["os"] == "Linux"
    assert "collaboration_style" in identity

    # Merging into an existing dict key (e.g. entities)
    pm.update_identity("entities", {"primary_alias": "Atlas"})
    updated_identity = pm.get_identity()
    assert updated_identity["entities"]["primary_alias"] == "Atlas"
    assert updated_identity["preferred_language"] == "en-US"


def test_push_hot_topic(config_dir: Path):
    pm = ProfileManager(config_dir)

    # Push 3 topics
    pm.push_hot_topic("canvas_rendering")
    pm.push_hot_topic("event_ledger")
    pm.push_hot_topic("qml_shaders")

    state = pm.get_working_state()
    assert state["hot_topics"] == ["canvas_rendering", "event_ledger", "qml_shaders"]

    # Deduplication moves topic to most recent (end of list)
    pm.push_hot_topic("canvas_rendering")
    state = pm.get_working_state()
    assert state["hot_topics"] == ["event_ledger", "qml_shaders", "canvas_rendering"]

    # Add topics up to cap (max 5)
    pm.push_hot_topic("vector_sim")
    pm.push_hot_topic("spatial_docking")
    state = pm.get_working_state()
    assert len(state["hot_topics"]) == 5
    assert state["hot_topics"] == [
        "event_ledger",
        "qml_shaders",
        "canvas_rendering",
        "vector_sim",
        "spatial_docking",
    ]

    # Exceeding cap pushes out oldest FIFO item ("event_ledger")
    pm.push_hot_topic("living_memory")
    state = pm.get_working_state()
    assert len(state["hot_topics"]) == 5
    assert state["hot_topics"] == [
        "qml_shaders",
        "canvas_rendering",
        "vector_sim",
        "spatial_docking",
        "living_memory",
    ]


def test_sync_staged_nodes_and_active_project(config_dir: Path):
    pm = ProfileManager(config_dir)

    staged_payload = [
        {"node_id": "node-101", "archetype": "document", "x": 10.0, "y": 20.0},
        {"node_id": "node-202", "archetype": "cluster", "x": 50.0, "y": 80.0},
    ]

    pm.sync_staged_nodes(staged_payload)
    state = pm.get_working_state()
    assert state["staged_nodes"] == staged_payload

    pm.update_active_project("aether_memory_phase1")
    state = pm.get_working_state()
    assert state["active_project"] == "aether_memory_phase1"
    # Verify staged nodes were not lost
    assert state["staged_nodes"] == staged_payload
