"""Cross-validation split generation and verification for Stage 2."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.model_selection import StratifiedKFold


@dataclass(frozen=True)
class CVSplit:
    """A single participant-disjoint cross-validation split."""

    repeat_idx: int
    seed: int
    fold_idx: int
    train_pids: list[str]
    test_pids: list[str]


@dataclass(frozen=True)
class InnerCVSplit:
    """An inner participant-grouped split within a training fold."""

    inner_fold_idx: int
    inner_train_pids: list[str]
    inner_val_pids: list[str]


def generate_repeated_cv_splits(
    participants: list[str],
    diag_groups: list[str],
    seeds: list[int] | None = None,
    n_splits: int = 5,
) -> list[CVSplit]:
    """Generate and verify repeated participant-disjoint stratified CV splits.

    Args:
        participants: Sorted list of 45 unique participant IDs.
        diag_groups: Aligned list of clinical diagnostic group labels.
        seeds: List of random seeds for the repetitions (default: seeds 42..51).
        n_splits: Number of folds per repetition (default: 5).

    Returns:
        List of CVSplit objects (exactly len(seeds) * n_splits splits total).
    """
    if seeds is None:
        seeds = [42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

    splits: list[CVSplit] = []
    p_set = set(participants)

    for r_idx, seed in enumerate(seeds):
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        fold_idx = 0
        for tr_idx, te_idx in skf.split(participants, diag_groups):
            tr_pids = [participants[i] for i in tr_idx]
            te_pids = [participants[i] for i in te_idx]

            # Invariance checks
            assert len(set(tr_pids).intersection(set(te_pids))) == 0, (
                f"Data leakage detected in repeat {r_idx}, fold {fold_idx}"
            )
            assert set(tr_pids).union(set(te_pids)) == p_set, (
                f"Incomplete partition in repeat {r_idx}, fold {fold_idx}"
            )

            splits.append(
                CVSplit(
                    repeat_idx=r_idx,
                    seed=seed,
                    fold_idx=fold_idx,
                    train_pids=tr_pids,
                    test_pids=te_pids,
                )
            )
            fold_idx += 1

    return splits


def generate_inner_cv_splits(
    train_pids: list[str],
    pid_to_group: dict[str, str],
    inner_seed: int,
    n_splits: int = 4,
) -> list[InnerCVSplit]:
    """Generate inner participant-grouped stratified splits from an outer training set.

    Args:
        train_pids: List of participant IDs in outer training fold (typically 36).
        pid_to_group: Mapping from participant ID to diagnostic group string.
        inner_seed: Random seed for inner splitting.
        n_splits: Number of inner splits (default: 4).

    Returns:
        List of InnerCVSplit objects.
    """
    sorted_pids = sorted(train_pids)
    groups = [pid_to_group.get(pid, "unknown") for pid in sorted_pids]

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=inner_seed)
    inner_splits: list[InnerCVSplit] = []

    for f_idx, (in_tr_idx, in_val_idx) in enumerate(skf.split(sorted_pids, groups)):
        in_tr_pids = [sorted_pids[i] for i in in_tr_idx]
        in_val_pids = [sorted_pids[i] for i in in_val_idx]
        inner_splits.append(
            InnerCVSplit(
                inner_fold_idx=f_idx,
                inner_train_pids=in_tr_pids,
                inner_val_pids=in_val_pids,
            )
        )

    return inner_splits
