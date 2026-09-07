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
def synthesizer(ledger: EventLedger, profile_manager: ProfileManager, tmp_path: Path, qapp) -> MemorySynthesizer:
    return MemorySynthesizer(
        event_ledger=ledger,
        profile_manager=profile_manager,
        idle_threshold_s=300.0,
        memory_db_path=tmp_path / "memory.db"
    )


def test_idle_threshold_detection(synthesizer: MemorySynthesizer, ledger: EventLedger):
    synthesizer.idle_threshold_s = 50.0

    # Record an interaction event
    ledger.record_event("omni_query", payload={"query": "active conversation topic extraction"})

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
    ledger.record_event("omni_query", payload={"query": "neural field rendering techniques"})
    ledger.record_event("omni_query", payload={"topic": "spatial memory graphs exploration"})

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
    assert "neural field rendering techniques" in state["hot_topics"]
    assert "spatial memory graphs exploration" in state["hot_topics"]

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

    ledger.record_event("omni_query", payload={"query": "shutdown topic for testing"})

    stats = synthesizer.shutdown()

    assert synthesizer.is_running is False
    assert stats["events_processed"] == 1
    assert stats["hot_topics_added"] == 1

    state = profile_manager.get_working_state()
    assert "shutdown topic for testing" in state["hot_topics"]


@pytest.mark.parametrize(
    "event_type,payload,expected_topic",
    [
        ("omni_query", {"query": "vector field dynamics optimization"}, "vector field dynamics optimization"),
        ("omni_query", {"topic": "graph layouts for visual nodes"}, "graph layouts for visual nodes"),
        ("omni_query", {"prompt": "how to build shaders"}, "how to build shaders"),
        ("omni_query", "raw query string test case", "raw query string test case"),
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


def test_heuristic_fact_and_project_extraction(
    synthesizer: MemorySynthesizer, ledger: EventLedger, profile_manager: ProfileManager
):
    # Log multiple queries to test fact extraction, project updates, and trivial rejection
    ledger.record_event("omni_query", payload={"query": "remember that primary_gpu is RTX 4090"})
    ledger.record_event("omni_query", payload={"query": "switch active project to Aether Core"})
    
    # Trivial queries
    ledger.record_event("omni_query", payload={"query": "hello"})
    ledger.record_event("omni_query", payload={"query": "thanks for the help"})
    ledger.record_event("omni_query", payload={"query": "can you help me fix this"})
    
    # Nested fact
    ledger.record_event("omni_query", payload={"query": "note that system environment architecture is x86_64"})
    # Substantive query
    ledger.record_event("omni_query", payload={"query": "cuda kernel optimization for fluid simulation"})
    
    stats = synthesizer.synthesize_sync()
    
    # Check facts
    identity = profile_manager.get_identity()
    assert identity.get("primary_gpu") == "RTX 4090"
    assert identity.get("system_environment", {}).get("architecture") == "x86_64"
    
    # Check active project
    state = profile_manager.get_working_state()
    assert state.get("active_project") == "Aether Core"
    
    # Check hot topics
    hot_topics = state.get("hot_topics", [])
    assert "cuda kernel optimization for fluid simulation" in hot_topics
    
    # Explicitly verify these are not added
    assert "hello" not in hot_topics
    assert "thanks for the help" not in hot_topics
    assert "can you help me fix this" not in hot_topics
    
    assert stats.get("facts_extracted") == 2

def test_semantic_distillation_threshold_and_application(
    synthesizer: MemorySynthesizer, ledger: EventLedger, profile_manager: ProfileManager
):
    invocations = []

    def mock_distiller(batch):
        invocations.append(batch)
        return {
            "active_project": "Project Nova",
            "facts_learned": {"user_preference": "dark mode"},
            "facts_retracted": ["old_fact"]
        }

    synthesizer.llm_distiller = mock_distiller
    profile_manager.update_identity("old_fact", "outdated value")

    # 1. Less than 3 queries - NEVER invoked
    ledger.record_event("omni_query", payload={"query": "Q1"})
    ledger.record_event("omni_query", payload={"query": "Q2"})
    ledger.record_event("click", payload={"target": "button"})  # Non-query event

    stats = synthesizer.synthesize_sync()
    assert stats["semantic_distillation_performed"] is False
    assert len(invocations) == 0

    # 2. Add 3rd query -> >= 3 uncompacted queries
    ledger.record_event("omni_query", payload={"query": "Q3"})
    ledger.record_event("omni_query", payload={"query": "Q4"})
    ledger.record_event("omni_query", payload={"query": "Q5"})

    stats = synthesizer.synthesize_sync()
    assert stats["semantic_distillation_performed"] is True
    assert len(invocations) == 1
    assert len(invocations[0]) == 3
    assert invocations[0][0]["text"] == "Q3"
    assert invocations[0][1]["text"] == "Q4"
    assert invocations[0][2]["text"] == "Q5"

    # 3. Verify mock output applied
    state = profile_manager.get_working_state()
    assert state.get("active_project") == "Project Nova"

    identity = profile_manager.get_identity()
    assert identity.get("user_preference") == "dark mode"
    assert "old_fact" not in identity

    # 4. Error handling
    def mock_distiller_error(batch):
        raise ValueError("Simulated timeout or error")

    synthesizer.llm_distiller = mock_distiller_error
    ledger.record_event("omni_query", payload={"query": "Q6"})
    ledger.record_event("omni_query", payload={"query": "Q7"})
    ledger.record_event("omni_query", payload={"query": "Q8"})

    stats = synthesizer.synthesize_sync()
    assert stats["semantic_distillation_performed"] is False
    assert synthesizer.engineState == "LATENT"


def test_long_term_memory_db_persistence(synthesizer: MemorySynthesizer, ledger: EventLedger, tmp_path: Path):
    import sqlite3
    db_path = tmp_path / "memory.db"
    weaver_db_path = tmp_path / "weaver_graph.db"
    
    # Log an explicit fact that should map to category general
    ledger.record_event("omni_query", payload={"query": "my preferred_ide is VS Code"})
    # Log an explicit fact with category routing
    ledger.record_event("omni_query", payload={"query": "remember that system_environment_os is Linux"})
    
    # Log active project so session summary is created
    ledger.record_event("omni_query", payload={"query": "switch active project to Aether Graph"})
    
    # Log touched node
    ledger.record_event("select", target_id=1, archetype="document", payload={"title": "DocA.md", "file_path": "/fake/DocA.md"})
    
    # Run compaction
    stats = synthesizer.synthesize_sync()
    
    assert stats["facts_persisted"] == 2
    assert stats["episodes_created"] == 1
    assert stats["file_refs_linked"] == 1
    
    # Check the database
    with sqlite3.connect(str(db_path)) as conn:
        # Check general fact
        cur = conn.execute("SELECT category, value FROM facts WHERE key = 'preferred_ide'")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "general"
        assert row[1] == "VS Code"
        
        # Check categorized fact
        cur = conn.execute("SELECT category, value FROM facts WHERE key = 'os'")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "system_environment"
        assert row[1] == "Linux"
        
        # Verify episode was created
        cur = conn.execute("SELECT summary, active_project FROM episodes")
        episode_rows = cur.fetchall()
        assert len(episode_rows) == 1
        assert "Aether Graph" in episode_rows[0][0] or "Aether Graph" in episode_rows[0][1]
        
        # Verify episode file ref
        cur = conn.execute("SELECT file_path, relation FROM episode_file_refs")
        ref_rows = cur.fetchall()
        assert len(ref_rows) == 1
        assert ref_rows[0][0] == "/fake/DocA.md"
        assert ref_rows[0][1] == "referenced"

    # Verify zero writes to weaver graph
    assert not weaver_db_path.exists()

