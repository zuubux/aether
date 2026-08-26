"""
Unit tests for Weaver File Extractors.
Tests archive, cloud, data/devops, envelope, extended, media, and office/vector extractors.
"""

import io
import json
import os
import stat
import tempfile
import tarfile
import zipfile
from pathlib import Path

from extractors.archive import extract_archive_manifest, get_archive_type, is_archive_file
from extractors.cloud import extract_gsuite
from extractors.config import extract_config, extract_desktop, extract_email, extract_reg, extract_vdf
from extractors.data import extract_csv, extract_json, extract_sql, extract_toml, extract_yaml
from extractors.devops import extract_compose, extract_dockerfile
from extractors.envelope import (
    detect_binary_type,
    extract_binary_envelope,
    format_permissions,
    format_size,
)
from extractors.image import extract_svg
from extractors.office import extract_pptx, extract_xlsx
from indexer.parser import EXTRACTOR_VERSION, extract_archetype_and_snippet


def test_extractor_version():
    assert EXTRACTOR_VERSION == 32


def test_archive_extractor():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        zip_path = tmp_path / "test_package.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("src/", "")
            zf.writestr("src/index.ts", "console.log('index');\n")
            zf.writestr("src/utils.ts", "export const foo = 1;\n")
            for i in range(12):
                zf.writestr(f"docs/doc_{i}.md", f"# Doc {i}\n")
            zf.writestr("package.json", '{"name": "test-pkg"}\n')

        assert is_archive_file(zip_path) is True
        assert get_archive_type(zip_path) == "ZIP"
        zip_info = extract_archive_manifest(zip_path)
        assert zip_info["file_count"] == 16
        assert zip_info["uncompressed_size"] > 0
        assert "src/" in zip_info["manifest"]
        assert "16 items •" in zip_info["summary"]

        targz_path = tmp_path / "archive_data.tar.gz"


def test_cloud_extractors():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        p_gdoc = tmp_path / "Project Blueprint.gdoc"
        p_gdoc.write_text(
            json.dumps({
                "url": "https://docs.google.com/document/d/111222333",
                "doc_id": "111222333",
                "email": "architect@aether.io",
                "resource_id": "doc_111",
            }),
            encoding="utf-8",
        )

        arch, snippet, payload = extract_gsuite(p_gdoc)
        assert arch == "DOCUMENT"
        assert payload is None
        assert "<span class='title'>Project Blueprint.gdoc</span><br/>" in snippet
        assert "<span class='label'>Cloud:</span> <span class='val'>Google Docs</span>" in snippet
        assert "<span class='dot'> • </span><span class='val'>architect@aether.io</span>" in snippet


def test_data_devops_extractors():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # JSON
        p_json = tmp_path / "config.json"
        p_json.write_text('{"name": "aether", "version": "1.0"}', encoding="utf-8")
        arch, snippet, _ = extract_json(p_json)
        assert arch == "CONFIG"
        assert "↳ name: aether" in snippet

        # YAML
        p_yaml = tmp_path / "config.yaml"
        p_yaml.write_text("app:\n  name: aether\n", encoding="utf-8")
        arch_y, snippet_y, _ = extract_yaml(p_yaml)
        assert arch_y == "CONFIG"

        # TOML
        p_toml = tmp_path / "config.toml"
        p_toml.write_text('title = "Aether"\n', encoding="utf-8")
        arch_t, snippet_t, _ = extract_toml(p_toml)
        assert arch_t == "CONFIG"

        # CSV
        p_csv = tmp_path / "data.csv"
        p_csv.write_text("col1,col2\nval1,val2\n", encoding="utf-8")
        arch_c, snippet_c, _ = extract_csv(p_csv)
        assert arch_c == "DOCUMENT"

        # SQL
        p_sql = tmp_path / "query.sql"
        p_sql.write_text("SELECT * FROM users;", encoding="utf-8")
        arch_s, snippet_s, _ = extract_sql(p_sql)
        assert arch_s == "CODE"

        # Dockerfile
        p_dock = tmp_path / "Dockerfile"
        p_dock.write_text("FROM alpine:latest\n", encoding="utf-8")
        arch_d, snippet_d, _ = extract_dockerfile(p_dock)
        assert arch_d == "CONFIG"
        assert "Base: alpine:latest" in snippet_d

        # Compose
        p_comp = tmp_path / "docker-compose.yml"
        p_comp.write_text("services:\n  app:\n    image: node:18\n", encoding="utf-8")
        arch_cp, snippet_cp, _ = extract_compose(p_comp)
        assert arch_cp == "CONFIG"
        assert "Compose (1 services)" in snippet_cp


def test_envelope_extractor():
    assert format_size(500) == "500 B"
    assert format_size(13107) == "12.8 KB"
    assert format_permissions(stat.S_IFREG | 0o644) == "rw-r--r--"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        p_pcap = tmp_path / "traffic.pcap"
        p_pcap.write_bytes(b"\xd4\xc3\xb2\xa1" + b"\x00" * 1024)
        os.chmod(p_pcap, 0o644)

        arch, snippet, payload = extract_binary_envelope(p_pcap)
        assert arch == "BINARY"
        assert payload is None
        assert "Packet Capture" in snippet


def test_extended_config_extractors():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # VDF
        p_vdf = tmp_path / "libraryfolders.vdf"
        p_vdf.write_text('"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"/home/user/.local/share/Steam"\n\t}\n}', encoding="utf-8")
        arch_vdf, snip_vdf, _ = extract_vdf(p_vdf)
        assert arch_vdf == "CONFIG"

        # REG
        p_reg = tmp_path / "system.reg"
        p_reg.write_text('[HKEY_CURRENT_USER\\Software\\Wine]\n"Version"="8.0"\n', encoding="utf-8")
        arch_reg, snip_reg, _ = extract_reg(p_reg)
        assert arch_reg == "CONFIG"
        assert "[HKEY_CURRENT_USER\\Software\\Wine]" in snip_reg


def test_office_vector_extractors():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # SVG
        p_svg = tmp_path / "icon.svg"
        p_svg.write_text('<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10"/></svg>', encoding="utf-8")
        arch_s, snip_s, _ = extract_svg(p_svg)
        assert arch_s == "IMAGE"
        assert "24×24" in snip_s

