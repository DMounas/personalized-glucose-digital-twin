"""Unit and regression tests for Stage 1B-Preflight reconciliations.

Verifies:
1. Participant ID reconciliation, erratum existence, and 100% bijective join.
2. Macronutrient distributions, exact meal counts (1,706), and fiber anomaly isolation.
3. Coverage denominators, absent minutes, and CGMacros-018 multi-session structure.
4. Schema retention of record_index and stripping of Unnamed: 0.
5. Clinical baseline checks (HbA1c 15/16/14 ADA split, BMI consistency, sentinel lipid values).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from dtwin.ingestion.schema import CanonicalSchemaMapper


@pytest.fixture(scope="module")
def preflight_results() -> dict:
    results_path = Path("docs/reports/stage1b_preflight_results.json")
    assert results_path.exists(), "stage1b_preflight_results.json must exist"
    with open(results_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def bio_df() -> pd.DataFrame:
    bio_path = Path("data/cgmacros/CGMacros/bio.csv")
    if not bio_path.exists():
        pytest.skip("Raw dataset not present (bio.csv missing in CI environment)")
    return pd.read_csv(bio_path)


def test_erratum_file_exists():
    """Verify that the dated erratum for participant ID discrepancy exists and is populated."""
    erratum_path = Path("docs/errata/2026-10-19-participant-id-discrepancy.md")
    assert erratum_path.exists(), "Erratum file must exist under docs/errata/"
    content = erratum_path.read_text(encoding="utf-8")
    assert "2026-10-19" in content
    assert "[24, 25, 37, 40]" in content
    assert "CGMacros-014" in content
    assert "CGMacros-018" in content
    assert "CGMacros-020" in content


def test_participant_id_reconciliation(preflight_results, bio_df):
    """Verify that verified missing IDs are exactly [24, 25, 37, 40] and 45 subjects exist in bio.csv."""
    recon = preflight_results["participant_id_reconciliation"]
    assert recon["verified_missing"] == [24, 25, 37, 40]
    assert recon["physical_folders_count"] == 45
    assert recon["bio_csv_subjects_count"] == 45
    assert recon["gut_health_subjects_count"] == 47
    assert recon["gut_only_subjects"] == [24, 25]

    # Check that bio.csv subjects match exactly
    actual_subjects = set(bio_df["subject"])
    expected_subjects = set(range(1, 50)) - {24, 25, 37, 40}
    assert actual_subjects == expected_subjects
    assert 14 in actual_subjects
    assert 18 in actual_subjects
    assert 20 in actual_subjects


def test_row_count_reconciliation_and_local_diagnostics(preflight_results):
    """Verify that total row count is reconciled to exactly 687,580 and local diagnostics exist."""
    recon = preflight_results["row_count_reconciliation"]
    assert recon["verified_ground_truth_total_rows"] == 687580
    assert recon["total_participant_files"] == 45
    assert recon["reconciliation_status"] == "RESOLVED"

    # Verify that local-only diagnostic file exists and is populated
    local_diag = Path("reports_local/diagnostic_file_counts.csv")
    if not local_diag.exists():
        pytest.skip(
            "Local diagnostic file counts not present (reports_local/ missing in CI environment)"
        )
    df_diag = pd.read_csv(local_diag)
    assert len(df_diag) == 45
    assert df_diag["row_count"].sum() == 687580
    assert (df_diag["row_count"] % 5 == 0).all()


def test_macronutrient_meal_counts_and_privacy_compliance(preflight_results):
    """Verify aggregate meal counts, zero-calorie count, and that no participant IDs are leaked with anomalies."""
    meals = preflight_results["meal_count_reconciliation"]
    assert meals["total_meals"] == 1706
    assert meals["breakdown_by_type"]["breakfast"] == 436
    assert meals["breakdown_by_type"]["lunch"] == 435
    assert meals["breakdown_by_type"]["dinner"] == 492
    assert meals["breakdown_by_type"]["snack"] == 343
    assert meals["main_meals_total"] == 1363
    assert meals["zero_calorie_unexplained_observations"] == 45
    assert meals["consecutive_1min_meal_pairs"] == 5
    assert meals["candidate_near_duplicate_15min_pairs"] == 54

    macro = preflight_results["macronutrient_distribution"]
    assert macro["total_rows_inspected"] == 687580
    assert macro["rows_with_macro_without_meal_type"] == 0
    assert macro["rows_with_meal_type_without_macro"] == 0
    assert macro["fiber_anomaly"]["rows_fiber_gt_100"] == 24
    assert macro["fiber_anomaly"]["participants_affected_count"] == 2
    assert macro["fiber_anomaly"]["max_observed_fiber"] == 2830.0

    # Privacy verification: no participant IDs inside fiber anomaly in committed report
    assert "participants_affected" not in macro["fiber_anomaly"]


def test_coverage_and_privacy_compliance(preflight_results):
    """Verify coverage metrics and privacy compliance (no participant IDs in gap reports)."""
    cov = preflight_results["coverage_and_gaps"]
    assert cov["total_rows_recorded"] == 687580
    assert cov["total_grid_span_minutes"] == 706312
    assert cov["total_absent_grid_minutes"] == 18732
    assert cov["participants_with_zero_absent_minutes"] == 35
    assert cov["participants_with_absent_minutes"] == 10
    assert cov["max_elapsed_span_days"] == pytest.approx(19.15, abs=0.05)
    assert cov["max_elapsed_sessions_count"] == 16

    # Privacy verification: no participant ID in max elapsed reporting
    assert "max_elapsed_participant" not in cov

    # Denominators
    denoms = cov["missingness_denominators"]
    assert denoms["libre"]["row_count_missing_pct"] == pytest.approx(0.032, abs=0.01)
    assert denoms["libre"]["elapsed_span_missing_pct"] == pytest.approx(2.683, abs=0.05)
    assert denoms["dexcom"]["row_count_missing_pct"] == pytest.approx(8.40, abs=0.1)
    assert denoms["dexcom"]["elapsed_span_missing_pct"] == pytest.approx(10.83, abs=0.1)


def test_schema_mapper_handles_record_index_and_unnamed():
    """Verify schema mapper retains record_index and strips Unnamed: 0."""
    mapper = CanonicalSchemaMapper()

    # Synthetic dataframe with both Unnamed: 0 and RecordIndex
    test_df = pd.DataFrame(
        {
            "Unnamed: 0": [0, 1],
            "Timestamp": ["2025-05-15 08:00:00", "2025-05-15 08:01:00"],
            "Libre GL": [110.0, 112.0],
            "Dexcom GL": [115.0, 114.0],
            "RecordIndex": [10.0, 25.0],
        }
    )
    mapped = mapper.map_dataframe(test_df, table_type="participant_timeseries", strict=True)
    assert "Unnamed: 0" not in mapped.columns
    assert "record_index" in mapped.columns
    assert mapped["record_index"].iloc[0] == 10.0
    assert mapped["record_index"].iloc[1] == 25.0


def test_clinical_baseline_checks(bio_df, preflight_results):
    """Verify ADA HbA1c classification, BMI formula consistency, and sentinel values."""
    checks = preflight_results["stage1_checks_inventory"]

    # 1. ADA HbA1c split: 15 / 16 / 14
    hba1c = bio_df["A1c PDL (Lab)"]
    normal_count = int((hba1c < 5.7).sum())
    prediabetes_count = int(((hba1c >= 5.7) & (hba1c <= 6.4)).sum())
    diabetes_count = int((hba1c >= 6.5).sum())

    assert normal_count == 15
    assert prediabetes_count == 16
    assert diabetes_count == 14
    assert checks["hba1c_distribution"]["normal_lt_5_7"] == 15
    assert checks["hba1c_distribution"]["prediabetes_5_7_to_6_4"] == 16
    assert checks["hba1c_distribution"]["diabetes_ge_6_5"] == 14

    # 2. BMI formula consistency: BMI = (weight * 703) / (height ^ 2)
    w = bio_df["Body weight "]
    h = bio_df["Height "]
    calc_bmi = (w * 703) / (h**2)
    max_diff = float((bio_df["BMI"] - calc_bmi).abs().max())
    assert max_diff < 0.01  # verified 0.0048 due to 703 rounding
    assert checks["bmi_consistency"]["max_abs_diff"] == pytest.approx(0.0048, abs=0.001)

    # 3. Sentinel values in Subject 12
    subj12 = bio_df[bio_df["subject"] == 12].iloc[0]
    assert subj12["Triglycerides"] == 1150
    assert subj12["LDL (Cal)"] == 800
    assert subj12["VLDL (Cal)"] == 400
    assert subj12["Cho/HDL Ratio"] == 400.0

    # 4. Small-cell suppression
    demo = checks["demographics_small_cell_suppression"]
    assert "<5" in demo["black_or_african_american"]
