"""Time semantics and contiguous run-based time-series primitives (T1–T7) (R3 corrected).

Enforces:
T1: Time is the actual timestamp. Row position is never an elapsed-time coordinate.
T2: Three explicit states per sensor: valid value, explicit null, absent timestamp.
T3: Run segmentation: maximal sequence of rows with consecutive delta == 60s.
T4: Explicit elapsed-time horizon pairs (t, t + h) strictly within the same contiguous run.
T5: No dropna() + positional slicing. Explicit helper functions for differencing and windows.
T6: Native-grid phase is an elapsed-time quantity (t_min mod p) evaluated per run.
T7: Configurable run length and bend criteria for inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ContiguousRun:
    """A maximal continuous sequence of 1-minute rows where delta == 60 seconds."""

    run_id: int
    start_index: int  # row index in parent DataFrame
    end_index: int  # inclusive row index in parent DataFrame
    start_time: pd.Timestamp
    end_time: pd.Timestamp
    start_elapsed_min: int  # (start_time - participant_t0) in minutes
    end_elapsed_min: int  # (end_time - participant_t0) in minutes
    length_minutes: int  # number of rows/minutes in this run


@dataclass
class ExcursionDetectionResult:
    """Detailed result of run-bounded excursion detection with hysteresis and censoring.

    Censoring definitions:
    - left_censored: Excursion episode was already in progress at the very start of the
      contiguous run (index 0). The true initiation timestamp and pre-recording duration are unknown.
    - right_censored: Excursion episode was still in progress when the contiguous run ended
      (or when interrupted by an unrecorded gap / excessive consecutive nulls).
      The true resolution timestamp and post-recording duration are unknown.
    - boundary_censored: Equal to right_censored (preserved for backward compatibility).
    """

    total_episodes: int
    boundary_censored: int
    durations: list[int]
    left_censored: int = 0
    right_censored: int = 0

    def __post_init__(self) -> None:
        if self.right_censored == 0 and self.boundary_censored > 0:
            self.right_censored = self.boundary_censored
        elif self.boundary_censored == 0 and self.right_censored > 0:
            self.boundary_censored = self.right_censored

    def __iter__(self):
        """Enable tuple unpacking for backward compatibility: ep, cens = res."""
        return iter((self.total_episodes, self.boundary_censored))

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int) -> int:
        return (self.total_episodes, self.boundary_censored)[index]


def compute_elapsed_minutes(
    timestamps: pd.Series | pd.DatetimeIndex,
    reference_t0: pd.Timestamp | None = None,
) -> np.ndarray:
    """Compute elapsed minutes from reference_t0, verifying integrality (T1)."""
    if len(timestamps) == 0:
        return np.array([], dtype=np.int64)

    if isinstance(timestamps, pd.DatetimeIndex):
        t0 = reference_t0 if reference_t0 is not None else timestamps[0]
        deltas = (timestamps - t0).total_seconds() / 60.0
        arr = np.asarray(deltas)
    else:
        ts = pd.to_datetime(timestamps)
        t0 = reference_t0 if reference_t0 is not None else ts.iloc[0]
        deltas = (ts - t0).dt.total_seconds() / 60.0
        arr = deltas.to_numpy()

    # Check for non-integer minute anomalies (tolerance 1e-4)
    non_integers = np.abs(arr - np.round(arr)) > 1e-4
    if np.any(non_integers):
        msg = f"Detected {int(np.sum(non_integers))} non-integer minute timestamps!"
        raise ValueError(msg)
    return np.round(arr).astype(np.int64)


def enumerate_runs(
    df: pd.DataFrame,
    timestamp_col: str = "Timestamp",
) -> list[ContiguousRun]:
    """Segment DataFrame into maximal contiguous runs where consecutive delta == 60s (T3)."""
    if len(df) == 0:
        return []

    ts = pd.to_datetime(df[timestamp_col]).reset_index(drop=True)
    t0 = ts.iloc[0]
    elapsed = np.round((ts - t0).dt.total_seconds() / 60.0).astype(np.int64)

    deltas = ts.diff().dt.total_seconds()
    # A new run begins when delta != 60 seconds (or at index 0)
    break_mask = (deltas != 60.0).to_numpy(copy=True)
    break_mask[0] = True
    run_starts = np.where(break_mask)[0]
    run_ends = np.append(run_starts[1:] - 1, len(ts) - 1)

    runs = []
    for r_id, (s_idx, e_idx) in enumerate(zip(run_starts, run_ends, strict=True)):
        length = int(e_idx - s_idx + 1)
        runs.append(
            ContiguousRun(
                run_id=r_id,
                start_index=int(s_idx),
                end_index=int(e_idx),
                start_time=ts.iloc[s_idx],
                end_time=ts.iloc[e_idx],
                start_elapsed_min=int(elapsed[s_idx]),
                end_elapsed_min=int(elapsed[e_idx]),
                length_minutes=length,
            )
        )
    return runs


def classify_sensor_states(
    df: pd.DataFrame,
    sensor_col: str,
    timestamp_col: str = "Timestamp",
) -> dict[str, Any]:
    """Classify minutes into the 3 explicit T2 states: valid, explicit null, absent timestamp."""
    ts = pd.to_datetime(df[timestamp_col])
    t_min = ts.min()
    t_max = ts.max()
    span_minutes = int(np.round((t_max - t_min).total_seconds() / 60.0)) + 1

    total_recorded_rows = len(df)
    absent_minutes = span_minutes - total_recorded_rows

    series = df[sensor_col]
    explicit_nulls = int(series.isna().sum())
    valid_values = total_recorded_rows - explicit_nulls

    return {
        "span_minutes": span_minutes,
        "recorded_rows": total_recorded_rows,
        "valid_values_count": valid_values,
        "explicit_nulls_count": explicit_nulls,
        "absent_timestamps_count": absent_minutes,
        "valid_fraction_of_recorded": round(valid_values / max(1, total_recorded_rows), 4),
        "valid_fraction_of_span": round(valid_values / max(1, span_minutes), 4),
    }


def pairs_at_offset(
    df: pd.DataFrame,
    col: str,
    horizon_min: int,
    runs: list[ContiguousRun] | None = None,
    strict_no_nulls: bool = False,
    timestamp_col: str = "Timestamp",
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Extract explicit elapsed-time pairs (y_t, y_{t+h}) strictly within the same contiguous run (T4).

    Returns:
        (y_t_array, y_t_plus_h_array, metadata_counts)
    """
    if runs is None:
        runs = enumerate_runs(df, timestamp_col=timestamp_col)

    vals = df[col].to_numpy()
    y_t_list = []
    y_h_list = []

    pairs_spanning_gaps = 0
    pairs_with_null_endpoints = 0
    pairs_with_intermediate_nulls = 0

    for r in runs:
        if r.length_minutes <= horizon_min:
            # Entire run too short for this horizon
            continue

        r_vals = vals[r.start_index : r.end_index + 1]
        n_r = len(r_vals)

        for i in range(n_r - horizon_min):
            v_t = r_vals[i]
            v_h = r_vals[i + horizon_min]

            if np.isnan(v_t) or np.isnan(v_h):
                pairs_with_null_endpoints += 1
                continue

            if strict_no_nulls:
                intermediate = r_vals[i + 1 : i + horizon_min]
                if np.any(np.isnan(intermediate)):
                    pairs_with_intermediate_nulls += 1
                    continue

            y_t_list.append(v_t)
            y_h_list.append(v_h)

    # Approximate pairs spanning gaps across runs
    total_valid = int(np.sum(~np.isnan(vals)))
    potential_pairs = max(0, total_valid - horizon_min)
    pairs_spanning_gaps = max(0, potential_pairs - len(y_t_list) - pairs_with_null_endpoints)

    meta = {
        "valid_pairs_count": len(y_t_list),
        "excluded_null_endpoints": pairs_with_null_endpoints,
        "excluded_intermediate_nulls": pairs_with_intermediate_nulls,
        "excluded_spanning_gaps": pairs_spanning_gaps,
    }
    return (
        np.array(y_t_list, dtype=np.float64),
        np.array(y_h_list, dtype=np.float64),
        meta,
    )


def first_differences_within_runs(
    df: pd.DataFrame,
    col: str,
    runs: list[ContiguousRun] | None = None,
    timestamp_col: str = "Timestamp",
) -> tuple[np.ndarray, dict[str, int]]:
    """Compute consecutive 1-minute differences strictly within runs (never across gaps) (T5)."""
    if runs is None:
        runs = enumerate_runs(df, timestamp_col=timestamp_col)

    vals = df[col].to_numpy()
    diffs = []
    boundary_skips = 0

    for r in runs:
        if r.length_minutes < 2:
            continue
        r_vals = vals[r.start_index : r.end_index + 1]
        r_diff = np.diff(r_vals)
        # Drop NaNs within run
        valid_diff = r_diff[~np.isnan(r_diff)]
        diffs.extend(valid_diff)
        boundary_skips += 1  # skipped difference between runs

    return np.array(diffs, dtype=np.float64), {
        "valid_diffs": len(diffs),
        "boundary_skips": boundary_skips,
    }


def enumerate_windows(
    df: pd.DataFrame,
    input_min: int,
    horizon_min: int,
    stride_min: int,
    sensor_col: str,
    runs: list[ContiguousRun] | None = None,
    strict_no_nulls: bool = True,
    timestamp_col: str = "Timestamp",
) -> list[dict[str, Any]]:
    """Deterministically enumerate forecasting windows without crossing gaps or null runs (T5).

    Returns explicit start, origin, and target indices, timestamps, and elapsed minutes.
    """
    if runs is None:
        runs = enumerate_runs(df, timestamp_col=timestamp_col)

    ts = pd.to_datetime(df[timestamp_col]).reset_index(drop=True)
    vals = df[sensor_col].to_numpy()
    window_length = input_min + horizon_min
    windows: list[dict[str, Any]] = []

    window_id = 0
    for r in runs:
        if r.length_minutes < window_length:
            continue

        r_vals = vals[r.start_index : r.end_index + 1]
        n_r = len(r_vals)

        for s in range(0, n_r - window_length + 1, stride_min):
            w_vals = r_vals[s : s + window_length]

            if strict_no_nulls and np.any(np.isnan(w_vals)):
                continue

            # In tolerant mode, at least origin and target points must be non-null
            if np.isnan(w_vals[input_min - 1]) or np.isnan(w_vals[-1]):
                continue

            start_row_idx = r.start_index + s
            origin_row_idx = r.start_index + s + input_min - 1
            target_row_idx = r.start_index + s + window_length - 1

            start_time = ts.iloc[start_row_idx]
            origin_time = ts.iloc[origin_row_idx]
            target_time = ts.iloc[target_row_idx]

            start_elapsed = r.start_elapsed_min + s
            origin_elapsed = r.start_elapsed_min + s + input_min - 1
            target_elapsed = r.start_elapsed_min + s + window_length - 1

            windows.append(
                {
                    "window_id": window_id,
                    "run_id": r.run_id,
                    "start_index": int(start_row_idx),
                    "origin_index": int(origin_row_idx),
                    "target_index": int(target_row_idx),
                    "start_time": start_time,
                    "origin_time": origin_time,
                    "target_time": target_time,
                    "start_elapsed_min": int(start_elapsed),
                    "origin_elapsed_min": int(origin_elapsed),
                    "target_elapsed_min": int(target_elapsed),
                    "target_value": float(w_vals[-1]),
                }
            )
            window_id += 1

    return windows


def detect_excursion_episodes_run_bounded(
    values: np.ndarray,
    threshold: float,
    kind: str = "hyper",
    min_persistence: int = 15,
    min_release: int = 15,
    hysteresis_margin: float = 5.0,
    max_null_min: int = 5,
) -> ExcursionDetectionResult:
    """Detect excursion episodes strictly bounded within a contiguous run with hysteresis (C2.3).

    Handles null values:
    - Nulls during entry persistence reset the persistence counter (requires continuous valid entry).
    - Nulls during an active episode are tolerated up to max_null_min; excessive nulls terminate as censored.
    - Tracks episode durations and boundary censoring.
    """
    if len(values) < min_persistence:
        return ExcursionDetectionResult(
            total_episodes=0,
            boundary_censored=0,
            durations=[],
            left_censored=0,
            right_censored=0,
        )

    if kind == "hyper":
        entry_thresh = threshold
        release_thresh = threshold - hysteresis_margin
        is_entry = values > entry_thresh
        is_released = values <= release_thresh
    else:  # hypo
        entry_thresh = threshold
        release_thresh = threshold + hysteresis_margin
        is_entry = values < entry_thresh
        is_released = values >= release_thresh

    episodes = 0
    boundary_censored = 0
    left_censored = 0
    durations: list[int] = []

    in_episode = False
    active_len = 0
    release_len = 0
    consecutive_nulls = 0
    current_episode_duration = 0
    starts_in_excursion = False

    for i, val in enumerate(values):
        if np.isnan(val):
            consecutive_nulls += 1
            if not in_episode:
                # Null during entry persistence breaks the consecutive run of valid values!
                active_len = 0
            else:
                release_len = 0  # Null during release persistence resets release_len!
                current_episode_duration += 1
                if consecutive_nulls > max_null_min:
                    # Terminated by excessive null run -> boundary censored
                    in_episode = False
                    boundary_censored += 1
                    durations.append(current_episode_duration)
                    current_episode_duration = 0
                    release_len = 0
            continue

        consecutive_nulls = 0

        if not in_episode:
            if is_entry[i]:
                if active_len == 0 and i == 0:
                    starts_in_excursion = True
                active_len += 1
                if active_len >= min_persistence:
                    episodes += 1
                    in_episode = True
                    current_episode_duration = active_len
                    release_len = 0
                    if starts_in_excursion and active_len == i + 1:
                        left_censored += 1
            else:
                active_len = 0
                starts_in_excursion = False
        else:
            # Inside active episode
            current_episode_duration += 1
            if is_released[i]:
                release_len += 1
                if release_len >= min_release:
                    # Episode ended with confirmed release
                    in_episode = False
                    durations.append(current_episode_duration - release_len)
                    active_len = 0
                    release_len = 0
                    current_episode_duration = 0
                    starts_in_excursion = False
            else:
                release_len = 0

    # If episode was still active at the end of the run, it is boundary-censored (right-censored)
    if in_episode:
        boundary_censored += 1
        durations.append(current_episode_duration)

    return ExcursionDetectionResult(
        total_episodes=episodes,
        boundary_censored=boundary_censored,
        durations=durations,
        left_censored=left_censored,
        right_censored=boundary_censored,
    )


def compute_interpolation_lookahead(
    t_minutes: int,
    phi_s: int,
    period: int = 5,
) -> int:
    """Compute deterministic forward look-ahead (in minutes) for linear interpolation.

    Under linear interpolation between native sampling vertices at period p and phase phi_s:
    Let delta = (t_minutes - phi_s) % p.
    - If delta == 0: t is exactly at a native vertex; zero forward look-ahead.
    - If delta > 0: linear interpolation at t incorporates the upcoming native vertex at
      t + (p - delta), introducing exactly (p - delta) minutes of future look-ahead into
      the interpolated value at t.

    Examples (p = 5):
    - delta = 0 -> 0 min look-ahead (on-grid native vertex, uses only data at t)
    - delta = 1 -> 4 min look-ahead (interpolates towards vertex at t + 4)
    - delta = 2 -> 3 min look-ahead (interpolates towards vertex at t + 3)
    - delta = 3 -> 2 min look-ahead (interpolates towards vertex at t + 2)
    - delta = 4 -> 1 min look-ahead (interpolates towards vertex at t + 1)
    """
    delta = (t_minutes - phi_s) % period
    return 0 if delta == 0 else period - delta


def verify_guard_band_safety(
    issuance_time_min: int,
    phi_s: int,
    guard_band_min: int = 5,
    period: int = 5,
) -> bool:
    """Verify that the latest native vertex used by guard-banded input does not exceed issuance time.

    For forecast issuance time t and guard band g >= period:
    The latest glucose input is sampled at t - g.
    Its look-ahead is at most (period - 1) minutes.
    The forward vertex used is at timestamp (t - g) + lookahead <= t - g + period - 1 <= t - 1 < t.
    Thus, no future native vertices beyond issuance time t are ever leaked into the predictors.
    """
    latest_input_time = issuance_time_min - guard_band_min
    lookahead = compute_interpolation_lookahead(latest_input_time, phi_s, period=period)
    latest_vertex_time = latest_input_time + lookahead
    return bool(latest_vertex_time <= issuance_time_min)
