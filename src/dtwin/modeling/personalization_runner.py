"""Stage 3: Personalization Experiment Runner.

Executes the participant-specific residual-correction personalization experiment
across both horizons (+30m, +60m) and three adaptation windows (2, 4, 6 study days).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from dtwin.analysis.aggregate_feasibility import load_diagnostic_group_mapping
from dtwin.modeling.covariates import (
    CovariatePreprocessor,
    assemble_rung5_matrix,
    tune_covariate_ridge_alpha,
)
from dtwin.modeling.cv import CVSplit, generate_repeated_cv_splits
from dtwin.modeling.dataset import ParticipantOrigins, extract_cohort_guard_band_dataset
from dtwin.modeling.manifest import calculate_sha256, get_git_commit_hash
from dtwin.modeling.meal import MealPreprocessor
from dtwin.modeling.personalization import (
    compute_personalization_cohort_summary,
    consolidate_personalization_metrics,
    fit_predict_personalized_participant,
)


def run_horizon_personalization(
    dataset: dict[str, ParticipantOrigins],
    splits: list[CVSplit],
    pid_to_group: dict[str, str],
    horizon_minutes: int,
    windows_days: list[int] | None = None,
    n_repeats: int = 10,
    n_splits_per_repeat: int = 5,
) -> dict[str, Any]:
    """Execute personalization benchmark for a single horizon across multiple adaptation windows.

    Args:
        dataset: Mapping of participant IDs to ParticipantOrigins.
        splits: List of 50 CVSplit objects.
        pid_to_group: Mapping of participant ID to diagnostic group string.
        horizon_minutes: Forecast horizon in minutes (+30 or +60).
        windows_days: List of adaptation windows in study days (default: [2, 4, 6]).
        n_repeats: Number of cross-validation repetitions (10).
        n_splits_per_repeat: Number of folds per repetition (5).

    Returns:
        Dictionary containing benchmark metrics, summaries, and out-of-fold predictions.
    """
    if windows_days is None:
        windows_days = [2, 4, 6]

    sorted_pids = sorted(dataset.keys())
    repeats_splits: list[list[CVSplit]] = []
    for r in range(n_repeats):
        rep = [sp for sp in splits if sp.repeat_idx == r]
        assert len(rep) == n_splits_per_repeat
        repeats_splits.append(rep)

    # Per-window tracking of repeat metrics and prediction arrays
    rep_metrics_by_window: dict[int, list[dict[str, dict[str, Any]]]] = {
        w: [] for w in windows_days
    }
    preds_by_window_and_pid: dict[int, dict[str, list[np.ndarray]]] = {
        w: {p: [] for p in sorted_pids} for w in windows_days
    }
    global_preds_by_pid: dict[str, list[np.ndarray]] = {p: [] for p in sorted_pids}

    for r_idx in range(n_repeats):
        rep_splits = repeats_splits[r_idx]
        current_rep_dicts: dict[int, dict[str, dict[str, Any]]] = {w: {} for w in windows_days}

        for sp in rep_splits:
            # Step 1: Tune global Rung 5 Ridge alpha on training participants (36)
            alpha_opt_global, _ = tune_covariate_ridge_alpha(
                dataset=dataset,
                train_pids=sp.train_pids,
                pid_to_group=pid_to_group,
                horizon_minutes=horizon_minutes,
                seed=sp.seed * 100 + sp.fold_idx,
            )

            # Step 2: Fit global Rung 5 preprocessing and model on full training fold
            X_tr_hist = np.vstack([dataset[p].history_lags for p in sp.train_pids])
            X_tr_meal = np.vstack([dataset[p].meal_features for p in sp.train_pids])
            cov_train_list = []
            for p in sp.train_pids:
                n_p = dataset[p].n_origins
                cov_train_list.append(np.tile(dataset[p].static_covariates, (n_p, 1)))
            X_tr_cov = np.vstack(cov_train_list)
            y_tr = np.concatenate([dataset[p].target for p in sp.train_pids])

            meal_prep = MealPreprocessor().fit(X_tr_meal)
            cov_prep = CovariatePreprocessor().fit(X_tr_cov)
            X_tr = assemble_rung5_matrix(X_tr_hist, X_tr_meal, X_tr_cov, meal_prep, cov_prep)

            scaler = StandardScaler(with_mean=True, with_std=True)
            X_tr_s = scaler.fit_transform(X_tr)

            global_model = Ridge(alpha=alpha_opt_global, fit_intercept=True)
            global_model.fit(X_tr_s, y_tr)

            # Step 3: Evaluate each test participant across each adaptation window
            for test_pid in sp.test_pids:
                orig = dataset[test_pid]

                # Full global predictions for tracking
                X_full_test = assemble_rung5_matrix(
                    orig.history_lags,
                    orig.meal_features,
                    orig.static_covariates,
                    meal_prep,
                    cov_prep,
                )
                X_full_test_s = scaler.transform(X_full_test)
                y_pred_glob_all = global_model.predict(X_full_test_s)
                global_preds_by_pid[test_pid].append(y_pred_glob_all)

                for w in windows_days:
                    res_p = fit_predict_personalized_participant(
                        orig=orig,
                        global_model=global_model,
                        meal_prep=meal_prep,
                        cov_prep=cov_prep,
                        scaler=scaler,
                        alpha_global=alpha_opt_global,
                        days=w,
                        purge_minutes=120,
                    )
                    current_rep_dicts[w][test_pid] = res_p
                    preds_by_window_and_pid[w][test_pid].append(res_p["y_pred_pers_eval"])

        for w in windows_days:
            rep_metrics_by_window[w].append(current_rep_dicts[w])

    # Consolidate metrics and compute cohort summaries across all windows
    window_results: dict[str, Any] = {}
    for w in windows_days:
        consolidated = consolidate_personalization_metrics(rep_metrics_by_window[w])
        summary = compute_personalization_cohort_summary(consolidated)
        total_eval_origins = sum(consolidated[p]["n_eval"] for p in sorted_pids)
        total_adapt_origins = sum(consolidated[p]["n_adapt"] for p in sorted_pids)

        window_results[f"window_{w}d"] = {
            "window_days": w,
            "total_adaptation_origins": total_adapt_origins,
            "total_evaluation_origins": total_eval_origins,
            "summary": summary,
            "participants": consolidated,
        }

    # Average global predictions across repetitions
    global_mean_preds = {p: np.mean(np.array(global_preds_by_pid[p]), axis=0) for p in sorted_pids}

    # Average personalized evaluation predictions across repetitions
    pers_mean_preds: dict[int, dict[str, np.ndarray]] = {}
    for w in windows_days:
        pers_mean_preds[w] = {
            p: np.mean(np.array(preds_by_window_and_pid[w][p]), axis=0) for p in sorted_pids
        }

    return {
        "horizon_minutes": horizon_minutes,
        "total_participants": len(sorted_pids),
        "windows": window_results,
        "oof_predictions": {
            "global_mean": global_mean_preds,
            "pers_mean_by_window": pers_mean_preds,
        },
    }


def save_personalization_oof_csv_gz(
    dataset: dict[str, ParticipantOrigins],
    res: dict[str, Any],
    output_path: Path,
    windows_days: list[int] | None = None,
) -> None:
    """Save machine-readable out-of-fold personalization predictions to gzip CSV."""
    if windows_days is None:
        windows_days = [2, 4, 6]

    rows: list[dict[str, Any]] = []
    sorted_pids = sorted(dataset.keys())
    h = res["horizon_minutes"]

    global_preds = res["oof_predictions"]["global_mean"]
    pers_preds = res["oof_predictions"]["pers_mean_by_window"]

    for pid in sorted_pids:
        orig = dataset[pid]
        p_glob = global_preds[pid]
        el = orig.elapsed_minutes
        n_orig = len(orig.target)

        # Precompute evaluation masks for each window
        eval_masks: dict[int, np.ndarray] = {}
        pers_arrays: dict[int, np.ndarray] = {}
        for w in windows_days:
            cutoff_m = w * 1440
            mask = el >= (cutoff_m + 120)
            eval_masks[w] = mask
            # Aligned full-length array initialized with NaN
            full_pers = np.full(n_orig, np.nan, dtype=float)
            if np.any(mask):
                full_pers[mask] = pers_preds[w][pid]
            pers_arrays[w] = full_pers

        for i in range(n_orig):
            row: dict[str, Any] = {
                "participant_id": pid,
                "diag_group": orig.diag_group,
                "timestamp": orig.timestamps[i],
                "elapsed_minutes": int(el[i]),
                "horizon_minutes": h,
                "y_true": float(orig.target[i]),
                "y_pred_global_mean": float(p_glob[i]),
            }
            for w in windows_days:
                row[f"in_eval_window_{w}d"] = bool(eval_masks[w][i])
                row[f"y_pred_pers_mean_{w}d"] = (
                    float(pers_arrays[w][i]) if eval_masks[w][i] else np.nan
                )
            rows.append(row)

    df_out = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_path, index=False, compression="gzip")


def run_stage3_personalization_pipeline(
    repo_root: Path,
    data_dir: Path,
    bio_path: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute complete Stage 3 personalization benchmark pipeline."""
    if output_dir is None:
        output_dir = repo_root / "docs" / "reports"

    # Step 1: Record experiment manifest before fitting
    manifest_path = output_dir / "stage3_personalization_manifest.json"
    protocol_path = repo_root / "docs" / "STAGE3_PERSONALIZATION_PROTOCOL.md"
    stage2_proto_path = repo_root / "docs" / "STAGE2_PROTOCOL_DRAFT.md"
    config_path = repo_root / "configs" / "stage1b.yaml"
    feasibility_path = repo_root / "docs" / "reports" / "stage2_aggregate_feasibility.json"

    created_at_utc = datetime.now(timezone.utc).isoformat()
    git_commit = get_git_commit_hash(repo_root)
    stage3_proto_sha = calculate_sha256(protocol_path)
    stage2_proto_sha = calculate_sha256(stage2_proto_path)
    stage1b_cfg_sha = calculate_sha256(config_path)
    feasibility_sha = calculate_sha256(feasibility_path)

    manifest: dict[str, Any] = {
        "metadata": {
            "title": "Stage 3 Predictive Modeling Personalization Benchmark Manifest",
            "experiment_id": "STAGE3-EXP-001-PERSONALIZATION",
            "protocol_version": "1.0.0",
            "created_at_utc": created_at_utc,
        },
        "artifact_integrity": {
            "git_commit": git_commit,
            "stage3_personalization_protocol": {
                "path": str(protocol_path.relative_to(repo_root)).replace("\\", "/"),
                "sha256": stage3_proto_sha,
            },
            "stage2_protocol": {
                "path": str(stage2_proto_path.relative_to(repo_root)).replace("\\", "/"),
                "sha256": stage2_proto_sha,
            },
            "stage1b_config": {
                "path": str(config_path.relative_to(repo_root)).replace("\\", "/"),
                "sha256": stage1b_cfg_sha,
            },
            "stage2_feasibility_report": {
                "path": str(feasibility_path.relative_to(repo_root)).replace("\\", "/"),
                "sha256": feasibility_sha,
            },
        },
        "experimental_setup": {
            "global_model": "Rung 5 Baseline-Covariate Ridge Regression (20 features)",
            "personalization_model": "Regularized Ridge Residual-Correction Model (16 dynamic features)",
            "adaptation_windows_days": [2, 4, 6],
            "purge_minutes": 120,
            "forecast_horizons_minutes": [30, 60],
            "validation_design": {
                "scheme": "Repeated Participant-Disjoint Stratified Cross-Validation",
                "n_repeats": 10,
                "n_splits_per_repeat": 5,
                "seeds": [42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
                "outer_train_participants_count": 36,
                "outer_test_participants_count": 9,
            },
            "bootstrap_evaluation": {
                "resampling_unit": "45 independent participants",
                "iterations": 2000,
                "seed": 42,
            },
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Step 2: Extract dataset origins
    pid_to_group = load_diagnostic_group_mapping(bio_path)
    ds30 = extract_cohort_guard_band_dataset(data_dir, bio_path, horizon_minutes=30)
    ds60 = extract_cohort_guard_band_dataset(data_dir, bio_path, horizon_minutes=60)

    # Generate 10-repeat 5-fold CV splits (seeds 42..51)
    participants = sorted(ds30.keys())
    diag_groups = [pid_to_group[p] for p in participants]
    splits = generate_repeated_cv_splits(participants, diag_groups)

    # Step 3: Run personalization experiment
    res30 = run_horizon_personalization(ds30, splits, pid_to_group, horizon_minutes=30)
    res60 = run_horizon_personalization(ds60, splits, pid_to_group, horizon_minutes=60)

    # Save out-of-fold predictions
    oof_30_path = output_dir / "stage3_personalization_oof_h30.csv.gz"
    oof_60_path = output_dir / "stage3_personalization_oof_h60.csv.gz"
    save_personalization_oof_csv_gz(ds30, res30, oof_30_path)
    save_personalization_oof_csv_gz(ds60, res60, oof_60_path)

    # Step 4: Compile machine-readable metrics report
    clean_res30 = {k: v for k, v in res30.items() if k != "oof_predictions"}
    clean_res60 = {k: v for k, v in res60.items() if k != "oof_predictions"}

    report = {
        "metadata": {
            "title": "Stage 3 Personalization Experiment Benchmark Results (2, 4, and 6 Study Days)",
            "version": "1.0.0",
            "experiment_id": "STAGE3-EXP-001-PERSONALIZATION",
            "created_at_utc": created_at_utc,
            "git_commit": git_commit,
            "protocol_stage3_sha256": stage3_proto_sha,
            "protocol_stage2_sha256": stage2_proto_sha,
            "stage1b_config_sha256": stage1b_cfg_sha,
            "stage2_feasibility_sha256": feasibility_sha,
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

    metrics_path = output_dir / "stage3_personalization_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 3 Personalization Experiment")
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

    print(f"Executing Stage 3 Personalization on {data_dir}...")
    _ = run_stage3_personalization_pipeline(
        repo_root=repo_root,
        data_dir=data_dir,
        bio_path=bio_path,
        output_dir=output_dir,
    )
    print("Stage 3 Personalization execution completed successfully!")
    print(f"Metrics saved to {output_dir / 'stage3_personalization_metrics.json'}")


if __name__ == "__main__":
    main()
