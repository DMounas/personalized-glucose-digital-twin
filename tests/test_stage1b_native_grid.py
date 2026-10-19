"""Unit and regression tests for Stage 1B Native-Grid Inference and Synthetic Benchmarks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from dtwin.analysis.native_grid import (
    generate_synthetic_trace,
    infer_native_grid_series,
    wilson_score_interval,
)


@pytest.fixture(scope="module")
def stage1b_results() -> dict:
    results_path = Path("docs/reports/stage1b_results.json")
    assert results_path.exists(), "stage1b_results.json must exist"
    with open(results_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def stage1b_config() -> dict:
    config_path = Path("configs/stage1b.yaml")
    assert config_path.exists(), "configs/stage1b.yaml must exist"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_wilson_score_interval_bounds():
    """Verify Wilson score confidence interval computation on known edge cases."""
    low, high = wilson_score_interval(100, 100)
    assert low > 0.95
    assert high == 1.0

    low_zero, high_zero = wilson_score_interval(0, 100)
    assert low_zero == 0.0
    assert high_zero < 0.05

    low_half, high_half = wilson_score_interval(50, 100)
    assert 0.40 < low_half < 0.50
    assert 0.50 < high_half < 0.60


def test_native_grid_synthetic_5min_discrimination(stage1b_config):
    """Verify that 5-minute native synthetic data is identified with period 5 and high confidence."""
    trace, meta = generate_synthetic_trace(
        scenario="five_minute_native",
        length_points=1440,
        noise_std=0.2,
        integer_rounding=True,
        seed=101,
    )
    assert meta["true_period"] == 5
    res = infer_native_grid_series(trace, stage1b_config)
    assert res.period_inferred == 5
    assert res.confidence == "HIGH_CONFIDENCE"
    assert res.is_native_inferred is True
    assert res.reconstruction_residual_mean < 0.25
    assert res.intermediate_5min_bends_count > 10


def test_native_grid_synthetic_15min_discrimination(stage1b_config):
    """Verify that 15-minute native synthetic data is identified with period 15 and intermediate bends are absent."""
    trace, meta = generate_synthetic_trace(
        scenario="fifteen_minute_native",
        length_points=1440,
        noise_std=0.2,
        integer_rounding=True,
        seed=202,
    )
    assert meta["true_period"] == 15
    res = infer_native_grid_series(trace, stage1b_config)
    assert res.period_inferred == 15
    assert res.confidence == "HIGH_CONFIDENCE"
    assert res.is_native_inferred is True
    assert res.reconstruction_residual_mean < 0.25
    # For true 15-minute data, intermediate 5-minute bends must be zero or near-zero
    assert res.intermediate_5min_bends_count <= 2


def test_native_grid_negative_control_rejection(stage1b_config):
    """Verify that continuous 1-minute physiological data is rejected (NO_RELIABLE_LATTICE)."""
    trace, meta = generate_synthetic_trace(
        scenario="continuous_one_minute_negative_control",
        length_points=1440,
        noise_std=0.2,
        integer_rounding=True,
        seed=303,
    )
    assert meta["true_period"] == 1
    res = infer_native_grid_series(trace, stage1b_config)
    assert res.is_native_inferred is False
    assert res.confidence == "NO_RELIABLE_LATTICE"
    assert res.period_inferred is None


def test_real_cohort_inference_results(stage1b_results):
    """Verify cohort-level real inference outcomes in stage1b_results.json."""
    grid = stage1b_results["real_native_grid_inference"]

    # Libre: 45/45 high confidence 15-min
    libre = grid["libre"]
    assert libre["high_confidence_count"] == 45
    assert libre["period_inferred"] == 15
    assert libre["reconstruction_residual_mean"] < 0.01

    # Dexcom: 44/45 high confidence 5-min
    dexcom = grid["dexcom"]
    assert dexcom["high_confidence_count"] == 44
    assert dexcom["ambiguous_count"] == 1
    assert dexcom["period_inferred"] == 5
    assert dexcom["reconstruction_residual_mean"] < 0.02


def test_config_hash_consistency(stage1b_results):
    """Verify that the frozen configuration hash is recorded and matches."""
    expected_hash = "8de86ba3edc17f21769f59dd608300f88c283a06f23beba46f90718132dbcdb3"
    assert stage1b_results["frozen_config_hash"] == expected_hash
