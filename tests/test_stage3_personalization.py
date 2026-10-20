"""Unit and regression tests for Stage 3 Personalization."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from dtwin.modeling.covariates import CovariatePreprocessor
from dtwin.modeling.dataset import ParticipantOrigins
from dtwin.modeling.meal import MealPreprocessor
from dtwin.modeling.personalization import (
    compute_personalization_cohort_summary,
    consolidate_personalization_metrics,
    fit_predict_personalized_participant,
    partition_participant_origins,
)


def test_partition_participant_origins_label_and_purge_guards() -> None:
    """Verify that partition_participant_origins strictly enforces label boundaries and purge buffer."""
    # 10 days of 5-minute grid origins: 10 * 288 = 2880 origins
    n = 2880
    elapsed_minutes = np.arange(n) * 5

    for h in [30, 60]:
        for days in [2, 4, 6]:
            cutoff_m = days * 1440
            part = partition_participant_origins(
                elapsed_minutes=elapsed_minutes,
                horizon_minutes=h,
                days=days,
                purge_minutes=120,
            )

            assert part.n_adapt > 0
            assert part.n_eval > 0

            # Guard 1: Adaptation labels never cross the cutoff
            adapt_el = elapsed_minutes[part.adapt_indices]
            assert np.all(adapt_el + h <= cutoff_m)

            # Guard 2: Evaluation origins start at or after cutoff + 120m
            eval_el = elapsed_minutes[part.eval_indices]
            assert np.all(eval_el >= cutoff_m + 120)

            # Guard 3: Disjoint sets (zero overlap)
            set_adapt = set(part.adapt_indices)
            set_eval = set(part.eval_indices)
            assert set_adapt.isdisjoint(set_eval)

            # Guard 4: Earliest evaluation feature lag (t - 65) is strictly after cutoff
            earliest_eval_t = eval_el[0]
            earliest_eval_lag = earliest_eval_t - 65
            assert earliest_eval_lag > cutoff_m


def test_fit_predict_personalized_participant_synthetic() -> None:
    """Verify end-to-end personalization model fitting and evaluation on synthetic participant data."""
    rng = np.random.default_rng(42)
    n = 2000
    elapsed = np.arange(n) * 5  # ~6.9 days
    h = 30

    X_hist = rng.normal(120.0, 20.0, size=(n, 13))
    X_meal = np.zeros((n, 7))
    X_meal[:, 0] = rng.uniform(10.0, 300.0, size=n)
    X_meal[:, 1] = np.where(X_meal[:, 0] <= 60.0, 1.0, 0.0)
    X_meal[:, 6] = 0.0
    static_cov = np.array([45.0, 1.0, 28.0, 5.8])

    # Participant has a true persistent bias (+8 mg/dL)
    target = X_hist[:, 0] + 8.0 + rng.normal(0.0, 1.5, size=n)

    orig = ParticipantOrigins(
        participant_id="P_SYNTH_01",
        diag_group="normal",
        horizon_minutes=h,
        timestamps=[f"2026-01-01 {i:04d}" for i in range(n)],
        y_base=X_hist[:, 0],
        roc=rng.normal(0.0, 0.5, size=n),
        target=target,
        elapsed_minutes=elapsed,
        history_lags=X_hist,
        meal_features=X_meal,
        static_covariates=static_cov,
    )

    # Preprocessors fitted on synthetic training fold
    meal_prep = MealPreprocessor().fit(X_meal)
    cov_prep = CovariatePreprocessor().fit(static_cov.reshape(1, -1))
    scaler = StandardScaler(with_mean=True, with_std=True)

    # Global model fitted with an overall zero bias
    X_mat = np.hstack([X_hist, X_meal[:, [0, 1, 6]], np.tile(static_cov, (n, 1))])
    X_s = scaler.fit_transform(X_mat)
    global_model = Ridge(alpha=100.0, fit_intercept=True)
    global_model.fit(X_s, X_hist[:, 0])  # predicts ~y_base without the +8 bias

    res = fit_predict_personalized_participant(
        orig=orig,
        global_model=global_model,
        meal_prep=meal_prep,
        cov_prep=cov_prep,
        scaler=scaler,
        alpha_global=100.0,
        days=2,
        purge_minutes=120,
    )

    assert res["n_adapt"] > 0
    assert res["n_eval"] > 0
    assert len(res["y_pred_pers_eval"]) == res["n_eval"]
    assert np.all(np.isfinite(res["y_pred_pers_eval"]))

    # Personalization should detect the +8 bias and reduce RMSE
    assert res["rmse_pers"] < res["rmse_global"]
    assert res["delta_rmse"] < 0.0
    assert res["pct_reduction"] > 0.0


def test_compute_personalization_cohort_summary_synthetic() -> None:
    """Verify cohort summary and participant bootstrap CI calculation."""
    pids = [f"CGMacros-{i:03d}" for i in range(1, 46)]
    repeat_records: list[dict[str, dict[str, Any]]] = []

    for _ in range(10):
        rep = {}
        for idx, p in enumerate(pids):
            grp = "normal" if idx < 15 else ("prediabetes" if idx < 31 else "diabetes")
            # 30 participants improve, 15 do not
            delta = -0.5 if idx < 30 else +0.2
            rmse_g = 20.0 + idx * 0.1
            rmse_p = rmse_g + delta
            rep[p] = {
                "participant_id": p,
                "diag_group": grp,
                "n_adapt": 500,
                "n_eval": 1500,
                "rmse_global": rmse_g,
                "rmse_pers": rmse_p,
                "mae_global": rmse_g * 0.8,
                "mae_pers": rmse_p * 0.8,
                "delta_rmse": delta,
                "pct_reduction": (-delta / rmse_g) * 100.0,
            }
        repeat_records.append(rep)

    consolidated = consolidate_personalization_metrics(repeat_records)
    assert len(consolidated) == 45

    summary = compute_personalization_cohort_summary(
        consolidated, n_bootstrap=500, bootstrap_seed=42
    )

    assert summary["cohort_participants"] == 45
    assert summary["paired_difference"]["n_improved"] == 30
    assert np.isclose(summary["paired_difference"]["fraction_improved"], 30 / 45)
    assert (
        summary["paired_difference"]["ci_95_mean_delta_rmse"][0]
        < summary["paired_difference"]["mean_delta_rmse"]
        < summary["paired_difference"]["ci_95_mean_delta_rmse"][1]
    )
    assert "normal" in summary["subgroups"]
    assert summary["subgroups"]["normal"]["n_participants"] == 15
