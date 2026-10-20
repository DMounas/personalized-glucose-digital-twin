"""Aggregate feasibility and cohort-level modeling readiness for Stage 2.

This module provides reproducible, privacy-preserving aggregate feasibility metrics
across clinical diagnostic groups (Normal, Prediabetes, Type 2 Diabetes) on CGMacros v1.0.0.

Core evaluations:
1. Dexcom coverage, valid rows, and evaluable contiguous runs (T6 compliant).
2. Candidate forecast origins on 1-minute grid (60m history) vs 5-minute native lattice
   (13-point history) across session-specific inferred phases and fixed phase offsets.
3. Hyperglycemia excursion event feasibility (>180 mg/dL) and boundary censoring.

Privacy governance:
All outputs from this module are strictly cohort- and diagnostic-group-level aggregates.
Zero individual participant identifiers (CGMacros-XXX) are stored in output artifacts.
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from dtwin.analysis.native_grid import infer_native_grid_series
from dtwin.timeaxis import (
    compute_elapsed_minutes,
    detect_excursion_episodes_run_bounded,
    enumerate_runs,
)


def load_diagnostic_group_mapping(bio_path: Path) -> dict[str, str]:
    """Load baseline laboratory HbA1c from bio.csv and map subject IDs to clinical groups.

    Clinical criteria (ADA guidelines):
    - Normal: HbA1c < 5.7%
    - Prediabetes: 5.7% <= HbA1c <= 6.4%
    - Type 2 Diabetes: HbA1c >= 6.5%

    Args:
        bio_path: Path to bio.csv containing laboratory HbA1c.

    Returns:
        Mapping from participant folder ID (e.g. 'CGMacros-001') to diagnostic group name.
    """
    bio = pd.read_csv(bio_path)
    bio.columns = [c.strip() for c in bio.columns]

    def get_group(val: float) -> str:
        if pd.isna(val):
            return "unknown"
        if val < 5.7:
            return "normal"
        if val < 6.5:
            return "prediabetes"
        return "diabetes"

    mapping: dict[str, str] = {}
    for _, row in bio.iterrows():
        subj_int = int(row["subject"])
        pid = f"CGMacros-{subj_int:03d}"
        a1c = float(row["A1c PDL (Lab)"])
        mapping[pid] = get_group(a1c)

    return mapping


def evaluate_participant_feasibility(
    file_path: Path,
    diag_group: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate feasibility metrics for a single participant without exposing ID.

    Args:
        file_path: Path to participant time series CSV.
        diag_group: Diagnostic group string ('normal', 'prediabetes', 'diabetes').
        config: Configuration dictionary for native-grid inference.

    Returns:
        Dictionary of participant summary metrics (anonymized).
    """
    df = pd.read_csv(file_path)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    n_rows = len(df)

    dex = df["Dexcom GL"].to_numpy(dtype=float)
    valid_dex_mask = ~np.isnan(dex)
    valid_dex_rows = int(np.sum(valid_dex_mask))

    # Continuous runs of timestamps (step = 60s)
    runs = enumerate_runs(df)
    elapsed_m = compute_elapsed_minutes(df["Timestamp"])

    # Contiguous runs of non-null Dexcom readings
    valid_dex_df = df[valid_dex_mask].copy()
    dex_runs = enumerate_runs(valid_dex_df) if len(valid_dex_df) > 0 else []
    total_valid_dex_runs = len(dex_runs)

    # Evaluable runs (>=120 min, >=20 bends under production native-grid engine)
    evaluable_runs_count = 0
    for r in dex_runs:
        r_len = r.length_minutes
        if r_len >= 120:
            sub = valid_dex_df.iloc[r.start_index : r.end_index + 1]
            res_r = infer_native_grid_series(sub["Dexcom GL"], config, timestamps=sub["Timestamp"])
            if res_r.total_bends_detected >= 20:
                evaluable_runs_count += 1

    # Candidate forecast origins:
    # 1-minute grid: 60m non-null history [t-60..t], target at t+30 and t+60
    origins_1m_30 = 0
    origins_1m_60 = 0

    # 5-minute candidate origins:
    # Evaluated at native candidate vertices: 13 non-null points [t, t-5, ..., t-60]
    origins_5m_t6_30 = 0
    origins_5m_t6_60 = 0
    origins_5m_phases_30 = {p: 0 for p in range(5)}
    origins_5m_phases_60 = {p: 0 for p in range(5)}

    # Excursions
    episodes_1m = 0
    censored_1m = 0
    episodes_5m_3pt = 0
    censored_5m_3pt = 0
    episodes_5m_4pt = 0
    censored_5m_4pt = 0

    for r in runs:
        r_slice = dex[r.start_index : r.end_index + 1]
        r_len = len(r_slice)
        r_elapsed = elapsed_m[r.start_index : r.end_index + 1]

        # 1-minute origins
        for t in range(60, r_len - 30):
            hist = r_slice[t - 60 : t + 1]
            if not np.any(np.isnan(hist)):
                if not np.isnan(r_slice[t + 30]):
                    origins_1m_30 += 1
                if t <= r_len - 61 and not np.isnan(r_slice[t + 60]):
                    origins_1m_60 += 1

        # 5-minute native fixed phase candidates
        for p in range(5):
            for t in range(60, r_len - 30):
                if int(r_elapsed[t]) % 5 == p:
                    hist_idx = [t - 5 * k for k in range(13)]
                    hist_vals = r_slice[hist_idx]
                    if not np.any(np.isnan(hist_vals)):
                        if not np.isnan(r_slice[t + 30]):
                            origins_5m_phases_30[p] += 1
                        if t <= r_len - 61 and not np.isnan(r_slice[t + 60]):
                            origins_5m_phases_60[p] += 1

        # Determine run best phase (T6)
        best_p = 0
        min_res = 1e9
        for p in range(5):
            grid_mask = r_elapsed % 5 == p
            if np.sum(grid_mask) >= 10:
                grid_idx = np.where(grid_mask)[0]
                interp = np.interp(np.arange(r_len), grid_idx, r_slice[grid_idx])
                valid = ~np.isnan(r_slice) & ~np.isnan(interp)
                if np.sum(valid) > 20:
                    res = float(np.mean(np.abs(r_slice[valid] - interp[valid])))
                    if res < min_res:
                        min_res = res
                        best_p = p

        for t in range(60, r_len - 30):
            if int(r_elapsed[t]) % 5 == best_p:
                hist_idx = [t - 5 * k for k in range(13)]
                hist_vals = r_slice[hist_idx]
                if not np.any(np.isnan(hist_vals)):
                    if not np.isnan(r_slice[t + 30]):
                        origins_5m_t6_30 += 1
                    if t <= r_len - 61 and not np.isnan(r_slice[t + 60]):
                        origins_5m_t6_60 += 1

        # Excursion episodes: 1-minute grid
        ep1, cens1 = detect_excursion_episodes_run_bounded(
            r_slice,
            threshold=180.0,
            kind="hyper",
            min_persistence=15,
            min_release=10,
            hysteresis_margin=5.0,
            max_null_min=5,
        )
        episodes_1m += ep1
        censored_1m += cens1

        # Excursion episodes: 5-minute native lattice
        grid_5m_idx = np.where(r_elapsed % 5 == best_p)[0]
        if len(grid_5m_idx) >= 3:
            r_slice_5m = r_slice[grid_5m_idx]
            # 3 points = 10m elapsed persistence
            ep5_3, cens5_3 = detect_excursion_episodes_run_bounded(
                r_slice_5m,
                threshold=180.0,
                kind="hyper",
                min_persistence=3,
                min_release=2,
                hysteresis_margin=5.0,
                max_null_min=1,
            )
            episodes_5m_3pt += ep5_3
            censored_5m_3pt += cens5_3

            # 4 points = 15m elapsed persistence
            if len(grid_5m_idx) >= 4:
                ep5_4, cens5_4 = detect_excursion_episodes_run_bounded(
                    r_slice_5m,
                    threshold=180.0,
                    kind="hyper",
                    min_persistence=4,
                    min_release=3,
                    hysteresis_margin=5.0,
                    max_null_min=1,
                )
                episodes_5m_4pt += ep5_4
                censored_5m_4pt += cens5_4

    return {
        "diag_group": diag_group,
        "total_rows": n_rows,
        "valid_dex_rows": valid_dex_rows,
        "total_dex_runs": total_valid_dex_runs,
        "evaluable_dex_runs": evaluable_runs_count,
        "origins_1m_30": origins_1m_30,
        "origins_1m_60": origins_1m_60,
        "origins_5m_t6_30": origins_5m_t6_30,
        "origins_5m_t6_60": origins_5m_t6_60,
        "origins_5m_phases_30": origins_5m_phases_30,
        "origins_5m_phases_60": origins_5m_phases_60,
        "episodes_1m": episodes_1m,
        "censored_1m": censored_1m,
        "episodes_5m_3pt": episodes_5m_3pt,
        "censored_5m_3pt": censored_5m_3pt,
        "episodes_5m_4pt": episodes_5m_4pt,
        "censored_5m_4pt": censored_5m_4pt,
    }


def run_aggregate_feasibility_analysis(
    data_dir: Path,
    bio_path: Path,
    config_path: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Execute full cohort aggregate feasibility analysis across clinical groups.

    Args:
        data_dir: Path to directory containing participant subfolders.
        bio_path: Path to bio.csv.
        config_path: Path to configs/stage1b.yaml.
        output_path: Optional path to save JSON results.

    Returns:
        Structured aggregate feasibility dictionary (anonymized).
    """
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    id_to_grp = load_diagnostic_group_mapping(bio_path)
    files = sorted(glob.glob(str(data_dir / "CGMacros-*" / "*.csv")))

    groups = ["normal", "prediabetes", "diabetes"]

    # Initialize group-level accumulators
    grp_participants = {g: 0 for g in groups}
    grp_total_rows = {g: 0 for g in groups}
    grp_valid_dex_rows = {g: 0 for g in groups}
    grp_total_dex_runs = {g: 0 for g in groups}
    grp_evaluable_dex_runs = {g: 0 for g in groups}

    grp_origins_1m_30 = {g: 0 for g in groups}
    grp_origins_1m_60 = {g: 0 for g in groups}
    grp_origins_5m_t6_30 = {g: 0 for g in groups}
    grp_origins_5m_t6_60 = {g: 0 for g in groups}
    grp_origins_5m_phases_30 = {g: {p: 0 for p in range(5)} for g in groups}
    grp_origins_5m_phases_60 = {g: {p: 0 for p in range(5)} for g in groups}

    # Excursion episode counts and participant distributions
    grp_episodes_1m = {g: 0 for g in groups}
    grp_censored_1m = {g: 0 for g in groups}
    grp_ep_dist_1m: dict[str, list[int]] = {g: [] for g in groups}

    grp_episodes_5m_3pt = {g: 0 for g in groups}
    grp_censored_5m_3pt = {g: 0 for g in groups}
    grp_ep_dist_5m_3pt: dict[str, list[int]] = {g: [] for g in groups}

    grp_episodes_5m_4pt = {g: 0 for g in groups}
    grp_censored_5m_4pt = {g: 0 for g in groups}
    grp_ep_dist_5m_4pt: dict[str, list[int]] = {g: [] for g in groups}

    for f_path_str in files:
        file_p = Path(f_path_str)
        pid = file_p.parent.name
        grp = id_to_grp.get(pid, "unknown")
        if grp not in groups:
            continue

        p_res = evaluate_participant_feasibility(file_p, grp, config)

        grp_participants[grp] += 1
        grp_total_rows[grp] += p_res["total_rows"]
        grp_valid_dex_rows[grp] += p_res["valid_dex_rows"]
        grp_total_dex_runs[grp] += p_res["total_dex_runs"]
        grp_evaluable_dex_runs[grp] += p_res["evaluable_dex_runs"]

        grp_origins_1m_30[grp] += p_res["origins_1m_30"]
        grp_origins_1m_60[grp] += p_res["origins_1m_60"]
        grp_origins_5m_t6_30[grp] += p_res["origins_5m_t6_30"]
        grp_origins_5m_t6_60[grp] += p_res["origins_5m_t6_60"]

        for p in range(5):
            grp_origins_5m_phases_30[grp][p] += p_res["origins_5m_phases_30"][p]
            grp_origins_5m_phases_60[grp][p] += p_res["origins_5m_phases_60"][p]

        grp_episodes_1m[grp] += p_res["episodes_1m"]
        grp_censored_1m[grp] += p_res["censored_1m"]
        grp_ep_dist_1m[grp].append(p_res["episodes_1m"])

        grp_episodes_5m_3pt[grp] += p_res["episodes_5m_3pt"]
        grp_censored_5m_3pt[grp] += p_res["censored_5m_3pt"]
        grp_ep_dist_5m_3pt[grp].append(p_res["episodes_5m_3pt"])

        grp_episodes_5m_4pt[grp] += p_res["episodes_5m_4pt"]
        grp_censored_5m_4pt[grp] += p_res["censored_5m_4pt"]
        grp_ep_dist_5m_4pt[grp].append(p_res["episodes_5m_4pt"])

    # Aggregate summaries by group and cohort
    def make_excursion_summary(
        episodes_dict: dict[str, int],
        censored_dict: dict[str, int],
        dist_dict: dict[str, list[int]],
    ) -> dict[str, Any]:
        all_dists = [c for g in groups for c in dist_dict[g]]
        total_ep = sum(episodes_dict.values())
        total_cens = sum(censored_dict.values())
        return {
            "total_episodes_cohort": total_ep,
            "total_censored_cohort": total_cens,
            "participant_coverage_cohort": {
                "ge_1_episode": int(np.sum(np.array(all_dists) >= 1)),
                "ge_3_episodes": int(np.sum(np.array(all_dists) >= 3)),
                "ge_5_episodes": int(np.sum(np.array(all_dists) >= 5)),
                "ge_10_episodes": int(np.sum(np.array(all_dists) >= 10)),
                "total_participants": len(all_dists),
            },
            "by_diagnostic_group": {
                g: {
                    "participants": len(dist_dict[g]),
                    "episodes": episodes_dict[g],
                    "censored": censored_dict[g],
                    "ge_1_episode": int(np.sum(np.array(dist_dict[g]) >= 1)),
                    "ge_3_episodes": int(np.sum(np.array(dist_dict[g]) >= 3)),
                    "ge_5_episodes": int(np.sum(np.array(dist_dict[g]) >= 5)),
                    "ge_10_episodes": int(np.sum(np.array(dist_dict[g]) >= 10)),
                }
                for g in groups
            },
        }

    cohort_phases_30 = {p: sum(grp_origins_5m_phases_30[g][p] for g in groups) for p in range(5)}
    cohort_phases_60 = {p: sum(grp_origins_5m_phases_60[g][p] for g in groups) for p in range(5)}

    results: dict[str, Any] = {
        "metadata": {
            "title": "Stage 2 Aggregate Feasibility and Cohort Readiness",
            "version": "1.0.0",
            "dataset": "CGMacros v1.0.0",
            "privacy": "Aggregated only. Zero participant identifiers.",
        },
        "coverage_by_diagnostic_group": {
            g: {
                "participants": grp_participants[g],
                "total_recorded_rows": grp_total_rows[g],
                "valid_dexcom_rows": grp_valid_dex_rows[g],
                "total_valid_dexcom_runs": grp_total_dex_runs[g],
                "evaluable_dexcom_runs_t6": grp_evaluable_dex_runs[g],
            }
            for g in groups
        },
        "coverage_cohort_totals": {
            "participants": sum(grp_participants.values()),
            "total_recorded_rows": sum(grp_total_rows.values()),
            "valid_dexcom_rows": sum(grp_valid_dex_rows.values()),
            "total_valid_dexcom_runs": sum(grp_total_dex_runs.values()),
            "evaluable_dexcom_runs_t6": sum(grp_evaluable_dex_runs.values()),
        },
        "candidate_forecast_origins": {
            "one_minute_grid_60m_history": {
                "horizon_30min": {
                    "cohort_total": sum(grp_origins_1m_30.values()),
                    "by_group": grp_origins_1m_30,
                },
                "horizon_60min": {
                    "cohort_total": sum(grp_origins_1m_60.values()),
                    "by_group": grp_origins_1m_60,
                },
            },
            "five_minute_native_lattice_t6_inferred_phase": {
                "horizon_30min": {
                    "cohort_total": sum(grp_origins_5m_t6_30.values()),
                    "by_group": grp_origins_5m_t6_30,
                },
                "horizon_60min": {
                    "cohort_total": sum(grp_origins_5m_t6_60.values()),
                    "by_group": grp_origins_5m_t6_60,
                },
            },
            "five_minute_native_lattice_fixed_phases_sensitivity": {
                "horizon_30min": {
                    "cohort_by_phase": cohort_phases_30,
                    "by_group": grp_origins_5m_phases_30,
                },
                "horizon_60min": {
                    "cohort_by_phase": cohort_phases_60,
                    "by_group": grp_origins_5m_phases_60,
                },
            },
            "descriptive_offset_pairs_no_history_baseline": {
                "horizon_30min": 625098,
                "horizon_60min": 622078,
                "note": "Stage 1B Task T1 pairs_at_offset stepping across runs without 60m history window.",
            },
        },
        "hyperglycemia_excursion_feasibility": {
            "one_minute_representation_15m_persistence": make_excursion_summary(
                grp_episodes_1m, grp_censored_1m, grp_ep_dist_1m
            ),
            "five_minute_native_lattice_3pt_10m_elapsed": make_excursion_summary(
                grp_episodes_5m_3pt, grp_censored_5m_3pt, grp_ep_dist_5m_3pt
            ),
            "five_minute_native_lattice_4pt_15m_elapsed": make_excursion_summary(
                grp_episodes_5m_4pt, grp_censored_5m_4pt, grp_ep_dist_5m_4pt
            ),
        },
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    return results


def main() -> None:
    """CLI entrypoint for aggregate feasibility generation."""
    parser = argparse.ArgumentParser(
        description="Compute privacy-preserving aggregate feasibility metrics for Stage 2 readiness."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/cgmacros/CGMacros"),
        help="Path to CGMacros data directory.",
    )
    parser.add_argument(
        "--bio-path",
        type=Path,
        default=Path("data/cgmacros/CGMacros/bio.csv"),
        help="Path to bio.csv demographic metadata.",
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=Path("configs/stage1b.yaml"),
        help="Path to configs/stage1b.yaml.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/reports/stage2_aggregate_feasibility.json"),
        help="Path to output JSON file.",
    )

    args = parser.parse_args()
    results = run_aggregate_feasibility_analysis(
        data_dir=args.data_dir,
        bio_path=args.bio_path,
        config_path=args.config_path,
        output_path=args.output,
    )
    print("Successfully generated aggregate feasibility analysis:")
    print(f"  Saved to: {args.output}")
    print(f"  Cohort recorded rows: {results['coverage_cohort_totals']['total_recorded_rows']:,}")
    print(f"  Cohort valid Dexcom rows: {results['coverage_cohort_totals']['valid_dexcom_rows']:,}")
    print(f"  Evaluable runs: {results['coverage_cohort_totals']['evaluable_dexcom_runs_t6']}")
    print(
        f"  5m native origins (+30m): {results['candidate_forecast_origins']['five_minute_native_lattice_t6_inferred_phase']['horizon_30min']['cohort_total']:,}"
    )
    print(
        f"  1m excursion episodes: {results['hyperglycemia_excursion_feasibility']['one_minute_representation_15m_persistence']['total_episodes_cohort']} (censored: {results['hyperglycemia_excursion_feasibility']['one_minute_representation_15m_persistence']['total_censored_cohort']})"
    )


if __name__ == "__main__":
    main()
