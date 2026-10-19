"""Unit and regression tests for Stage 1B Dual-Sensor Agreement, Apparent Lag, and Tasks."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dtwin.analysis.dual_sensor import compute_repeated_measures_bland_altman
from dtwin.analysis.tasks import count_excursion_episodes


@pytest.fixture(scope="module")
def stage1b_results() -> dict:
    results_path = Path("docs/reports/stage1b_results.json")
    assert results_path.exists(), "stage1b_results.json must exist"
    with open(results_path, encoding="utf-8") as f:
        return json.load(f)


def test_bland_altman_repeated_measures_synthetic():
    """Verify Bland-Altman repeated measures calculation on synthetic multi-participant pairs."""
    rng = np.random.default_rng(42)
    records = []
    # 5 participants, each with 200 pairs, true mean bias = -20 mg/dL
    for p in range(5):
        pid = f"P{p:02d}"
        p_bias = rng.normal(-20.0, 5.0)
        dex = rng.uniform(80.0, 180.0, 200)
        lib = dex + p_bias + rng.normal(0, 3.0, 200)
        for dex_val, lib_val in zip(dex, lib, strict=False):
            records.append(
                {
                    "participant_id": pid,
                    "dexcom": dex_val,
                    "libre": lib_val,
                    "diff": lib_val - dex_val,
                    "mean": (lib_val + dex_val) / 2.0,
                }
            )
    df_syn = pd.DataFrame(records)
    res = compute_repeated_measures_bland_altman(df_syn, bootstrap_replicates=100, seed=42)
    assert res.n_participants == 5
    assert res.n_paired_points == 1000
    assert -25.0 < res.mean_difference < -15.0
    assert res.sd_repeated_measures > 0
    assert res.limits_of_agreement_lower < res.mean_difference < res.limits_of_agreement_upper
    assert res.bootstrap_mean_ci_95[0] <= res.mean_difference <= res.bootstrap_mean_ci_95[1]


def test_dual_sensor_agreement_in_results(stage1b_results):
    """Verify dual-sensor agreement statistics in stage1b_results.json."""
    agreement = stage1b_results["dual_sensor_agreement"]
    assert agreement["difference_convention"] == "libre_minus_dexcom"

    # Set B (common grid)
    b = agreement["set_b_common_grid"]
    assert b["n_participants"] == 45
    assert b["n_paired_points"] == 629605
    assert b["mean_difference"] == pytest.approx(-31.95, abs=0.1)
    assert b["sd_repeated_measures"] == pytest.approx(24.59, abs=0.1)
    assert b["limits_of_agreement_lower"] == pytest.approx(-80.14, abs=0.2)
    assert b["limits_of_agreement_upper"] == pytest.approx(16.24, abs=0.2)
    assert b["bootstrap_mean_ci_95"][0] < -25.0
    assert b["bootstrap_mean_ci_95"][1] > -38.0

    # Set A (inferred native pairs)
    a = agreement["set_a_paired_native"]
    assert a["n_participants"] == 39
    assert a["n_paired_points"] == 37030
    assert a["mean_difference"] == pytest.approx(-30.45, abs=0.2)
    assert a["pearson_r"] > 0.80


def test_stratified_bland_altman_results(stage1b_results):
    """Verify that stratified agreement statistics reflect clinical dispersion patterns."""
    strata = stage1b_results["dual_sensor_agreement"]["stratified_by_hba1c"]
    assert len(strata) == 3
    assert strata["normal"]["participants_count"] == 15
    assert strata["prediabetes"]["participants_count"] == 16
    assert strata["diabetes"]["participants_count"] == 14

    # All strata should confirm negative mean difference (Libre reads lower than Dexcom)
    for grp in ["normal", "prediabetes", "diabetes"]:
        assert strata[grp]["mean_difference_mg_dl"] < -20.0

    # Glucose range strata: hyperglycemia should have wider SD
    glu_strata = stage1b_results["dual_sensor_agreement"]["stratified_by_glucose_range"]
    assert (
        glu_strata["hyperglycemia_gt_180"]["sd_difference_mg_dl"]
        > glu_strata["target_range_70_180"]["sd_difference_mg_dl"]
    )


def test_apparent_lag_results(stage1b_results):
    """Verify apparent lag summary in stage1b_results.json."""
    lag = stage1b_results["dual_sensor_agreement"]["apparent_lag"]
    assert lag["participants_evaluated"] > 40
    # Negative lag indicates Libre lags Dexcom
    assert lag["median_lag_minutes"] == pytest.approx(-5.0, abs=0.5)


def test_fingerstick_analysis_omission(stage1b_results):
    """Verify fingerstick analysis is declared not defensible and omitted."""
    fs = stage1b_results["fingerstick_analysis"]
    assert fs["status"] == "ALIGNMENT_NOT_DEFENSIBLE"
    assert "date" in fs["rationale"].lower()


def test_excursion_episode_counting_logic():
    """Verify excursion episode logic enforces persistence and separation requirements."""
    # Series with a 10-minute spike (>180) -> should NOT count as episode (min persistence 15)
    s1 = np.array([120] * 20 + [200] * 10 + [120] * 30)
    assert count_excursion_episodes(s1, threshold=180.0, kind="hyper", min_persistence=15) == 0

    # Series with a 20-minute spike (>180) -> should count as 1 episode
    s2 = np.array([120] * 20 + [200] * 20 + [120] * 30)
    assert count_excursion_episodes(s2, threshold=180.0, kind="hyper", min_persistence=15) == 1

    # Series with two spikes separated by only 10 minutes -> should count as 1 single episode (min separation 30)
    s3 = np.array([120] * 20 + [200] * 20 + [120] * 10 + [200] * 20 + [120] * 40)
    assert (
        count_excursion_episodes(
            s3, threshold=180.0, kind="hyper", min_persistence=15, min_separation=30
        )
        == 1
    )

    # Series with two spikes separated by 40 minutes -> should count as 2 episodes
    s4 = np.array([120] * 20 + [200] * 20 + [120] * 40 + [200] * 20 + [120] * 40)
    assert (
        count_excursion_episodes(
            s4, threshold=180.0, kind="hyper", min_persistence=15, min_separation=30
        )
        == 2
    )


def test_candidate_task_decisions(stage1b_results):
    """Verify task decisions in stage1b_results.json adhere to protocol."""
    dec = stage1b_results["modeling_readiness_decisions"]
    assert dec["t1_glucose_regression_30_60min"] == "CONDITIONAL_GO"
    assert dec["t2_excursion_event_prediction"] == "CONDITIONAL_GO"
    assert dec["t3_postprandial_meal_response"] == "GO"
    assert "Dexcom" in dec["primary_device_recommendation"]
