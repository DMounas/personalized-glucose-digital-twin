"""Stage 2 Rung 6: Native HistGradientBoostingRegressor (Fixed Settings).

Evaluates a compact nonlinear gradient-boosted decision tree model using scikit-learn's
HistGradientBoostingRegressor with exact prespecified settings from Protocol v1.0.0 Section 4.7:
- loss = 'squared_error'
- learning_rate = 0.05
- max_iter = 100
- max_depth = 4
- min_samples_leaf = 50
- l2_regularization = 0.0
- random_state = 42

Predictor vector:
Exact Rung 5 feature set (20 dimensions):
- 13 guarded glucose history lags [y(t-5), ..., y(t-65)]
- 3 meal-timing features [time_since_last_meal, meal_in_last_60m, no_recent_meal]
- 4 static baseline covariates [Age, Gender (Female=1.0), BMI, Baseline_HbA1c]

All preprocessing (MealPreprocessor and CovariatePreprocessor) is fitted strictly on
training participants only. No post-hoc hyperparameter tuning is performed.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from dtwin.modeling.covariates import CovariatePreprocessor, assemble_rung5_matrix
from dtwin.modeling.dataset import ParticipantOrigins
from dtwin.modeling.meal import MealPreprocessor


def build_fixed_hist_gradient_boosting(
    random_state: int = 42,
) -> HistGradientBoostingRegressor:
    """Instantiate HistGradientBoostingRegressor with exact frozen Protocol v1.0.0 settings.

    Args:
        random_state: PRNG seed for tree fitting (default 42).

    Returns:
        Configured HistGradientBoostingRegressor instance.
    """
    return HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.05,
        max_iter=100,
        max_depth=4,
        min_samples_leaf=50,
        l2_regularization=0.0,
        random_state=random_state,
    )


def fit_predict_hist_gradient_boosting(
    dataset: dict[str, ParticipantOrigins],
    train_pids: list[str],
    test_pids: list[str],
    random_state: int = 42,
) -> tuple[
    dict[str, np.ndarray], MealPreprocessor, CovariatePreprocessor, HistGradientBoostingRegressor
]:
    """Fit preprocessing and fixed HistGradientBoostingRegressor on training participants and predict on test fold.

    Args:
        dataset: Mapping of participant IDs to ParticipantOrigins.
        train_pids: List of participant IDs in outer training fold (36 participants).
        test_pids: List of participant IDs in outer test fold (9 participants).
        random_state: PRNG seed for model training.

    Returns:
        Tuple of (test_predictions_by_pid, fitted_meal_prep, fitted_cov_prep, fitted_gbdt_model).
    """
    X_tr_hist = np.vstack([dataset[p].history_lags for p in train_pids])
    X_tr_meal = np.vstack([dataset[p].meal_features for p in train_pids])
    cov_train_list = []
    for p in train_pids:
        n_p = dataset[p].n_origins
        cov_train_list.append(np.tile(dataset[p].static_covariates, (n_p, 1)))
    X_tr_cov = np.vstack(cov_train_list)
    y_tr = np.concatenate([dataset[p].target for p in train_pids])

    # Fit preprocessors strictly on training participants
    meal_prep = MealPreprocessor().fit(X_tr_meal)
    cov_prep = CovariatePreprocessor().fit(X_tr_cov)

    X_tr = assemble_rung5_matrix(X_tr_hist, X_tr_meal, X_tr_cov, meal_prep, cov_prep)

    model = build_fixed_hist_gradient_boosting(random_state=random_state)
    model.fit(X_tr, y_tr)

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
        preds_by_pid[te_p] = model.predict(X_te)

    return preds_by_pid, meal_prep, cov_prep, model
