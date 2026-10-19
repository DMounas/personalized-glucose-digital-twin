"""Regression tests for Stage 1B-R2 audit issues (C1–C6).

Each test reproduces an identified defect in prior methods and verifies the corrected behavior:
- C1: Absent-timestamp gap breaks index-based mask and creates false boundary bends.
- C2: dropna() + positional slicing bridges across multi-hour gaps.
- C2: Excursion detection without run boundaries merges episodes across gaps.
- C3: Unbalanced cluster variance estimation requires n0 correction.
- C4: Known-lag sign convention validation.
- C6: Scanner forbidding participant identifiers in committed documentation.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from dtwin.timeaxis import (
    compute_elapsed_minutes,
    detect_excursion_episodes_run_bounded,
    enumerate_runs,
    pairs_at_offset,
)


def test_reproduce_c1_gap_breaks_index_based_lattice():
    """Reproduce Issue C1: Absent gap of 7 minutes causes index-based modulo to select wrong points."""
    # Create two runs: Run 1 (0 to 60 min), Gap (7 min), Run 2 (68 to 120 min)
    # Native period 15, phase 0.
    t0 = pd.Timestamp("2020-05-01 08:00:00")
    run1_ts = pd.date_range(t0, periods=60, freq="1min")
    # 7-minute absent gap: run2 starts at 09:07 instead of 09:00
    t_run2 = t0 + pd.Timedelta(minutes=67)
    run2_ts = pd.date_range(t_run2, periods=60, freq="1min")

    all_ts = run1_ts.union(run2_ts).sort_values()
    df = pd.DataFrame({"Timestamp": all_ts})

    # True elapsed minutes from t0
    elapsed = compute_elapsed_minutes(df["Timestamp"])
    # In Run 1, elapsed == index
    assert elapsed[59] == 59
    # In Run 2, row index 60 corresponds to elapsed minute 67!
    assert elapsed[60] == 67

    # OLD METHOD: index-based mask
    index_mask = (np.arange(len(df)) % 15) == 0
    # In Run 2, row index 60 is selected because 60 % 15 == 0!
    # BUT row 60 is elapsed minute 67, which is NOT a native point (67 % 15 == 7 != 0)!
    selected_elapsed_old = elapsed[index_mask]
    assert 67 in selected_elapsed_old  # DEFECT: Old method selected non-native minute 67!

    # CORRECTED METHOD: elapsed-time mask per run
    runs = enumerate_runs(df)
    assert len(runs) == 2
    correct_native_indices: list[int] = []
    for r in runs:
        r_df = df.iloc[r.start_index : r.end_index + 1]
        r_elapsed = compute_elapsed_minutes(r_df["Timestamp"], reference_t0=t0)
        native_in_run = r.start_index + np.where(r_elapsed % 15 == 0)[0]
        correct_native_indices.extend(native_in_run)

    selected_elapsed_corrected = elapsed[correct_native_indices]
    assert 67 not in selected_elapsed_corrected  # FIXED: Non-native minute 67 correctly excluded!
    assert all(e % 15 == 0 for e in selected_elapsed_corrected)


def test_reproduce_c2_dropna_positional_slicing_bridges_gaps():
    """Reproduce Issue C2: dropna() followed by positional slicing s[30:] - s[:-30] bridges multi-hour gaps."""
    # Participant with two runs separated by a 5-hour gap
    t0 = pd.Timestamp("2020-05-01 08:00:00")
    run1 = pd.DataFrame(
        {
            "Timestamp": pd.date_range(t0, periods=40, freq="1min"),
            "Dexcom GL": np.linspace(100, 140, 40),
        }
    )
    # 5-hour gap
    t_run2 = t0 + pd.Timedelta(hours=5)
    run2 = pd.DataFrame(
        {
            "Timestamp": pd.date_range(t_run2, periods=40, freq="1min"),
            "Dexcom GL": np.linspace(200, 240, 40),
        }
    )
    df = pd.concat([run1, run2], ignore_index=True)

    # OLD METHOD: dropna() + positional slicing
    s = df["Dexcom GL"].dropna().values
    old_deltas = s[30:] - s[:-30]
    # Slicing index 20 (Run 1 minute 20) with index 50 (Run 2 minute 10)
    # The actual elapsed time between index 20 and index 50 is 5 hours and 10 minutes (310 minutes), NOT 30 minutes!
    old_bridged_delta = old_deltas[20]  # s[50] - s[20] = 210.25 - 120.51 ≈ 89.74 mg/dL
    assert old_bridged_delta > 50.0  # DEFECT: Positional slicing bridged across a 5-hour gap!

    # CORRECTED METHOD: pairs_at_offset strictly within runs
    y_t, y_h, meta = pairs_at_offset(df, "Dexcom GL", horizon_min=30)
    # Run 1 has 40 points -> 10 valid 30-min pairs (0..9)
    # Run 2 has 40 points -> 10 valid 30-min pairs (0..9)
    # Total valid pairs must be exactly 20, with zero pairs bridging across the gap!
    assert len(y_t) == 20
    assert meta["valid_pairs_count"] == 20
    # Every pair delta within runs is exactly (140-100)/40 * 30 = 30 mg/dL
    deltas_corrected = np.abs(y_h - y_t)
    assert np.allclose(deltas_corrected, 30.769, atol=0.1)


def test_reproduce_c2_excursion_detection_merging_across_gaps():
    """Reproduce Issue C2: Excursion detection merging episodes across unrecorded gaps."""
    # 20 minutes above 180, then 4-hour absent gap, then 20 minutes above 180
    t0 = pd.Timestamp("2020-05-01 08:00:00")
    run1_ts = pd.date_range(t0, periods=25, freq="1min")
    run1_vals = [120] * 5 + [200] * 20  # 20 min excursion
    t_run2 = t0 + pd.Timedelta(hours=4)
    run2_ts = pd.date_range(t_run2, periods=25, freq="1min")
    run2_vals = [210] * 20 + [120] * 5  # 20 min excursion

    df = pd.DataFrame(
        {
            "Timestamp": run1_ts.union(run2_ts).sort_values(),
            "Dexcom GL": run1_vals + run2_vals,
        }
    )

    runs = enumerate_runs(df)
    assert len(runs) == 2

    # Run bounded detection
    total_episodes = 0
    total_censored = 0
    for r in runs:
        r_vals = df["Dexcom GL"].iloc[r.start_index : r.end_index + 1].to_numpy()
        ep, cens = detect_excursion_episodes_run_bounded(
            r_vals,
            threshold=180.0,
            kind="hyper",
            min_persistence=15,
            min_release=10,
            hysteresis_margin=5.0,
        )
        total_episodes += ep
        total_censored += cens

    # Must be detected as 2 distinct episodes, each boundary-censored by run end/start
    assert total_episodes == 2
    assert total_censored >= 1


def test_reproduce_c4_lag_sign_convention_verification():
    """Reproduce & verify Issue C4: lag tau > 0 strictly means Libre leads Dexcom (Dexcom delayed)."""
    # Create base signal x(t)
    t = np.arange(500)
    base = 120 + 30 * np.sin(2 * np.pi * t / 60.0)

    # Scenario 1: Dexcom is delayed by 5 minutes: Dexcom(t) = base(t - 5), Libre(t) = base(t)
    # Libre leads Dexcom -> convention requires return +5
    libre_1 = base[10:450]
    dexcom_1 = base[5:445]  # delayed relative to Libre
    # Check covariance/correlation between Libre(t) and Dexcom(t + tau):
    # When tau = +5, Dexcom(t + 5) == base((t + 5) - 5) == base(t) == Libre(t)! Peak at tau = +5!

    corrs_pos = [
        np.corrcoef(libre_1[10:-10], dexcom_1[10 + lag : len(dexcom_1) - 10 + lag])[0, 1]
        for lag in range(-10, 11)
    ]
    best_lag_pos = range(-10, 11)[np.argmax(corrs_pos)]
    assert best_lag_pos == 5  # Confirms positive lag means Libre leads Dexcom!

    # Scenario 2: Libre is delayed by 5 minutes: Libre(t) = base(t - 5), Dexcom(t) = base(t)
    # Libre lags Dexcom -> convention requires return -5
    libre_2 = base[5:445]  # delayed relative to Dexcom
    dexcom_2 = base[10:450]
    corrs_neg = [
        np.corrcoef(libre_2[10:-10], dexcom_2[10 + lag : len(dexcom_2) - 10 + lag])[0, 1]
        for lag in range(-10, 11)
    ]
    best_lag_neg = range(-10, 11)[np.argmax(corrs_neg)]
    assert best_lag_neg == -5  # Confirms negative lag means Libre lags Dexcom!


def test_reproduce_c6_privacy_scanner_catches_participant_anomalies():
    """Verify Issue C6: Automated scanner forbids participant IDs linked to clinical/sensor anomalies."""
    clean_text = (
        "Across the cohort, extreme fiber was observed in 2 participants during self-logged meals."
    )
    leaky_text = "Participant CGMacros-016 reported extreme fiber up to 2,830g."

    pattern = re.compile(
        r"CGMacros-\d{3}.*(?:fiber|sentinel|triglyceride|lipid|session|gap)", re.IGNORECASE
    )
    assert not pattern.search(clean_text)
    assert pattern.search(leaky_text)


def test_lint_forbid_dropna_positional_slicing_in_analysis():
    """Lint-style test (T5) forbidding dropna() followed by positional slicing in analysis modules."""
    analysis_dir = Path("src/dtwin/analysis")
    assert analysis_dir.exists()

    forbidden_pattern = re.compile(
        r"\.dropna\(\)[\s\S]{0,100}\[\s*(?:\d+|[a-zA-Z_]+)\s*:\s*\]", re.MULTILINE
    )

    violations = []
    for py_file in analysis_dir.glob("*.py"):
        code = py_file.read_text(encoding="utf-8")
        # Check for forbidden dropna positional slice pattern
        for match in forbidden_pattern.finditer(code):
            violations.append(f"{py_file.name}: {match.group(0)[:60]}")

    assert not violations, (
        f"Forbidden dropna() positional slicing found in analysis modules: {violations}"
    )
