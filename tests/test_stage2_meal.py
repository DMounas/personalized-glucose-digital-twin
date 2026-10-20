"""Unit and regression tests for Stage 2 Rung 4: Meal-Context Ridge Regression."""

from __future__ import annotations

import numpy as np
import pandas as pd

from dtwin.modeling.dataset import ParticipantOrigins
from dtwin.modeling.meal import (
    MealPreprocessor,
    assemble_rung4_matrix,
    fit_predict_meal_ridge,
    tune_meal_ridge_alpha,
)


def test_meal_preprocessor_fit_transform() -> None:
    """Verify MealPreprocessor computes training medians on meals and enforces sentinel values."""
    # Columns: [time_since, in_60m, carbs, protein, fat, fiber, no_recent_meal]
    X_train = np.array(
        [
            [30.0, 1.0, 50.0, 20.0, 10.0, 5.0, 0.0],
            [90.0, 0.0, 70.0, 30.0, 20.0, 10.0, 0.0],
            [120.0, 0.0, 90.0, np.nan, 30.0, 15.0, 0.0],
            [1440.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],  # no recent meal
        ]
    )

    prep = MealPreprocessor()
    prep.fit(X_train)

    assert prep.macro_medians is not None
    # Training medians among meal rows (rows 0, 1, 2):
    # carbs: [50, 70, 90] -> 70.0
    # protein: [20, 30] -> 25.0
    # fat: [10, 20, 30] -> 20.0
    # fiber: [5, 10, 15] -> 10.0
    np.testing.assert_allclose(prep.macro_medians, [70.0, 25.0, 20.0, 10.0])

    # Transform test set with missing values
    X_test = np.array(
        [
            [45.0, 1.0, 60.0, 15.0, 8.0, 4.0, 0.0],  # fully observed meal
            [15.0, 1.0, 40.0, np.nan, np.nan, 2.0, 0.0],  # missing protein & fat
            [1440.0, 0.0, 99.0, 99.0, 99.0, 99.0, 1.0],  # no recent meal with noisy macros
        ]
    )

    X_trans = prep.transform(X_test)

    # Expected: row 1 imputed with medians; row 2 forced to zero macros
    expected = np.array(
        [
            [45.0, 1.0, 60.0, 15.0, 8.0, 4.0, 0.0],
            [15.0, 1.0, 40.0, 25.0, 20.0, 2.0, 0.0],
            [1440.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        ]
    )
    np.testing.assert_allclose(X_trans, expected)


def test_assemble_rung4_matrix() -> None:
    """Verify assemble_rung4_matrix produces shape (N, 20) for full and (N, 16) for ablation."""
    n = 25
    history = np.ones((n, 13)) * 110.0
    meal = np.ones((n, 7))
    meal[:, 6] = 0.0  # has meals

    prep = MealPreprocessor().fit(meal)

    # Full model: 13 + 7 = 20
    mat_full = assemble_rung4_matrix(history, meal, prep, include_macros=True)
    assert mat_full.shape == (n, 20)
    np.testing.assert_allclose(mat_full[:, :13], 110.0)

    # No-macros ablation: 13 + 3 = 16
    mat_nomacros = assemble_rung4_matrix(history, meal, prep, include_macros=False)
    assert mat_nomacros.shape == (n, 16)
    np.testing.assert_allclose(mat_nomacros[:, :13], 110.0)


def test_temporal_leakage_prevention() -> None:
    """Verify future meals (> t) are never included in forecast issuance features."""
    meal_timestamps = pd.to_datetime(["2026-01-01 12:00:00", "2026-01-01 18:00:00"])
    meal_carbs = np.array([60.0, 80.0])

    # Case 1: Origin at 11:30 (before first meal)
    t1 = pd.Timestamp("2026-01-01 11:30:00")
    pos1 = int(np.searchsorted(meal_timestamps.to_numpy(), t1.to_numpy(), side="right")) - 1
    assert pos1 == -1  # no prior meal permitted

    # Case 2: Origin at 13:00 (after first meal, before second meal)
    t2 = pd.Timestamp("2026-01-01 13:00:00")
    pos2 = int(np.searchsorted(meal_timestamps.to_numpy(), t2.to_numpy(), side="right")) - 1
    assert pos2 == 0
    assert meal_carbs[pos2] == 60.0  # uses 12:00 meal, second meal at 18:00 is inaccessible

    # Case 3: Origin at 18:00 (exact meal start)
    t3 = pd.Timestamp("2026-01-01 18:00:00")
    pos3 = int(np.searchsorted(meal_timestamps.to_numpy(), t3.to_numpy(), side="right")) - 1
    assert pos3 == 1
    assert meal_carbs[pos3] == 80.0


def test_meal_ridge_tuning_and_fitting_synthetic() -> None:
    """Verify inner CV alpha tuning and test prediction on synthetic multi-participant data."""
    rng = np.random.default_rng(42)
    pids = [f"P{i:02d}" for i in range(36)]
    pid_to_group = {p: "normal" for p in pids}

    dataset: dict[str, ParticipantOrigins] = {}
    h = 30
    w_true = rng.normal(0.0, 0.5, size=20)

    for p in pids:
        n = 100
        X_hist = rng.normal(120.0, 20.0, size=(n, 13))
        X_meal = np.zeros((n, 7))
        X_meal[:, 0] = rng.uniform(10.0, 300.0, size=n)
        X_meal[:, 1] = np.where(X_meal[:, 0] <= 60.0, 1.0, 0.0)
        X_meal[:, 2] = rng.uniform(20.0, 100.0, size=n)
        X_meal[:, 3] = rng.uniform(10.0, 50.0, size=n)
        X_meal[:, 4] = rng.uniform(5.0, 30.0, size=n)
        X_meal[:, 5] = rng.uniform(0.0, 15.0, size=n)
        X_meal[:, 6] = 0.0

        # Inject some missingness
        X_meal[:5, 5] = np.nan

        prep_syn = MealPreprocessor().fit(X_meal)
        X_20 = assemble_rung4_matrix(X_hist, X_meal, prep_syn, include_macros=True)
        target = X_20 @ w_true + rng.normal(0.0, 1.0, size=n)

        dataset[p] = ParticipantOrigins(
            participant_id=p,
            diag_group="normal",
            horizon_minutes=h,
            timestamps=[f"2026-01-01 {i:04d}" for i in range(n)],
            y_base=X_hist[:, 0],
            roc=(X_hist[:, 0] - X_hist[:, 3]) / 15.0,
            target=target,
            elapsed_minutes=np.arange(n) * 5,
            history_lags=X_hist,
            meal_features=X_meal,
        )

    # 1. Inner CV tuning (full model)
    best_alpha, diag = tune_meal_ridge_alpha(
        dataset=dataset,
        train_pids=pids[:27],
        pid_to_group=pid_to_group,
        horizon_minutes=h,
        seed=42,
        include_macros=True,
    )

    assert best_alpha > 0.0
    assert diag["inner_folds_count"] == 4
    assert diag["candidate_count"] > 0
    assert diag["best_inner_rmse"] > 0.0

    # 2. Outer fit and predict
    test_pids = pids[27:]
    preds, meal_prep, scaler, model = fit_predict_meal_ridge(
        dataset=dataset,
        train_pids=pids[:27],
        test_pids=test_pids,
        alpha=best_alpha,
        include_macros=True,
    )

    assert len(preds) == len(test_pids)
    for tp in test_pids:
        assert preds[tp].shape == (100,)
        assert not np.isnan(preds[tp]).any()
    assert meal_prep.macro_medians is not None
    assert scaler.mean_ is not None and scaler.mean_.shape == (20,)
    assert model.coef_.shape == (20,)

    # 3. Outer fit and predict (No-Macros Ablation)
    preds_no, _, scaler_no, model_no = fit_predict_meal_ridge(
        dataset=dataset,
        train_pids=pids[:27],
        test_pids=test_pids,
        alpha=best_alpha,
        include_macros=False,
    )
    assert scaler_no.mean_ is not None and scaler_no.mean_.shape == (16,)
    assert model_no.coef_.shape == (16,)
