"""Stage 2 Rung 4: Meal-Context Ridge Regression.

Integrates nutritional information available at meal start:
x_meal = [
    time_since_last_meal_minutes (clamped to 1,440 if no meal in 24h),
    I_meal_in_60m,
    carbs_grams,
    protein_grams,
    fat_grams,
    fiber_grams,
    I_no_recent_meal
]^T in R^7.

Combined predictor vector:
x_rung4 = [x_autoreg (13), x_meal (7)]^T in R^20.

No-Macros Ablation predictor vector:
x_rung4_nomacros = [x_autoreg (13), x_meal_timing (3)]^T in R^16,
where x_meal_timing = [time_since_last_meal_minutes, I_meal_in_60m, I_no_recent_meal]^T.

Missing macronutrients are imputed strictly using training-fold medians.
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
class MealPreprocessor:
    """Training-fold-only imputer for dietary macronutrient features."""

    macro_medians: np.ndarray | None = None  # shape (4,): [carbs, protein, fat, fiber]

    def fit(self, X_meal_train: np.ndarray) -> MealPreprocessor:
        """Compute macronutrient column medians on non-null training meals.

        Columns:
            0: time_since_last_meal_minutes
            1: I_meal_in_60m
            2: carbs
            3: protein
            4: fat
            5: fiber
            6: I_no_recent_meal
        """
        # Fit medians strictly on rows where a meal was present (no_recent_meal == 0)
        has_meal = X_meal_train[:, 6] == 0.0
        meal_rows = X_meal_train[has_meal]

        meds: list[float] = []
        for j in range(2, 6):
            if len(meal_rows) > 0:
                col = meal_rows[:, j]
                valid = col[~np.isnan(col)]
                if len(valid) > 0:
                    meds.append(float(np.median(valid)))
                else:
                    meds.append(0.0)
            else:
                meds.append(0.0)

        self.macro_medians = np.array(meds, dtype=np.float64)
        return self

    def transform(self, X_meal: np.ndarray) -> np.ndarray:
        """Impute missing macronutrient values using fitted training medians."""
        assert self.macro_medians is not None, "MealPreprocessor must be fitted before transform."
        X_out = np.asarray(X_meal, dtype=np.float64).copy()

        # For rows with no recent meal (sentinel 1440 min), ensure zero macros
        no_meal_mask = X_out[:, 6] == 1.0
        X_out[no_meal_mask, 0] = 1440.0
        X_out[no_meal_mask, 1] = 0.0
        X_out[no_meal_mask, 2:6] = 0.0

        # For rows with a meal, impute any NaN in macros with training-fold medians
        for j in range(2, 6):
            macro_nan = (~no_meal_mask) & np.isnan(X_out[:, j])
            X_out[macro_nan, j] = self.macro_medians[j - 2]

        return X_out


def assemble_rung4_matrix(
    history_lags: np.ndarray,
    meal_features: np.ndarray,
    preprocessor: MealPreprocessor,
    include_macros: bool = True,
) -> np.ndarray:
    """Assemble predictor matrix for Rung 4.

    Args:
        history_lags: Array of shape (N, 13) containing guard-banded glucose lags.
        meal_features: Array of shape (N, 7) containing raw meal features.
        preprocessor: Fitted MealPreprocessor instance.
        include_macros: If True, returns full 20-dim matrix (13 lags + 7 meal features).
            If False, returns 16-dim matrix for no-macros ablation (13 lags + 3 timing features).

    Returns:
        Feature matrix of shape (N, 20) or (N, 16).
    """
    meal_imputed = preprocessor.transform(meal_features)
    if include_macros:
        return np.hstack([history_lags, meal_imputed])
    else:
        # No-macros ablation: columns 0 (time_since), 1 (in_60m), 6 (no_recent_meal)
        timing_features = meal_imputed[:, [0, 1, 6]]
        return np.hstack([history_lags, timing_features])


def tune_meal_ridge_alpha(
    dataset: dict[str, ParticipantOrigins],
    train_pids: list[str],
    pid_to_group: dict[str, str],
    horizon_minutes: int,
    seed: int,
    candidate_alphas: np.ndarray | None = None,
    include_macros: bool = True,
) -> tuple[float, dict[str, Any]]:
    """Estimate optimal Ridge alpha for Rung 4 via inner 4-fold participant-grouped CV.

    Evaluated strictly on outer training participants (36 participants).
    Preprocessing (MealPreprocessor imputation + StandardScaler) is fitted
    strictly on inner training folds (27 participants).

    Args:
        dataset: Mapping of participant IDs to ParticipantOrigins.
        train_pids: List of participant IDs in outer training fold (36 participants).
        pid_to_group: Mapping from participant ID to diagnostic group string.
        horizon_minutes: Forecast horizon in minutes (+30 or +60).
        seed: Random seed for inner fold partitioning.
        candidate_alphas: Array of candidate alpha values. Defaults to 17 log-spaced
            values in [10^-2, 10^6].
        include_macros: Whether to include full macronutrient features or run no-macros ablation.

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
    n_features = 20 if include_macros else 16
    eye_n = np.eye(n_features, dtype=np.float64)

    for in_split in inner_splits:
        X_in_hist = np.vstack([dataset[p].history_lags for p in in_split.inner_train_pids])
        X_in_meal = np.vstack([dataset[p].meal_features for p in in_split.inner_train_pids])
        y_in_tr = np.concatenate([dataset[p].target for p in in_split.inner_train_pids])

        # Fit meal preprocessor strictly on inner training fold
        meal_prep = MealPreprocessor().fit(X_in_meal)
        X_in_tr = assemble_rung4_matrix(
            X_in_hist, X_in_meal, meal_prep, include_macros=include_macros
        )

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
            X_val = assemble_rung4_matrix(
                orig.history_lags, orig.meal_features, meal_prep, include_macros=include_macros
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
        "include_macros": include_macros,
    }

    return best_alpha, diagnostics


def fit_predict_meal_ridge(
    dataset: dict[str, ParticipantOrigins],
    train_pids: list[str],
    test_pids: list[str],
    alpha: float,
    include_macros: bool = True,
) -> tuple[dict[str, np.ndarray], MealPreprocessor, StandardScaler, Ridge]:
    """Fit meal preprocessor, scaler, and Ridge on training participants and predict on test participants.

    Args:
        dataset: Mapping of participant IDs to ParticipantOrigins.
        train_pids: List of participant IDs in outer training fold (36 participants).
        test_pids: List of participant IDs in outer test fold (9 participants).
        alpha: Optimal Ridge regularization alpha.
        include_macros: Whether to include full macronutrient features or run no-macros ablation.

    Returns:
        Tuple of (test_predictions_by_pid, fitted_meal_prep, fitted_scaler, fitted_ridge_model).
    """
    X_tr_hist = np.vstack([dataset[p].history_lags for p in train_pids])
    X_tr_meal = np.vstack([dataset[p].meal_features for p in train_pids])
    y_tr = np.concatenate([dataset[p].target for p in train_pids])

    # Fit preprocessing strictly on training fold
    meal_prep = MealPreprocessor().fit(X_tr_meal)
    X_tr = assemble_rung4_matrix(X_tr_hist, X_tr_meal, meal_prep, include_macros=include_macros)

    scaler = StandardScaler(with_mean=True, with_std=True)
    X_tr_s = scaler.fit_transform(X_tr)

    model = Ridge(alpha=alpha, fit_intercept=True)
    model.fit(X_tr_s, y_tr)

    preds_by_pid: dict[str, np.ndarray] = {}
    for te_p in test_pids:
        orig = dataset[te_p]
        X_te = assemble_rung4_matrix(
            orig.history_lags, orig.meal_features, meal_prep, include_macros=include_macros
        )
        X_te_s = scaler.transform(X_te)
        preds_by_pid[te_p] = model.predict(X_te_s)

    return preds_by_pid, meal_prep, scaler, model
