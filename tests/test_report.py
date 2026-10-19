"""Tests for audit report schema stability and markdown formatting."""

import json
from pathlib import Path

from dtwin.audit.cli import main


def test_report_json_schema_stability(synthetic_data_dir: Path, tmp_path: Path):
    out_dir = tmp_path / "schema_out"
    main(
        [
            "--data-dir",
            str(synthetic_data_dir),
            "--output-dir",
            str(out_dir),
        ]
    )

    json_path = out_dir / "audit_report.json"
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    required_keys = [
        "schema_version",
        "tool_version",
        "audit_timestamp_utc",
        "git_commit",
        "environment",
        "status",
        "data_dir",
        "data_dir_fingerprint",
        "config_in_effect",
        "truncation",
        "discovery_summary",
        "schema_families",
        "timeseries_analysis",
        "warnings",
        "what_this_audit_does_not_verify",
    ]

    for k in required_keys:
        assert k in data, f"Required schema key '{k}' missing from audit_report.json"

    assert data["schema_version"] == "1.0.0"
    assert data["status"] == "DATA PRESENT"
    assert len(data["what_this_audit_does_not_verify"]) == 5


def test_markdown_banner_and_disclaimer(synthetic_data_dir: Path, tmp_path: Path):
    out_dir = tmp_path / "md_banner_out"
    main(
        [
            "--data-dir",
            str(synthetic_data_dir),
            "--output-dir",
            str(out_dir),
        ]
    )

    md_path = out_dir / "audit_report.md"
    content = md_path.read_text(encoding="utf-8")

    assert "# Dataset Audit Report" in content
    assert "> **STATUS: DATA PRESENT**" in content
    assert "## What This Audit Does NOT Verify" in content
    assert "Semantic correctness of values" in content
    assert "Clinical validity" in content


def test_markdown_no_data_banner(tmp_path: Path):
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    out_dir = tmp_path / "md_empty_banner_out"

    main(
        [
            "--data-dir",
            str(empty_dir),
            "--output-dir",
            str(out_dir),
        ]
    )

    md_path = out_dir / "audit_report.md"
    content = md_path.read_text(encoding="utf-8")

    assert "# Dataset Audit Report" in content
    assert "> **STATUS: NO DATA FOUND**" in content
    assert "Acquisition Guidance" in content
    assert "What This Audit Does NOT Verify" in content
