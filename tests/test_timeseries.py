"""Tests for timeseries detection, sampling interval mode/median, gaps, and ambiguities."""

from pathlib import Path
from typing import Any

import pandas as pd

from dtwin.audit.timeseries import (
    analyze_timeseries_column,
    detect_candidate_columns,
)


def test_regular_5min_timeseries(synthetic_data_dir: Path, sample_config: dict[str, Any]):
    # In synthetic_data_dir, CGMacros-001 has 5-minute steps
    prof = analyze_timeseries_column(
        col_name="Timestamp",
        files=["CGMacros-001/CGMacros-001.csv"],
        data_dir=synthetic_data_dir,
        delimiters={"CGMacros-001/CGMacros-001.csv": ","},
        config=sample_config,
    )

    assert prof is not None
    assert prof.parse_success_rate == 1.0
    # 5 minutes = 300 seconds
    assert prof.mode_delta_seconds == 300.0
    assert prof.median_delta_seconds == 300.0
    assert prof.mode_delta_percent == 100.0
    assert prof.gap_count == 0
    assert prof.duplicate_count == 0
    assert prof.non_monotonic_count == 0


def test_15min_and_irregular_intervals(tmp_path: Path, sample_config: dict[str, Any]):
    d = tmp_path / "ts_test"
    d.mkdir()

    # 15-minute intervals: 0, 15, 30, 45, 60
    # then a big gap (+180m), duplicate (0m), non-monotonic (-15m)
    timestamps = [
        "2024-01-01 10:00:00",
        "2024-01-01 10:15:00",
        "2024-01-01 10:30:00",
        "2024-01-01 10:45:00",
        "2024-01-01 11:00:00",
        "2024-01-01 14:00:00",  # 3-hour gap (180 mins = 10800s > 3 * 900s)
        "2024-01-01 14:00:00",  # Duplicate timestamp (0s)
        "2024-01-01 13:45:00",  # Non-monotonic (-15m)
        "2024-01-01 14:15:00",
    ]
    df = pd.DataFrame({"record_time": timestamps, "val": range(len(timestamps))})
    df.to_csv(d / "ts15.csv", index=False)

    prof = analyze_timeseries_column(
        col_name="record_time",
        files=["ts15.csv"],
        data_dir=d,
        delimiters={"ts15.csv": ","},
        config=sample_config,
    )

    assert prof is not None
    # 15 mins = 900 seconds
    assert prof.mode_delta_seconds == 900.0
    assert prof.gap_count >= 1
    assert prof.duplicate_count >= 1
    assert prof.non_monotonic_count >= 1


def test_unparsable_column(tmp_path: Path, sample_config: dict[str, Any]):
    d = tmp_path / "unparse_test"
    d.mkdir()

    df = pd.DataFrame(
        {
            "time_string": ["not_a_time", "random_words", "still_not_time"] * 5,
            "val": range(15),
        }
    )
    df.to_csv(d / "invalid.csv", index=False)

    prof = analyze_timeseries_column(
        col_name="time_string",
        files=["invalid.csv"],
        data_dir=d,
        delimiters={"invalid.csv": ","},
        config=sample_config,
    )
    # Parse rate < 0.8 should return None (not qualified as valid timeseries)
    assert prof is None


def test_format_variation_warning(tmp_path: Path, sample_config: dict[str, Any]):
    d = tmp_path / "mixed_fmt"
    d.mkdir()

    # File 1 uses slash format, File 2 uses dash format
    df1 = pd.DataFrame({"time": ["01/01/2024 10:00", "01/01/2024 10:05"]})
    df2 = pd.DataFrame({"time": ["2024-01-01 10:00", "2024-01-01 10:05"]})
    df1.to_csv(d / "f1.csv", index=False)
    df2.to_csv(d / "f2.csv", index=False)

    prof = analyze_timeseries_column(
        col_name="time",
        files=["f1.csv", "f2.csv"],
        data_dir=d,
        delimiters={"f1.csv": ",", "f2.csv": ","},
        config=sample_config,
    )
    assert prof is not None
    assert prof.format_ambiguity_warning is not None
    assert "slash_separated" in prof.format_ambiguity_warning


def test_candidate_detection():
    cols = ["Timestamp", "Dexcom GL", "Meal_Time", "DateOfBirth", "Insulin", "HR"]
    hints = ["time", "date", "timestamp"]
    candidates = detect_candidate_columns(cols, hints)
    assert "Timestamp" in candidates
    assert "Meal_Time" in candidates
    assert "DateOfBirth" in candidates
    assert "Insulin" not in candidates
    assert "Dexcom GL" not in candidates
