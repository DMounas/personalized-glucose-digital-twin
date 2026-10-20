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
    activity_features: np.ndarray = field(
        default_factory=lambda: np.empty((0, 4), dtype=np.float64)
    )
    meal_features: np.ndarray = field(default_factory=lambda: np.empty((0, 7), dtype=np.float64))

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
    df = pd.read_csv(file_path)
    cols = [c.strip() for c in df.columns]
    has_hr = "HR" in cols
    mets_col = next((c for c in cols if c.lower() == "mets"), None)

    ts = pd.to_datetime(df["Timestamp"])
    dex = df["Dexcom GL"].to_numpy(dtype=float)
    hr_arr = df["HR"].to_numpy(dtype=float) if has_hr else np.full(len(df), np.nan)
    mets_arr = (
        df[mets_col].to_numpy(dtype=float) if mets_col is not None else np.full(len(df), np.nan)
    )
    elapsed_m = compute_elapsed_minutes(ts)

    # Meal logging data
    meal_mask = df["Carbs"].notna().to_numpy()
    meal_indices = np.where(meal_mask)[0]
    meal_ts = ts.iloc[meal_indices].to_numpy()
    meal_carbs = df.loc[meal_mask, "Carbs"].to_numpy(dtype=float)
    meal_protein = df.loc[meal_mask, "Protein"].to_numpy(dtype=float)
    meal_fat = df.loc[meal_mask, "Fat"].to_numpy(dtype=float)
    meal_fiber = df.loc[meal_mask, "Fiber"].to_numpy(dtype=float)

    runs = enumerate_runs(df)

    timestamps_list: list[str] = []
    y_base_list: list[float] = []
    roc_list: list[float] = []
    target_list: list[float] = []
    elapsed_list: list[int] = []
    history_lags_list: list[np.ndarray] = []
    activity_list: list[list[float]] = []
    meal_list: list[list[float]] = []

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

                        # Physical activity features over [t-30, t]
                        orig_idx = r.start_index + t
                        w_hr = hr_arr[orig_idx - 30 : orig_idx + 1]
                        w_mets = mets_arr[orig_idx - 30 : orig_idx + 1]

                        v_hr = w_hr[~np.isnan(w_hr)]
                        m_hr = float(np.mean(v_hr)) if len(v_hr) > 0 else np.nan
                        d_hr = (
                            float(v_hr[-1] - v_hr[0])
                            if len(v_hr) >= 2
                            else (0.0 if len(v_hr) > 0 else np.nan)
                        )

                        v_mets = w_mets[~np.isnan(w_mets)]
                        m_mets = float(np.mean(v_mets) / 10.0) if len(v_mets) > 0 else np.nan

                        is_missing = (
                            1.0 if (np.isnan(m_hr) or np.isnan(d_hr) or np.isnan(m_mets)) else 0.0
                        )

                        # Meal context features: look up most recent meal start <= t
                        curr_t_ns = ts.iloc[orig_idx].to_numpy()
                        pos = int(np.searchsorted(meal_ts, curr_t_ns, side="right")) - 1
                        if pos < 0:
                            time_since_meal = 1440.0
                            meal_in_60m = 0.0
                            carbs_val = 0.0
                            protein_val = 0.0
                            fat_val = 0.0
                            fiber_val = 0.0
                            no_recent_meal = 1.0
                        else:
                            dt_min = float((curr_t_ns - meal_ts[pos]) / np.timedelta64(1, "m"))
                            if dt_min > 1440.0:
                                time_since_meal = 1440.0
                                meal_in_60m = 0.0
                                carbs_val = 0.0
                                protein_val = 0.0
                                fat_val = 0.0
                                fiber_val = 0.0
                                no_recent_meal = 1.0
                            else:
                                time_since_meal = dt_min
                                meal_in_60m = 1.0 if dt_min <= 60.0 else 0.0
                                carbs_val = float(meal_carbs[pos])
                                protein_val = float(meal_protein[pos])
                                fat_val = float(meal_fat[pos])
                                fiber_val = float(meal_fiber[pos])
                                no_recent_meal = 0.0

                        timestamps_list.append(str(r_ts.iloc[t]))
                        y_base_list.append(y_5)
                        roc_list.append(roc_val)
                        target_list.append(float(target_val))
                        elapsed_list.append(int(r_elapsed[t]))
                        history_lags_list.append(guard_hist_vals.copy())
                        activity_list.append([m_hr, d_hr, m_mets, is_missing])
                        meal_list.append(
                            [
                                time_since_meal,
                                meal_in_60m,
                                carbs_val,
                                protein_val,
                                fat_val,
                                fiber_val,
                                no_recent_meal,
                            ]
                        )

    history_lags_arr = (
        np.array(history_lags_list, dtype=np.float64)
        if len(history_lags_list) > 0
        else np.empty((0, 13), dtype=np.float64)
    )
    activity_arr = (
        np.array(activity_list, dtype=np.float64)
        if len(activity_list) > 0
        else np.empty((0, 4), dtype=np.float64)
    )
    meal_arr = (
        np.array(meal_list, dtype=np.float64)
        if len(meal_list) > 0
        else np.empty((0, 7), dtype=np.float64)
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
        activity_features=activity_arr,
        meal_features=meal_arr,
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
