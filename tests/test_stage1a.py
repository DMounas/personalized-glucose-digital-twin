"""Tests for Stage 1A: Manifest, Canonical Schema, Relative Time, Gate G1, and Profiling."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dtwin.ingestion.baseline import (
    GateG1Result,
    join_participant_baseline,
    verify_gate_g1,
)
from dtwin.ingestion.manifest import generate_manifest, verify_manifest
from dtwin.ingestion.profiler import profile_meals, profile_timeseries_coverage
from dtwin.ingestion.schema import CanonicalSchemaMapper, SchemaValidationError
from dtwin.ingestion.timeseries import calculate_relative_time

# ---------------------------------------------------------------------------
# 1. Manifest Generation & Verification
# ---------------------------------------------------------------------------


def test_manifest_generation_and_self_exclusion(tmp_path: Path):
    """Test streaming manifest generation and ensure manifest itself is excluded."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create dummy files
    (data_dir / "sample.csv").write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    (data_dir / "image.jpg").write_bytes(b"\xff\xd8\xff\xe0dummy_jpeg_bytes\xff\xd9")

    manifest_file = data_dir / "extracted_sha256sums.txt"

    # Generate manifest
    info = generate_manifest(data_dir=data_dir, output_file=manifest_file)
    assert info["status"] == "CREATED"
    assert info["total_files"] == 2  # Exactly sample.csv and image.jpg

    # Read manifest and verify manifest itself is NOT in its own hash list
    content = manifest_file.read_text(encoding="utf-8")
    assert "sample.csv" in content
    assert "image.jpg" in content
    assert "extracted_sha256sums.txt" not in content

    # Verify manifest
    verify_res = verify_manifest(manifest_file, data_dir)
    assert verify_res["status"] == "PASSED"
    assert verify_res["matched"] == 2
    assert verify_res["mismatched_count"] == 0
    assert verify_res["missing_count"] == 0


def test_manifest_mismatch_and_missing_detection(tmp_path: Path):
    """Test that tampering or deleting a file is detected by verify_manifest."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    f1 = data_dir / "file1.txt"
    f2 = data_dir / "file2.txt"
    f1.write_text("hello", encoding="utf-8")
    f2.write_text("world", encoding="utf-8")

    manifest = data_dir / "manifest.txt"
    generate_manifest(data_dir, manifest)

    # Tamper with file1
    f1.write_text("tampered", encoding="utf-8")
    # Delete file2
    f2.unlink()

    res = verify_manifest(manifest, data_dir)
    assert res["status"] == "FAILED"
    assert res["mismatched_count"] == 1
    assert res["missing_count"] == 1


# ---------------------------------------------------------------------------
# 2. Canonical Schema Mapping & Strict Validation
# ---------------------------------------------------------------------------


def test_schema_mapper_resolves_all_header_families():
    """Test that schema mapper cleanly normalizes varied participant CSV headers."""
    mapper = CanonicalSchemaMapper()

    # Family 1: Unnamed: 0, trailing space in Amount Consumed
    raw_f1 = pd.DataFrame(
        {
            "Unnamed: 0": [0],
            "Timestamp": ["2025-05-15 08:00:00"],
            "Libre GL": [105.0],
            "Dexcom GL": [112.0],
            "HR": [72.0],
            "Calories (Activity)": [1.4],
            "METs": [12.0],
            "Meal Type": ["Breakfast"],
            "Calories": [450.0],
            "Carbs": [55.0],
            "Protein": [25.0],
            "Fat": [15.0],
            "Fiber": [6.0],
            "Amount Consumed ": [100.0],
            "Image path": ["photos/meal_01.jpg"],
        }
    )
    mapped_f1 = mapper.map_dataframe(raw_f1, table_type="participant_timeseries", strict=True)
    assert "Unnamed: 0" not in mapped_f1.columns
    assert "amount_consumed" in mapped_f1.columns
    assert "libre_gl" in mapped_f1.columns
    assert mapped_f1["libre_gl"].iloc[0] == 105.0

    # Family 3: swapped Libre and Dexcom columns
    raw_f3 = pd.DataFrame(
        {
            "Unnamed: 0": [0],
            "Timestamp": ["2025-05-15 08:00:00"],
            "Dexcom GL": [115.0],
            "Libre GL": [108.0],
        }
    )
    mapped_f3 = mapper.map_dataframe(raw_f3, table_type="participant_timeseries", strict=True)
    assert mapped_f3["dexcom_gl"].iloc[0] == 115.0
    assert mapped_f3["libre_gl"].iloc[0] == 108.0

    # Family 4: Steps and RecordIndex
    raw_f4 = pd.DataFrame(
        {
            "Timestamp": ["2025-05-15 08:00:00"],
            "Libre GL": [100.0],
            "Dexcom GL": [102.0],
            "Steps": [15],
            "RecordIndex": [1],
        }
    )
    mapped_f4 = mapper.map_dataframe(raw_f4, table_type="participant_timeseries", strict=True)
    assert "RecordIndex" not in mapped_f4.columns
    assert "steps" in mapped_f4.columns
    assert mapped_f4["steps"].iloc[0] == 15


def test_schema_mapper_strict_mode_fails_loudly():
    """Test that unexpected columns raise SchemaValidationError in strict mode."""
    mapper = CanonicalSchemaMapper()
    invalid_df = pd.DataFrame(
        {
            "Timestamp": ["2025-05-15 08:00:00"],
            "Libre GL": [100.0],
            "Dexcom GL": [100.0],
            "UNEXPECTED_ROGUE_COLUMN": [999],
        }
    )

    # Strict mode must raise
    with pytest.raises(SchemaValidationError, match="unexpected unapproved column"):
        mapper.map_dataframe(invalid_df, table_type="participant_timeseries", strict=True)

    # Permissive mode preserves unexpected column
    permissive_df = mapper.map_dataframe(
        invalid_df, table_type="participant_timeseries", strict=False
    )
    assert "UNEXPECTED_ROGUE_COLUMN" in permissive_df.columns


def test_schema_mapper_handles_duplicate_bio_headers():
    """Test handling of bio.csv with duplicated Time (t) headers."""
    mapper = CanonicalSchemaMapper()
    raw_bio = pd.DataFrame(
        {
            "subject": [1],
            "Age": [45],
            "Gender": ["M"],
            "BMI": [28.5],
            "Body weight ": [185.0],
            "Height ": [70.0],
            "Self-identify ": ["White"],
            "A1c PDL (Lab)": [5.8],
            "Fasting GLU - PDL (Lab)": [105.0],
            "Insulin ": [12.0],
            "Triglycerides": [150.0],
            "Cholesterol": [200.0],
            "HDL": [45.0],
            "Non HDL ": [155.0],
            "LDL (Cal)": [125.0],
            "VLDL (Cal)": [30.0],
            "Cho/HDL Ratio": [4.4],
            "Collection time PDL (Lab)": ["08:30"],
            "#1 Contour Fingerstick GLU": [110.0],
            "Time (t)": ["08:35"],
            " #2 Contour Fingerstick GLU": [112.0],
            "Time (t).1": ["09:05"],
            "#3 Contour Fingerstick GLU": [108.0],
            "Time (t).2": ["09:35"],
        }
    )
    mapped = mapper.map_dataframe(raw_bio, table_type="bio_baseline", strict=True)
    assert mapped["participant_id"].iloc[0] == 1
    assert mapped["fingerstick_time_1"].iloc[0] == "08:35"
    assert mapped["fingerstick_time_2"].iloc[0] == "09:05"
    assert mapped["fingerstick_time_3"].iloc[0] == "09:35"
    assert mapped["hba1c_percent"].iloc[0] == 5.8


# ---------------------------------------------------------------------------
# 3. Relative Time Coordinates (Non-Calendar)
# ---------------------------------------------------------------------------


def test_calculate_relative_time_no_calendar_features():
    """Assert relative time calculation starts at 0 and adds no calendar features."""
    df = pd.DataFrame(
        {
            "timestamp": [
                "2025-05-15 08:00:00",
                "2025-05-15 08:01:00",
                "2025-05-15 08:05:00",
                "2025-05-16 08:00:00",
            ],
            "libre_gl": [100.0, 101.0, 102.0, 105.0],
        }
    )
    result = calculate_relative_time(df, timestamp_col="timestamp")

    assert "relative_time_seconds" in result.columns
    assert "relative_time_minutes" in result.columns
    assert "day_offset" in result.columns

    # Verify t0
    assert result["relative_time_seconds"].iloc[0] == 0.0
    assert result["relative_time_minutes"].iloc[0] == 0.0
    assert result["day_offset"].iloc[0] == 0.0

    # Verify progression
    assert result["relative_time_seconds"].iloc[1] == 60.0
    assert result["relative_time_minutes"].iloc[1] == 1.0
    assert result["relative_time_minutes"].iloc[2] == 5.0
    assert result["day_offset"].iloc[3] == 1.0

    # Assert strictly NO calendar-based columns were created
    forbidden = [
        "month",
        "day_of_week",
        "day_of_month",
        "dayofweek",
        "year",
        "is_weekend",
        "season",
    ]
    for col in forbidden:
        assert col not in result.columns


# ---------------------------------------------------------------------------
# 4. Gate G1 Verification & Baseline Join
# ---------------------------------------------------------------------------


def test_verify_gate_g1_passed_on_synthetic_data(tmp_path: Path):
    """Test Gate G1 verification when folders and bio.csv match 100%."""
    data_dir = tmp_path / "cgm_data"
    data_dir.mkdir()

    # Create 45 folders with missing IDs [24, 25, 37, 40]
    expected_ids = [i for i in range(1, 50) if i not in [24, 25, 37, 40]]
    assert len(expected_ids) == 45

    for pid in expected_ids:
        pdir = data_dir / f"CGMacros-{pid:03d}"
        pdir.mkdir()
        (pdir / f"CGMacros-{pid:03d}.csv").write_text("Timestamp,Libre GL\n", encoding="utf-8")

    # Create bio.csv with matching subjects
    bio_df = pd.DataFrame(
        {
            "subject": expected_ids,
            "A1c PDL (Lab)": [5.5] * 45,
        }
    )
    bio_df.to_csv(data_dir / "bio.csv", index=False)

    gate_res = verify_gate_g1(data_dir=data_dir)
    assert gate_res.is_passed is True
    assert gate_res.status == "GATE_G1_PASSED"
    assert gate_res.matched_count == 45
    assert gate_res.missing_participant_ids == [24, 25, 37, 40]


def test_verify_gate_g1_blocked_on_mismatch(tmp_path: Path):
    """Test Gate G1 blocks if folders and bio.csv mismatch."""
    data_dir = tmp_path / "cgm_data"
    data_dir.mkdir()

    # Create only 40 folders
    for pid in range(1, 41):
        pdir = data_dir / f"CGMacros-{pid:03d}"
        pdir.mkdir()

    # bio.csv has 45 subjects
    bio_df = pd.DataFrame({"subject": list(range(1, 46))})
    bio_df.to_csv(data_dir / "bio.csv", index=False)

    gate_res = verify_gate_g1(data_dir=data_dir)
    assert gate_res.is_passed is False
    assert gate_res.status == "GATE_G1_BLOCKED"


def test_join_participant_baseline_enforces_gate():
    """Test that join_participant_baseline works when Gate G1 passes and errors when blocked."""
    part_df = pd.DataFrame(
        {
            "timestamp": ["2025-05-15 08:00:00"],
            "relative_time_minutes": [0.0],
            "libre_gl": [110.0],
        }
    )
    bio_df = pd.DataFrame(
        {
            "participant_id": [3],
            "age_years": [42.0],
            "hba1c_percent": [5.9],  # Pre-diabetes
        }
    )

    passed_gate = GateG1Result(
        status="GATE_G1_PASSED",
        is_passed=True,
        evidence_tag="[ESTABLISHED]",
        participant_dirs_count=45,
        bio_rows_count=45,
        matched_count=45,
        missing_participant_ids=[24, 25, 37, 40],
        unmatched_dirs=[],
        unmatched_bio_ids=[],
        mapping_mechanism="ID",
        primary_source_citation="citation",
        rationale="pass",
    )

    joined = join_participant_baseline(
        part_df, participant_id=3, bio_df=bio_df, gate_result=passed_gate
    )
    assert joined["participant_id"].iloc[0] == 3
    assert joined["baseline_age_years"].iloc[0] == 42.0
    assert joined["metabolic_status"].iloc[0] == "pre_diabetes"

    # Test blocked gate
    blocked_gate = GateG1Result(
        status="GATE_G1_BLOCKED",
        is_passed=False,
        evidence_tag="[HYPOTHESIS]",
        participant_dirs_count=40,
        bio_rows_count=45,
        matched_count=40,
        missing_participant_ids=[],
        unmatched_dirs=[],
        unmatched_bio_ids=[],
        mapping_mechanism="ID",
        primary_source_citation="",
        rationale="blocked",
    )
    with pytest.raises(RuntimeError, match="Gate G1 is BLOCKED"):
        join_participant_baseline(
            part_df, participant_id=3, bio_df=bio_df, gate_result=blocked_gate
        )


# ---------------------------------------------------------------------------
# 5. Profiler & Privacy Safeguards
# ---------------------------------------------------------------------------


def test_profile_meals_and_timeseries_coverage():
    """Test aggregate profiler on synthetic participant timeseries."""
    df1 = pd.DataFrame(
        {
            "timestamp": ["2025-05-15 08:00:00", "2025-05-15 08:01:00", "2025-05-15 12:00:00"],
            "relative_time_seconds": [0.0, 60.0, 14400.0],
            "libre_gl": [100.0, 102.0, 105.0],
            "dexcom_gl": [108.0, 110.0, np.nan],
            "heart_rate": [70.0, 72.0, 75.0],
            "meal_type": ["Breakfast", None, "lunch"],
            "meal_calories": [400.0, None, 600.0],
            "meal_carbs": [50.0, None, 70.0],
            "meal_protein": [20.0, None, 30.0],
            "meal_fat": [15.0, None, 20.0],
            "meal_fiber": [5.0, None, 8.0],
            "image_path": ["photos/01.jpg", None, "photos/02.jpg"],
        }
    )

    meal_prof = profile_meals([df1])
    assert meal_prof["total_meal_events"] == 2
    assert meal_prof["meal_types_distribution"]["breakfast"] == 1
    assert meal_prof["meal_types_distribution"]["lunch"] == 1
    assert meal_prof["meals_with_photo_path_count"] == 2
    assert meal_prof["macro_distributions"]["meal_calories"]["mean"] == 500.0

    ts_prof = profile_timeseries_coverage([df1])
    assert ts_prof["cohort_size"] == 1
    assert ts_prof["total_rows_sum"] == 3
    assert ts_prof["sensor_coverage_pct"]["libre_gl"]["mean"] == 100.0
