"""Tests for Stage 1B-R2 dual sensor agreement: unbalanced ANOVA, n0 correction, and censoring."""

from __future__ import annotations

import numpy as np
import pandas as pd

from dtwin.analysis.dual_sensor import (
    _compute_unbalanced_rm_anova,
    compute_repeated_measures_bland_altman,
    estimate_apparent_lag,
)


def test_unbalanced_rm_anova_analytical_example():
    """Verify unbalanced random effects ANOVA formulas against exact hand-calculated values."""
    # Cluster 1: n1 = 2, mean = 11, var = 2 (sumsq = 2)
    # Cluster 2: n2 = 4, mean = 23, var = 6.666667 (sumsq = 20)
    p_counts = np.array([2.0, 4.0])
    p_means = np.array([11.0, 23.0])
    p_vars = np.array([2.0, 20.0 / 3.0])

    mu_pool, mu_eq, sd_b, sd_w, n0, sd_rm, var_rm = _compute_unbalanced_rm_anova(
        p_counts, p_means, p_vars
    )

    # 1. Check estimands
    assert np.isclose(mu_pool, 19.0, atol=1e-5)
    assert np.isclose(mu_eq, 17.0, atol=1e-5)

    # 2. Check n0 multiplier: (6 - (4 + 16)/6) / 1 = 6 - 20/6 = 8/3 ≈ 2.666667
    assert np.isclose(n0, 8.0 / 3.0, atol=1e-5)

    # 3. Check MSW (var_w): (1*2 + 3*(20/3)) / (6 - 2) = (2 + 20) / 4 = 5.5
    assert np.isclose(sd_w**2, 5.5, atol=1e-5)

    # 4. Check SSB = 2*(11-19)^2 + 4*(23-19)^2 = 128 + 64 = 192 -> MSB = 192
    # var_b = (MSB - MSW) / n0 = (192 - 5.5) / (8/3) = 186.5 * 3 / 8 = 69.9375
    assert np.isclose(sd_b**2, 69.9375, atol=1e-5)

    # 5. Check var_rm = var_b + var_w = 69.9375 + 5.5 = 75.4375
    assert np.isclose(var_rm, 75.4375, atol=1e-5)
    assert np.isclose(sd_rm, np.sqrt(75.4375), atol=1e-5)


def test_bland_altman_rm_pipeline_with_censoring():
    """Verify compute_repeated_measures_bland_altman with saturation limit censoring."""
    # Create DataFrame with normal values and saturation outliers
    p1 = pd.DataFrame(
        {
            "participant_id": ["P1"] * 10,
            "libre": [100.0] * 9 + [400.0],  # 1 saturated
            "dexcom": [110.0] * 9 + [420.0],
            "diff": [-10.0] * 9 + [-20.0],
            "mean": [105.0] * 9 + [410.0],
        }
    )
    p2 = pd.DataFrame(
        {
            "participant_id": ["P2"] * 10,
            "libre": [150.0] * 10,
            "dexcom": [160.0] * 10,
            "diff": [-10.0] * 10,
            "mean": [155.0] * 10,
        }
    )
    df = pd.concat([p1, p2], ignore_index=True)

    # Uncensored: all 20 rows
    res_uncensored = compute_repeated_measures_bland_altman(
        df, bootstrap_replicates=50, censor_saturation=False
    )
    assert res_uncensored.n_paired_points == 20

    # Censored: saturated point (> 400) excluded -> 19 rows
    res_censored = compute_repeated_measures_bland_altman(
        df,
        bootstrap_replicates=50,
        censor_saturation=True,
        saturation_limits=(40.0, 399.0),
    )
    assert res_censored.n_paired_points == 19
    # In censored data, diff is strictly -10 across all points
    assert np.isclose(res_censored.mean_difference_pool, -10.0)


def test_apparent_lag_direction_verified():
    """Verify estimate_apparent_lag directionality."""
    t = np.arange(200)
    sig = 120.0 + 20.0 * np.sin(2 * np.pi * t / 40.0)

    # Libre leads Dexcom by 3 minutes (Dexcom is delayed: dex[t+3] == lib[t])
    lib = sig[:180]
    dex = np.roll(sig, 3)[:180]  # delayed by 3
    lag = estimate_apparent_lag(lib, dex, max_lag=10)
    assert lag == 3

    # Dexcom leads Libre by 4 minutes (Libre is delayed: lib[t+4] == dex[t])
    dex_lead = sig[:180]
    lib_lead = np.roll(sig, 4)[:180]
    lag_neg = estimate_apparent_lag(lib_lead, dex_lead, max_lag=10)
    assert lag_neg == -4
