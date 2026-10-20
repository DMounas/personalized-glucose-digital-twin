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


def test_interpolation_lookahead_and_guard_band_safety():
    """Verify deterministic forward look-ahead calculation and guard-band safety (Claude Review Item A.5).

    Given delta = (t - phi_s) mod 5:
    - delta = 0 -> 0 min look-ahead (exact native vertex)
    - delta = 1 -> 4 min look-ahead (interpolates towards vertex at t + 4)
    - delta = 2 -> 3 min look-ahead (interpolates towards vertex at t + 3)
    - delta = 3 -> 2 min look-ahead (interpolates towards vertex at t + 2)
    - delta = 4 -> 1 min look-ahead (interpolates towards vertex at t + 1)
    """
    from dtwin.timeaxis import compute_interpolation_lookahead, verify_guard_band_safety

    # 1. Exact synthetic cases requested: delta=1 -> 4 min, delta=4 -> 1 min, delta=0 -> 0 min
    assert compute_interpolation_lookahead(t_minutes=6, phi_s=1, period=5) == 0  # (6-1)%5 = 0
    assert (
        compute_interpolation_lookahead(t_minutes=7, phi_s=1, period=5) == 4
    )  # (7-1)%5 = 1 -> 4 min
    assert (
        compute_interpolation_lookahead(t_minutes=8, phi_s=1, period=5) == 3
    )  # (8-1)%5 = 2 -> 3 min
    assert (
        compute_interpolation_lookahead(t_minutes=9, phi_s=1, period=5) == 2
    )  # (9-1)%5 = 3 -> 2 min
    assert (
        compute_interpolation_lookahead(t_minutes=10, phi_s=1, period=5) == 1
    )  # (10-1)%5 = 4 -> 1 min

    # Verify across all possible phases phi_s in {0, 1, 2, 3, 4}
    for phi in range(5):
        for delta in range(5):
            t = 100 + phi + delta
            expected_lookahead = 0 if delta == 0 else 5 - delta
            assert compute_interpolation_lookahead(t, phi, period=5) == expected_lookahead

    # 2. Guard-band safety verification:
    # Under a 5-minute guard band [t-5, t-10, ...], the latest native vertex used
    # never exceeds issuance time t across all issuance times and phases.
    for issuance_t in range(50, 150):
        for phi in range(5):
            assert verify_guard_band_safety(issuance_t, phi, guard_band_min=5, period=5) is True
