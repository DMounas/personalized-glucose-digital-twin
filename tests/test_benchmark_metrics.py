"""Regression safeguard tests for benchmark metrics.

Verifies that canonical reports:
- docs/reports/stage2_baseline_metrics.json
- docs/reports/stage3_personalization_metrics.json
contain complete, mathematically sound, and internally consistent metrics
matching the preregistered Protocol v1.0.0 and Stage 3 Addendum v1.0.0.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGE2_METRICS_PATH = REPO_ROOT / "docs" / "reports" / "stage2_baseline_metrics.json"
STAGE3_METRICS_PATH = REPO_ROOT / "docs" / "reports" / "stage3_personalization_metrics.json"


@pytest.fixture(scope="module")
def stage2_metrics() -> dict:
    """Load canonical Stage 2 baseline metrics JSON."""
    assert STAGE2_METRICS_PATH.exists(), f"Missing {STAGE2_METRICS_PATH}"
    with open(STAGE2_METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def stage3_metrics() -> dict:
    """Load canonical Stage 3 personalization metrics JSON."""
    assert STAGE3_METRICS_PATH.exists(), f"Missing {STAGE3_METRICS_PATH}"
    with open(STAGE3_METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_stage2_horizons_and_participant_count(stage2_metrics: dict) -> None:
    """Verify horizons and participant invariants in Stage 2."""
    assert "horizons" in stage2_metrics
    for h in ["h30", "h60"]:
        assert h in stage2_metrics["horizons"]
        h_data = stage2_metrics["horizons"][h]
        assert h_data["total_participants"] == 45
        assert h_data["total_origins"] > 100_000


def test_stage2_canonical_rmse_values(stage2_metrics: dict) -> None:
    """Verify headline RMSE values for all 8 rungs match canonical reference."""
    h30 = stage2_metrics["horizons"]["h30"]
    h60 = stage2_metrics["horizons"]["h60"]

    # Invariant canonical values (mean RMSE within 0.01 tolerance)
    expected_h30 = {
        "rung0_guarded_persistence": 21.554,
        "rung1_damped_trend": 21.394,
        "rung2_ridge_regression": 19.866,
        "rung3_activity_ridge": 19.849,
        "rung4_meal_ridge": 19.191,
        "rung4_nomacros_ablation": 19.181,
        "rung5_baseline_covariates": 18.853,
        "rung6_hist_gradient_boosting": 19.146,
    }

    expected_h60 = {
        "rung0_guarded_persistence": 29.321,
        "rung1_damped_trend": 29.332,
        "rung2_ridge_regression": 26.966,
        "rung3_activity_ridge": 26.974,
        "rung4_meal_ridge": 27.032,
        "rung4_nomacros_ablation": 26.257,
        "rung5_baseline_covariates": 25.452,
        "rung6_hist_gradient_boosting": 25.642,
    }

    for model_key, exp_rmse in expected_h30.items():
        assert model_key in h30, f"Missing {model_key} in h30"
        actual = h30[model_key]["summary"]["headline_rmse"]["mean"]
        assert actual == pytest.approx(exp_rmse, abs=0.01), (
            f"h30 {model_key} RMSE mismatch: actual={actual}, expected={exp_rmse}"
        )

    for model_key, exp_rmse in expected_h60.items():
        assert model_key in h60, f"Missing {model_key} in h60"
        actual = h60[model_key]["summary"]["headline_rmse"]["mean"]
        assert actual == pytest.approx(exp_rmse, abs=0.01), (
            f"h60 {model_key} RMSE mismatch: actual={actual}, expected={exp_rmse}"
        )


def test_stage2_bootstrap_confidence_intervals(stage2_metrics: dict) -> None:
    """Verify that 95% bootstrap CIs are monotonic and bracket the point estimate."""
    for h in ["h30", "h60"]:
        h_data = stage2_metrics["horizons"][h]
        for key, val in h_data.items():
            if isinstance(val, dict) and "summary" in val:
                summary = val["summary"]
                mean_rmse = summary["headline_rmse"]["mean"]
                ci = summary["headline_rmse"]["ci_95_mean"]
                assert len(ci) == 2
                assert ci[0] < mean_rmse < ci[1], (
                    f"{h} {key} CI [{ci[0]}, {ci[1]}] does not bracket mean {mean_rmse}"
                )


def test_stage3_canonical_personalization_values(stage3_metrics: dict) -> None:
    """Verify personalization paired difference RMSE values match canonical reference."""
    h30_win = stage3_metrics["horizons"]["h30"]["windows"]
    h60_win = stage3_metrics["horizons"]["h60"]["windows"]

    expected_deltas_h30 = {
        "window_2d": +0.289,
        "window_4d": -0.428,
        "window_6d": -0.825,
    }

    expected_deltas_h60 = {
        "window_2d": -0.025,
        "window_4d": -1.146,
        "window_6d": -1.811,
    }

    for w, exp_delta in expected_deltas_h30.items():
        actual = h30_win[w]["summary"]["paired_difference"]["mean_delta_rmse"]
        assert actual == pytest.approx(exp_delta, abs=0.01), (
            f"h30 {w} delta mismatch: actual={actual}, expected={exp_delta}"
        )

    for w, exp_delta in expected_deltas_h60.items():
        actual = h60_win[w]["summary"]["paired_difference"]["mean_delta_rmse"]
        assert actual == pytest.approx(exp_delta, abs=0.01), (
            f"h60 {w} delta mismatch: actual={actual}, expected={exp_delta}"
        )


def test_stage3_statistical_significance_properties(stage3_metrics: dict) -> None:
    """Verify statistical significance claims against bootstrap confidence intervals.

    Crucial scientific verification:
    - At +30 min: All three adaptation windows (2d, 4d, 6d) have paired delta CIs that
      bracket zero (i.e. lower < 0 < upper). None may be portrayed as statistically significant.
    - At +60 min: 4-day and 6-day adaptation windows strictly exclude zero (upper < 0).
      2-day window brackets zero.
    """
    h30_win = stage3_metrics["horizons"]["h30"]["windows"]
    h60_win = stage3_metrics["horizons"]["h60"]["windows"]

    # All +30m windows MUST span zero
    for w in ["window_2d", "window_4d", "window_6d"]:
        ci = h30_win[w]["summary"]["paired_difference"]["ci_95_mean_delta_rmse"]
        assert ci[0] < 0 < ci[1], (
            f"h30 {w} CI [{ci[0]}, {ci[1]}] should cross zero (non-significant)"
        )

    # +60m 2d must span zero
    ci_2d_60 = h60_win["window_2d"]["summary"]["paired_difference"]["ci_95_mean_delta_rmse"]
    assert ci_2d_60[0] < 0 < ci_2d_60[1], (
        f"h60 window_2d CI [{ci_2d_60[0]}, {ci_2d_60[1]}] should cross zero"
    )

    # +60m 4d and 6d must strictly exclude zero (upper < 0)
    for w in ["window_4d", "window_6d"]:
        ci = h60_win[w]["summary"]["paired_difference"]["ci_95_mean_delta_rmse"]
        assert ci[1] < 0.0, (
            f"h60 {w} CI [{ci[0]}, {ci[1]}] must strictly exclude zero (statistically significant)"
        )


def test_stage3_matched_baseline_consistency(stage3_metrics: dict) -> None:
    """Verify matched global baseline RMSE decreases monotonically with evaluation origins."""
    for h in ["h30", "h60"]:
        h_win = stage3_metrics["horizons"][h]["windows"]
        for w in ["window_2d", "window_4d", "window_6d"]:
            summary = h_win[w]["summary"]
            mg = summary["matched_global"]["mean_rmse"]
            pers = summary["personalized"]["mean_rmse"]
            delta = summary["paired_difference"]["mean_delta_rmse"]
            # delta = personalized - matched_global
            assert (pers - mg) == pytest.approx(delta, abs=1e-5), (
                f"{h} {w}: delta {delta} != pers ({pers}) - matched ({mg})"
            )


def test_asset_generation_validation_safeguard(stage2_metrics: dict, stage3_metrics: dict) -> None:
    """Verify that validate_metrics from generate_readme_assets passes on canonical metrics and catches corruption."""
    import copy
    import sys

    # Add scripts to sys.path
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from generate_readme_assets import validate_metrics

    # Must pass on canonical data
    validate_metrics(stage2_metrics, stage3_metrics)

    # Must fail when an invariant is corrupted
    corrupt_s2 = copy.deepcopy(stage2_metrics)
    corrupt_s2["horizons"]["h30"]["rung0_guarded_persistence"]["summary"]["headline_rmse"][
        "mean"
    ] = 99.9
    with pytest.raises(ValueError, match="Validation failure for Rung 0 Persistence h30"):
        validate_metrics(corrupt_s2, stage3_metrics)

    # Must fail when significance property is violated
    corrupt_s3 = copy.deepcopy(stage3_metrics)
    corrupt_s3["horizons"]["h30"]["windows"]["window_6d"]["summary"]["paired_difference"][
        "ci_95_mean_delta_rmse"
    ] = [-2.0, -1.0]
    with pytest.raises(ValueError, match="does not cross zero"):
        validate_metrics(stage2_metrics, corrupt_s3)
