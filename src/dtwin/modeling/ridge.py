"""Stage 2 Rung 2: Guarded Ridge Regression (Autoregressive Lags).

Evaluates regularized linear regression on the 13 guard-banded glucose lags:
x_autoreg = [y(t-5), y(t-10), ..., y(t-65)]^T.

Regularization alpha is tuned strictly within training-fold participants
using inner 4-fold participant-grouped cross-validation.
All preprocessing (StandardScaler) is fitted strictly on training data only.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from dtwin.modeling.cv import generate_inner_cv_splits
from dtwin.modeling.dataset import ParticipantOrigins


def tune_ridge_alpha(
    dataset: dict[str, ParticipantOrigins],
    train_pids: list[str],
    pid_to_group: dict[str, str],
    horizon_minutes: int,
    seed: int,
    candidate_alphas: np.ndarray | None = None,
) -> tuple[float, dict[str, Any]]:
    """Estimate optimal Ridge regularization alpha via inner 4-fold participant-grouped CV.

    Evaluated strictly on outer training participants (36 participants).
    Preprocessing (StandardScaler) is fitted strictly on inner training folds.
    Candidate alpha values are benchmarked by participant-averaged validation RMSE.

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

    # Pre-structure each inner fold: fit scaler, compute XtX, Xty, and cache validation scaled arrays
    inner_fold_data = []
    n_features = 13
    eye_n = np.eye(n_features, dtype=np.float64)

    for in_split in inner_splits:
        X_in_tr = np.vstack([dataset[p].history_lags for p in in_split.inner_train_pids])
        y_in_tr = np.concatenate([dataset[p].target for p in in_split.inner_train_pids])

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
            X_val_s = scaler.transform(orig.history_lags)
            val_cache.append((X_val_s, orig.target, orig.n_origins))

        inner_fold_data.append((XtX, Xty, y_mean, val_cache))

    alpha_scores: list[float] = []

    for alpha in candidate_alphas:
        a = float(alpha)
        fold_participant_rmses: list[float] = []

        for XtX, Xty, y_mean, val_cache in inner_fold_data:
            # Solve normal equations: w = (XtX + alpha * I)^-1 @ Xty
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


def fit_predict_ridge(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, StandardScaler, Ridge]:
    """Fit StandardScaler and Ridge on training data and predict on test data.

    Args:
        X_train: Training predictor matrix (N_train, 13).
        y_train: Training target array (N_train,).
        X_test: Test predictor matrix (N_test, 13).
        alpha: Ridge L2 regularization parameter.

    Returns:
        Tuple of (y_pred_test, fitted_scaler, fitted_ridge_model).
    """
    scaler = StandardScaler(with_mean=True, with_std=True)
    X_train_s = scaler.fit_transform(X_train)

    model = Ridge(alpha=alpha, fit_intercept=True)
    model.fit(X_train_s, y_train)

    X_test_s = scaler.transform(X_test)
    y_pred = model.predict(X_test_s)

    return y_pred, scaler, model
