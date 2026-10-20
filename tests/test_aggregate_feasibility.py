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
