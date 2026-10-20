"""Unit and regression tests for Stage 2 Rung 5: Baseline-Covariate Augmentation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from dtwin.modeling.covariates import (
    CovariatePreprocessor,
    assemble_rung5_matrix,
    fit_predict_covariate_ridge,
    load_participant_covariates,
    tune_covariate_ridge_alpha,
)
from dtwin.modeling.dataset import ParticipantOrigins
from dtwin.modeling.meal import MealPreprocessor


def test_load_participant_covariates() -> None:
    """Verify loading of baseline covariates from bio.csv."""
    bio_path = Path("data/cgmacros/CGMacros/bio.csv")
    if not bio_path.exists():
        pytest.skip("Raw dataset not present (bio.csv missing in CI environment)")
    cov_map = load_participant_covariates(bio_path)

    assert len(cov_map) == 45
    assert "CGMacros-001" in cov_map

    cov1 = cov_map["CGMacros-001"]
    assert cov1.shape == (4,)
    # CGMacros-001 in bio.csv: Age=27, Gender=M (0.0), BMI=24.53, A1c=5.4
    assert cov1[0] == 27.0
    assert cov1[1] == 0.0  # Male = 0.0
    assert not np.isnan(cov1[2])
    assert not np.isnan(cov1[3])

    # Check a female subject: CGMacros-002: Age=49, Gender=F (1.0)
    cov2 = cov_map["CGMacros-002"]
    assert cov2[1] == 1.0  # Female = 1.0


def test_covariate_preprocessor_fit_transform() -> None:
    """Verify CovariatePreprocessor computes training medians and imputes missing values."""
    X_train = np.array(
        [
            [40.0, 1.0, 25.0, 5.5],
            [50.0, 0.0, 30.0, 6.0],
            [60.0, 1.0, np.nan, 6.5],
        ]
    )

    prep = CovariatePreprocessor()
    prep.fit(X_train)

    assert prep.medians is not None
    # Medians: age=50.0, gender=1.0, bmi=27.5, hba1c=6.0
    np.testing.assert_allclose(prep.medians, [50.0, 1.0, 27.5, 6.0])

    X_test = np.array(
        [
            [np.nan, np.nan, np.nan, np.nan],
            [35.0, 0.0, 22.0, 5.2],
        ]
    )
    X_trans = prep.transform(X_test)
    expected = np.array(
        [
            [50.0, 1.0, 27.5, 6.0],
            [35.0, 0.0, 22.0, 5.2],
        ]
    )
    np.testing.assert_allclose(X_trans, expected)


def test_assemble_rung5_matrix() -> None:
    """Verify assemble_rung5_matrix produces shape (N, 20) with correct feature concatenation."""
    n = 30
    history = np.ones((n, 13)) * 120.0
    meal = np.ones((n, 7))
    meal[:, 6] = 0.0
    static_cov = np.array([45.0, 1.0, 28.5, 5.8])

    meal_prep = MealPreprocessor().fit(meal)
    cov_prep = CovariatePreprocessor().fit(static_cov.reshape(1, -1))

    mat20 = assemble_rung5_matrix(history, meal, static_cov, meal_prep, cov_prep)

    assert mat20.shape == (n, 20)
    # Lags (13)
    np.testing.assert_allclose(mat20[:, :13], 120.0)
    # Meal timing (3: cols 0, 1, 6)
    np.testing.assert_allclose(mat20[:, 13], 1.0)
    np.testing.assert_allclose(mat20[:, 14], 1.0)
    np.testing.assert_allclose(mat20[:, 15], 0.0)
    # Static covariates (4)
    np.testing.assert_allclose(mat20[:, 16], 45.0)
    np.testing.assert_allclose(mat20[:, 17], 1.0)
    np.testing.assert_allclose(mat20[:, 18], 28.5)
    np.testing.assert_allclose(mat20[:, 19], 5.8)


def test_covariate_ridge_tuning_and_fitting_synthetic() -> None:
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
        X_meal[:, 6] = 0.0

        static_cov = rng.normal([48.0, 0.5, 30.0, 6.0], [5.0, 0.5, 3.0, 0.5])

        meal_prep = MealPreprocessor().fit(X_meal)
        cov_prep = CovariatePreprocessor().fit(static_cov.reshape(1, -1))
        X_20 = assemble_rung5_matrix(X_hist, X_meal, static_cov, meal_prep, cov_prep)
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
            static_covariates=static_cov,
        )

    # 1. Inner CV alpha tuning
    best_alpha, diag = tune_covariate_ridge_alpha(
        dataset=dataset,
        train_pids=pids[:27],
        pid_to_group=pid_to_group,
        horizon_minutes=h,
        seed=42,
    )

    assert best_alpha > 0.0
    assert diag["inner_folds_count"] == 4
    assert diag["candidate_count"] > 0
    assert diag["best_inner_rmse"] > 0.0

    # 2. Outer fit and predict
    test_pids = pids[27:]
    preds, meal_prep, cov_prep, scaler, model = fit_predict_covariate_ridge(
        dataset=dataset,
        train_pids=pids[:27],
        test_pids=test_pids,
        alpha=best_alpha,
    )

    assert len(preds) == len(test_pids)
    for tp in test_pids:
        assert preds[tp].shape == (100,)
        assert not np.isnan(preds[tp]).any()
    assert cov_prep.medians is not None
    assert scaler.mean_ is not None and scaler.mean_.shape == (20,)
    assert model.coef_.shape == (20,)
