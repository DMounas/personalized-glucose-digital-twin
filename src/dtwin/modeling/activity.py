"""Stage 2 Rung 3: Activity-Augmented Ridge Regression.

Integrates past-30-minute physiological activity summaries:
x_activity = [mean_HR_[t-30, t], delta_HR_[t-30, t], mean_METs/10_[t-30, t], I_missing_activity]^T.

Combined predictor vector:
x_rung3 = [x_autoreg (13), x_activity (4)]^T in R^17.

Missing activity values are imputed strictly using training-fold medians,
with explicit missingness indicator flag I_missing_activity in {0, 1}.
All preprocessing (imputation + StandardScaler) and Ridge alpha tuning
are fitted strictly on training participants only via inner 4-fold participant-grouped CV.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from dtwin.modeling.cv import generate_inner_cv_splits
from dtwin.modeling.dataset import ParticipantOrigins


@dataclass
class ActivityPreprocessor:
    """Training-fold-only imputer for physical activity features."""

    medians: np.ndarray | None = None

    def fit(self, X_act_train: np.ndarray) -> ActivityPreprocessor:
        """Compute column medians on non-null training activity features."""
        # Columns 0: mean_hr, 1: delta_hr, 2: mean_mets
        meds = []
        for j in range(3):
            col = X_act_train[:, j]
            valid = col[~np.isnan(col)]
            if len(valid) > 0:
                meds.append(float(np.median(valid)))
            else:
                meds.append(0.0)
        self.medians = np.array(meds, dtype=np.float64)
        return self

    def transform(self, X_act: np.ndarray) -> np.ndarray:
        """Impute missing values using fitted training medians and set missingness flag."""
        assert self.medians is not None, "ActivityPreprocessor must be fitted before transform."
        X_out = np.asarray(X_act, dtype=np.float64).copy()

        # Identify rows with any missing activity values before imputation
        any_missing = np.isnan(X_out[:, :3]).any(axis=1)

        for j in range(3):
            nan_mask = np.isnan(X_out[:, j])
            X_out[nan_mask, j] = self.medians[j]

        # Explicit binary indicator flag I_missing_activity in {0, 1}
        X_out[:, 3] = np.where(any_missing, 1.0, 0.0)
        return X_out


def assemble_rung3_matrix(
    history_lags: np.ndarray,
    activity_features: np.ndarray,
    preprocessor: ActivityPreprocessor,
) -> np.ndarray:
    """Assemble 17-dimensional predictor matrix: 13 glucose lags + 4 activity features."""
    act_imputed = preprocessor.transform(activity_features)
    return np.hstack([history_lags, act_imputed])


def tune_activity_ridge_alpha(
    dataset: dict[str, ParticipantOrigins],
    train_pids: list[str],
    pid_to_group: dict[str, str],
    horizon_minutes: int,
    seed: int,
    candidate_alphas: np.ndarray | None = None,
) -> tuple[float, dict[str, Any]]:
    """Estimate optimal Ridge alpha for Rung 3 via inner 4-fold participant-grouped CV.

    Evaluated strictly on outer training participants (36 participants).
    Preprocessing (ActivityPreprocessor imputation + StandardScaler) is fitted
    strictly on inner training folds (27 participants).

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
    n_features = 17
    eye_n = np.eye(n_features, dtype=np.float64)

    for in_split in inner_splits:
        X_in_hist = np.vstack([dataset[p].history_lags for p in in_split.inner_train_pids])
        X_in_act = np.vstack([dataset[p].activity_features for p in in_split.inner_train_pids])
        y_in_tr = np.concatenate([dataset[p].target for p in in_split.inner_train_pids])

        # Fit activity preprocessor strictly on inner training fold
        act_prep = ActivityPreprocessor().fit(X_in_act)
        X_in_tr_17 = assemble_rung3_matrix(X_in_hist, X_in_act, act_prep)

        # Fit StandardScaler strictly on inner training fold
        scaler = StandardScaler(with_mean=True, with_std=True)
        X_in_tr_s = scaler.fit_transform(X_in_tr_17)

        y_mean = float(np.mean(y_in_tr))
        y_c = y_in_tr - y_mean
        XtX = X_in_tr_s.T @ X_in_tr_s
        Xty = X_in_tr_s.T @ y_c

        # Transform and cache validation participants
        val_cache: list[tuple[np.ndarray, np.ndarray, int]] = []
        for val_p in in_split.inner_val_pids:
            orig = dataset[val_p]
            X_val_17 = assemble_rung3_matrix(orig.history_lags, orig.activity_features, act_prep)
            X_val_s = scaler.transform(X_val_17)
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


def fit_predict_activity_ridge(
    dataset: dict[str, ParticipantOrigins],
    train_pids: list[str],
    test_pids: list[str],
    alpha: float,
) -> tuple[dict[str, np.ndarray], ActivityPreprocessor, StandardScaler, Ridge]:
    """Fit activity preprocessor, scaler, and Ridge on training participants and predict on test participants.

    Args:
        dataset: Mapping of participant IDs to ParticipantOrigins.
        train_pids: List of participant IDs in outer training fold (36 participants).
        test_pids: List of participant IDs in outer test fold (9 participants).
        alpha: Optimal Ridge regularization alpha.

    Returns:
        Tuple of (test_predictions_by_pid, fitted_act_prep, fitted_scaler, fitted_ridge_model).
    """
    X_tr_hist = np.vstack([dataset[p].history_lags for p in train_pids])
    X_tr_act = np.vstack([dataset[p].activity_features for p in train_pids])
    y_tr = np.concatenate([dataset[p].target for p in train_pids])

    # Fit preprocessing strictly on training fold
    act_prep = ActivityPreprocessor().fit(X_tr_act)
    X_tr_17 = assemble_rung3_matrix(X_tr_hist, X_tr_act, act_prep)

    scaler = StandardScaler(with_mean=True, with_std=True)
    X_tr_s = scaler.fit_transform(X_tr_17)

    model = Ridge(alpha=alpha, fit_intercept=True)
    model.fit(X_tr_s, y_tr)

    preds_by_pid: dict[str, np.ndarray] = {}
    for te_p in test_pids:
        orig = dataset[te_p]
        X_te_17 = assemble_rung3_matrix(orig.history_lags, orig.activity_features, act_prep)
        X_te_s = scaler.transform(X_te_17)
        preds_by_pid[te_p] = model.predict(X_te_s)

    return preds_by_pid, act_prep, scaler, model
