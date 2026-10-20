"""Rung 0 (Guarded Persistence) and Rung 1 (Damped Trend) baseline models."""

from __future__ import annotations

from typing import Any

import numpy as np

from dtwin.modeling.cv import generate_inner_cv_splits
from dtwin.modeling.dataset import ParticipantOrigins


def predict_guarded_persistence(y_base: np.ndarray) -> np.ndarray:
    """Rung 0: Guarded Persistence Baseline.

    Predicts future glucose using the latest permitted guard-band observation:
    y_hat(t + h) = y(t - 5).

    Args:
        y_base: Array of y(t - 5) glucose readings.

    Returns:
        Array of persistence predictions.
    """
    return np.asarray(y_base, dtype=np.float64).copy()


def predict_damped_trend(
    y_base: np.ndarray,
    roc: np.ndarray,
    horizon_minutes: int,
    gamma: float,
) -> np.ndarray:
    """Rung 1: Damped-Trend Baseline.

    Extrapolates recent rate of change with an estimated empirical damping factor:
    y_hat(t + h) = y(t - 5) + gamma_h * ((y(t - 5) - y(t - 20)) / 15) * h.

    Args:
        y_base: Array of y(t - 5) glucose readings.
        roc: Array of first-order rate of change ((y(t-5) - y(t-20)) / 15).
        horizon_minutes: Forecast horizon in minutes (+30 or +60).
        gamma: Empirical damping parameter in [0, 1].

    Returns:
        Array of damped-trend predictions.
    """
    y_b = np.asarray(y_base, dtype=np.float64)
    r = np.asarray(roc, dtype=np.float64)
    return y_b + float(gamma) * r * float(horizon_minutes)


def tune_damped_trend_gamma(
    dataset: dict[str, ParticipantOrigins],
    train_pids: list[str],
    pid_to_group: dict[str, str],
    horizon_minutes: int,
    seed: int,
    candidate_gammas: np.ndarray | None = None,
) -> tuple[float, dict[str, Any]]:
    """Estimate optimal damping factor gamma_h via inner 4-fold participant-grouped CV.

    Evaluated strictly on training-fold participants. Candidate values are
    benchmarked by participant-averaged validation RMSE across inner validation folds.

    Args:
        dataset: Mapping of participant IDs to ParticipantOrigins.
        train_pids: List of participant IDs in outer training fold (36 participants).
        pid_to_group: Mapping from participant ID to diagnostic group string.
        horizon_minutes: Forecast horizon in minutes (+30 or +60).
        seed: Random seed for inner fold partitioning.
        candidate_gammas: Optional array of candidate gamma values in [0, 1].
            Defaults to 101 values from 0.0 to 1.0 (step 0.01).

    Returns:
        Tuple of (optimal_gamma, tuning_diagnostics).
    """
    if candidate_gammas is None:
        candidate_gammas = np.linspace(0.0, 1.0, 101)

    inner_splits = generate_inner_cv_splits(
        train_pids=train_pids,
        pid_to_group=pid_to_group,
        inner_seed=seed,
        n_splits=4,
    )

    # Precompute participant quadratic coefficients for ultra-fast exact evaluation:
    # SSE_p(gamma) = A_p * gamma^2 + B_p * gamma + C_p
    # where v = roc * h, e = target - y_base
    quad_coeffs: dict[str, tuple[float, float, float, int]] = {}
    h = float(horizon_minutes)
    for pid in train_pids:
        orig = dataset[pid]
        v = orig.roc * h
        e = orig.target - orig.y_base
        a_p = float(np.sum(v**2))
        b_p = float(-2.0 * np.sum(e * v))
        c_p = float(np.sum(e**2))
        n_p = len(orig.target)
        quad_coeffs[pid] = (a_p, b_p, c_p, n_p)

    gamma_scores: list[float] = []

    for gamma in candidate_gammas:
        g = float(gamma)
        fold_participant_rmses: list[float] = []

        for in_split in inner_splits:
            for val_pid in in_split.inner_val_pids:
                a_p, b_p, c_p, n_p = quad_coeffs[val_pid]
                if n_p > 0:
                    sse = max(0.0, a_p * g * g + b_p * g + c_p)
                    rmse_p = np.sqrt(sse / n_p)
                    fold_participant_rmses.append(float(rmse_p))

        mean_rmse = float(np.mean(fold_participant_rmses))
        gamma_scores.append(mean_rmse)

    best_idx = int(np.argmin(gamma_scores))
    best_gamma = float(candidate_gammas[best_idx])

    diagnostics = {
        "best_gamma": best_gamma,
        "best_inner_rmse": float(gamma_scores[best_idx]),
        "persistence_inner_rmse": float(gamma_scores[0]),  # gamma = 0.0 is persistence
        "inner_folds_count": len(inner_splits),
        "candidate_count": len(candidate_gammas),
    }

    return best_gamma, diagnostics
