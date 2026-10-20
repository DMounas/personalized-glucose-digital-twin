"""Unit and regression tests for Stage 2 baseline modeling (Rungs 0 & 1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from dtwin.modeling.baselines import (
    predict_damped_trend,
    predict_guarded_persistence,
    tune_damped_trend_gamma,
)
from dtwin.modeling.cv import generate_inner_cv_splits, generate_repeated_cv_splits
from dtwin.modeling.dataset import ParticipantOrigins
from dtwin.modeling.manifest import calculate_sha256, get_git_commit_hash
from dtwin.modeling.metrics import (
    compute_cohort_summary_and_bootstrap,
    compute_participant_metrics,
    consolidate_repeated_metrics,
)


def test_manifest_hashing_and_git_commit() -> None:
    """Verify hash calculation and git commit retrieval."""
    root = Path(__file__).resolve().parent.parent
    protocol_path = root / "docs" / "STAGE2_PROTOCOL_DRAFT.md"
    config_path = root / "configs" / "stage1b.yaml"

    h_proto = calculate_sha256(protocol_path)
    h_cfg = calculate_sha256(config_path)

    assert len(h_proto) == 64
    assert len(h_cfg) == 64
    assert h_cfg == "cf2763408891feb97c67dd5184ad4674dd2c98a736922ad322c8b66bc11bd467"

    git_hash = get_git_commit_hash(root)
    assert len(git_hash) == 40


def test_repeated_cv_splits_properties() -> None:
    """Verify participant-disjoint stratification and zero leakage across 10 repeats."""
    participants = [f"CGMacros-{i:03d}" for i in range(1, 46)]
    diag_groups = ["normal"] * 15 + ["prediabetes"] * 16 + ["diabetes"] * 14
    seeds = [42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

    splits = generate_repeated_cv_splits(participants, diag_groups, seeds=seeds, n_splits=5)
    assert len(splits) == 50

    p_set = set(participants)
    pid_to_group = dict(zip(participants, diag_groups, strict=True))

    for sp in splits:
        assert len(sp.test_pids) == 9
        assert len(sp.train_pids) == 36
        assert set(sp.train_pids).intersection(set(sp.test_pids)) == set()
        assert set(sp.train_pids).union(set(sp.test_pids)) == p_set

        # Verify stratification in each fold: 3 normal, 3-4 prediabetes, 2-3 diabetes
        test_groups = [pid_to_group[p] for p in sp.test_pids]
        assert test_groups.count("normal") == 3
        assert test_groups.count("prediabetes") in (3, 4)
        assert test_groups.count("diabetes") in (2, 3)

        # Test inner 4-fold split from outer training set
        inner_splits = generate_inner_cv_splits(
            sp.train_pids, pid_to_group, inner_seed=sp.seed, n_splits=4
        )
        assert len(inner_splits) == 4
        in_p_set = set(sp.train_pids)
        for in_sp in inner_splits:
            assert len(in_sp.inner_val_pids) == 9
            assert len(in_sp.inner_train_pids) == 27
            assert set(in_sp.inner_train_pids).intersection(set(in_sp.inner_val_pids)) == set()
            assert set(in_sp.inner_train_pids).union(set(in_sp.inner_val_pids)) == in_p_set


def test_baseline_predictions_mathematics() -> None:
    """Verify mathematical definitions of Rung 0 and Rung 1."""
    y_base = np.array([100.0, 120.0, 140.0])
    roc = np.array([0.5, -0.2, 0.0])

    # Rung 0: Guarded Persistence
    p_r0 = predict_guarded_persistence(y_base)
    np.testing.assert_array_equal(p_r0, y_base)

    # Rung 1 with gamma = 0.0 must be identical to persistence
    p_r1_zero = predict_damped_trend(y_base, roc, horizon_minutes=30, gamma=0.0)
    np.testing.assert_array_equal(p_r1_zero, y_base)

    # Rung 1 with gamma = 0.2 at h = 30
    # Expected: y_base + 0.2 * roc * 30 = y_base + 6 * roc
    p_r1_30 = predict_damped_trend(y_base, roc, horizon_minutes=30, gamma=0.2)
    expected = y_base + 6.0 * roc
    np.testing.assert_allclose(p_r1_30, expected)


def test_metrics_persistence_zero_skill() -> None:
    """Verify that guarded persistence has strictly 0.0 skill against itself."""
    y_true = np.array([110.0, 130.0, 150.0])
    y_base = np.array([100.0, 125.0, 140.0])

    rmse, mae, skill = compute_participant_metrics(y_true, y_base, y_base, is_persistence=True)
    assert rmse > 0.0
    assert mae > 0.0
    assert skill == 0.0


def test_damped_trend_gamma_tuning_synthetic() -> None:
    """Verify that inner CV gamma tuning correctly identifies optimal damping."""
    rng = np.random.default_rng(42)
    pids = [f"P{i:02d}" for i in range(36)]
    pid_to_group = {p: "normal" for p in pids}

    # Generate synthetic origins where true gamma is exactly 0.20
    dataset: dict[str, ParticipantOrigins] = {}
    true_gamma = 0.20
    h = 30

    for p in pids:
        n = 100
        y_b = rng.normal(120.0, 20.0, size=n)
        r = rng.normal(0.0, 0.5, size=n)
        noise = rng.normal(0.0, 2.0, size=n)
        target = y_b + true_gamma * r * h + noise

        dataset[p] = ParticipantOrigins(
            participant_id=p,
            diag_group="normal",
            horizon_minutes=h,
            timestamps=[f"2026-01-01 {i:04d}" for i in range(n)],
            y_base=y_b,
            roc=r,
            target=target,
            elapsed_minutes=np.arange(n) * 5,
        )

    best_gamma, diag = tune_damped_trend_gamma(
        dataset=dataset,
        train_pids=pids,
        pid_to_group=pid_to_group,
        horizon_minutes=h,
        seed=42,
    )

    # Must be very close to 0.20
    assert abs(best_gamma - true_gamma) <= 0.03
    assert diag["best_inner_rmse"] < diag["persistence_inner_rmse"]


def test_bootstrap_45_participants_unit() -> None:
    """Verify that cohort summary and bootstrap resample 45 participants."""
    repeat_metrics: list[dict[str, dict[str, Any]]] = []
    pids = [f"CGMacros-{i:03d}" for i in range(1, 46)]

    for _ in range(10):
        rep = {}
        for idx, p in enumerate(pids):
            grp = "normal" if idx < 15 else ("prediabetes" if idx < 31 else "diabetes")
            rep[p] = {
                "diag_group": grp,
                "n_origins": 1000,
                "rmse": 15.0 + (idx % 5),
                "mae": 10.0 + (idx % 3),
                "skill": 0.05 + 0.001 * idx,
            }
        repeat_metrics.append(rep)

    consolidated = consolidate_repeated_metrics(repeat_metrics)
    assert len(consolidated) == 45

    summary = compute_cohort_summary_and_bootstrap(consolidated, n_bootstrap=100, bootstrap_seed=42)
    assert summary["cohort_participants"] == 45
    assert summary["bootstrap_metadata"]["resampling_unit"] == "45 independent participants"
    assert summary["headline_skill"]["mean"] > 0.0
    assert summary["headline_skill"]["fraction_improved"] == 1.0
