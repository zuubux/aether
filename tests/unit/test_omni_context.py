import sqlite3
import pytest
from pathlib import Path
from aia_canvas.src.omni.context import AetherContextBuilder

@pytest.fixture
def memory_db_path(tmp_path):
    db_path = tmp_path / "memory.db"
    
    with sqlite3.connect(f"file:{db_path}?mode=rwc", uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                category TEXT,
                key TEXT,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        facts = [
            ("project", "PythonVersion", "We are using Python 3.10", "2023-01-01 10:00:00"),
            ("preferences", "Theme", "Dark Mode", "2023-01-02 10:00:00"),
            ("architecture", "Database", "SQLite with WAL mode", "2023-01-03 10:00:00"),
            ("random", "DogName", "Fido", "2023-01-04 10:00:00"),
            ("random", "CatName", "Whiskers", "2023-01-05 10:00:00"),
            ("random", "BirdName", "Tweety", "2023-01-06 10:00:00"),
        ]
        cursor.executemany("INSERT INTO facts (category, key, value, updated_at) VALUES (?, ?, ?, ?)", facts)
        conn.commit()
    return db_path

class DummyProfileManager:
    def get_identity(self):
        return {
            "system_environment": {"os": "linux"},
            "collaboration_style": {"tone": "helpful"},
            "entities": {"User": "Nic"}
        }
    def get_working_state(self):
        return {}

def test_query_relevant_facts_with_keywords(memory_db_path):
    builder = AetherContextBuilder(memory_db_path=memory_db_path)
    
    # "Database" is a keyword (len > 3)
    facts = builder._query_relevant_facts(query_text="What database are we using?")
    
    assert len(facts) > 0
    # The architecture fact should be retrieved
    assert any(f["key"] == "Database" for f in facts)

def test_query_relevant_facts_fallback_to_recent(memory_db_path):
    builder = AetherContextBuilder(memory_db_path=memory_db_path)
    
    # "a" is not a keyword (len <= 3), no keywords found
    facts = builder._query_relevant_facts(query_text="a", limit=3)
    
    assert len(facts) == 3
    # Ordered by updated_at DESC, so Tweety, Whiskers, Fido
    keys = [f["key"] for f in facts]
    assert keys == ["BirdName", "CatName", "DogName"]

def test_graceful_fallback_no_db(tmp_path):
    non_existent_db = tmp_path / "does_not_exist.db"
    builder = AetherContextBuilder(memory_db_path=non_existent_db, profile_manager=DummyProfileManager())
    
    # Should not crash, just return default identity
    ground_truth = builder.format_ground_truth(query_text="Hello")
    assert "[GROUND TRUTH MEMORY]" in ground_truth
    assert "Environment: os: linux" in ground_truth
    assert "Dynamic Context" not in ground_truth

def test_token_budget_constraint(memory_db_path):
    # Insert a very large fact
    with sqlite3.connect(f"file:{memory_db_path}?mode=rwc", uri=True) as conn:
        cursor = conn.cursor()
        large_value = "Long value " * 1000
        cursor.execute("INSERT INTO facts (category, key, value, updated_at) VALUES (?, ?, ?, ?)", ("huge", "HugeKey", large_value, "2023-01-07 10:00:00"))
        conn.commit()

    builder = AetherContextBuilder(memory_db_path=memory_db_path, profile_manager=DummyProfileManager())
    
    # Fetch ground truth which includes the large fact
    ground_truth = builder.format_ground_truth(query_text="HugeKey")
    
    # Estimate tokens
    tokens = builder._estimate_tokens(ground_truth)
    
    # Ensure it's bounded by 450
    assert tokens <= 450
    assert "HugeKey" in ground_truth
