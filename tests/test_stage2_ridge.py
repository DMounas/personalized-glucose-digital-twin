"""Unit and regression tests for Stage 2 Rung 2: Guarded Ridge Regression."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from dtwin.modeling.dataset import ParticipantOrigins
from dtwin.modeling.ridge import fit_predict_ridge, tune_ridge_alpha


def test_ridge_fit_predict_shape_and_scaling() -> None:
    """Verify fit_predict_ridge outputs, scaler fitting, and model coefficients."""
    rng = np.random.default_rng(42)
    n_train = 500
    n_test = 100
    n_features = 13

    X_train = rng.normal(120.0, 15.0, size=(n_train, n_features))
    y_train = X_train @ rng.normal(0.0, 1.0, size=n_features) + rng.normal(0.0, 2.0, size=n_train)
    X_test = rng.normal(120.0, 15.0, size=(n_test, n_features))

    alpha = 10.0
    y_pred, scaler, model = fit_predict_ridge(X_train, y_train, X_test, alpha)

    assert y_pred.shape == (n_test,)
    assert scaler.mean_ is not None and scaler.mean_.shape == (n_features,)
    assert scaler.scale_ is not None and scaler.scale_.shape == (n_features,)
    assert model.coef_.shape == (n_features,)
    assert isinstance(model.intercept_, float)


def test_ridge_normal_equations_matches_scikit_learn() -> None:
    """Verify that normal equations used in inner CV match scikit-learn Ridge to machine precision."""
    rng = np.random.default_rng(42)
    X = rng.normal(130.0, 25.0, size=(1000, 13))
    w_true = rng.normal(0.0, 1.0, size=13)
    y = X @ w_true + rng.normal(0.0, 3.0, size=1000)

    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)

    for alpha in [0.01, 1.0, 50.0, 500.0]:
        sk_model = Ridge(alpha=alpha, fit_intercept=True)
        sk_model.fit(X_s, y)
        sk_pred = sk_model.predict(X_s)

        # Normal equations with centered y
        y_mean = float(np.mean(y))
        y_c = y - y_mean
        XtX = X_s.T @ X_s
        Xty = X_s.T @ y_c
        w_norm = np.linalg.solve(XtX + alpha * np.eye(13), Xty)
        norm_pred = y_mean + X_s @ w_norm

        np.testing.assert_allclose(sk_pred, norm_pred, rtol=1e-9, atol=1e-9)


def test_ridge_alpha_tuning_synthetic() -> None:
    """Verify inner 4-fold participant-grouped alpha tuning on synthetic dataset."""
    rng = np.random.default_rng(42)
    pids = [f"P{i:02d}" for i in range(36)]
    pid_to_group = {p: "normal" for p in pids}

    dataset: dict[str, ParticipantOrigins] = {}
    h = 30
    w_true = rng.normal(0.0, 0.5, size=13)

    for p in pids:
        n = 150
        X = rng.normal(120.0, 20.0, size=(n, 13))
        noise = rng.normal(0.0, 2.0, size=n)
        target = X @ w_true + noise

        dataset[p] = ParticipantOrigins(
            participant_id=p,
            diag_group="normal",
            horizon_minutes=h,
            timestamps=[f"2026-01-01 {i:04d}" for i in range(n)],
            y_base=X[:, 0],
            roc=(X[:, 0] - X[:, 3]) / 15.0,
            target=target,
            elapsed_minutes=np.arange(n) * 5,
            history_lags=X,
        )

    best_alpha, diag = tune_ridge_alpha(
        dataset=dataset,
        train_pids=pids,
        pid_to_group=pid_to_group,
        horizon_minutes=h,
        seed=42,
    )

    assert best_alpha > 0.0
    assert diag["inner_folds_count"] == 4
    assert diag["candidate_count"] > 0
    assert diag["best_inner_rmse"] > 0.0
