"""Unit and regression tests for Stage 2 Rung 6: Native HistGradientBoostingRegressor."""

from __future__ import annotations

import numpy as np

from dtwin.modeling.boosting import (
    build_fixed_hist_gradient_boosting,
    fit_predict_hist_gradient_boosting,
)
from dtwin.modeling.dataset import ParticipantOrigins
from dtwin.modeling.metrics import (
    ParticipantMetricRecord,
    compute_paired_bootstrap_difference,
)


def test_build_fixed_hist_gradient_boosting() -> None:
    """Verify HistGradientBoostingRegressor configuration adheres strictly to Protocol v1.0.0 Section 4.7."""
    model = build_fixed_hist_gradient_boosting(random_state=42)

    assert model.loss == "squared_error"
    assert model.learning_rate == 0.05
    assert model.max_iter == 100
    assert model.max_depth == 4
    assert model.min_samples_leaf == 50
    assert model.l2_regularization == 0.0
    assert model.random_state == 42


def test_fit_predict_hist_gradient_boosting_synthetic() -> None:
    """Verify end-to-end training and prediction on synthetic multi-participant dataset."""
    rng = np.random.default_rng(42)
    pids = [f"P{i:02d}" for i in range(10)]
    train_pids = pids[:8]
    test_pids = pids[8:]

    dataset: dict[str, ParticipantOrigins] = {}
    h = 30

    for p in pids:
        n = 80
        X_hist = rng.normal(120.0, 20.0, size=(n, 13))
        X_meal = np.zeros((n, 7))
        X_meal[:, 0] = rng.uniform(10.0, 300.0, size=n)
        X_meal[:, 1] = np.where(X_meal[:, 0] <= 60.0, 1.0, 0.0)
        X_meal[:, 6] = 0.0

        static_cov = rng.normal([48.0, 0.5, 30.0, 6.0], [5.0, 0.5, 3.0, 0.5])
        target = X_hist[:, 0] + rng.normal(0.0, 2.0, size=n)

        dataset[p] = ParticipantOrigins(
            participant_id=p,
            diag_group="normal",
            horizon_minutes=h,
            timestamps=[f"2026-01-01 {i:04d}" for i in range(n)],
            y_base=X_hist[:, 0],
            roc=rng.normal(0.0, 0.5, size=n),
            target=target,
            elapsed_minutes=np.arange(n) * 5,
            history_lags=X_hist,
            meal_features=X_meal,
            static_covariates=static_cov,
        )

    preds_by_pid, meal_prep, cov_prep, model = fit_predict_hist_gradient_boosting(
        dataset=dataset,
        train_pids=train_pids,
        test_pids=test_pids,
        random_state=42,
    )

    assert set(preds_by_pid.keys()) == set(test_pids)
    for p in test_pids:
        preds = preds_by_pid[p]
        assert preds.shape == (80,)
        assert np.all(np.isfinite(preds))
        assert not np.any(np.isnan(preds))


def test_hist_gradient_boosting_deterministic_reproducibility() -> None:
    """Verify that identical random_state generates bit-exact reproducible predictions."""
    rng = np.random.default_rng(123)
    pids = [f"P{i:02d}" for i in range(6)]
    train_pids = pids[:4]
    test_pids = pids[4:]

    dataset: dict[str, ParticipantOrigins] = {}
    h = 30

    for p in pids:
        n = 60
        X_hist = rng.normal(120.0, 20.0, size=(n, 13))
        X_meal = np.zeros((n, 7))
        static_cov = np.array([45.0, 1.0, 25.0, 5.5])
        target = X_hist[:, 0] * 0.9 + 10.0

        dataset[p] = ParticipantOrigins(
            participant_id=p,
            diag_group="normal",
            horizon_minutes=h,
            timestamps=[f"2026-01-01 {i:04d}" for i in range(n)],
            y_base=X_hist[:, 0],
            roc=np.zeros(n),
            target=target,
            elapsed_minutes=np.arange(n) * 5,
            history_lags=X_hist,
            meal_features=X_meal,
            static_covariates=static_cov,
        )

    preds1, _, _, _ = fit_predict_hist_gradient_boosting(
        dataset, train_pids, test_pids, random_state=42
    )
    preds2, _, _, _ = fit_predict_hist_gradient_boosting(
        dataset, train_pids, test_pids, random_state=42
    )

    for p in test_pids:
        np.testing.assert_allclose(preds1[p], preds2[p])


def test_paired_bootstrap_difference_math() -> None:
    """Verify paired bootstrap difference calculation and participant-level CI."""
    pids = [f"CGMacros-{i:03d}" for i in range(1, 46)]

    # Model A has lower error for 35 out of 45 participants
    records_a = {}
    records_b = {}
    for idx, p in enumerate(pids):
        rmse_b = 20.0 + idx * 0.1
        rmse_a = rmse_b - 0.5 if idx < 35 else rmse_b + 0.5
        records_a[p] = ParticipantMetricRecord(
            participant_id=p,
            diag_group="normal",
            n_origins=100,
            mean_rmse=rmse_a,
            mean_mae=rmse_a * 0.8,
            mean_skill=0.1,
            rmse_per_repeat=[rmse_a] * 10,
            mae_per_repeat=[rmse_a * 0.8] * 10,
            skill_per_repeat=[0.1] * 10,
        )
        records_b[p] = ParticipantMetricRecord(
            participant_id=p,
            diag_group="normal",
            n_origins=100,
            mean_rmse=rmse_b,
            mean_mae=rmse_b * 0.8,
            mean_skill=0.08,
            rmse_per_repeat=[rmse_b] * 10,
            mae_per_repeat=[rmse_b * 0.8] * 10,
            skill_per_repeat=[0.08] * 10,
        )

    res = compute_paired_bootstrap_difference(
        records_a, records_b, metric_name="rmse", n_bootstrap=500, bootstrap_seed=42
    )

    assert res["n_participants"] == 45
    assert res["n_improved"] == 35
    assert np.isclose(res["fraction_improved"], 35 / 45)
    # Expected mean diff: (35 * (-0.5) + 10 * 0.5) / 45 = (-17.5 + 5.0) / 45 = -12.5 / 45 ≈ -0.2778
    assert np.isclose(res["mean_diff"], -12.5 / 45)
    assert res["ci_95_mean_diff"][0] < res["mean_diff"] < res["ci_95_mean_diff"][1]
