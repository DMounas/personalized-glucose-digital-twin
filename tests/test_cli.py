"""Tests for command-line interface execution and exit codes."""

from pathlib import Path

import pytest

from dtwin.audit.cli import main


def test_cli_success_exit_code_zero(synthetic_data_dir: Path, tmp_path: Path):
    out_dir = tmp_path / "cli_out"
    ret = main(
        [
            "--data-dir",
            str(synthetic_data_dir),
            "--output-dir",
            str(out_dir),
            "--format",
            "both",
        ]
    )
    assert ret == 0
    assert (out_dir / "audit_report.json").exists()
    assert (out_dir / "audit_report.md").exists()


def test_cli_no_data_exit_code_two(tmp_path: Path):
    empty_dir = tmp_path / "non_existent_or_empty"
    out_dir = tmp_path / "cli_empty_out"

    ret = main(
        [
            "--data-dir",
            str(empty_dir),
            "--output-dir",
            str(out_dir),
        ]
    )
    assert ret == 2
    # Reports should still be generated with NO DATA FOUND status
    assert (out_dir / "audit_report.json").exists()
    assert (out_dir / "audit_report.md").exists()


def test_cli_env_var_data_dir(
    synthetic_data_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DTWIN_DATA_DIR", str(synthetic_data_dir))
    out_dir = tmp_path / "env_var_out"

    ret = main(["--output-dir", str(out_dir)])
    assert ret == 0
    assert (out_dir / "audit_report.json").exists()


def test_cli_max_files_truncation(synthetic_data_dir: Path, tmp_path: Path):
    out_dir = tmp_path / "truncation_out"
    ret = main(
        [
            "--data-dir",
            str(synthetic_data_dir),
            "--output-dir",
            str(out_dir),
            "--max-files",
            "2",
        ]
    )
    assert ret == 0
    json_path = out_dir / "audit_report.json"
    assert json_path.exists()

    import json

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["truncation"]["is_truncated"] is True
    assert data["truncation"]["max_files_limit"] == 2
