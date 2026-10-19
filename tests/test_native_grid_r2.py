"""Tests for Stage 1B-R2 native grid inference and 15-scenario detector-blind benchmark."""

from __future__ import annotations

import numpy as np
import pandas as pd

from dtwin.analysis.benchmark_generator import (
    generate_blind_benchmark_trace,
    simulate_physiological_glucose,
)
from dtwin.analysis.native_grid import infer_native_grid_series


def test_simulate_physiological_glucose_bounds():
    """Verify physiological simulator generates continuous signal within physiological bounds."""
    trace = simulate_physiological_glucose(length_points=1440, seed=123)
    assert len(trace) == 1440
    assert np.all(trace >= 40.0)
    assert np.all(trace <= 400.0)
    assert np.std(trace) > 5.0  # Dynamic range present


def test_blind_benchmark_all_15_scenarios_generate():
    """Verify all 15 scenarios generate valid arrays and metadata."""
    scenarios = [
        "true_5min_linear",
        "true_15min_linear",
        "true_5min_rounded",
        "true_15min_rounded",
        "native_timestamp_jitter_5min",
        "native_timestamp_jitter_15min",
        "dropped_native_bridged_5min",
        "dropped_native_bridged_15min",
        "dropped_native_nan_5min",
        "absent_timestamp_gaps_15min",
        "collinear_flat_periods",
        "low_dynamic_range",
        "alternative_resampling_cubic_pchip",
        "alternative_resampling_nearest",
        "physiological_simulator_continuous",
    ]
    for sc in scenarios:
        trace, meta = generate_blind_benchmark_trace(sc, length_points=720, seed=42)
        assert len(trace) == 720
        assert meta["scenario"] == sc


def test_native_grid_gap_unaware_vs_run_bounded():
    """Verify run-bounded inference handles absent timestamp gap without spurious boundary bends."""
    # Create two runs: 0..60 min and 80..140 min (20-min absent gap)
    t0 = pd.Timestamp("2020-05-01 08:00:00")
    ts1 = pd.date_range(t0, periods=60, freq="1min")
    ts2 = pd.date_range(t0 + pd.Timedelta(minutes=80), periods=60, freq="1min")
    all_ts = ts1.union(ts2).sort_values()

    # Native period 15, linear ramp
    # At gap boundary, values jump from 120 to 180
    v1 = np.linspace(100, 120, 60)
    v2 = np.linspace(180, 200, 60)
    all_vals = np.concatenate([v1, v2])

    res = infer_native_grid_series(all_vals, timestamps=all_ts)
    # The gap boundary is not counted as a bend because second diffs are strictly intra-run!
    assert res.total_bends_detected == 0  # Linear ramps have zero second difference bends
