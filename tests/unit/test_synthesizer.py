"""Unit tests for MemorySynthesizer background distillation worker."""

import sys
import time
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from aia_canvas.src.memory.event_ledger import EventLedger
    from aia_canvas.src.memory.profile_manager import ProfileManager
    from aia_canvas.src.memory.synthesizer import MemorySynthesizer
except ModuleNotFoundError:
    from memory.event_ledger import EventLedger
    from memory.profile_manager import ProfileManager
    from memory.synthesizer import MemorySynthesizer


@pytest.fixture
def ledger(tmp_path: Path) -> EventLedger:
    db_path = tmp_path / "events.db"
    return EventLedger(db_path)


@pytest.fixture
def profile_manager(tmp_path: Path) -> ProfileManager:
    config_dir = tmp_path / "config"
    return ProfileManager(config_dir)


@pytest.fixture
def synthesizer(ledger: EventLedger, profile_manager: ProfileManager, qapp) -> MemorySynthesizer:
    return MemorySynthesizer(
        event_ledger=ledger,
        profile_manager=profile_manager,
        idle_threshold_s=300.0,
    )


def test_idle_threshold_detection(synthesizer: MemorySynthesizer, ledger: EventLedger):
    synthesizer.idle_threshold_s = 50.0

    # Record an interaction event
    ledger.record_event("omni_query", payload={"query": "active conversation"})

    # Not idle yet: current time is within threshold
    assert synthesizer.check_idle_and_synthesize() is None
    assert synthesizer.last_compacted_event_id == 0

    # Notify event resets last_event_time
    synthesizer.last_event_time = 100.0
    synthesizer.notify_event_occurred()
    assert synthesizer.last_event_time > 100.0

    # Artificially age idle time beyond threshold
    synthesizer.last_event_time = time.time() - 60.0

    # Idle crossed and uncompacted event exists -> triggers distillation
    stats = synthesizer.check_idle_and_synthesize()
    assert stats is not None
    assert stats["events_processed"] == 1
    assert stats["hot_topics_added"] == 1
    assert synthesizer.last_compacted_event_id > 0

    # Calling again when idle without new events -> does not re-trigger
    synthesizer.last_event_time = time.time() - 60.0
    assert synthesizer.check_idle_and_synthesize() is None


def test_compaction_hot_topics_and_staged_nodes(
    synthesizer: MemorySynthesizer, ledger: EventLedger, profile_manager: ProfileManager
):
    # Log dummy queries
    ledger.record_event("omni_query", payload={"query": "neural field rendering"})
    ledger.record_event("omni_query", payload={"topic": "spatial memory graphs"})

    # Log touched canvas nodes
    ledger.record_event("select", target_id=101, archetype="document", payload={"title": "DocA.md"})
    ledger.record_event("dwell", target_id=102, archetype="code", payload={"title": "EngineWorker.py"})
    ledger.record_event("pin", target_id=103, archetype="cluster", payload={"title": "ClusterOmega"})

    # Trigger compaction
    stats = synthesizer.synthesize_sync()

    assert stats["events_processed"] == 5
    assert stats["hot_topics_added"] == 2

    # Assert queries appear in working_state.json hot topics
    state = profile_manager.get_working_state()
    assert "neural field rendering" in state["hot_topics"]
    assert "spatial memory graphs" in state["hot_topics"]

    # Assert touched nodes appear in staged nodes
    staged = state["staged_nodes"]
    assert len(staged) >= 3

    staged_titles = {n.get("title") for n in staged}
    assert {"DocA.md", "EngineWorker.py", "ClusterOmega"}.issubset(staged_titles)

    staged_node_ids = {n.get("node_id") for n in staged}
    assert {101, 102, 103}.issubset(staged_node_ids)


def test_identity_extraction(
    synthesizer: MemorySynthesizer, ledger: EventLedger, profile_manager: ProfileManager
):
    # Record explicit identity facts in payloads
    ledger.record_event(
        "identity_update",
        payload={"fact_key": "preferred_theme", "fact_value": "dark_nebula"},
    )
    ledger.record_event(
        "identity_update",
        payload={"fact_key": "entities", "fact_value": {"lead_agent": "Aether"}},
    )

    synthesizer.synthesize_sync()

    identity = profile_manager.get_identity()
    assert identity["preferred_theme"] == "dark_nebula"
    assert identity["entities"]["lead_agent"] == "Aether"
    assert identity["system_environment"]["os"] == "Linux"


def test_graceful_shutdown(
    synthesizer: MemorySynthesizer, ledger: EventLedger, profile_manager: ProfileManager
):
    synthesizer.start(check_interval_ms=1000)
    assert synthesizer.is_running is True

    ledger.record_event("omni_query", payload={"query": "shutdown topic"})

    stats = synthesizer.shutdown()

    assert synthesizer.is_running is False
    assert stats["events_processed"] == 1
    assert stats["hot_topics_added"] == 1

    state = profile_manager.get_working_state()
    assert "shutdown topic" in state["hot_topics"]


@pytest.mark.parametrize(
    "event_type,payload,expected_topic",
    [
        ("omni_query", {"query": "vector field dynamics"}, "vector field dynamics"),
        ("omni_query", {"topic": "graph layouts"}, "graph layouts"),
        ("omni_query", {"prompt": "how to build shaders"}, "how to build shaders"),
        ("omni_query", "raw query string", "raw query string"),
    ],
)
def test_query_payload_topic_extraction(
    synthesizer: MemorySynthesizer,
    ledger: EventLedger,
    profile_manager: ProfileManager,
    event_type: str,
    payload: object,
    expected_topic: str,
):
    ledger.record_event(event_type, payload=payload)
    stats = synthesizer.synthesize_sync()

    assert stats["events_processed"] == 1
    assert stats["hot_topics_added"] == 1

    state = profile_manager.get_working_state()
    assert expected_topic in state["hot_topics"]


def test_prune_expired_events_during_synthesis(
    synthesizer: MemorySynthesizer, ledger: EventLedger
):
    # Insert expired event directly (older than 7 days)
    eight_days_ago = time.time() - (8 * 86400)
    cursor = ledger.conn.cursor()
    cursor.execute(
        "INSERT INTO interaction_events (timestamp, event_type, target_id, archetype, payload) VALUES (?, ?, ?, ?, ?)",
        (eight_days_ago, "expired_event", 999, "stale", "{}"),
    )
    ledger.conn.commit()

    # Record a fresh event
    ledger.record_event("fresh_event", target_id=1)

    stats = synthesizer.synthesize_sync()
    assert stats["pruned"] == 1
    assert stats["events_processed"] >= 1

