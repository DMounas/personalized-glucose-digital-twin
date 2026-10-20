"""Stage 2 Rung 5: Baseline-Covariate Augmentation.

Extends the Rung 4 No-Macros Timing model with static participant covariates from bio.csv:
x_static = [Age, Gender (Female=1.0, Male=0.0), BMI, Baseline_HbA1c]^T in R^4.

Combined predictor vector:
x_rung5 = [x_autoreg (13), x_meal_timing (3), x_static (4)]^T in R^20.

Missing covariates are imputed strictly using training-fold medians/modes.
All preprocessing (imputation + StandardScaler) and Ridge alpha tuning
are fitted strictly on training participants only via inner 4-fold participant-grouped CV.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from dtwin.modeling.cv import generate_inner_cv_splits
from dtwin.modeling.dataset import ParticipantOrigins
from dtwin.modeling.meal import MealPreprocessor


def load_participant_covariates(bio_path: Path) -> dict[str, np.ndarray]:
    """Load baseline participant demographic and clinical covariates from bio.csv.

    Columns extracted (Protocol v1.0.0 Section 4.6):
    - Age: Age in years
    - Gender: Binary indicator (Female = 1.0, Male = 0.0)
    - BMI: Body Mass Index (kg/m^2)
    - Baseline_HbA1c: Laboratory HbA1c from 'A1c PDL (Lab)' (%)

    Args:
        bio_path: Path to bio.csv.

    Returns:
        Mapping from participant folder ID ('CGMacros-0XX') to static covariate array of shape (4,).
    """
    bio_df = pd.read_csv(bio_path)
    bio_df.columns = [c.strip() for c in bio_df.columns]

    cov_map: dict[str, np.ndarray] = {}
    for _, row in bio_df.iterrows():
        subj_int = int(row["subject"])
        pid = f"CGMacros-{subj_int:03d}"

        age = float(row["Age"]) if pd.notna(row["Age"]) else np.nan
        gender_str = str(row["Gender"]).strip().upper() if pd.notna(row["Gender"]) else ""
        gender = 1.0 if gender_str == "F" else (0.0 if gender_str == "M" else np.nan)
        bmi = float(row["BMI"]) if pd.notna(row["BMI"]) else np.nan
        hba1c = float(row["A1c PDL (Lab)"]) if pd.notna(row["A1c PDL (Lab)"]) else np.nan

        cov_map[pid] = np.array([age, gender, bmi, hba1c], dtype=np.float64)

    return cov_map


@dataclass
class CovariatePreprocessor:
    """Training-fold-only imputer for static participant covariates."""

    medians: np.ndarray | None = None  # shape (4,): [age, gender, bmi, hba1c]

    def fit(self, X_cov_train: np.ndarray) -> CovariatePreprocessor:
        """Compute column medians on non-null training covariates."""
        meds: list[float] = []
        for j in range(4):
            col = X_cov_train[:, j]
            valid = col[~np.isnan(col)]
            if len(valid) > 0:
                meds.append(float(np.median(valid)))
            else:
                meds.append(0.0)
        self.medians = np.array(meds, dtype=np.float64)
        return self

    def transform(self, X_cov: np.ndarray) -> np.ndarray:
        """Impute missing values using fitted training medians."""
        assert self.medians is not None, "CovariatePreprocessor must be fitted before transform."
        X_out = np.asarray(X_cov, dtype=np.float64).copy()
        if X_out.ndim == 1:
            X_out = X_out.reshape(1, -1)

        for j in range(4):
            nan_mask = np.isnan(X_out[:, j])
            X_out[nan_mask, j] = self.medians[j]

        return X_out


def assemble_rung5_matrix(
    history_lags: np.ndarray,
    meal_features: np.ndarray,
    static_covariates: np.ndarray,
    meal_preprocessor: MealPreprocessor,
    cov_preprocessor: CovariatePreprocessor,
) -> np.ndarray:
    """Assemble 20-dimensional predictor matrix for Rung 5.

    Components:
    - 13 glucose history lags: [y(t-5), ..., y(t-65)]
    - 3 meal timing features (Rung 4 No-Macros Ablation): [time_since, in_60m, no_recent_meal]
    - 4 static baseline covariates: [Age, Gender, BMI, Baseline_HbA1c]

    Args:
        history_lags: Array of shape (N, 13).
        meal_features: Array of shape (N, 7).
        static_covariates: Array of shape (4,) or (N, 4).
        meal_preprocessor: Fitted MealPreprocessor.
        cov_preprocessor: Fitted CovariatePreprocessor.

    Returns:
        Array of shape (N, 20).
    """
    n = len(history_lags)
    # Meal timing features (3 columns)
    meal_imputed = meal_preprocessor.transform(meal_features)
    timing_features = meal_imputed[:, [0, 1, 6]]

    # Static covariates (4 columns, broadcast to N rows)
    if static_covariates.ndim == 1:
        cov_matrix = np.tile(static_covariates, (n, 1))
    else:
        cov_matrix = static_covariates

    cov_imputed = cov_preprocessor.transform(cov_matrix)
    return np.hstack([history_lags, timing_features, cov_imputed])


def tune_covariate_ridge_alpha(
    dataset: dict[str, ParticipantOrigins],
    train_pids: list[str],
    pid_to_group: dict[str, str],
    horizon_minutes: int,
    seed: int,
    candidate_alphas: np.ndarray | None = None,
) -> tuple[float, dict[str, Any]]:
    """Estimate optimal Ridge alpha for Rung 5 via inner 4-fold participant-grouped CV.

    Evaluated strictly on outer training participants (36 participants).
    Preprocessing (imputation + StandardScaler) is fitted strictly on inner training folds.

    Args:
        dataset: Mapping of participant IDs to ParticipantOrigins.
        train_pids: List of participant IDs in outer training fold (36 participants).
        pid_to_group: Mapping from participant ID to diagnostic group string.
        horizon_minutes: Forecast horizon in minutes (+30 or +60).
        seed: Random seed for inner fold partitioning.
        candidate_alphas: Array of candidate alpha values. Defaults to 17 log-spaced
            values in [10^-2, 10^6].

    Returns:
        Tuple of (optimal_alpha, tuning_diagnostics).
    """
    if candidate_alphas is None:
        candidate_alphas = np.logspace(-2, 6, 17)

    inner_splits = generate_inner_cv_splits(
        train_pids=train_pids,
        pid_to_group=pid_to_group,
        inner_seed=seed,
        n_splits=4,
    )

    inner_fold_data = []
    n_features = 20
    eye_n = np.eye(n_features, dtype=np.float64)

    for in_split in inner_splits:
        X_in_hist = np.vstack([dataset[p].history_lags for p in in_split.inner_train_pids])
        X_in_meal = np.vstack([dataset[p].meal_features for p in in_split.inner_train_pids])
        cov_train_list = []
        for p in in_split.inner_train_pids:
            n_p = dataset[p].n_origins
            cov_train_list.append(np.tile(dataset[p].static_covariates, (n_p, 1)))
        X_in_cov = np.vstack(cov_train_list)
        y_in_tr = np.concatenate([dataset[p].target for p in in_split.inner_train_pids])

        # Fit preprocessors strictly on inner training fold
        meal_prep = MealPreprocessor().fit(X_in_meal)
        cov_prep = CovariatePreprocessor().fit(X_in_cov)

        X_in_tr = assemble_rung5_matrix(X_in_hist, X_in_meal, X_in_cov, meal_prep, cov_prep)

        # Fit StandardScaler strictly on inner training fold
        scaler = StandardScaler(with_mean=True, with_std=True)
        X_in_tr_s = scaler.fit_transform(X_in_tr)

        y_mean = float(np.mean(y_in_tr))
        y_c = y_in_tr - y_mean
        XtX = X_in_tr_s.T @ X_in_tr_s
        Xty = X_in_tr_s.T @ y_c

        # Transform and cache validation participants
        val_cache: list[tuple[np.ndarray, np.ndarray, int]] = []
        for val_p in in_split.inner_val_pids:
            orig = dataset[val_p]
            X_val = assemble_rung5_matrix(
                orig.history_lags,
                orig.meal_features,
                orig.static_covariates,
                meal_prep,
                cov_prep,
            )
            X_val_s = scaler.transform(X_val)
            val_cache.append((X_val_s, orig.target, orig.n_origins))

        inner_fold_data.append((XtX, Xty, y_mean, val_cache))

    alpha_scores: list[float] = []

    for alpha in candidate_alphas:
        a = float(alpha)
        fold_participant_rmses: list[float] = []

        for XtX, Xty, y_mean, val_cache in inner_fold_data:
            w = np.linalg.solve(XtX + a * eye_n, Xty)

            for X_val_s, y_target, n_orig in val_cache:
                if n_orig > 0:
                    pred = y_mean + X_val_s @ w
                    rmse_p = float(np.sqrt(np.mean((y_target - pred) ** 2)))
                    fold_participant_rmses.append(rmse_p)

        mean_rmse = float(np.mean(fold_participant_rmses))
        alpha_scores.append(mean_rmse)

    best_idx = int(np.argmin(alpha_scores))
    best_alpha = float(candidate_alphas[best_idx])

    diagnostics = {
        "best_alpha": best_alpha,
        "best_inner_rmse": float(alpha_scores[best_idx]),
        "inner_folds_count": len(inner_splits),
        "candidate_count": len(candidate_alphas),
        "horizon_minutes": horizon_minutes,
    }

    return best_alpha, diagnostics


def fit_predict_covariate_ridge(
    dataset: dict[str, ParticipantOrigins],
    train_pids: list[str],
    test_pids: list[str],
    alpha: float,
) -> tuple[dict[str, np.ndarray], MealPreprocessor, CovariatePreprocessor, StandardScaler, Ridge]:
    """Fit meal and covariate preprocessors, scaler, and Ridge on training participants and predict on test participants.

    Args:
        dataset: Mapping of participant IDs to ParticipantOrigins.
        train_pids: List of participant IDs in outer training fold (36 participants).
        test_pids: List of participant IDs in outer test fold (9 participants).
        alpha: Optimal Ridge regularization alpha.

    Returns:
        Tuple of (test_predictions_by_pid, fitted_meal_prep, fitted_cov_prep, fitted_scaler, fitted_ridge_model).
    """
    X_tr_hist = np.vstack([dataset[p].history_lags for p in train_pids])
    X_tr_meal = np.vstack([dataset[p].meal_features for p in train_pids])
    cov_train_list = []
    for p in train_pids:
        n_p = dataset[p].n_origins
        cov_train_list.append(np.tile(dataset[p].static_covariates, (n_p, 1)))
    X_tr_cov = np.vstack(cov_train_list)
    y_tr = np.concatenate([dataset[p].target for p in train_pids])

    # Fit preprocessing strictly on training fold
    meal_prep = MealPreprocessor().fit(X_tr_meal)
    cov_prep = CovariatePreprocessor().fit(X_tr_cov)

    X_tr = assemble_rung5_matrix(X_tr_hist, X_tr_meal, X_tr_cov, meal_prep, cov_prep)

    scaler = StandardScaler(with_mean=True, with_std=True)
    X_tr_s = scaler.fit_transform(X_tr)

    model = Ridge(alpha=alpha, fit_intercept=True)
    model.fit(X_tr_s, y_tr)

    preds_by_pid: dict[str, np.ndarray] = {}
    for te_p in test_pids:
        orig = dataset[te_p]
        X_te = assemble_rung5_matrix(
            orig.history_lags,
            orig.meal_features,
            orig.static_covariates,
            meal_prep,
            cov_prep,
        )
        X_te_s = scaler.transform(X_te)
        preds_by_pid[te_p] = model.predict(X_te_s)

    return preds_by_pid, meal_prep, cov_prep, scaler, model
