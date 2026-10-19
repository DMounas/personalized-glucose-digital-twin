"""Dual-sensor agreement, repeated-measures Bland-Altman, and cross-correlation analysis (R2 corrected).

Statistical methodology:
- Unbalanced one-way random-effects ANOVA with Bland-Altman (1999, 2007) n0 correction.
- Explicit estimands: pooled grand mean (mu_pool) vs equal-weighted subject mean (mu_eq).
- Participant-clustered bootstrap recalculating the full ANOVA estimator per replicate.
- Censored sensitivity analysis excluding sensor saturation boundaries (<= 40, >= 400 mg/dL).
- Strict lag sign convention: tau > 0 means Libre leads Dexcom (Dexcom delayed).
- Neutral scientific language: observed systematic disagreement, zero unverified physiological attribution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BlandAltmanRMResult:
    """Repeated-measures Bland-Altman agreement results with unbalanced ANOVA and exact bootstrap."""

    n_participants: int
    n_paired_points: int
    mean_difference_pool: float
    mean_difference_eq: float
    mean_difference: float  # alias to mean_difference_pool for backward compatibility
    sd_between: float
    sd_within: float
    n0_multiplier: float
    sd_repeated_measures: float
    limits_of_agreement_lower: float
    limits_of_agreement_upper: float
    limits_of_agreement_eq_lower: float
    limits_of_agreement_eq_upper: float
    bootstrap_mean_ci_95: list[float]
    bootstrap_mean_eq_ci_95: list[float]
    bootstrap_loa_lower_ci_95: list[float]
    bootstrap_loa_upper_ci_95: list[float]
    pearson_r: float
    spearman_rho: float
    proportional_bias_slope: float
    proportional_bias_intercept: float


def _compute_unbalanced_rm_anova(
    p_counts: np.ndarray,
    p_means: np.ndarray,
    p_vars: np.ndarray,
) -> tuple[float, float, float, float, float, float, float]:
    """Compute unbalanced one-way random effects ANOVA components.

    Returns:
    (mu_pool, mu_eq, sd_between, sd_within, n0, sd_rm, var_rm)
    """
    k = len(p_counts)
    n_total = float(np.sum(p_counts))
    if k <= 1 or n_total <= k:
        mu = float(np.mean(p_means)) if k > 0 else 0.0
        return (mu, mu, 0.0, 0.0, 1.0, 0.0, 0.0)

    # Estimands
    mu_pool = float(np.sum(p_counts * p_means) / n_total)
    mu_eq = float(np.mean(p_means))

    # Sum of Squares Between: SSB = sum(n_i * (mean_i - mu_pool)^2)
    ssb = float(np.sum(p_counts * ((p_means - mu_pool) ** 2)))
    df_b = k - 1
    msb = ssb / df_b

    # Sum of Squares Within: SSW = sum((n_i - 1) * s_i^2)
    # Note: for clusters with n_i == 1, (n_i - 1) * s_i^2 is 0
    ssw = float(np.sum(np.maximum(0, p_counts - 1) * np.nan_to_num(p_vars, nan=0.0)))
    df_w = max(1.0, n_total - k)
    msw = ssw / df_w

    # Within-subject variance component
    var_w = max(0.0, msw)
    sd_w = math.sqrt(var_w)

    # Effective cluster size multiplier n0
    sum_n2 = float(np.sum(p_counts**2))
    n0 = max(1.0, (n_total - (sum_n2 / n_total)) / df_b)

    # Between-subject variance component
    var_b = max(0.0, (msb - msw) / n0)
    sd_b = math.sqrt(var_b)

    # Total repeated-measures variance
    var_rm = var_b + var_w
    sd_rm = math.sqrt(var_rm)

    return (mu_pool, mu_eq, sd_b, sd_w, n0, sd_rm, var_rm)


def compute_repeated_measures_bland_altman(
    df_pairs: pd.DataFrame,
    bootstrap_replicates: int = 500,
    seed: int = 42,
    censor_saturation: bool = False,
    saturation_limits: tuple[float, float] = (40.0, 400.0),
) -> BlandAltmanRMResult:
    """Compute repeated-measures Bland-Altman statistics with participant-clustered bootstrap.

    Expects df_pairs with columns: ['participant_id', 'libre', 'dexcom', 'diff', 'mean'].
    Fixed convention: diff = libre - dexcom.
    """
    df = df_pairs.copy()
    if censor_saturation:
        low, high = saturation_limits
        valid_mask = (
            (df["libre"] > low)
            & (df["libre"] < high)
            & (df["dexcom"] > low)
            & (df["dexcom"] < high)
        )
        df = df[valid_mask]

    n_pairs = len(df)
    p_stats = df.groupby("participant_id")["diff"].agg(["count", "mean", "var"]).reset_index()
    p_stats["var"] = p_stats["var"].fillna(0.0)
    k_participants = len(p_stats)

    p_counts = p_stats["count"].to_numpy(dtype=float)
    p_means = p_stats["mean"].to_numpy(dtype=float)
    p_vars = p_stats["var"].to_numpy(dtype=float)

    (
        mu_pool,
        mu_eq,
        sd_b,
        sd_w,
        n0,
        sd_rm,
        _,
    ) = _compute_unbalanced_rm_anova(p_counts, p_means, p_vars)

    # Limits of Agreement
    loa_pool_lower = mu_pool - 1.96 * sd_rm
    loa_pool_upper = mu_pool + 1.96 * sd_rm
    loa_eq_lower = mu_eq - 1.96 * sd_rm
    loa_eq_upper = mu_eq + 1.96 * sd_rm

    # Linear regression for proportional bias
    slope, intercept = np.polyfit(df["mean"], df["diff"], 1)

    # Correlation metrics
    pearson_r = float(np.corrcoef(df["libre"], df["dexcom"])[0, 1])
    if n_pairs > 50000:
        sample_idx = np.random.default_rng(seed).choice(n_pairs, size=50000, replace=False)
        sub_l = df["libre"].iloc[sample_idx]
        sub_d = df["dexcom"].iloc[sample_idx]
        spearman_rho = float(sub_l.corr(sub_d, method="spearman"))
    else:
        spearman_rho = float(df["libre"].corr(df["dexcom"], method="spearman"))

    # Participant-clustered bootstrap recalculating the full ANOVA estimator
    rng = np.random.default_rng(seed)
    boot_mu_pool: list[float] = []
    boot_mu_eq: list[float] = []
    boot_loa_lower: list[float] = []
    boot_loa_upper: list[float] = []

    for _ in range(bootstrap_replicates):
        boot_idx = rng.choice(k_participants, size=k_participants, replace=True)
        b_counts = p_counts[boot_idx]
        b_means = p_means[boot_idx]
        b_vars = p_vars[boot_idx]

        b_mu_pool, b_mu_eq, _, _, _, b_sd_rm, _ = _compute_unbalanced_rm_anova(
            b_counts, b_means, b_vars
        )
        boot_mu_pool.append(b_mu_pool)
        boot_mu_eq.append(b_mu_eq)
        boot_loa_lower.append(b_mu_pool - 1.96 * b_sd_rm)
        boot_loa_upper.append(b_mu_pool + 1.96 * b_sd_rm)

    mean_ci = [float(np.percentile(boot_mu_pool, 2.5)), float(np.percentile(boot_mu_pool, 97.5))]
    mean_eq_ci = [float(np.percentile(boot_mu_eq, 2.5)), float(np.percentile(boot_mu_eq, 97.5))]
    loa_low_ci = [
        float(np.percentile(boot_loa_lower, 2.5)),
        float(np.percentile(boot_loa_lower, 97.5)),
    ]
    loa_high_ci = [
        float(np.percentile(boot_loa_upper, 2.5)),
        float(np.percentile(boot_loa_upper, 97.5)),
    ]

    return BlandAltmanRMResult(
        n_participants=k_participants,
        n_paired_points=n_pairs,
        mean_difference_pool=round(mu_pool, 2),
        mean_difference_eq=round(mu_eq, 2),
        mean_difference=round(mu_pool, 2),
        sd_between=round(sd_b, 2),
        sd_within=round(sd_w, 2),
        n0_multiplier=round(n0, 2),
        sd_repeated_measures=round(sd_rm, 2),
        limits_of_agreement_lower=round(loa_pool_lower, 2),
        limits_of_agreement_upper=round(loa_pool_upper, 2),
        limits_of_agreement_eq_lower=round(loa_eq_lower, 2),
        limits_of_agreement_eq_upper=round(loa_eq_upper, 2),
        bootstrap_mean_ci_95=[round(mean_ci[0], 2), round(mean_ci[1], 2)],
        bootstrap_mean_eq_ci_95=[round(mean_eq_ci[0], 2), round(mean_eq_ci[1], 2)],
        bootstrap_loa_lower_ci_95=[round(loa_low_ci[0], 2), round(loa_low_ci[1], 2)],
        bootstrap_loa_upper_ci_95=[round(loa_high_ci[0], 2), round(loa_high_ci[1], 2)],
        pearson_r=round(pearson_r, 4),
        spearman_rho=round(spearman_rho, 4),
        proportional_bias_slope=round(float(slope), 4),
        proportional_bias_intercept=round(float(intercept), 2),
    )


def estimate_apparent_lag(
    libre_vals: np.ndarray,
    dexcom_vals: np.ndarray,
    max_lag: int = 15,
) -> int:
    """Estimate apparent lag between Libre and Dexcom using first differences.

    Convention (verified by C4 test):
    - tau > 0: Libre leads Dexcom (Dexcom is delayed relative to Libre).
    - tau < 0: Dexcom leads Libre (Libre is delayed relative to Dexcom).
    - tau == 0: Synchronous.
    """
    n = min(len(libre_vals), len(dexcom_vals))
    if n < 60:
        return 0

    l_arr = np.asarray(libre_vals[:n], dtype=float)
    d_arr = np.asarray(dexcom_vals[:n], dtype=float)

    best_lag = 0
    best_corr = -2.0

    # Test lag tau from -max_lag to +max_lag
    for tau in range(-max_lag, max_lag + 1):
        if tau > 0:
            # Libre at t compares to Dexcom at t + tau
            # If Dexcom is delayed by tau, dexcom[t + tau] == libre[t]
            s_libre = l_arr[:-tau]
            s_dexcom = d_arr[tau:]
        elif tau < 0:
            # Libre at t + |tau| compares to Dexcom at t
            # If Libre is delayed by |tau|, libre[t + |tau|] == dexcom[t]
            k_abs = abs(tau)
            s_libre = l_arr[k_abs:]
            s_dexcom = d_arr[:-k_abs]
        else:
            s_libre = l_arr
            s_dexcom = d_arr

        if len(s_libre) < 30:
            continue

        dl = np.diff(s_libre)
        dd = np.diff(s_dexcom)

        valid = ~np.isnan(dl) & ~np.isnan(dd)
        if np.sum(valid) < 30:
            continue

        dl_v = dl[valid]
        dd_v = dd[valid]

        # Standard deviation check to prevent division by zero
        if np.std(dl_v) < 1e-6 or np.std(dd_v) < 1e-6:
            continue

        r = float(np.corrcoef(dl_v, dd_v)[0, 1])
        if r > best_corr:
            best_corr = r
            best_lag = tau

    return best_lag
