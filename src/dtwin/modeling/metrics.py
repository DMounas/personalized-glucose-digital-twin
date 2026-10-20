"""Evaluation metrics, cross-validation aggregation, and participant bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ParticipantMetricRecord:
    """Consolidated metric record for a single participant."""

    participant_id: str
    diag_group: str
    n_origins: int
    mean_rmse: float
    mean_mae: float
    mean_skill: float
    rmse_per_repeat: list[float]
    mae_per_repeat: list[float]
    skill_per_repeat: list[float]


def compute_participant_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_base: np.ndarray,
    is_persistence: bool = False,
) -> tuple[float, float, float]:
    """Compute participant RMSE, MAE, and skill score against guarded persistence.

    Args:
        y_true: Ground truth target glucose values.
        y_pred: Model predicted glucose values.
        y_base: Guarded persistence baseline values (y(t-5)).
        is_persistence: If True, skill is strictly set to 0.0 by definition.

    Returns:
        Tuple of (rmse, mae, skill).
    """
    n = len(y_true)
    if n == 0:
        return 0.0, 0.0, 0.0

    diff = y_true - y_pred
    rmse = float(np.sqrt(np.mean(diff**2)))
    mae = float(np.mean(np.abs(diff)))

    if is_persistence:
        skill = 0.0
    else:
        diff_base = y_true - y_base
        rmse_base = float(np.sqrt(np.mean(diff_base**2)))
        if rmse_base > 1e-9:
            skill = float(1.0 - (rmse / rmse_base))
        else:
            skill = 0.0

    return rmse, mae, skill


def consolidate_repeated_metrics(
    repeat_participant_metrics: list[dict[str, dict[str, Any]]],
) -> dict[str, ParticipantMetricRecord]:
    """Consolidate participant metrics across the 10 cross-validation repetitions.

    Args:
        repeat_participant_metrics: List of 10 dicts (one per repetition),
            mapping participant_id -> {'diag_group', 'n_origins', 'rmse', 'mae', 'skill'}.

    Returns:
        Mapping of participant_id -> ParticipantMetricRecord.
    """
    pids = sorted(repeat_participant_metrics[0].keys())
    assert len(repeat_participant_metrics) == 10, "Expected exactly 10 CV repetitions"

    consolidated: dict[str, ParticipantMetricRecord] = {}

    for pid in pids:
        group = str(repeat_participant_metrics[0][pid]["diag_group"])
        n_origins = int(repeat_participant_metrics[0][pid]["n_origins"])

        rmses = [float(rep[pid]["rmse"]) for rep in repeat_participant_metrics]
        maes = [float(rep[pid]["mae"]) for rep in repeat_participant_metrics]
        skills = [float(rep[pid]["skill"]) for rep in repeat_participant_metrics]

        mean_rmse = float(np.mean(rmses))
        mean_mae = float(np.mean(maes))
        mean_skill = float(np.mean(skills))

        consolidated[pid] = ParticipantMetricRecord(
            participant_id=pid,
            diag_group=group,
            n_origins=n_origins,
            mean_rmse=mean_rmse,
            mean_mae=mean_mae,
            mean_skill=mean_skill,
            rmse_per_repeat=rmses,
            mae_per_repeat=maes,
            skill_per_repeat=skills,
        )

    return consolidated


def compute_cohort_summary_and_bootstrap(
    consolidated_participants: dict[str, ParticipantMetricRecord],
    n_bootstrap: int = 2000,
    bootstrap_seed: int = 42,
) -> dict[str, Any]:
    """Compute cohort headline metrics and 95% participant-bootstrap confidence intervals.

    CRITICAL METHODOLOGICAL INVARIANCE:
    Resampling is strictly conducted over the 45 INDEPENDENT PARTICIPANTS,
    never over the 450 participant-repeat records, avoiding artificial degrees-of-freedom inflation.

    Args:
        consolidated_participants: Mapping of participant_id -> ParticipantMetricRecord (45 entries).
        n_bootstrap: Number of bootstrap iterations (default: 2,000).
        bootstrap_seed: Random seed for bootstrap reproducibility (default: 42).

    Returns:
        Dictionary containing cohort headline summaries and bootstrap confidence intervals.
    """
    pids = sorted(consolidated_participants.keys())
    n_participants = len(pids)
    assert n_participants == 45, f"Expected 45 participants, found {n_participants}"

    skills = np.array([consolidated_participants[p].mean_skill for p in pids], dtype=np.float64)
    rmses = np.array([consolidated_participants[p].mean_rmse for p in pids], dtype=np.float64)
    maes = np.array([consolidated_participants[p].mean_mae for p in pids], dtype=np.float64)
    groups = [consolidated_participants[p].diag_group for p in pids]

    cohort_mean_skill = float(np.mean(skills))
    cohort_median_skill = float(np.median(skills))
    cohort_std_skill = float(np.std(skills, ddof=1))

    improved_mask = skills > 0.0
    n_improved = int(np.sum(improved_mask))
    fraction_improved = float(n_improved / n_participants)

    cohort_mean_rmse = float(np.mean(rmses))
    cohort_median_rmse = float(np.median(rmses))
    cohort_mean_mae = float(np.mean(maes))
    cohort_median_mae = float(np.median(maes))

    # Participant bootstrap: resample 45 participants with replacement
    rng = np.random.default_rng(bootstrap_seed)
    boot_indices = rng.integers(0, n_participants, size=(n_bootstrap, n_participants))

    boot_mean_skills = np.mean(skills[boot_indices], axis=1)
    boot_median_skills = np.median(skills[boot_indices], axis=1)
    boot_mean_rmses = np.mean(rmses[boot_indices], axis=1)
    boot_mean_maes = np.mean(maes[boot_indices], axis=1)

    ci_mean_skill = [
        float(np.percentile(boot_mean_skills, 2.5)),
        float(np.percentile(boot_mean_skills, 97.5)),
    ]
    ci_median_skill = [
        float(np.percentile(boot_median_skills, 2.5)),
        float(np.percentile(boot_median_skills, 97.5)),
    ]
    ci_mean_rmse = [
        float(np.percentile(boot_mean_rmses, 2.5)),
        float(np.percentile(boot_mean_rmses, 97.5)),
    ]
    ci_mean_mae = [
        float(np.percentile(boot_mean_maes, 2.5)),
        float(np.percentile(boot_mean_maes, 97.5)),
    ]

    # Subgroup breakdowns
    subgroup_summaries: dict[str, Any] = {}
    for grp in ["normal", "prediabetes", "diabetes"]:
        grp_mask = np.array([g == grp for g in groups], dtype=bool)
        n_grp = int(np.sum(grp_mask))
        if n_grp > 0:
            grp_skills = skills[grp_mask]
            grp_rmses = rmses[grp_mask]
            grp_maes = maes[grp_mask]
            subgroup_summaries[grp] = {
                "n_participants": n_grp,
                "mean_skill": float(np.mean(grp_skills)),
                "median_skill": float(np.median(grp_skills)),
                "fraction_improved": float(np.sum(grp_skills > 0.0) / n_grp),
                "mean_rmse": float(np.mean(grp_rmses)),
                "median_rmse": float(np.median(grp_rmses)),
                "mean_mae": float(np.mean(grp_maes)),
                "median_mae": float(np.median(grp_maes)),
            }

    return {
        "cohort_participants": n_participants,
        "headline_skill": {
            "mean": cohort_mean_skill,
            "median": cohort_median_skill,
            "std": cohort_std_skill,
            "ci_95_mean": ci_mean_skill,
            "ci_95_median": ci_median_skill,
            "fraction_improved": fraction_improved,
            "n_participants_improved": n_improved,
        },
        "headline_rmse": {
            "mean": cohort_mean_rmse,
            "median": cohort_median_rmse,
            "ci_95_mean": ci_mean_rmse,
        },
        "headline_mae": {
            "mean": cohort_mean_mae,
            "median": cohort_median_mae,
            "ci_95_mean": ci_mean_mae,
        },
        "subgroups": subgroup_summaries,
        "bootstrap_metadata": {
            "resampling_unit": "45 independent participants",
            "iterations": n_bootstrap,
            "seed": bootstrap_seed,
            "prohibited_pooling_checked": True,
        },
    }
