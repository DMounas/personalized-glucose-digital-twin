"""Execution runner for Stage 2 baseline modeling experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from dtwin.analysis.aggregate_feasibility import load_diagnostic_group_mapping
from dtwin.modeling.baselines import (
    predict_damped_trend,
    predict_guarded_persistence,
    tune_damped_trend_gamma,
)
from dtwin.modeling.cv import CVSplit, generate_repeated_cv_splits
from dtwin.modeling.dataset import ParticipantOrigins, extract_cohort_guard_band_dataset
from dtwin.modeling.manifest import build_experiment_manifest
from dtwin.modeling.metrics import (
    compute_cohort_summary_and_bootstrap,
    compute_participant_metrics,
    consolidate_repeated_metrics,
)


def run_horizon_baselines(
    dataset: dict[str, ParticipantOrigins],
    splits: list[CVSplit],
    pid_to_group: dict[str, str],
    horizon_minutes: int,
) -> dict[str, Any]:
    """Execute repeated 10-seed 5-fold evaluation of Rung 0 and Rung 1 for one horizon.

    Args:
        dataset: Mapping of participant_id -> ParticipantOrigins.
        splits: List of 50 CVSplit objects (10 repeats x 5 folds).
        pid_to_group: Mapping of participant_id -> diagnostic group string.
        horizon_minutes: Forecast horizon in minutes (+30 or +60).

    Returns:
        Structured dictionary of results, predictions, parameters, and cohort metrics.
    """
    sorted_pids = sorted(dataset.keys())
    assert len(sorted_pids) == 45, f"Expected 45 participants, found {len(sorted_pids)}"

    # Group splits by repetition index (0..9)
    n_repeats = 10
    repeats_splits: dict[int, list[CVSplit]] = {r: [] for r in range(n_repeats)}
    for s in splits:
        repeats_splits[s.repeat_idx].append(s)

    r0_rep_metrics: list[dict[str, dict[str, Any]]] = []
    r1_rep_metrics: list[dict[str, dict[str, Any]]] = []

    # Store fold gammas: list of 50 entries
    fold_gammas: list[dict[str, Any]] = []

    # Repetition-level predictions collector for participant-level averaging
    # pid -> 2D array [10 repeats, n_origins]
    r0_preds_by_pid: dict[str, list[np.ndarray]] = {p: [] for p in sorted_pids}
    r1_preds_by_pid: dict[str, list[np.ndarray]] = {p: [] for p in sorted_pids}

    for r_idx in range(n_repeats):
        rep_splits = repeats_splits[r_idx]
        rep_r0_dict: dict[str, dict[str, Any]] = {}
        rep_r1_dict: dict[str, dict[str, Any]] = {}

        for sp in rep_splits:
            # Tune Rung 1 gamma on outer training participants (36)
            gamma_opt, diag = tune_damped_trend_gamma(
                dataset=dataset,
                train_pids=sp.train_pids,
                pid_to_group=pid_to_group,
                horizon_minutes=horizon_minutes,
                seed=sp.seed * 100 + sp.fold_idx,
            )

            fold_gammas.append(
                {
                    "repeat_idx": sp.repeat_idx,
                    "seed": sp.seed,
                    "fold_idx": sp.fold_idx,
                    "horizon_minutes": horizon_minutes,
                    "gamma_opt": gamma_opt,
                    "tuning_diagnostics": diag,
                    "train_participants_count": len(sp.train_pids),
                    "test_participants_count": len(sp.test_pids),
                }
            )

            # Evaluate on outer test participants (9)
            for test_pid in sp.test_pids:
                orig = dataset[test_pid]
                y_true = orig.target
                y_base = orig.y_base
                roc = orig.roc
                n_orig = len(y_true)

                # Rung 0: Guarded Persistence
                pred_r0 = predict_guarded_persistence(y_base)
                rmse_r0, mae_r0, skill_r0 = compute_participant_metrics(
                    y_true, pred_r0, y_base, is_persistence=True
                )
                rep_r0_dict[test_pid] = {
                    "diag_group": orig.diag_group,
                    "n_origins": n_orig,
                    "rmse": rmse_r0,
                    "mae": mae_r0,
                    "skill": skill_r0,
                }
                r0_preds_by_pid[test_pid].append(pred_r0)

                # Rung 1: Damped Trend
                pred_r1 = predict_damped_trend(y_base, roc, horizon_minutes, gamma_opt)
                rmse_r1, mae_r1, skill_r1 = compute_participant_metrics(
                    y_true, pred_r1, y_base, is_persistence=False
                )
                rep_r1_dict[test_pid] = {
                    "diag_group": orig.diag_group,
                    "n_origins": n_orig,
                    "rmse": rmse_r1,
                    "mae": mae_r1,
                    "skill": skill_r1,
                }
                r1_preds_by_pid[test_pid].append(pred_r1)

        r0_rep_metrics.append(rep_r0_dict)
        r1_rep_metrics.append(rep_r1_dict)

    # Consolidate participant metrics across 10 repetitions
    r0_consolidated = consolidate_repeated_metrics(r0_rep_metrics)
    r1_consolidated = consolidate_repeated_metrics(r1_rep_metrics)

    # Compute cohort summary and participant bootstrap CIs
    r0_summary = compute_cohort_summary_and_bootstrap(r0_consolidated)
    r1_summary = compute_cohort_summary_and_bootstrap(r1_consolidated)

    # Average out-of-fold predictions across repetitions
    r0_mean_preds: dict[str, np.ndarray] = {
        p: np.mean(np.array(r0_preds_by_pid[p]), axis=0) for p in sorted_pids
    }
    r1_mean_preds: dict[str, np.ndarray] = {
        p: np.mean(np.array(r1_preds_by_pid[p]), axis=0) for p in sorted_pids
    }

    gammas_only = [fg["gamma_opt"] for fg in fold_gammas]

    return {
        "horizon_minutes": horizon_minutes,
        "total_origins": sum(orig.n_origins for orig in dataset.values()),
        "total_participants": len(sorted_pids),
        "gammas_summary": {
            "mean": float(np.mean(gammas_only)),
            "std": float(np.std(gammas_only)),
            "min": float(np.min(gammas_only)),
            "max": float(np.max(gammas_only)),
            "all_50_splits": fold_gammas,
        },
        "rung0_guarded_persistence": {
            "summary": r0_summary,
            "participants": {
                p: {
                    "diag_group": r0_consolidated[p].diag_group,
                    "n_origins": r0_consolidated[p].n_origins,
                    "mean_rmse": r0_consolidated[p].mean_rmse,
                    "mean_mae": r0_consolidated[p].mean_mae,
                    "mean_skill": r0_consolidated[p].mean_skill,
                    "rmse_per_repeat": r0_consolidated[p].rmse_per_repeat,
                    "mae_per_repeat": r0_consolidated[p].mae_per_repeat,
                    "skill_per_repeat": r0_consolidated[p].skill_per_repeat,
                }
                for p in sorted_pids
            },
        },
        "rung1_damped_trend": {
            "summary": r1_summary,
            "participants": {
                p: {
                    "diag_group": r1_consolidated[p].diag_group,
                    "n_origins": r1_consolidated[p].n_origins,
                    "mean_rmse": r1_consolidated[p].mean_rmse,
                    "mean_mae": r1_consolidated[p].mean_mae,
                    "mean_skill": r1_consolidated[p].mean_skill,
                    "rmse_per_repeat": r1_consolidated[p].rmse_per_repeat,
                    "mae_per_repeat": r1_consolidated[p].mae_per_repeat,
                    "skill_per_repeat": r1_consolidated[p].skill_per_repeat,
                }
                for p in sorted_pids
            },
        },
        "oof_predictions": {
            "r0_mean": r0_mean_preds,
            "r1_mean": r1_mean_preds,
        },
    }


def save_oof_predictions_csv_gz(
    dataset: dict[str, ParticipantOrigins],
    res: dict[str, Any],
    output_path: Path,
) -> None:
    """Save machine-readable out-of-fold predictions to a gzip CSV file.

    Columns:
    - participant_id
    - diag_group
    - timestamp
    - horizon_minutes
    - y_true
    - y_pred_persistence (Rung 0)
    - y_pred_damped_mean (Rung 1, averaged across 10 repeated CV test fits)
    """
    rows: list[dict[str, Any]] = []
    sorted_pids = sorted(dataset.keys())
    h = res["horizon_minutes"]

    r0_preds = res["oof_predictions"]["r0_mean"]
    r1_preds = res["oof_predictions"]["r1_mean"]

    for pid in sorted_pids:
        orig = dataset[pid]
        p_r0 = r0_preds[pid]
        p_r1 = r1_preds[pid]

        for i in range(len(orig.target)):
            rows.append(
                {
                    "participant_id": pid,
                    "diag_group": orig.diag_group,
                    "timestamp": orig.timestamps[i],
                    "horizon_minutes": h,
                    "y_true": float(orig.target[i]),
                    "y_pred_persistence": float(p_r0[i]),
                    "y_pred_damped_mean": float(p_r1[i]),
                }
            )

    df_out = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_path, index=False, compression="gzip")


def run_stage2_baselines_pipeline(
    repo_root: Path,
    data_dir: Path,
    bio_path: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute complete Stage 2 baseline experiment pipeline."""
    if output_dir is None:
        output_dir = repo_root / "docs" / "reports"

    # Step 1: Record experiment identity before fitting
    manifest_path = output_dir / "stage2_baseline_manifest.json"
    manifest = build_experiment_manifest(repo_root=repo_root, manifest_path=manifest_path)

    # Step 2: Extract dataset origins
    pid_to_group = load_diagnostic_group_mapping(bio_path)
    ds30 = extract_cohort_guard_band_dataset(data_dir, bio_path, horizon_minutes=30)
    ds60 = extract_cohort_guard_band_dataset(data_dir, bio_path, horizon_minutes=60)

    # Verify origin count invariance
    tot30 = sum(p.n_origins for p in ds30.values())
    tot60 = sum(p.n_origins for p in ds60.values())
    assert tot30 == 123599, f"Origin count mismatch for +30m: {tot30} != 123599"
    assert tot60 == 123164, f"Origin count mismatch for +60m: {tot60} != 123164"

    # Generate 10-repeat 5-fold CV splits (seeds 42..51)
    participants = sorted(ds30.keys())
    diag_groups = [pid_to_group[p] for p in participants]
    splits = generate_repeated_cv_splits(participants, diag_groups)

    # Step 3: Run baselines
    res30 = run_horizon_baselines(ds30, splits, pid_to_group, horizon_minutes=30)
    res60 = run_horizon_baselines(ds60, splits, pid_to_group, horizon_minutes=60)

    # Save out-of-fold predictions
    oof_30_path = output_dir / "stage2_baseline_oof_h30.csv.gz"
    oof_60_path = output_dir / "stage2_baseline_oof_h60.csv.gz"
    save_oof_predictions_csv_gz(ds30, res30, oof_30_path)
    save_oof_predictions_csv_gz(ds60, res60, oof_60_path)

    # Compile final metrics report (excluding in-memory prediction arrays from JSON)
    clean_res30 = {k: v for k, v in res30.items() if k != "oof_predictions"}
    clean_res60 = {k: v for k, v in res60.items() if k != "oof_predictions"}

    report = {
        "metadata": {
            "title": "Stage 2 Predictive Modeling Baseline Results (Rungs 0 & 1)",
            "version": "1.0.0",
            "experiment_id": "STAGE2-EXP-001-BASELINES",
            "created_at_utc": manifest["metadata"]["created_at_utc"],
            "git_commit": manifest["artifact_integrity"]["git_commit"],
            "protocol_sha256": manifest["artifact_integrity"]["protocol"]["sha256"],
            "stage1b_config_sha256": manifest["artifact_integrity"]["stage1b_config"]["sha256"],
            "stage2_feasibility_sha256": manifest["artifact_integrity"][
                "stage2_feasibility_report"
            ]["sha256"],
        },
        "horizons": {
            "h30": clean_res30,
            "h60": clean_res60,
        },
        "artifacts_generated": {
            "manifest": str(manifest_path.relative_to(repo_root)).replace("\\", "/"),
            "oof_h30_csv_gz": str(oof_30_path.relative_to(repo_root)).replace("\\", "/"),
            "oof_h60_csv_gz": str(oof_60_path.relative_to(repo_root)).replace("\\", "/"),
        },
    }

    metrics_path = output_dir / "stage2_baseline_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 2 Baseline Modeling (Rungs 0 & 1)")
    parser.add_argument("--repo-root", type=str, default=".", help="Repository root path")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/cgmacros/CGMacros",
        help="Path to participant directories",
    )
    parser.add_argument(
        "--bio-path",
        type=str,
        default="data/cgmacros/CGMacros/bio.csv",
        help="Path to bio.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/reports",
        help="Output directory for reports and predictions",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    data_dir = (repo_root / args.data_dir).resolve()
    bio_path = (repo_root / args.bio_path).resolve()
    output_dir = (repo_root / args.output_dir).resolve()

    print(f"Executing Stage 2 Baselines on {data_dir}...")
    _ = run_stage2_baselines_pipeline(
        repo_root=repo_root,
        data_dir=data_dir,
        bio_path=bio_path,
        output_dir=output_dir,
    )
    print("Baseline execution completed successfully!")
    print(f"Metrics saved to {output_dir / 'stage2_baseline_metrics.json'}")


if __name__ == "__main__":
    main()
