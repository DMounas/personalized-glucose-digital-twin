"""Tests for schema family grouping, numeric profiling, sentinels, and chunking parity."""

from pathlib import Path
from typing import Any

import pandas as pd

from dtwin.audit.discovery import discover_directory
from dtwin.audit.profiling import (
    group_schema_families,
    profile_schema_family,
)


def test_schema_grouping_and_profiling(synthetic_data_dir: Path, sample_config: dict[str, Any]):
    disc = discover_directory(synthetic_data_dir)
    grouped = group_schema_families(
        synthetic_data_dir,
        disc.tabular_files,
        disc.tabular_delimiters,
    )

    # We should have at least 2 distinct schema families:
    # the 3 participant files and bio.csv (and dict)
    assert len(grouped) >= 2

    dominant_sig = max(grouped.keys(), key=lambda k: len(grouped[k]))
    assert len(dominant_sig) == 7  # CGMacros-00X.csv columns
    assert "Glucose" in dominant_sig

    fam_prof = profile_schema_family(
        family_id="Family_1",
        column_signature=list(dominant_sig),
        files=grouped[dominant_sig],
        data_dir=synthetic_data_dir,
        delimiters=disc.tabular_delimiters,
        config=sample_config,
        is_dominant=True,
    )

    # Total rows = 25 (P1) + 20 (P2) + 15 (P4) = 60 rows
    assert fam_prof.total_rows == 60
    assert fam_prof.rows_per_file["min"] == 15.0
    assert fam_prof.rows_per_file["max"] == 25.0
    assert fam_prof.rows_per_file["median"] == 20.0

    # Numeric profiling on Glucose
    glu_prof = fam_prof.columns["Glucose"]
    assert glu_prof.numeric_stats is not None
    assert glu_prof.numeric_stats.min == 100.0
    assert glu_prof.numeric_stats.max > 130.0
    assert glu_prof.numeric_stats.zero_count == 0

    # Sentinel counts
    sent_prof = fam_prof.columns["Sentinel_Col"]
    assert sent_prof.numeric_stats is not None
    assert sent_prof.numeric_stats.sentinel_counts["-999"] == 2
    assert sent_prof.numeric_stats.sentinel_counts["400"] == 1
    assert sent_prof.numeric_stats.sentinel_counts["800"] == 2
    assert sent_prof.numeric_stats.zero_count == 5

    # Small cell suppression on Category_Rare
    cat_prof = fam_prof.columns["Category_Rare"]
    assert cat_prof.categorical_stats is not None
    counts = cat_prof.categorical_stats.category_counts
    assert counts is not None
    assert "Common" in counts
    # Rare categories (<5) must be suppressed!
    assert "<5 suppressed" in counts
    assert "Rare_A" not in counts
    assert "Rare_B" not in counts


def test_small_table_suppression(tmp_path: Path, sample_config: dict[str, Any]):
    small_dir = tmp_path / "small_table_data"
    small_dir.mkdir()

    # Create a 3-row table (< min_rows_for_stats=5)
    df = pd.DataFrame(
        {
            "Patient": ["A", "B", "C"],
            "Value": [10.0, 20.0, 30.0],
        }
    )
    df.to_csv(small_dir / "tiny.csv", index=False)

    fam_prof = profile_schema_family(
        family_id="Family_Tiny",
        column_signature=["Patient", "Value"],
        files=["tiny.csv"],
        data_dir=small_dir,
        delimiters={"tiny.csv": ","},
        config=sample_config,
    )

    assert fam_prof.is_small_table_suppressed is True
    # Value numeric stats should be None due to small table privacy protection
    val_prof = fam_prof.columns["Value"]
    assert val_prof.is_stats_suppressed is True
    assert val_prof.numeric_stats is None
    # Missingness and row counts are still present
    assert val_prof.missing_count == 0


def test_chunked_vs_in_memory_parity(tmp_path: Path, sample_config: dict[str, Any]):
    """Assert chunked reading path produces the identical statistics as in-memory path."""
    test_dir = tmp_path / "parity_test"
    test_dir.mkdir()

    # Create 500 rows with mixed types, sentinels, and nulls
    rows = []
    for i in range(500):
        val = float(i) if i % 10 != 0 else None
        sent = -999.0 if i % 50 == 0 else (400.0 if i % 70 == 0 else 50.0)
        rows.append(
            {
                "id": f"rec_{i}",
                "value": val,
                "sentinel": sent,
                "category": "cat_X" if i % 2 == 0 else "cat_Y",
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(test_dir / "large.csv", index=False)

    # 1. Profile with force_chunked=False
    prof_in_mem = profile_schema_family(
        family_id="Fam1",
        column_signature=["id", "value", "sentinel", "category"],
        files=["large.csv"],
        data_dir=test_dir,
        delimiters={"large.csv": ","},
        config=sample_config,
        force_chunked=False,
    )

    # 2. Profile with force_chunked=True
    prof_chunked = profile_schema_family(
        family_id="Fam1",
        column_signature=["id", "value", "sentinel", "category"],
        files=["large.csv"],
        data_dir=test_dir,
        delimiters={"large.csv": ","},
        config=sample_config,
        force_chunked=True,
    )

    # Compare total rows
    assert prof_in_mem.total_rows == prof_chunked.total_rows == 500

    # Compare numeric statistics
    num_mem = prof_in_mem.columns["value"].numeric_stats
    num_chk = prof_chunked.columns["value"].numeric_stats
    assert num_mem is not None and num_chk is not None
    assert num_mem.min == num_chk.min
    assert num_mem.max == num_chk.max
    assert num_mem.mean == num_chk.mean
    assert num_mem.median == num_chk.median
    assert num_mem.quantiles == num_chk.quantiles
    assert num_mem.missing_count == num_chk.missing_count

    # Compare sentinels
    s_mem = prof_in_mem.columns["sentinel"].numeric_stats
    s_chk = prof_chunked.columns["sentinel"].numeric_stats
    assert s_mem is not None and s_chk is not None
    assert s_mem.sentinel_counts == s_chk.sentinel_counts
