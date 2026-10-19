"""Tests for discovery and participant extraction module."""

from pathlib import Path

from dtwin.audit.discovery import discover_directory, extract_participant_id


def test_discovery_on_synthetic_data(synthetic_data_dir: Path):
    result = discover_directory(synthetic_data_dir)

    assert result.exists is True
    assert result.is_empty is False
    assert result.total_files > 0
    assert result.fingerprint_sha256 != ""
    assert result.is_truncated is False

    # Check extension counts
    assert result.extension_counts[".csv"] >= 4
    assert result.extension_counts[".zip"] == 1
    assert result.extension_counts[".jpg"] == 1
    assert result.extension_counts[".png"] == 1

    # Image files counted but not opened
    assert result.image_count == 2
    assert result.image_counts_by_extension[".jpg"] == 1
    assert result.image_counts_by_extension[".png"] == 1

    # Archive inspected without extraction
    assert len(result.archives) == 1
    arc = result.archives[0]
    assert arc.archive_type == "zip"
    assert arc.member_count == 2
    assert arc.uncompressed_bytes is not None and arc.uncompressed_bytes > 0


def test_discovery_empty_and_missing_dir(tmp_path: Path):
    # Missing directory
    missing = tmp_path / "does_not_exist"
    res_missing = discover_directory(missing)
    assert res_missing.exists is False
    assert res_missing.is_empty is True
    assert res_missing.total_files == 0

    # Empty directory
    empty = tmp_path / "empty_dir"
    empty.mkdir()
    res_empty = discover_directory(empty)
    assert res_empty.exists is True
    assert res_empty.is_empty is True
    assert res_empty.total_files == 0


def test_discovery_deterministic_ordering(tmp_path: Path):
    d = tmp_path / "ordering_test"
    d.mkdir()
    (d / "b.csv").write_text("a\n1\n", encoding="utf-8")
    (d / "a.csv").write_text("a\n2\n", encoding="utf-8")
    (d / "c.csv").write_text("a\n3\n", encoding="utf-8")

    res1 = discover_directory(d)
    res2 = discover_directory(d)

    assert res1.tabular_files == ["a.csv", "b.csv", "c.csv"]
    assert res1.fingerprint_sha256 == res2.fingerprint_sha256


def test_participant_extraction_rules():
    # Filename digits
    pid, rule = extract_participant_id("data/cgm005.csv")
    assert pid == "005"
    assert rule == "filename_digits"

    # Parent directory digits
    pid, rule = extract_participant_id("CGMacros-042/sensor_stream.csv")
    assert pid == "042"
    assert rule == "parent_dir_digits"

    # Custom regex
    pid, rule = extract_participant_id("subject_P99_day1.csv", custom_regex=r"subject_([A-Z0-9]+)")
    assert pid == "P99"
    assert rule == "custom_regex"

    # No ID
    pid, rule = extract_participant_id("general_readme.txt")
    assert pid is None
    assert rule == "none"


def test_participant_numeric_sequence_gaps(synthetic_data_dir: Path):
    result = discover_directory(synthetic_data_dir)
    assert result.participant_summary is not None
    summary = result.participant_summary

    # In conftest, we created CGMacros-001, CGMacros-002, CGMacros-004
    # The numeric IDs are 1, 2, 4. So gap is 3!
    assert "001" in summary.distinct_identifiers or "1" in summary.distinct_identifiers
    assert "004" in summary.distinct_identifiers or "4" in summary.distinct_identifiers
    assert 3 in summary.numeric_id_gaps
