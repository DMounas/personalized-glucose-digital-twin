"""Unit tests for aggregate feasibility calculation module."""

from __future__ import annotations

from pathlib import Path

from dtwin.analysis.aggregate_feasibility import load_diagnostic_group_mapping


def test_load_diagnostic_group_mapping_counts_and_boundaries():
    """Verify participant mapping counts and boundary HbA1c classification."""
    bio_path = Path("data/cgmacros/CGMacros/bio.csv")
    assert bio_path.exists()

    mapping = load_diagnostic_group_mapping(bio_path)
    assert len(mapping) == 45

    groups = list(mapping.values())
    norm_count = groups.count("normal")
    pred_count = groups.count("prediabetes")
    diab_count = groups.count("diabetes")

    assert norm_count == 15
    assert pred_count == 16
    assert diab_count == 14

    # Boundary participant verifications:
    # CGMacros-001: 5.4 -> normal
    assert mapping["CGMacros-001"] == "normal"
    # CGMacros-003: 6.5 -> diabetes (>= 6.5)
    assert mapping["CGMacros-003"] == "diabetes"
    # CGMacros-009: 5.7 -> prediabetes (>= 5.7)
    assert mapping["CGMacros-009"] == "prediabetes"
    # CGMacros-020: 6.4 -> prediabetes (<= 6.4)
    assert mapping["CGMacros-020"] == "prediabetes"
    # CGMacros-035: 8.5 -> diabetes
    assert mapping["CGMacros-035"] == "diabetes"


def test_synthetic_excursion_entry_and_release_conventions_1min():
    """Verify excursion entry and release semantics at 1-minute spacing under both conventions:

    Convention B (Interval-Bin Duration - Primary):
    - Entry: 15 points (15 min exposure duration: N * 1m = 15m)
    - Release: 10 points (10 min exposure duration: M * 1m = 10m)

    Convention A (Point-to-Point Elapsed Duration - Sensitivity):
    - Entry: 16 points (15 min elapsed duration: t_15 - t_0 = 15m)
    - Release: 11 points (10 min elapsed duration: t_10 - t_0 = 10m)
    """
    import numpy as np

    from dtwin.timeaxis import detect_excursion_episodes_run_bounded

    # Convention B:
    # 14 points hyper (>180): not an episode
    t_14 = np.array([120.0] * 10 + [200.0] * 14 + [120.0] * 20)
    res_b_14 = detect_excursion_episodes_run_bounded(
        t_14, threshold=180.0, min_persistence=15, min_release=10, hysteresis_margin=5.0
    )
    assert res_b_14.total_episodes == 0

    # 15 points hyper: triggers episode (duration=15)
    t_15 = np.array([120.0] * 10 + [200.0] * 15 + [120.0] * 20)
    res_b_15 = detect_excursion_episodes_run_bounded(
        t_15, threshold=180.0, min_persistence=15, min_release=10, hysteresis_margin=5.0
    )
    assert res_b_15.total_episodes == 1
    assert res_b_15.boundary_censored == 0
    assert res_b_15.durations == [15]

    # Convention B Release check: 9 points <= 175 does not release, 10 points releases
    t_rel_9 = np.array([120.0] * 5 + [200.0] * 15 + [170.0] * 9 + [200.0] * 10)
    res_rel_9 = detect_excursion_episodes_run_bounded(
        t_rel_9, threshold=180.0, min_persistence=15, min_release=10, hysteresis_margin=5.0
    )
    # Episode remained active continuously (never released)
    assert res_rel_9.total_episodes == 1
    assert res_rel_9.boundary_censored == 1  # active at end

    t_rel_10 = np.array([120.0] * 5 + [200.0] * 15 + [170.0] * 10 + [200.0] * 10)
    res_rel_10 = detect_excursion_episodes_run_bounded(
        t_rel_10, threshold=180.0, min_persistence=15, min_release=10, hysteresis_margin=5.0
    )
    # Episode released at point 10, then a second episode triggered after another 15
    assert res_rel_10.total_episodes == 1  # 2nd had only 10 points so total is 1
    assert res_rel_10.boundary_censored == 0  # 1st episode released cleanly!
    assert res_rel_10.durations == [15]

    # Convention A:
    # 15 points hyper: does NOT trigger under min_persistence=16 (14 min elapsed)
    res_a_15 = detect_excursion_episodes_run_bounded(
        t_15, threshold=180.0, min_persistence=16, min_release=11, hysteresis_margin=5.0
    )
    assert res_a_15.total_episodes == 0

    # 16 points hyper: triggers episode under min_persistence=16 (15 min elapsed)
    t_16 = np.array([120.0] * 10 + [200.0] * 16 + [120.0] * 20)
    res_a_16 = detect_excursion_episodes_run_bounded(
        t_16, threshold=180.0, min_persistence=16, min_release=11, hysteresis_margin=5.0
    )
    assert res_a_16.total_episodes == 1
    assert res_a_16.boundary_censored == 0
    assert res_a_16.durations == [16]


def test_synthetic_excursion_entry_and_release_conventions_5min():
    """Verify excursion entry and release semantics at 5-minute spacing under both conventions:

    Convention B (Interval-Bin Duration - Primary):
    - Entry: 3 points (15 min exposure duration: 3 * 5m = 15m)
    - Release: 2 points (10 min exposure duration: 2 * 5m = 10m)

    Convention A (Point-to-Point Elapsed Duration - Sensitivity):
    - Entry: 4 points (15 min elapsed duration: t_3 - t_0 = 15m)
    - Release: 3 points (10 min elapsed duration: t_2 - t_0 = 10m)
    """
    import numpy as np

    from dtwin.timeaxis import detect_excursion_episodes_run_bounded

    # Convention B:
    # 2 points (10m exposure): not an episode
    t5_2 = np.array([120.0] * 3 + [200.0] * 2 + [120.0] * 5)
    res_b_2 = detect_excursion_episodes_run_bounded(
        t5_2, threshold=180.0, min_persistence=3, min_release=2, hysteresis_margin=5.0
    )
    assert res_b_2.total_episodes == 0

    # 3 points (15m exposure): triggers episode
    t5_3 = np.array([120.0] * 3 + [200.0] * 3 + [120.0] * 5)
    res_b_3 = detect_excursion_episodes_run_bounded(
        t5_3, threshold=180.0, min_persistence=3, min_release=2, hysteresis_margin=5.0
    )
    assert res_b_3.total_episodes == 1
    assert res_b_3.boundary_censored == 0
    assert res_b_3.durations == [3]

    # Convention B Release check: 1 point <= 175 does not release, 2 points releases
    t5_rel_1 = np.array([120.0] * 2 + [200.0] * 3 + [170.0] * 1 + [200.0] * 2)
    res_rel_1 = detect_excursion_episodes_run_bounded(
        t5_rel_1, threshold=180.0, min_persistence=3, min_release=2, hysteresis_margin=5.0
    )
    assert res_rel_1.total_episodes == 1
    assert res_rel_1.boundary_censored == 1  # not released

    t5_rel_2 = np.array([120.0] * 2 + [200.0] * 3 + [170.0] * 2 + [200.0] * 2)
    res_rel_2 = detect_excursion_episodes_run_bounded(
        t5_rel_2, threshold=180.0, min_persistence=3, min_release=2, hysteresis_margin=5.0
    )
    assert res_rel_2.total_episodes == 1
    assert res_rel_2.boundary_censored == 0  # cleanly released!
    assert res_rel_2.durations == [3]

    # Convention A:
    # 3 points (10m elapsed): does NOT trigger under min_persistence=4
    res_a_3 = detect_excursion_episodes_run_bounded(
        t5_3, threshold=180.0, min_persistence=4, min_release=3, hysteresis_margin=5.0
    )
    assert res_a_3.total_episodes == 0

    # 4 points (15m elapsed): triggers under min_persistence=4
    t5_4 = np.array([120.0] * 3 + [200.0] * 4 + [120.0] * 5)
    res_a_4 = detect_excursion_episodes_run_bounded(
        t5_4, threshold=180.0, min_persistence=4, min_release=3, hysteresis_margin=5.0
    )
    assert res_a_4.total_episodes == 1
    assert res_a_4.boundary_censored == 0
    assert res_a_4.durations == [4]
