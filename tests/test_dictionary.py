"""Tests for data dictionary parsing, mapping, and range checks."""

from pathlib import Path

import pandas as pd

from dtwin.audit.dictionary import (
    check_family_conformance,
    parse_dictionary_file,
    parse_numeric_range,
)
from dtwin.audit.profiling import ColumnProfile, NumericStats


def test_numeric_range_regex():
    # Standard format: "Numeric: 40-400 mg/dL"
    low, high, status = parse_numeric_range("Numeric: 40-400 mg/dL")
    assert status == "parsed"
    assert low == 40.0
    assert high == 400.0

    # Interval brackets: "[10, 50]"
    low, high, status = parse_numeric_range("[10, 50]")
    assert status == "parsed"
    assert low == 10.0
    assert high == 50.0

    # Text / categorical range -> "range not machine-parsed"
    low, high, status = parse_numeric_range("Breakfast, Lunch, Dinner")
    assert status == "range not machine-parsed"
    assert low is None
    assert high is None

    # Empty / None
    low, high, status = parse_numeric_range(None)
    assert status == "no range specified"


def test_dictionary_parsing_and_conformance(tmp_path: Path):
    d = tmp_path / "dict_test"
    d.mkdir()

    # Create dictionary CSV
    dict_csv = d / "data_dict.csv"
    df_dict = pd.DataFrame(
        {
            "Field": ["Glucose", "BMI", "Documented_Only_Field"],
            "Range": ["Numeric: 40-400 mg/dL", "15 to 45", "Categorical text"],
            "Description": ["Sensor glucose", "Body mass index", "Extra variable"],
        }
    )
    df_dict.to_csv(dict_csv, index=False)

    doc_fields, warnings = parse_dictionary_file(dict_csv)
    assert "Glucose" in doc_fields
    assert doc_fields["Glucose"].min_value == 40.0
    assert doc_fields["Glucose"].max_value == 400.0
    assert doc_fields["Documented_Only_Field"].range_status == "range not machine-parsed"

    # Test conformance against observed columns
    observed_cols = ["Glucose", "BMI", "Observed_Only_Col"]
    profiles = {
        "Glucose": ColumnProfile(
            name="Glucose",
            inferred_dtype="float64",
            is_dtype_consistent=True,
            observed_dtypes=["float64"],
            missing_count=0,
            missing_percent=0.0,
            files_all_missing_count=0,
            numeric_stats=NumericStats(
                count=100,
                missing_count=0,
                missing_percent=0.0,
                non_finite_count=0,
                zero_count=0,
                sentinel_counts={},
                min=35.0,  # Below 40 -> out of range!
                max=450.0,  # Above 400 -> out of range!
                mean=120.0,
                median=110.0,
                quantiles={},
            ),
        ),
        "BMI": ColumnProfile(
            name="BMI",
            inferred_dtype="float64",
            is_dtype_consistent=True,
            observed_dtypes=["float64"],
            missing_count=0,
            missing_percent=0.0,
            files_all_missing_count=0,
            numeric_stats=NumericStats(
                count=50,
                missing_count=0,
                missing_percent=0.0,
                non_finite_count=0,
                zero_count=0,
                sentinel_counts={},
                min=20.0,  # Within 15-45
                max=40.0,
                mean=25.0,
                median=24.0,
                quantiles={},
            ),
        ),
    }

    rep = check_family_conformance(
        dict_path=dict_csv,
        family_id="Fam1",
        observed_columns=observed_cols,
        column_profiles=profiles,
    )

    assert "Glucose" in rep.matched_columns
    assert "BMI" in rep.matched_columns
    assert "Documented_Only_Field" in rep.documented_but_missing
    assert "Observed_Only_Col" in rep.observed_but_undocumented

    # Check out-of-range counts
    assert len(rep.range_checks) >= 1
    glu_check = next(rc for rc in rep.range_checks if rc.column_name == "Glucose")
    assert glu_check.out_of_range_count > 0
