"""Timeseries and timestamp analysis module.

Detects candidate datetime columns, evaluates parse-success rates,
computes sampling interval modes and medians, tracks gaps/duplicates/non-monotonic rows,
and checks timezone/format ambiguities.
"""

from __future__ import annotations

import warnings as py_warnings
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from dtwin.audit.profiling import read_table_chunks


@dataclass
class TimeseriesProfile:
    column_name: str
    parse_success_rate: float
    min_timestamp: str | None
    max_timestamp: str | None
    duration_per_file: dict[str, float]  # min, median, max duration in seconds
    mode_delta_seconds: float | None
    median_delta_seconds: float | None
    mode_delta_percent: float | None
    gap_count: int
    duplicate_count: int
    non_monotonic_count: int
    timezone_info: str
    format_ambiguity_warning: str | None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_candidate_columns(
    columns: list[str],
    hints: list[str],
) -> list[str]:
    """Identify column names that match datetime hints."""
    candidates = []
    for col in columns:
        col_lower = col.strip().lower()
        if any(h.lower() in col_lower for h in hints):
            candidates.append(col)
    return candidates


def analyze_timeseries_column(
    col_name: str,
    files: list[str],
    data_dir: Path,
    delimiters: dict[str, str],
    config: dict[str, Any],
) -> TimeseriesProfile | None:
    """Analyze a single candidate datetime column across files in a schema family."""
    parse_threshold = float(config.get("datetime_parse_threshold", 0.8))
    gap_multiplier = float(config.get("gap_multiplier", 3.0))
    chunk_size = int(config.get("chunk_size", 50000))
    chunk_threshold = int(config.get("chunk_size_bytes_threshold", 52428800))

    total_observed = 0
    total_parsed = 0
    all_positive_deltas: list[float] = []
    total_duplicates = 0
    total_non_monotonic = 0
    total_gaps = 0
    durations_seconds: list[float] = []

    global_min_ts: pd.Timestamp | None = None
    global_max_ts: pd.Timestamp | None = None

    tz_observed: set[str] = set()
    date_formats_observed: set[str] = set()
    warnings: list[str] = []

    for rel_path in files:
        full_path = data_dir / rel_path
        delim = delimiters.get(rel_path, ",")

        file_timestamps: list[pd.Timestamp] = []

        try:
            chunks = read_table_chunks(
                full_path,
                delimiter=delim,
                chunk_size=chunk_size,
                chunk_size_bytes_threshold=chunk_threshold,
            )
            for chunk in chunks:
                if col_name not in chunk.columns:
                    continue
                series = chunk[col_name].dropna()
                if series.empty:
                    continue

                total_observed += len(series)
                # Sample format check
                for val in series.head(5):
                    sval = str(val).strip()
                    if "/" in sval:
                        date_formats_observed.add("slash_separated")
                    elif "-" in sval:
                        date_formats_observed.add("dash_separated")

                with py_warnings.catch_warnings():
                    py_warnings.simplefilter("ignore", category=UserWarning)
                    parsed = pd.to_datetime(series, errors="coerce")
                valid_ts = parsed.dropna()
                total_parsed += len(valid_ts)

                for ts in valid_ts:
                    tz_observed.add(str(ts.tz))
                    file_timestamps.append(ts)

        except Exception as e:
            warnings.append(f"Error parsing timeseries in '{rel_path}': {type(e).__name__}")

        if file_timestamps:
            f_min = min(file_timestamps)
            f_max = max(file_timestamps)
            if global_min_ts is None or f_min < global_min_ts:
                global_min_ts = f_min
            if global_max_ts is None or f_max > global_max_ts:
                global_max_ts = f_max

            duration = (f_max - f_min).total_seconds()
            durations_seconds.append(duration)

            # Analyze deltas within file
            s_ts = pd.Series(file_timestamps)
            diffs = s_ts.diff().dt.total_seconds().dropna()

            if not diffs.empty:
                f_dups = int((diffs == 0).sum())
                f_non_mono = int((diffs < 0).sum())
                pos = diffs[diffs > 0].values

                total_duplicates += f_dups
                total_non_monotonic += f_non_mono
                all_positive_deltas.extend(pos)

    # Check parse success rate
    if total_observed == 0:
        return None
    success_rate = total_parsed / total_observed
    if success_rate < parse_threshold:
        return None  # Does not qualify as a reliable datetime column

    # Interval analysis
    mode_delta: float | None = None
    median_delta: float | None = None
    mode_percent: float | None = None

    if all_positive_deltas:
        arr_pos = np.array(all_positive_deltas)
        median_delta = round(float(np.median(arr_pos)), 2)

        # Compute mode using frequency counter rounded to nearest second
        counts = Counter(np.round(arr_pos, 1))
        mode_val, mode_count = counts.most_common(1)[0]
        mode_delta = float(mode_val)
        mode_percent = round((mode_count / len(arr_pos)) * 100.0, 2)

        # Count gaps (delta > gap_multiplier * mode_delta)
        gap_threshold = gap_multiplier * mode_delta
        total_gaps = int((arr_pos > gap_threshold).sum())

    # Duration summary
    if durations_seconds:
        sorted_d = sorted(durations_seconds)
        n = len(sorted_d)
        med_d = sorted_d[n // 2] if n % 2 != 0 else (sorted_d[n // 2 - 1] + sorted_d[n // 2]) / 2.0
        dur_summary = {
            "min_seconds": float(sorted_d[0]),
            "median_seconds": float(med_d),
            "max_seconds": float(sorted_d[-1]),
        }
    else:
        dur_summary = {"min_seconds": 0.0, "median_seconds": 0.0, "max_seconds": 0.0}

    # Timezone check
    tz_info = ", ".join(sorted(tz_observed)) if tz_observed else "None (naive)"
    if len(tz_observed) > 1:
        warnings.append(f"Mixed timezones observed across files: {tz_info}")

    format_warning = None
    if len(date_formats_observed) > 1:
        format_warning = (
            f"Multiple date string formats observed across files: {sorted(date_formats_observed)}"
        )
        warnings.append(format_warning)

    return TimeseriesProfile(
        column_name=col_name,
        parse_success_rate=round(success_rate, 4),
        min_timestamp=global_min_ts.isoformat() if global_min_ts is not None else None,
        max_timestamp=global_max_ts.isoformat() if global_max_ts is not None else None,
        duration_per_file=dur_summary,
        mode_delta_seconds=mode_delta,
        median_delta_seconds=median_delta,
        mode_delta_percent=mode_percent,
        gap_count=total_gaps,
        duplicate_count=total_duplicates,
        non_monotonic_count=total_non_monotonic,
        timezone_info=tz_info,
        format_ambiguity_warning=format_warning,
        warnings=warnings,
    )
