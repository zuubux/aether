"""
Unit tests for Spatial Context Assembler, Data Models & Persona
"""

import os
from pathlib import Path
import sqlite3
import pytest

from omni.models import SpatialContext
from omni.context import assemble_spatial_context, format_spatial_envelope
from omni.engines.conversation.persona import AETHER_SYSTEM_INSTRUCTION



def test_spatial_context_dataclass_defaults():
    ctx = SpatialContext()
    assert ctx.target_path is None
    assert ctx.mime_type is None
    assert ctx.file_size == 0
    assert ctx.total_lines == 0
    assert ctx.head_excerpt == ""
    assert ctx.is_truncated is False
    assert ctx.remaining_lines == 0
    assert ctx.is_binary is False
    assert ctx.graph_neighbors == []
    assert ctx.cwd == ""
    assert ctx.timestamp == ""
    assert ctx.node_count == 0


def test_text_file_head_slicing_and_truncation(tmp_path):
    # 1. Test text file with > 50 lines
    file_path = tmp_path / "large_sample.py"
    lines = [f"# Line {i}\n" for i in range(1, 76)]  # 75 lines
    file_path.write_text("".join(lines), encoding="utf-8")

    ctx = assemble_spatial_context(focused_node_id=str(file_path))

    assert ctx.target_path == str(file_path.resolve())
    assert ctx.is_binary is False
    assert ctx.total_lines == 75
    assert ctx.is_truncated is True
    assert ctx.remaining_lines == 25
    assert len(ctx.head_excerpt.splitlines()) == 50

    envelope = format_spatial_envelope(ctx)
    assert "[Spatial Context]" in envelope
    assert "Truncated: True (25 remaining lines)" in envelope
    assert str(file_path.resolve()) in envelope

    # 2. Test text file with <= 50 lines
    small_file = tmp_path / "small_sample.txt"
    small_lines = [f"Line {i}\n" for i in range(1, 11)]  # 10 lines
    small_file.write_text("".join(small_lines), encoding="utf-8")

    ctx_small = assemble_spatial_context(focused_node_id=str(small_file))
    assert ctx_small.total_lines == 10
    assert ctx_small.is_truncated is False
    assert ctx_small.remaining_lines == 0
    assert ctx_small.head_excerpt == "".join(small_lines)

    envelope_small = format_spatial_envelope(ctx_small)
    assert "Truncated: False" in envelope_small


def test_text_file_byte_truncation_guardrail(tmp_path):
    # Test line length exceeding 2048 bytes
    file_path = tmp_path / "wide_line.txt"
    wide_line = "A" * 3000 + "\n"  # 3000 chars in single line
    file_path.write_text(wide_line, encoding="utf-8")

    ctx = assemble_spatial_context(focused_node_id=str(file_path))
    assert ctx.is_truncated is True
    assert len(ctx.head_excerpt.encode("utf-8")) <= 2048


def test_binary_asset_metadata_handling(tmp_path):
    # Create binary asset with null bytes
    bin_file = tmp_path / "sample_image.png"
    bin_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    bin_file.write_bytes(bin_content)

    ctx = assemble_spatial_context(focused_node_id=str(bin_file))

    assert ctx.target_path == str(bin_file.resolve())
    assert ctx.is_binary is True
    assert ctx.head_excerpt == ""
    assert ctx.total_lines == 0
    assert ctx.remaining_lines == 0
    assert ctx.file_size == len(bin_content)

    envelope = format_spatial_envelope(ctx)
    assert "Binary Asset" in envelope



def test_sqlite_neighbor_traversal(tmp_path):
    db_path = tmp_path / "test_weaver_graph.db"
    target_file = tmp_path / "target.py"
    target_file.write_text("print('hello')", encoding="utf-8")
    target_str = str(target_file.resolve())

    neighbor1 = str((tmp_path / "dep1.py").resolve())
    neighbor2 = str((tmp_path / "dep2.py").resolve())

    # Create SQLite database with nodes & edges schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            edge_type TEXT NOT NULL,
            weight REAL DEFAULT 1.0
        );
    """)

    cursor.execute("INSERT INTO nodes (file_path) VALUES (?)", (target_str,))
    target_id = cursor.lastrowid
    cursor.execute("INSERT INTO nodes (file_path) VALUES (?)", (neighbor1,))
    n1_id = cursor.lastrowid
    cursor.execute("INSERT INTO nodes (file_path) VALUES (?)", (neighbor2,))
    n2_id = cursor.lastrowid

    cursor.execute("INSERT INTO edges (source_id, target_id, edge_type, weight) VALUES (?, ?, 'explicit', 0.9)", (target_id, n1_id))
    cursor.execute("INSERT INTO edges (source_id, target_id, edge_type, weight) VALUES (?, ?, 'semantic', 0.8)", (n2_id, target_id))
    conn.commit()
    conn.close()

    ctx = assemble_spatial_context(focused_node_id=target_str, graph_db_path=str(db_path))

    assert len(ctx.graph_neighbors) == 2
    paths = [n["neighbor_path"] for n in ctx.graph_neighbors]
    assert neighbor1 in paths
    assert neighbor2 in paths

    envelope = format_spatial_envelope(ctx)
    assert "- Graph Neighbors:" in envelope
    assert neighbor1 in envelope
    assert "explicit" in envelope


def test_sqlite_resilience_missing_db_or_tables(tmp_path):
    target_file = tmp_path / "dummy.py"
    target_file.write_text("x = 1", encoding="utf-8")

    # 1. Non-existent DB path
    ctx = assemble_spatial_context(focused_node_id=str(target_file), graph_db_path="/tmp/non_existent_db_12345.db")
    assert ctx.graph_neighbors == []

    # 2. Corrupted / Empty DB
    empty_db = tmp_path / "empty.db"
    empty_db.write_text("not a sqlite db", encoding="utf-8")
    ctx_empty = assemble_spatial_context(focused_node_id=str(target_file), graph_db_path=str(empty_db))
    assert ctx_empty.graph_neighbors == []


def test_empty_focus_canvas_telemetry(tmp_path):
    db_path = tmp_path / "canvas_db.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE nodes (id INTEGER PRIMARY KEY, file_path TEXT)")
    conn.execute("INSERT INTO nodes (file_path) VALUES ('a'), ('b'), ('c')")
    conn.commit()
    conn.close()

    ctx = assemble_spatial_context(focused_node_id=None, graph_db_path=str(db_path))

    assert ctx.target_path is None
    assert ctx.cwd == os.getcwd()
    assert ctx.timestamp != ""
    assert ctx.node_count == 3

    envelope = format_spatial_envelope(ctx)
    assert "[Spatial Context]" in envelope
    assert "Target Node: None (Empty Canvas)" in envelope
    assert "Canvas Node Count: 3" in envelope


def test_persona_cleanliness_and_content():
    persona_file = Path(__file__).parent.parent.parent / "aia_canvas" / "src" / "omni" / "engines" / "conversation" / "persona.py"
    assert persona_file.exists()

    lines = persona_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) < 35, f"persona.py must be < 35 lines, got {len(lines)}"

    assert isinstance(AETHER_SYSTEM_INSTRUCTION, str)
    assert "Aether" in AETHER_SYSTEM_INSTRUCTION
    assert "Target Telemetry" in AETHER_SYSTEM_INSTRUCTION
