"""Tests for privacy guards and planted sentinel leakage prevention."""

from pathlib import Path

import pytest

from dtwin.audit.cli import run_audit
from tests.conftest import (
    PLANTED_SENTINEL_NAME,
    PLANTED_SENTINEL_PATH,
    PLANTED_SENTINEL_STRING,
)


def test_planted_sentinels_never_leak(
    synthetic_data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
):
    """Assert that planted patient names, photo paths, and secrets never leak.

    Checks JSON report, Markdown report, stdout, and stderr.
    """
    output_dir = tmp_path / "privacy_reports"
    output_dir.mkdir()

    # Execute full audit run
    ret = run_audit(
        data_dir=synthetic_data_dir,
        output_dir=output_dir,
        output_format="both",
    )
    assert ret == 0

    captured = capsys.readouterr()
    stdout_text = captured.out
    stderr_text = captured.err

    json_report_path = output_dir / "audit_report.json"
    md_report_path = output_dir / "audit_report.md"

    assert json_report_path.exists()
    assert md_report_path.exists()

    json_content = json_report_path.read_text(encoding="utf-8")
    md_content = md_report_path.read_text(encoding="utf-8")

    all_outputs = [
        ("stdout", stdout_text),
        ("stderr", stderr_text),
        ("audit_report.json", json_content),
        ("audit_report.md", md_content),
    ]

    sentinels = [
        ("PLANTED_SENTINEL_STRING", PLANTED_SENTINEL_STRING),
        ("PLANTED_SENTINEL_PATH", PLANTED_SENTINEL_PATH),
        ("PLANTED_SENTINEL_NAME", PLANTED_SENTINEL_NAME),
    ]

    for stream_name, content in all_outputs:
        for s_name, s_val in sentinels:
            assert s_val not in content, (
                f"Privacy leak detected: {s_name} ('{s_val}') leaked into {stream_name}!"
            )
