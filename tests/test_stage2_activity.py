"""Unit and regression tests for Stage 2 Rung 3: Activity-Augmented Ridge Regression."""

from __future__ import annotations

import numpy as np

from dtwin.modeling.activity import (
    ActivityPreprocessor,
    assemble_rung3_matrix,
    fit_predict_activity_ridge,
    tune_activity_ridge_alpha,
)
from dtwin.modeling.dataset import ParticipantOrigins


def test_activity_preprocessor_fit_transform() -> None:
    """Verify ActivityPreprocessor computes training medians and flags missingness."""
    # Columns: [mean_hr, delta_hr, mean_mets, placeholder_missing_flag]
    X_train = np.array(
        [
            [70.0, 2.0, 1.5, 0.0],
            [80.0, 4.0, 2.5, 0.0],
            [np.nan, 6.0, 3.5, 0.0],
            [90.0, np.nan, np.nan, 0.0],
        ]
    )

    prep = ActivityPreprocessor()
    prep.fit(X_train)

    assert prep.medians is not None
    # Medians:
    # col 0 (HR): [70, 80, 90] -> median 80.0
    # col 1 (delta_HR): [2, 4, 6] -> median 4.0
    # col 2 (METs): [1.5, 2.5, 3.5] -> median 2.5
    np.testing.assert_allclose(prep.medians, [80.0, 4.0, 2.5])

    # Transform test set with missing values
    X_test = np.array(
        [
            [75.0, 1.0, 2.0, 0.0],  # fully observed -> missing flag 0
            [np.nan, 5.0, 2.0, 0.0],  # missing HR -> missing flag 1
            [85.0, np.nan, 1.0, 0.0],  # missing delta_HR -> missing flag 1
            [np.nan, np.nan, np.nan, 0.0],  # all missing -> missing flag 1
        ]
    )

    X_trans = prep.transform(X_test)

    # Check imputed values
    expected = np.array(
        [
            [75.0, 1.0, 2.0, 0.0],
            [80.0, 5.0, 2.0, 1.0],
            [85.0, 4.0, 1.0, 1.0],
            [80.0, 4.0, 2.5, 1.0],
        ]
    )
    np.testing.assert_allclose(X_trans, expected)


def test_assemble_rung3_matrix() -> None:
    """Verify assemble_rung3_matrix produces shape (N, 17) with correct lag and activity columns."""
    n = 20
    history = np.ones((n, 13)) * 120.0
    act = np.ones((n, 4)) * 5.0

    prep = ActivityPreprocessor().fit(act)
    matrix_17 = assemble_rung3_matrix(history, act, prep)

    assert matrix_17.shape == (n, 17)
    np.testing.assert_allclose(matrix_17[:, :13], 120.0)
    np.testing.assert_allclose(matrix_17[:, 13:16], 5.0)
    np.testing.assert_allclose(matrix_17[:, 16], 0.0)  # non-missing flag


def test_activity_ridge_tuning_and_fitting_synthetic() -> None:
    """Verify inner CV alpha tuning and test prediction on synthetic multi-participant data."""
    rng = np.random.default_rng(42)
    pids = [f"P{i:02d}" for i in range(36)]
    pid_to_group = {p: "normal" for p in pids}

    dataset: dict[str, ParticipantOrigins] = {}
    h = 30
    w_true = rng.normal(0.0, 0.5, size=17)

    for p in pids:
        n = 100
        X_hist = rng.normal(120.0, 20.0, size=(n, 13))
        X_act = rng.normal(70.0, 10.0, size=(n, 4))
        # Add some missingness to verify robustness
        X_act[:10, 0] = np.nan
        X_act[10:20, 2] = np.nan

        # Generate target from 17 features
        prep_syn = ActivityPreprocessor().fit(X_act)
        X_17 = assemble_rung3_matrix(X_hist, X_act, prep_syn)
        target = X_17 @ w_true + rng.normal(0.0, 1.0, size=n)

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
            activity_features=X_act,
        )

    # 1. Test inner CV tuning
    best_alpha, diag = tune_activity_ridge_alpha(
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

    # 2. Test outer fit and predict
    test_pids = pids[27:]
    preds, act_prep, scaler, model = fit_predict_activity_ridge(
        dataset=dataset,
        train_pids=pids[:27],
        test_pids=test_pids,
        alpha=best_alpha,
    )

    assert len(preds) == len(test_pids)
    for tp in test_pids:
        assert preds[tp].shape == (100,)
        assert not np.isnan(preds[tp]).any()
    assert act_prep.medians is not None
    assert scaler.mean_ is not None and scaler.mean_.shape == (17,)
    assert model.coef_.shape == (17,)
