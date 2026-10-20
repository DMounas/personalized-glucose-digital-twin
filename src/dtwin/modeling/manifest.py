"""Stage 2 Experiment Manifest and Artifact Hash Verification."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def calculate_sha256(file_path: Path) -> str:
    """Calculate the exact lowercase SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def get_git_commit_hash(repo_dir: Path | None = None) -> str:
    """Get the full 40-character git commit hash of HEAD."""
    cmd = ["git", "rev-parse", "HEAD"]
    res = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, check=True)
    return res.stdout.strip()


def build_experiment_manifest(
    repo_root: Path,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Build and record the Stage 2 experiment identity manifest.

    Args:
        repo_root: Root path of the repository.
        manifest_path: Optional path to save the manifest JSON.

    Returns:
        Dictionary representing the complete experiment manifest.
    """
    protocol_path = repo_root / "docs" / "STAGE2_PROTOCOL_DRAFT.md"
    config_path = repo_root / "configs" / "stage1b.yaml"
    feasibility_path = repo_root / "docs" / "reports" / "stage2_aggregate_feasibility.json"

    protocol_sha256 = calculate_sha256(protocol_path)
    config_sha256 = calculate_sha256(config_path)
    feasibility_sha256 = calculate_sha256(feasibility_path)
    git_commit = get_git_commit_hash(repo_root)

    manifest: dict[str, Any] = {
        "metadata": {
            "title": "Stage 2 Predictive Modeling Baseline Experiment Manifest",
            "experiment_id": "STAGE2-EXP-001-BASELINES",
            "protocol_version": "1.0.0",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "artifact_integrity": {
            "git_commit": git_commit,
            "protocol": {
                "path": str(protocol_path.relative_to(repo_root)).replace("\\", "/"),
                "sha256": protocol_sha256,
            },
            "stage1b_config": {
                "path": str(config_path.relative_to(repo_root)).replace("\\", "/"),
                "sha256": config_sha256,
            },
            "stage2_feasibility_report": {
                "path": str(feasibility_path.relative_to(repo_root)).replace("\\", "/"),
                "sha256": feasibility_sha256,
            },
        },
        "experimental_setup": {
            "sensor": "Dexcom G6 Pro (1-minute release grid, 5-minute candidate sampling)",
            "primary_phase": "phi=0",
            "deterministic_minute_coordinate": "m(t) = round((t - t0) / 60s)",
            "history_window_minutes": 60,
            "guard_band_minutes": 5,
            "predictor_lags_minutes": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65],
            "forecast_horizons_minutes": [30, 60],
            "models": [
                {
                    "rung": 0,
                    "name": "Guarded Persistence",
                    "formula": "y_hat(t+h) = y(t-5)",
                    "trainable_parameters": 0,
                },
                {
                    "rung": 1,
                    "name": "Damped Trend",
                    "formula": "y_hat(t+h) = y(t-5) + gamma_h * ((y(t-5) - y(t-20)) / 15) * h",
                    "damping_range": [0.0, 1.0],
                    "selection_method": "Inner 4-fold participant-grouped cross-validation on training participants",
                },
                {
                    "rung": 2,
                    "name": "Guarded Ridge Regression (13 Autoregressive Lags)",
                    "formula": "y_hat(t+h) = w_0 + sum_{k=1}^13 w_k * StandardScaler(y(t - 5k))",
                    "features": "13 guard-banded glucose history lags: [y(t-5), y(t-10), ..., y(t-65)]",
                    "preprocessing": "StandardScaler fitted strictly on training fold",
                    "regularization": "L2 Ridge penalty (alpha selected via inner 4-fold participant-grouped CV)",
                },
                {
                    "rung": 3,
                    "name": "Activity-Augmented Ridge Regression",
                    "formula": "y_hat(t+h) = w_0 + sum_{k=1}^13 w_k * StandardScaler(y(t - 5k)) + sum_{j=1}^4 w_{13+j} * StandardScaler(x_{activity, j})",
                    "features": "13 guard-banded glucose lags + 4 past-30-minute activity features: [mean_HR, delta_HR, mean_METs/10, I_missing_activity]",
                    "preprocessing": "ActivityPreprocessor (training-fold median imputation + missingness flag) + StandardScaler fitted strictly on training fold",
                    "regularization": "L2 Ridge penalty (alpha selected via inner 4-fold participant-grouped CV)",
                },
                {
                    "rung": 4,
                    "name": "Meal-Context Ridge Regression",
                    "formula": "y_hat(t+h) = w_0 + sum_{k=1}^13 w_k * StandardScaler(y(t - 5k)) + sum_{j=1}^7 w_{13+j} * StandardScaler(x_{meal, j})",
                    "features": "13 guard-banded glucose lags + 7 meal context features: [time_since_last_meal, meal_in_last_60m, carbs, protein, fat, fiber, no_recent_meal]",
                    "preprocessing": "MealPreprocessor (training-fold macro median imputation) + StandardScaler fitted strictly on training fold",
                    "regularization": "L2 Ridge penalty (alpha selected via inner 4-fold participant-grouped CV)",
                },
                {
                    "rung": "4_ablation_nomacros",
                    "name": "Meal-Context Ridge Regression (No-Macros Ablation)",
                    "formula": "y_hat(t+h) = w_0 + sum_{k=1}^13 w_k * StandardScaler(y(t - 5k)) + sum_{j=1}^3 w_{13+j} * StandardScaler(x_{meal_timing, j})",
                    "features": "13 guard-banded glucose lags + 3 meal timing features: [time_since_last_meal, meal_in_last_60m, no_recent_meal]",
                    "preprocessing": "MealPreprocessor + StandardScaler fitted strictly on training fold",
                    "regularization": "L2 Ridge penalty (alpha selected via inner 4-fold participant-grouped CV)",
                },
                {
                    "rung": 5,
                    "name": "Baseline-Covariate Augmentation (No-Macros Timing + Static Covariates)",
                    "formula": "y_hat(t+h) = w_0 + sum_{k=1}^13 w_k * StandardScaler(y(t - 5k)) + sum_{j=1}^3 w_{13+j} * StandardScaler(x_{meal_timing, j}) + sum_{m=1}^4 w_{16+m} * StandardScaler(x_{static, m})",
                    "features": "13 guard-banded glucose lags + 3 meal timing features + 4 static covariates: [Age, Gender (Female=1), BMI, Baseline_HbA1c]",
                    "preprocessing": "CovariatePreprocessor (training-fold medians/modes) + MealPreprocessor + StandardScaler fitted strictly on training fold",
                    "regularization": "L2 Ridge penalty (alpha selected via inner 4-fold participant-grouped CV)",
                },
                {
                    "rung": 6,
                    "name": "Native HistGradientBoostingRegressor (Fixed Settings)",
                    "formula": "y_hat(t+h) = GBDT(x_rung5)",
                    "features": "13 guard-banded glucose lags + 3 meal timing features + 4 static covariates: [Age, Gender (Female=1), BMI, Baseline_HbA1c]",
                    "preprocessing": "CovariatePreprocessor (training-fold medians/modes) + MealPreprocessor (fitted strictly on training fold)",
                    "hyperparameters": {
                        "loss": "squared_error",
                        "learning_rate": 0.05,
                        "max_iter": 100,
                        "max_depth": 4,
                        "min_samples_leaf": 50,
                        "l2_regularization": 0.0,
                        "random_state": 42,
                    },
                },
            ],
            "validation_design": {
                "scheme": "Repeated Participant-Disjoint Stratified Cross-Validation",
                "n_repeats": 10,
                "n_splits": 5,
                "seeds": [42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
                "total_participants": 45,
                "stratification_target": "Clinical baseline HbA1c diagnostic group (15 Normal, 16 Prediabetes, 14 Diabetes)",
                "bootstrap_resampling_unit": "45 independent participants (B=2,000 iterations)",
            },
        },
    }

    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    return manifest
