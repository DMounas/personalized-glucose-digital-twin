"""Dataset extraction for Stage 2 guard-banded forecast origins."""

from __future__ import annotations

import glob
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from dtwin.analysis.aggregate_feasibility import load_diagnostic_group_mapping
from dtwin.timeaxis import compute_elapsed_minutes, enumerate_runs


@dataclass(frozen=True)
class ParticipantOrigins:
    """Eligible forecast origins and target outcomes for an individual participant."""

    participant_id: str
    diag_group: str
    horizon_minutes: int
    timestamps: list[str]
    y_base: np.ndarray  # y(t - 5)
    roc: np.ndarray  # (y(t - 5) - y(t - 20)) / 15.0
    target: np.ndarray  # y(t + h)
    elapsed_minutes: np.ndarray  # m(t)
    history_lags: np.ndarray = field(default_factory=lambda: np.empty((0, 13), dtype=np.float64))

    @property
    def n_origins(self) -> int:
        return len(self.target)


def extract_participant_guard_band_origins(
    file_path: Path,
    diag_group: str,
    horizon_minutes: int,
    phase: int = 0,
) -> ParticipantOrigins:
    """Extract eligible guard-band forecast origins from a single participant file.

    Requires:
    1. Issuance time t satisfies m(t) = round((t - t0) / 60s) = phase (mod 5).
    2. All 13 guard-band history lags [t-5, t-10, ..., t-65] are non-null and
       reside strictly within the same contiguous Dexcom run.
    3. Target y(t + h) is non-null and within the same contiguous Dexcom run.

    Args:
        file_path: Path to participant time series CSV.
        diag_group: Clinical diagnostic stratum ('normal', 'prediabetes', 'diabetes').
        horizon_minutes: Forecast horizon in minutes (+30 or +60).
        phase: Deterministic lattice phase offset (0 for primary evaluation grid).

    Returns:
        ParticipantOrigins containing aligned arrays of y_base, roc, and target.
    """
    pid = file_path.parent.name
    df = pd.read_csv(file_path, usecols=["Timestamp", "Dexcom GL"])
    ts = pd.to_datetime(df["Timestamp"])
    dex = df["Dexcom GL"].to_numpy(dtype=float)
    elapsed_m = compute_elapsed_minutes(ts)

    runs = enumerate_runs(df)

    timestamps_list: list[str] = []
    y_base_list: list[float] = []
    roc_list: list[float] = []
    target_list: list[float] = []
    elapsed_list: list[int] = []
    history_lags_list: list[np.ndarray] = []

    h = horizon_minutes
    max_lag = 65  # 13 lags at 5m steps

    for r in runs:
        r_slice = dex[r.start_index : r.end_index + 1]
        r_ts = ts.iloc[r.start_index : r.end_index + 1].reset_index(drop=True)
        r_len = len(r_slice)
        r_elapsed = elapsed_m[r.start_index : r.end_index + 1]

        # Contiguous origin loop
        for t in range(max_lag, r_len - h):
            if int(r_elapsed[t]) % 5 == phase:
                # 13 guard-band lags: t-5, t-10, ..., t-65
                guard_hist_idx = [t - 5 * k for k in range(1, 14)]
                guard_hist_vals = r_slice[guard_hist_idx]

                if not np.any(np.isnan(guard_hist_vals)):
                    target_val = r_slice[t + h]
                    if not np.isnan(target_val):
                        y_5 = float(r_slice[t - 5])
                        y_20 = float(r_slice[t - 20])
                        roc_val = (y_5 - y_20) / 15.0

                        timestamps_list.append(str(r_ts.iloc[t]))
                        y_base_list.append(y_5)
                        roc_list.append(roc_val)
                        target_list.append(float(target_val))
                        elapsed_list.append(int(r_elapsed[t]))
                        history_lags_list.append(guard_hist_vals.copy())

    history_lags_arr = (
        np.array(history_lags_list, dtype=np.float64)
        if len(history_lags_list) > 0
        else np.empty((0, 13), dtype=np.float64)
    )

    return ParticipantOrigins(
        participant_id=pid,
        diag_group=diag_group,
        horizon_minutes=h,
        timestamps=timestamps_list,
        y_base=np.array(y_base_list, dtype=np.float64),
        roc=np.array(roc_list, dtype=np.float64),
        target=np.array(target_list, dtype=np.float64),
        elapsed_minutes=np.array(elapsed_list, dtype=np.int64),
        history_lags=history_lags_arr,
    )


def extract_cohort_guard_band_dataset(
    data_dir: Path,
    bio_path: Path,
    horizon_minutes: int,
    phase: int = 0,
) -> dict[str, ParticipantOrigins]:
    """Extract eligible guard-band forecast origins across all cohort participants.

    Args:
        data_dir: Path to directory containing participant subfolders (CGMacros-*).
        bio_path: Path to bio.csv for clinical HbA1c diagnostic stratification.
        horizon_minutes: Forecast horizon in minutes (+30 or +60).
        phase: Sampling phase offset (0 for primary grid).

    Returns:
        Mapping from participant_id to ParticipantOrigins.
    """
    id_to_grp = load_diagnostic_group_mapping(bio_path)
    files = sorted(glob.glob(str(data_dir / "CGMacros-*" / "*.csv")))

    dataset: dict[str, ParticipantOrigins] = {}
    for f_path_str in files:
        f_path = Path(f_path_str)
        pid = f_path.parent.name
        grp = id_to_grp.get(pid, "unknown")
        origins = extract_participant_guard_band_origins(
            f_path,
            diag_group=grp,
            horizon_minutes=horizon_minutes,
            phase=phase,
        )
        dataset[pid] = origins

    return dataset
