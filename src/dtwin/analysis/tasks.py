"""Candidate glucose task feasibility, descriptive difficulty, and effective sample size analysis (R2 corrected).

Time semantics (T1-T7):
- Forecast horizons evaluated strictly at elapsed-time offsets (t, t + h) within contiguous runs.
- Positional slicing on dropna() arrays is strictly forbidden (zero gap-bridging).
- Excursion episodes require run-bounded hysteresis margins and boundary-censoring accounting.
- Deterministic window enumeration strictly within contiguous runs.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from dtwin.timeaxis import (
    detect_excursion_episodes_run_bounded,
    enumerate_runs,
    enumerate_windows,
    pairs_at_offset,
)


def evaluate_forecast_difficulty(
    data: pd.DataFrame | np.ndarray | pd.Series,
    col_or_horizons: str | list[int] | tuple[int, ...] = "Dexcom GL",
    horizons: tuple[int, ...] | list[int] = (30, 60),
    timestamps: Any | None = None,
) -> dict[int, dict[str, float]]:
    """Compute empirical distribution of absolute glucose changes at specified horizons.

    Explicitly labeled as 'descriptive, not a model'.
    Guaranteed: evaluated strictly at elapsed-time offset within contiguous runs.
    """
    if isinstance(data, pd.DataFrame):
        df = data
        col = str(col_or_horizons) if isinstance(col_or_horizons, str) else "Dexcom GL"
        eval_horizons = horizons if isinstance(col_or_horizons, str) else list(col_or_horizons)
    else:
        # Array or Series
        vals = (
            data.to_numpy(dtype=float)
            if isinstance(data, pd.Series)
            else np.asarray(data, dtype=float)
        )
        eval_horizons = horizons if isinstance(col_or_horizons, str) else list(col_or_horizons)
        if timestamps is not None:
            ts = pd.to_datetime(timestamps)
        elif isinstance(data, pd.Series) and isinstance(data.index, pd.DatetimeIndex):
            ts = data.index
        else:
            ts = pd.date_range("2020-01-01 00:00:00", periods=len(vals), freq="1min")
        df = pd.DataFrame({"Timestamp": ts, "GL": vals})
        col = "GL"

    out: dict[int, dict[str, float]] = {}

    for h in eval_horizons:
        y_t, y_h, meta = pairs_at_offset(df, col, horizon_min=h)
        if len(y_t) == 0:
            continue
        deltas = np.abs(y_h - y_t)
        out[h] = {
            "mean_delta_mg_dl": round(float(np.mean(deltas)), 2),
            "median_delta_mg_dl": round(float(np.median(deltas)), 2),
            "q25_delta_mg_dl": round(float(np.percentile(deltas, 25)), 2),
            "q75_delta_mg_dl": round(float(np.percentile(deltas, 75)), 2),
            "q90_delta_mg_dl": round(float(np.percentile(deltas, 90)), 2),
            "samples_evaluated": len(deltas),
        }

    return out


def count_excursion_episodes(
    series: np.ndarray | pd.Series,
    threshold: float,
    kind: str = "hyper",
    min_persistence: int = 15,
    min_separation: int = 30,
    hysteresis_margin: float = 5.0,
) -> int:
    """Count distinct excursion episodes requiring persistence and hysteresis release within run.

    Backward-compatible wrapper around detect_excursion_episodes_run_bounded.
    """
    vals = (
        series.to_numpy(dtype=float)
        if isinstance(series, pd.Series)
        else np.asarray(series, dtype=float)
    )
    # Split by NaNs into contiguous segments to prevent gap-merging
    valid_mask = ~np.isnan(vals)
    valid_idx = np.where(valid_mask)[0]
    if len(valid_idx) < min_persistence:
        return 0

    total_episodes = 0
    cur_start = 0
    for i in range(1, len(valid_idx)):
        if valid_idx[i] != valid_idx[i - 1] + 1:
            segment = vals[valid_idx[cur_start] : valid_idx[i - 1] + 1]
            ep, _ = detect_excursion_episodes_run_bounded(
                segment,
                threshold=threshold,
                kind=kind,
                min_persistence=min_persistence,
                min_release=min_separation,
                hysteresis_margin=hysteresis_margin,
            )
            total_episodes += ep
            cur_start = i

    segment = vals[valid_idx[cur_start] : valid_idx[-1] + 1]
    ep, _ = detect_excursion_episodes_run_bounded(
        segment,
        threshold=threshold,
        kind=kind,
        min_persistence=min_persistence,
        min_release=min_separation,
        hysteresis_margin=hysteresis_margin,
    )
    total_episodes += ep

    return total_episodes


def evaluate_cohort_excursion_episodes(
    df: pd.DataFrame,
    col: str,
    threshold: float,
    kind: str = "hyper",
    min_persistence: int = 15,
    min_release: int = 10,
    hysteresis_margin: float = 5.0,
) -> tuple[int, int]:
    """Evaluate excursion episodes across all contiguous runs in a DataFrame.

    Returns:
    (total_episodes, total_boundary_censored)
    """
    runs = enumerate_runs(df)
    total_episodes = 0
    total_censored = 0

    for r in runs:
        r_slice = df[col].iloc[r.start_index : r.end_index + 1].to_numpy(dtype=float)
        ep, cens = detect_excursion_episodes_run_bounded(
            r_slice,
            threshold=threshold,
            kind=kind,
            min_persistence=min_persistence,
            min_release=min_release,
            hysteresis_margin=hysteresis_margin,
        )
        total_episodes += ep
        total_censored += cens

    return total_episodes, total_censored


def count_non_overlapping_windows(
    df: pd.DataFrame,
    window_minutes: int = 120,
) -> int:
    """Count non-overlapping windows strictly within contiguous runs (zero gap-bridging)."""
    sensor_col = "Dexcom GL" if "Dexcom GL" in df.columns else df.columns[1]
    windows = enumerate_windows(
        df,
        input_min=window_minutes,
        horizon_min=0,
        stride_min=window_minutes,
        sensor_col=sensor_col,
        strict_no_nulls=False,
    )
    return len(windows)
