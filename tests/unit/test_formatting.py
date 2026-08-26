"""
Unit tests for formatting helpers and Node display title formatting.
"""

from extractors.formatting import (
    format_dot_list,
    format_duration,
    format_meta_row,
    format_tabular_preview,
    is_generic_or_empty,
)
from models import Node


def test_format_duration():
    assert format_duration(None) == "00:00"
    assert format_duration(0) == "00:00"
    assert format_duration(-5) == "00:00"
    assert format_duration(0.4) == "0.4s"
    assert format_duration(10.0) == "00:10"
    assert format_duration(60.0) == "01:00"
    assert format_duration(3661.0) == "01:01:01"


def test_is_generic_or_empty():
    assert is_generic_or_empty(None) is True
    assert is_generic_or_empty("") is True
    assert is_generic_or_empty("   ") is True
    assert is_generic_or_empty("Unknown Artist") is True
    assert is_generic_or_empty("N/A") is True
    assert is_generic_or_empty("Smashing Pumpkins") is False


def test_format_dot_list():
    res = format_dot_list("44.1 kHz", "Unknown Artist", None, "", "16-bit PCM", "Stereo")
    assert res == "44.1 kHz<span class='dot'> • </span>16-bit PCM<span class='dot'> • </span>Stereo"


def test_format_meta_row():
    assert format_meta_row("Artist:", "Unknown Artist") == ""
    assert (
        format_meta_row("Artist:", "Smashing Pumpkins")
        == "<span class='label'>Artist:</span> <span class='val'>Smashing Pumpkins</span>"
    )


def test_format_tabular_preview():
    rows = [
        ["Col1", "Col2"],
        ["Val1", "Val2"],
    ]
    res = format_tabular_preview("Sheet1", rows)
    assert "<span class='label'>Sheet:</span> <span class='val'>Sheet1</span><br/>" in res
    assert "Col1  Col2" in res


def test_node_display_title_formatting():
    test_cases = [
        ("/path/to/.gitignore", ".gitignore", ".gitignore"),
        ("/path/to/Weekly Newsletter.pdf", "Weekly Newsletter.pdf", "Weekly Newsletter"),
        ("/path/to/test_backup.zip", "test_backup.zip", "test_backup"),
        ("/path/to/archive.tar.gz", "archive.tar.gz", "archive"),
        ("/path/to/my.notes.txt", "my.notes.txt", "my.notes"),
    ]

    for path, exp_fn, exp_dt in test_cases:
        node = Node(id=1, file_path=path)
        assert node.fileName == exp_fn
        assert node.display_title == exp_dt
        assert node.displayTitle == exp_dt

        d = node.to_dict()
        assert d["fileName"] == exp_fn
        assert d["displayTitle"] == exp_dt
