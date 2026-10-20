"""Stage 3: Participant-Specific Residual-Correction Personalization.

Under Protocol Addendum v1.0.0 (docs/STAGE3_PERSONALIZATION_PROTOCOL.md):
- Global Model: Rung 5 Baseline-Covariate Ridge regression (20 features) trained on outer training participants.
- Adaptation Windows: First 2, 4, or 6 study days (2880, 5760, 8640 elapsed minutes).
- Adaptation Labels: Target outcomes y(t+h) must not cross the adaptation cutoff (m(t) + h <= T_cutoff).
- Purge Buffer: Mandatory >= 120-minute gap immediately following adaptation cutoff.
- Evaluation Origins: m(t) >= T_cutoff + 120 minutes.
- Personalization Model: Participant-specific Ridge regression fitting residuals r(t) = y(t+h) - y_hat_global(t+h)
  using the 13 guarded glucose history lags and 3 meal-timing features (16 features total).
  Reuses the outer training fold's optimal alpha_global.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from dtwin.modeling.covariates import (
    CovariatePreprocessor,
    assemble_rung5_matrix,
)
from dtwin.modeling.dataset import ParticipantOrigins
from dtwin.modeling.meal import MealPreprocessor


@dataclass(frozen=True)
class PartitionIndices:
    """Boolean and integer masks for adaptation, purge, and evaluation sets."""

    adapt_indices: np.ndarray
    eval_indices: np.ndarray
    n_adapt: int
    n_eval: int
    cutoff_minutes: int
    eval_start_minutes: int


def partition_participant_origins(
    elapsed_minutes: np.ndarray,
    horizon_minutes: int,
    days: int,
    purge_minutes: int = 120,
) -> PartitionIndices:
    """Partition participant origins into adaptation and evaluation sets under protocol rules.

    Args:
        elapsed_minutes: Array of integer elapsed minutes m(t) from recording t0.
        horizon_minutes: Forecast horizon h in minutes (+30 or +60).
        days: Adaptation window length in study days (2, 4, or 6).
        purge_minutes: Minimum purge interval in minutes (default: 120).

    Returns:
        PartitionIndices containing integer indices of adaptation and evaluation origins.
    """
    cutoff_m = days * 1440
    eval_start_m = cutoff_m + purge_minutes

    # Label boundary guard: target y(t+h) cannot cross the adaptation cutoff
    adapt_mask = (elapsed_minutes + horizon_minutes) <= cutoff_m
    eval_mask = elapsed_minutes >= eval_start_m

    adapt_idx = np.where(adapt_mask)[0]
    eval_idx = np.where(eval_mask)[0]

    return PartitionIndices(
        adapt_indices=adapt_idx,
        eval_indices=eval_idx,
        n_adapt=len(adapt_idx),
        n_eval=len(eval_idx),
        cutoff_minutes=cutoff_m,
        eval_start_minutes=eval_start_m,
    )


def fit_predict_personalized_participant(
    orig: ParticipantOrigins,
    global_model: Ridge,
    meal_prep: MealPreprocessor,
    cov_prep: CovariatePreprocessor,
    scaler: StandardScaler,
    alpha_global: float,
    days: int,
    purge_minutes: int = 120,
) -> dict[str, Any]:
    """Fit residual-correction Ridge model on adaptation window and evaluate on matched test period.

    Args:
        orig: ParticipantOrigins for a single held-out test participant.
        global_model: Trained outer Rung 5 Ridge model.
        meal_prep: Fitted MealPreprocessor from outer training fold.
        cov_prep: Fitted CovariatePreprocessor from outer training fold.
        scaler: Fitted StandardScaler from outer training fold (20 features).
        alpha_global: Optimal Ridge alpha from outer training fold.
        days: Adaptation window in study days (2, 4, or 6).
        purge_minutes: Minimum purge buffer in minutes (default: 120).

    Returns:
        Dictionary containing matched predictions, metrics, and partition diagnostics.
    """
    part = partition_participant_origins(
        elapsed_minutes=orig.elapsed_minutes,
        horizon_minutes=orig.horizon_minutes,
        days=days,
        purge_minutes=purge_minutes,
    )

    # Assemble 20-dimensional feature matrix for all participant origins
    X_full = assemble_rung5_matrix(
        orig.history_lags,
        orig.meal_features,
        orig.static_covariates,
        meal_prep,
        cov_prep,
    )
    X_full_s = scaler.transform(X_full)

    # Global predictions on all origins
    y_pred_global_all = global_model.predict(X_full_s)

    # If no evaluation origins exist (safety check, though verified > 0 for all participants)
    if part.n_eval == 0:
        return {
            "participant_id": orig.participant_id,
            "diag_group": orig.diag_group,
            "days": days,
            "n_adapt": part.n_adapt,
            "n_eval": 0,
            "rmse_global": 0.0,
            "rmse_pers": 0.0,
            "mae_global": 0.0,
            "mae_pers": 0.0,
            "delta_rmse": 0.0,
            "pct_reduction": 0.0,
            "eval_indices": np.array([], dtype=int),
            "y_true_eval": np.array([], dtype=float),
            "y_pred_global_eval": np.array([], dtype=float),
            "y_pred_pers_eval": np.array([], dtype=float),
        }

    # Extract dynamic 16 features: 13 glucose lags + 3 meal timing features
    Z_full_s = X_full_s[:, :16]

    # Fit residual-correction model on adaptation observations
    if part.n_adapt > 0:
        Z_adapt = Z_full_s[part.adapt_indices]
        y_adapt_true = orig.target[part.adapt_indices]
        y_adapt_global = y_pred_global_all[part.adapt_indices]
        r_adapt = y_adapt_true - y_adapt_global

        corr_model = Ridge(alpha=alpha_global, fit_intercept=True)
        corr_model.fit(Z_adapt, r_adapt)

        # Residual predictions on evaluation origins
        Z_eval = Z_full_s[part.eval_indices]
        r_eval_pred = corr_model.predict(Z_eval)
    else:
        # Fallback: if zero adaptation data, correction is zero
        r_eval_pred = np.zeros(part.n_eval)

    # Matched evaluation on identical evaluation timestamps
    y_true_eval = orig.target[part.eval_indices]
    y_pred_global_eval = y_pred_global_all[part.eval_indices]
    y_pred_pers_eval = y_pred_global_eval + r_eval_pred

    err_global = y_true_eval - y_pred_global_eval
    err_pers = y_true_eval - y_pred_pers_eval

    rmse_global = float(np.sqrt(np.mean(err_global**2)))
    rmse_pers = float(np.sqrt(np.mean(err_pers**2)))
    mae_global = float(np.mean(np.abs(err_global)))
    mae_pers = float(np.mean(np.abs(err_pers)))

    delta_rmse = rmse_pers - rmse_global
    pct_reduction = (
        float((rmse_global - rmse_pers) / rmse_global * 100.0) if rmse_global > 1e-9 else 0.0
    )

    return {
        "participant_id": orig.participant_id,
        "diag_group": orig.diag_group,
        "days": days,
        "n_adapt": part.n_adapt,
        "n_eval": part.n_eval,
        "rmse_global": rmse_global,
        "rmse_pers": rmse_pers,
        "mae_global": mae_global,
        "mae_pers": mae_pers,
        "delta_rmse": delta_rmse,
        "pct_reduction": pct_reduction,
        "eval_indices": part.eval_indices,
        "y_true_eval": y_true_eval,
        "y_pred_global_eval": y_pred_global_eval,
        "y_pred_pers_eval": y_pred_pers_eval,
    }


def consolidate_personalization_metrics(
    repeat_records: list[dict[str, dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Consolidate participant metrics across the 10 cross-validation repetitions.

    Args:
        repeat_records: List of 10 dicts (one per repetition), mapping participant_id -> metrics dict.

    Returns:
        Mapping of participant_id -> consolidated summary with averaged RMSE, MAE, delta_rmse, etc.
    """
    assert len(repeat_records) == 10, "Expected exactly 10 CV repetitions"
    pids = sorted(repeat_records[0].keys())

    consolidated: dict[str, dict[str, Any]] = {}
    for pid in pids:
        group = repeat_records[0][pid]["diag_group"]
        n_adapt = repeat_records[0][pid]["n_adapt"]
        n_eval = repeat_records[0][pid]["n_eval"]

        rmses_g = [r[pid]["rmse_global"] for r in repeat_records]
        rmses_p = [r[pid]["rmse_pers"] for r in repeat_records]
        maes_g = [r[pid]["mae_global"] for r in repeat_records]
        maes_p = [r[pid]["mae_pers"] for r in repeat_records]
        deltas = [r[pid]["delta_rmse"] for r in repeat_records]
        pct_reds = [r[pid]["pct_reduction"] for r in repeat_records]

        mean_rmse_g = float(np.mean(rmses_g))
        mean_rmse_p = float(np.mean(rmses_p))
        mean_mae_g = float(np.mean(maes_g))
        mean_mae_p = float(np.mean(maes_p))
        mean_delta = float(np.mean(deltas))
        mean_pct_red = float(np.mean(pct_reds))

        consolidated[pid] = {
            "participant_id": pid,
            "diag_group": group,
            "n_adapt": n_adapt,
            "n_eval": n_eval,
            "mean_rmse_global": mean_rmse_g,
            "mean_rmse_pers": mean_rmse_p,
            "mean_mae_global": mean_mae_g,
            "mean_mae_pers": mean_mae_p,
            "mean_delta_rmse": mean_delta,
            "mean_pct_reduction": mean_pct_red,
            "rmse_global_per_repeat": rmses_g,
            "rmse_pers_per_repeat": rmses_p,
            "delta_rmse_per_repeat": deltas,
        }

    return consolidated


def compute_personalization_cohort_summary(
    consolidated_participants: dict[str, dict[str, Any]],
    n_bootstrap: int = 2000,
    bootstrap_seed: int = 42,
) -> dict[str, Any]:
    """Compute cohort headline metrics and 95% participant-bootstrap confidence intervals for personalization.

    Resampling is strictly conducted over the 45 INDEPENDENT PARTICIPANTS.

    Args:
        consolidated_participants: Mapping of participant_id -> consolidated dict (45 entries).
        n_bootstrap: Number of bootstrap iterations (default: 2,000).
        bootstrap_seed: PRNG seed for bootstrap reproducibility (default: 42).

    Returns:
        Dictionary of cohort statistics, paired differences, bootstrap CIs, and subgroup breakdowns.
    """
    pids = sorted(consolidated_participants.keys())
    n_p = len(pids)
    assert n_p == 45, f"Expected 45 participants, found {n_p}"

    rmse_g = np.array([consolidated_participants[p]["mean_rmse_global"] for p in pids])
    rmse_p = np.array([consolidated_participants[p]["mean_rmse_pers"] for p in pids])
    mae_g = np.array([consolidated_participants[p]["mean_mae_global"] for p in pids])
    mae_p = np.array([consolidated_participants[p]["mean_mae_pers"] for p in pids])
    delta_rmse = np.array([consolidated_participants[p]["mean_delta_rmse"] for p in pids])
    pct_red = np.array([consolidated_participants[p]["mean_pct_reduction"] for p in pids])
    groups = [consolidated_participants[p]["diag_group"] for p in pids]

    mean_rmse_g = float(np.mean(rmse_g))
    median_rmse_g = float(np.median(rmse_g))
    mean_rmse_p = float(np.mean(rmse_p))
    median_rmse_p = float(np.median(rmse_p))

    mean_mae_g = float(np.mean(mae_g))
    median_mae_g = float(np.median(mae_g))
    mean_mae_p = float(np.mean(mae_p))
    median_mae_p = float(np.median(mae_p))

    mean_delta_rmse = float(np.mean(delta_rmse))
    median_delta_rmse = float(np.median(delta_rmse))
    mean_pct_reduction = float(np.mean(pct_red))
    median_pct_reduction = float(np.median(pct_red))

    # Improved if delta_rmse < 0 (i.e. personalized RMSE < global RMSE)
    improved_mask = delta_rmse < 0.0
    n_improved = int(np.sum(improved_mask))
    fraction_improved = float(n_improved / n_p)

    # Participant bootstrap: resample 45 participants with replacement
    rng = np.random.default_rng(bootstrap_seed)
    boot_idx = rng.integers(0, n_p, size=(n_bootstrap, n_p))

    boot_mean_delta = np.mean(delta_rmse[boot_idx], axis=1)
    boot_median_delta = np.median(delta_rmse[boot_idx], axis=1)
    boot_mean_pct_red = np.mean(pct_red[boot_idx], axis=1)

    ci_mean_delta = [
        float(np.percentile(boot_mean_delta, 2.5)),
        float(np.percentile(boot_mean_delta, 97.5)),
    ]
    ci_median_delta = [
        float(np.percentile(boot_median_delta, 2.5)),
        float(np.percentile(boot_median_delta, 97.5)),
    ]
    ci_mean_pct_red = [
        float(np.percentile(boot_mean_pct_red, 2.5)),
        float(np.percentile(boot_mean_pct_red, 97.5)),
    ]

    # Subgroup breakdown
    subgroups: dict[str, Any] = {}
    for grp in ["normal", "prediabetes", "diabetes"]:
        grp_mask = np.array([g == grp for g in groups], dtype=bool)
        n_grp = int(np.sum(grp_mask))
        if n_grp > 0:
            subgroups[grp] = {
                "n_participants": n_grp,
                "mean_rmse_global": float(np.mean(rmse_g[grp_mask])),
                "mean_rmse_pers": float(np.mean(rmse_p[grp_mask])),
                "mean_delta_rmse": float(np.mean(delta_rmse[grp_mask])),
                "median_delta_rmse": float(np.median(delta_rmse[grp_mask])),
                "mean_pct_reduction": float(np.mean(pct_red[grp_mask])),
                "n_improved": int(np.sum(delta_rmse[grp_mask] < 0.0)),
                "fraction_improved": float(np.sum(delta_rmse[grp_mask] < 0.0) / n_grp),
            }

    return {
        "cohort_participants": n_p,
        "matched_global": {
            "mean_rmse": mean_rmse_g,
            "median_rmse": median_rmse_g,
            "mean_mae": mean_mae_g,
            "median_mae": median_mae_g,
        },
        "personalized": {
            "mean_rmse": mean_rmse_p,
            "median_rmse": median_rmse_p,
            "mean_mae": mean_mae_p,
            "median_mae": median_mae_p,
        },
        "paired_difference": {
            "mean_delta_rmse": mean_delta_rmse,
            "median_delta_rmse": median_delta_rmse,
            "ci_95_mean_delta_rmse": ci_mean_delta,
            "ci_95_median_delta_rmse": ci_median_delta,
            "mean_pct_reduction": mean_pct_reduction,
            "median_pct_reduction": median_pct_reduction,
            "ci_95_mean_pct_reduction": ci_mean_pct_red,
            "n_improved": n_improved,
            "fraction_improved": fraction_improved,
        },
        "subgroups": subgroups,
        "bootstrap_metadata": {
            "resampling_unit": "45 independent participants",
            "iterations": n_bootstrap,
            "seed": bootstrap_seed,
        },
    }
