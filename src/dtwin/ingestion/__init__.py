"""Data ingestion, canonical schema mapping, provenance, and Gate G1 baseline join package."""

from dtwin.ingestion.baseline import (
    GateG1Result,
    extract_participant_id,
    join_participant_baseline,
    verify_gate_g1,
)
from dtwin.ingestion.manifest import generate_manifest, hash_file_streaming, verify_manifest
from dtwin.ingestion.profiler import profile_baseline, profile_meals, profile_timeseries_coverage
from dtwin.ingestion.schema import CanonicalSchemaMapper, SchemaValidationError
from dtwin.ingestion.timeseries import calculate_relative_time, calculate_timeseries_metrics

__all__ = [
    "CanonicalSchemaMapper",
    "GateG1Result",
    "SchemaValidationError",
    "calculate_relative_time",
    "calculate_timeseries_metrics",
    "extract_participant_id",
    "generate_manifest",
    "hash_file_streaming",
    "join_participant_baseline",
    "profile_baseline",
    "profile_meals",
    "profile_timeseries_coverage",
    "verify_gate_g1",
    "verify_manifest",
]
