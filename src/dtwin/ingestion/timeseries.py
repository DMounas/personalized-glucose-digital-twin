"""Timeseries utilities for CGMacros relative time calculation and coverage metrics.

Calculates participant relative elapsed time (elapsed from first valid timestamp)
without generating calendar-based features (e.g. month, day of week), strictly preserving
de-identification boundaries while allowing continuous physiological modeling.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def calculate_relative_time(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    sort_chronologically: bool = True,
) -> pd.DataFrame:
    """Calculate participant relative time from the first valid timestamp.

    Adds:
        - relative_time_seconds: Elapsed seconds from t0 (float)
        - relative_time_minutes: Elapsed minutes from t0 (float)
        - day_offset: Elapsed fractional days from t0 (float)

    Strictly avoids calendar features (month, day of week, day of year, season)
    because dates were randomized by +/- N days (365 < N < 720) for de-identification.
    """
    if timestamp_col not in df.columns:
        raise KeyError(
            f"Timestamp column '{timestamp_col}' not found in DataFrame columns: {list(df.columns)}"
        )

    result = df.copy()
    ts_series = pd.to_datetime(result[timestamp_col], errors="coerce")

    if ts_series.dropna().empty:
        raise ValueError(f"No valid datetime values could be parsed from column '{timestamp_col}'")

    if sort_chronologically and not ts_series.is_monotonic_increasing:
        result = result.sort_values(by=timestamp_col).reset_index(drop=True)
        ts_series = pd.to_datetime(result[timestamp_col], errors="coerce")

    # t0 is the first valid timestamp
    t0 = ts_series.dropna().iloc[0]

    # Calculate elapsed delta from t0
    delta = ts_series - t0
    delta_seconds = delta.dt.total_seconds()

    result["relative_time_seconds"] = delta_seconds
    result["relative_time_minutes"] = delta_seconds / 60.0
    result["day_offset"] = delta_seconds / 86400.0

    return result


def calculate_timeseries_metrics(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    gap_multiplier: float = 3.0,
) -> dict[str, Any]:
    """Calculate sampling cadence, sensor availability, and coverage metrics."""
    if timestamp_col not in df.columns:
        return {"error": f"Missing column {timestamp_col}"}

    total_rows = len(df)
    if total_rows == 0:
        return {"total_rows": 0, "duration_days": 0.0}

    ts = pd.to_datetime(df[timestamp_col], errors="coerce").dropna()
    if len(ts) < 2:
        return {"total_rows": total_rows, "duration_days": 0.0}

    deltas_sec = ts.diff().dropna().dt.total_seconds()
    mode_delta = float(deltas_sec.mode().iloc[0]) if not deltas_sec.empty else 60.0
    median_delta = float(deltas_sec.median()) if not deltas_sec.empty else 60.0
    mode_match_count = int((deltas_sec == mode_delta).sum()) if not deltas_sec.empty else 0
    mode_pct = (mode_match_count / len(deltas_sec) * 100.0) if len(deltas_sec) > 0 else 0.0

    # Gap detection
    gap_threshold = mode_delta * gap_multiplier
    gaps_count = int((deltas_sec > gap_threshold).sum()) if not deltas_sec.empty else 0

    duration_sec = float((ts.max() - ts.min()).total_seconds())
    duration_days = duration_sec / 86400.0

    # Sensor coverage
    libre_present = int(df["libre_gl"].notnull().sum()) if "libre_gl" in df.columns else 0
    dexcom_present = int(df["dexcom_gl"].notnull().sum()) if "dexcom_gl" in df.columns else 0
    both_cgm = (
        int((df["libre_gl"].notnull() & df["dexcom_gl"].notnull()).sum())
        if "libre_gl" in df.columns and "dexcom_gl" in df.columns
        else 0
    )
    hr_present = int(df["heart_rate"].notnull().sum()) if "heart_rate" in df.columns else 0

    return {
        "total_rows": total_rows,
        "duration_days": round(duration_days, 2),
        "mode_delta_seconds": round(mode_delta, 1),
        "median_delta_seconds": round(median_delta, 1),
        "mode_pct": round(mode_pct, 2),
        "gaps_count": gaps_count,
        "libre_coverage_pct": round(libre_present / total_rows * 100.0, 2),
        "dexcom_coverage_pct": round(dexcom_present / total_rows * 100.0, 2),
        "dual_cgm_overlap_pct": round(both_cgm / total_rows * 100.0, 2),
        "hr_coverage_pct": round(hr_present / total_rows * 100.0, 2),
    }
