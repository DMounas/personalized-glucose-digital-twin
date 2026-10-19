"""Detector-blind synthetic benchmark generator for native-grid inference (C5).

Written independently from detector implementation without shared helper functions.
Covers 15 scenarios:
- Core linear grids (5m, 15m)
- Precision & rounding (integer vs float)
- Native timestamp jitter and phase shifts
- Dropped samples (bridged vs NaN)
- Absent timestamp gaps
- Collinear and flat stretches
- Low dynamic range
- Non-linear interpolation alternatives (PCHIP, cubic, nearest-neighbor)
- Negative controls (continuous 1-min physiological simulation, smoothed random walk)
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.interpolate import PchipInterpolator, interp1d


def simulate_physiological_glucose(
    length_points: int = 1440,
    seed: int | None = None,
) -> np.ndarray:
    """Simulate a continuous 1-minute physiological glucose trace (circadian + meals + stochastic drift)."""
    rng = np.random.default_rng(seed)
    t = np.arange(length_points, dtype=np.float64)

    # Basal circadian rhythm (100 - 130 mg/dL)
    basal = 115.0 + 12.0 * np.sin(2 * np.pi * t / 1440.0 - np.pi / 2)

    # 3 meal excursions: breakfast (t=420), lunch (t=780), dinner (t=1200)
    # Using asymmetric dual-exponential postprandial curves
    meals = np.zeros(length_points)
    for m_time, m_carb, m_tau_up, m_tau_down in [
        (420, 50.0, 35.0, 70.0),
        (780, 65.0, 40.0, 85.0),
        (1200, 80.0, 45.0, 95.0),
    ]:
        dt = t - m_time
        mask = dt >= 0
        curve = (m_carb * 0.9) * (np.exp(-dt[mask] / m_tau_down) - np.exp(-dt[mask] / m_tau_up))
        meals[mask] += np.maximum(0.0, curve)

    # Ornstein-Uhlenbeck stochastic drift (autocorrelated physiological noise)
    ou_noise = np.zeros(length_points)
    theta = 0.05
    sigma = 0.6
    for i in range(1, length_points):
        ou_noise[i] = ou_noise[i - 1] - theta * ou_noise[i - 1] + rng.normal(0, sigma)

    trace = basal + meals + ou_noise
    return np.clip(trace, 40.0, 400.0)


def generate_blind_benchmark_trace(
    scenario: str,
    length_points: int = 1440,
    seed: int | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Generate a single detector-blind benchmark trace with known ground truth."""
    rng = np.random.default_rng(seed)
    base = simulate_physiological_glucose(length_points, seed=seed)
    t = np.arange(length_points)

    meta: dict[str, Any] = {"scenario": scenario, "length": length_points}

    if scenario == "true_5min_linear":
        phase = int(rng.integers(0, 5))
        native_idx = np.arange(phase, length_points, 5)
        native_vals = base[native_idx]
        trace = np.interp(t, native_idx, native_vals)
        meta.update({"true_period": 5, "true_phase": phase, "is_lattice": True})
        return trace, meta

    if scenario == "true_15min_linear":
        phase = int(rng.integers(0, 15))
        native_idx = np.arange(phase, length_points, 15)
        native_vals = base[native_idx]
        trace = np.interp(t, native_idx, native_vals)
        meta.update({"true_period": 15, "true_phase": phase, "is_lattice": True})
        return trace, meta

    if scenario == "true_5min_rounded":
        phase = int(rng.integers(0, 5))
        native_idx = np.arange(phase, length_points, 5)
        native_vals = np.round(base[native_idx])
        trace = np.interp(t, native_idx, native_vals)
        meta.update({"true_period": 5, "true_phase": phase, "is_lattice": True})
        return trace, meta

    if scenario == "true_15min_rounded":
        phase = int(rng.integers(0, 15))
        native_idx = np.arange(phase, length_points, 15)
        native_vals = np.round(base[native_idx])
        trace = np.interp(t, native_idx, native_vals)
        meta.update({"true_period": 15, "true_phase": phase, "is_lattice": True})
        return trace, meta

    if scenario == "native_timestamp_jitter_5min":
        # Native points have +/- 1 min jitter in sampling
        phase = int(rng.integers(0, 5))
        native_idx = np.arange(phase, length_points, 5)
        jitter = rng.integers(-1, 2, size=len(native_idx))
        jittered_idx = np.clip(native_idx + jitter, 0, length_points - 1)
        jittered_idx = np.unique(jittered_idx)
        native_vals = base[jittered_idx]
        trace = np.interp(t, jittered_idx, native_vals)
        meta.update(
            {"true_period": 5, "true_phase": phase, "is_lattice": False, "has_jitter": True}
        )
        return trace, meta

    if scenario == "native_timestamp_jitter_15min":
        phase = int(rng.integers(0, 15))
        native_idx = np.arange(phase, length_points, 15)
        jitter = rng.integers(-1, 2, size=len(native_idx))
        jittered_idx = np.clip(native_idx + jitter, 0, length_points - 1)
        jittered_idx = np.unique(jittered_idx)
        native_vals = base[jittered_idx]
        trace = np.interp(t, jittered_idx, native_vals)
        meta.update(
            {"true_period": 15, "true_phase": phase, "is_lattice": False, "has_jitter": True}
        )
        return trace, meta

    if scenario == "dropped_native_bridged_5min":
        phase = int(rng.integers(0, 5))
        native_idx = np.arange(phase, length_points, 5)
        keep = rng.uniform(0, 1, len(native_idx)) > 0.15
        keep[0] = keep[-1] = True
        kept_idx = native_idx[keep]
        trace = np.interp(t, kept_idx, base[kept_idx])
        meta.update({"true_period": 5, "true_phase": phase, "is_lattice": True, "has_drops": True})
        return trace, meta

    if scenario == "dropped_native_bridged_15min":
        phase = int(rng.integers(0, 15))
        native_idx = np.arange(phase, length_points, 15)
        # Drop 15% of native samples and bridge across them
        keep = rng.uniform(0, 1, len(native_idx)) > 0.15
        keep[0] = keep[-1] = True
        kept_idx = native_idx[keep]
        trace = np.interp(t, kept_idx, base[kept_idx])
        meta.update({"true_period": 15, "true_phase": phase, "is_lattice": True, "has_drops": True})
        return trace, meta

    if scenario == "dropped_native_nan_5min":
        phase = int(rng.integers(0, 5))
        native_idx = np.arange(phase, length_points, 5)
        native_vals = base[native_idx]
        trace = np.interp(t, native_idx, native_vals)
        # Punch NaN gaps (e.g., 30-minute missing block)
        trace[600:640] = np.nan
        meta.update({"true_period": 5, "true_phase": phase, "is_lattice": True, "has_nans": True})
        return trace, meta

    if scenario == "absent_timestamp_gaps_15min":
        phase = int(rng.integers(0, 15))
        native_idx = np.arange(phase, length_points, 15)
        native_vals = base[native_idx]
        trace = np.interp(t, native_idx, native_vals)
        trace[500:540] = np.nan  # represents missing block
        meta.update({"true_period": 15, "true_phase": phase, "is_lattice": True, "has_gaps": True})
        return trace, meta

    if scenario == "collinear_flat_periods":
        phase = int(rng.integers(0, 15))
        native_idx = np.arange(phase, length_points, 15)
        vals = base[native_idx]
        # Fasting flatline between 0 and 400
        vals[native_idx < 400] = 95.0
        trace = np.interp(t, native_idx, vals)
        meta.update({"true_period": 15, "true_phase": phase, "is_lattice": True, "has_flat": True})
        return trace, meta

    if scenario == "low_dynamic_range":
        # Basal variance only (std < 5 mg/dL)
        low_base = 100.0 + 3.0 * np.sin(2 * np.pi * t / 1440.0) + rng.normal(0, 0.5, length_points)
        phase = int(rng.integers(0, 5))
        native_idx = np.arange(phase, length_points, 5)
        trace = np.interp(t, native_idx, low_base[native_idx])
        meta.update({"true_period": 5, "true_phase": phase, "is_lattice": True, "low_range": True})
        return trace, meta

    if scenario == "alternative_resampling_cubic_pchip":
        # 15-min native points resampled with PCHIP instead of linear
        phase = int(rng.integers(0, 15))
        native_idx = np.arange(phase, length_points, 15)
        pchip = PchipInterpolator(native_idx, base[native_idx])
        trace = pchip(t)
        meta.update({"true_period": 15, "true_phase": phase, "is_lattice": False, "is_pchip": True})
        return trace, meta

    if scenario == "alternative_resampling_nearest":
        # 5-min native points with nearest-neighbor step function
        phase = int(rng.integers(0, 5))
        native_idx = np.arange(phase, length_points, 5)
        nearest = interp1d(native_idx, base[native_idx], kind="nearest", fill_value="extrapolate")
        trace = nearest(t)
        meta.update(
            {"true_period": 5, "true_phase": phase, "is_lattice": False, "is_nearest": True}
        )
        return trace, meta

    if scenario == "physiological_simulator_continuous":
        # Continuous 1-minute physiological series WITHOUT downsampling (Negative Control)
        meta.update({"true_period": 1, "true_phase": 0, "is_lattice": False})
        return base, meta

    if scenario == "non_lattice_noise_control":
        # Smoothed random walk with no underlying grid (Negative Control)
        rw = np.cumsum(rng.normal(0, 0.8, length_points)) + 120.0
        # Light smooth
        kernel = np.ones(5) / 5.0
        smooth_rw = np.convolve(rw, kernel, mode="same")
        meta.update({"true_period": 1, "true_phase": 0, "is_lattice": False})
        return smooth_rw, meta

    msg = f"Unknown scenario: {scenario}"
    raise ValueError(msg)
