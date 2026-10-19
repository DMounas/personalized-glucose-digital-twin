"""Audit report builder module.

Produces audit_report.json (machine-readable, stable schema) and audit_report.md
(human-readable with clear status banner and aggregate-only privacy protections).
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from dtwin import __version__ as dtwin_version

SCHEMA_VERSION = "1.0.0"

WHAT_THIS_AUDIT_DOES_NOT_VERIFY = [
    "Semantic correctness of values (e.g., whether glucose of 400 is physiological or artifact).",
    "Clinical validity or diagnostic accuracy of recorded biosensor measurements.",
    "Whether resampling/interpolation occurred (e.g., 1-minute vs 5/15-minute sensor sampling).",
    "Sensor accuracy, drift, or concordance between devices (e.g., Libre vs Dexcom bias).",
    "Cross-file consistency of measurement units (e.g., whether HbA1c is in mmol/mol vs percent).",
]

ACQUISITION_GUIDANCE = (
    "To acquire the dataset, download CGMacros v1.0.0 from PhysioNet:\n"
    "Official URL: https://physionet.org/content/cgmacros/1.0.0/\n"
    "Step-by-step instructions: see docs/DATA_ACQUISITION.md\n"
    "Download Options:\n"
    "  1. Browser ZIP: Download 'CGMacros_dateshifted365.zip' and extract into data/cgmacros/\n"
    "  2. Wget (Linux/macOS): wget -r -N -c -np https://physionet.org/files/cgmacros/1.0.0/\n"
    "  3. AWS S3: aws s3 sync --no-sign-request s3://physionet-open/cgmacros/1.0.0/ <DEST>\n"
    "Reminder: Data files must remain in 'data/' and are git-ignored. Never commit raw data."
)


def get_git_commit() -> str:
    """Retrieve current git commit hash if available."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "uncommitted / git unavailable"


def get_environment_info() -> dict[str, str]:
    """Capture environment and package versions."""
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "pyyaml_version": yaml.__version__,
    }


def build_audit_data_structure(
    status: str,  # "DATA PRESENT" or "NO DATA FOUND"
    data_dir_path: str,
    fingerprint: dict[str, Any],
    config_in_effect: dict[str, Any],
    discovery_result: dict[str, Any] | None = None,
    schema_families: list[dict[str, Any]] | None = None,
    timeseries_profiles: dict[str, list[dict[str, Any]]] | None = None,
    dictionary_reports: list[dict[str, Any]] | None = None,
    checksum_report: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    truncation_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble stable ordered dictionary for JSON serialization."""
    report = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": dtwin_version,
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": get_git_commit(),
        "environment": get_environment_info(),
        "status": status,
        "data_dir": data_dir_path,
        "data_dir_fingerprint": fingerprint,
        "config_in_effect": config_in_effect,
        "truncation": truncation_info or {"is_truncated": False, "max_files_limit": None},
        "acquisition_guidance": ACQUISITION_GUIDANCE if status == "NO DATA FOUND" else None,
        "discovery_summary": discovery_result,
        "schema_families": schema_families or [],
        "timeseries_analysis": timeseries_profiles or {},
        "dictionary_conformance": dictionary_reports or [],
        "checksum_verification": checksum_report,
        "warnings": warnings or [],
        "what_this_audit_does_not_verify": WHAT_THIS_AUDIT_DOES_NOT_VERIFY,
    }
    return report


def write_json_report(report_data: dict[str, Any], output_path: Path) -> None:
    """Write machine-readable JSON report with stable formatting."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)


def write_markdown_report(report_data: dict[str, Any], output_path: Path) -> None:
    """Write human-readable Markdown report with status banner and aggregate-only tables."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    status = report_data.get("status", "UNKNOWN")
    lines: list[str] = []

    # Title & Status Banner
    lines.append("# Dataset Audit Report")
    lines.append("")
    if status == "DATA PRESENT":
        lines.append("> **STATUS: DATA PRESENT**")
    else:
        lines.append("> **STATUS: NO DATA FOUND**")
    lines.append("")

    # If NO DATA FOUND
    if status == "NO DATA FOUND":
        lines.append("## Notice")
        lines.append(
            "No supported tabular data files (`.csv`, `.tsv`, `.txt`, `.parquet`) were found in "
            f"the specified target directory: `{report_data.get('data_dir')}`."
        )
        lines.append("")
        lines.append("## Acquisition Guidance")
        lines.append("```text")
        lines.append(ACQUISITION_GUIDANCE)
        lines.append("```")
        lines.append("")
        lines.append("## What This Audit Does NOT Verify")
        for item in report_data.get("what_this_audit_does_not_verify", []):
            lines.append(f"- {item}")
        lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return

    # Metadata Table
    lines.append("## Executive Metadata")
    lines.append("| Metric | Value |")
    lines.append("|:---|:---|")
    lines.append(f"| **Audit Timestamp (UTC)** | `{report_data.get('audit_timestamp_utc')}` |")
    lines.append(f"| **Tool Version** | `{report_data.get('tool_version')}` |")
    commit_str = report_data.get("git_commit") or "N/A"
    lines.append(f"| **Git Commit** | `{commit_str[:12]}` |")
    lines.append(
        f"| **Python Version** | `{report_data.get('environment', {}).get('python_version')}` |"
    )
    lines.append(f"| **Platform** | `{report_data.get('environment', {}).get('platform')}` |")
    lines.append(f"| **Data Directory** | `{report_data.get('data_dir')}` |")

    fp = report_data.get("data_dir_fingerprint", {})
    lines.append(f"| **Total Files** | `{fp.get('total_files', 0):,}` |")
    lines.append(f"| **Total Volume** | `{fp.get('total_bytes', 0):,} bytes` |")
    lines.append(
        f"| **Directory Fingerprint (SHA-256)** | `{fp.get('fingerprint_sha256', 'N/A')}` |"
    )
    lines.append("")

    # Discovery & Archives
    disc = report_data.get("discovery_summary") or {}
    lines.append("## File Discovery & Media Inventory")
    lines.append(f"- **Tabular Candidates**: {len(disc.get('tabular_files', []))} files")
    lines.append(f"- **Image Files (Unopened)**: {disc.get('image_count', 0)} files")
    lines.append(f"- **Archives Detected**: {len(disc.get('archives', []))} archives")
    lines.append("")

    archives = disc.get("archives", [])
    if archives:
        lines.append("### Archives Detail")
        lines.append("| Archive Path | Size | Members | Uncompressed | Action |")
        lines.append("|:---|:---|:---|:---|:---|")
        for arc in archives:
            mc = arc.get("member_count")
            mc_str = f"{mc:,}" if mc is not None else "Unknown"
            ub = arc.get("uncompressed_bytes")
            ub_str = f"{ub:,} B" if ub is not None else "Unknown"
            lines.append(
                f"| `{arc.get('relative_path')}` | {arc.get('size_bytes', 0):,} B | "
                f"{mc_str} | {ub_str} | Extract manually |"
            )
        lines.append("")

    # Participant Summary
    part = disc.get("participant_summary")
    if part:
        lines.append("## Participant Identifiers (Inferred)")
        lines.append(f"> *{part.get('inference_note')}*")
        lines.append("")
        lines.append(f"- **Extraction Rule**: {part.get('rule_used_description')}")
        lines.append(
            f"- **Distinct Identifiers Detected**: {part.get('distinct_participant_count')}"
        )
        lines.append(f"- **Files Without Identifiers**: {part.get('files_without_id_count')}")
        dist = part.get("files_per_id_distribution", {})
        lines.append(
            f"- **Files per Identifier**: Min = {dist.get('min')}, "
            f"Median = {dist.get('median')}, Max = {dist.get('max')}"
        )
        if part.get("numeric_id_gaps"):
            lines.append(f"- **Gaps in Numeric Sequence**: `{part.get('numeric_id_gaps')}`")
        else:
            lines.append("- **Gaps in Numeric Sequence**: None detected")
        lines.append("")

    # Schema Families
    families = report_data.get("schema_families", [])
    lines.append(f"## Schema Families ({len(families)} identified)")
    lines.append("")

    for fam in families:
        fid = fam.get("family_id")
        dom = " (Dominant Signature)" if fam.get("is_dominant_family") else ""
        lines.append(f"### Family `{fid}`{dom}")
        lines.append(f"- **File Count**: {fam.get('file_count')}")
        lines.append(f"- **Total Rows**: {fam.get('total_rows'):,}")
        rpf = fam.get("rows_per_file", {})
        lines.append(
            f"- **Rows per File**: Min = {rpf.get('min'):,}, "
            f"Median = {rpf.get('median'):,}, Max = {rpf.get('max'):,}"
        )

        if fam.get("is_small_table_suppressed"):
            lines.append("> *Small table suppression in effect: statistical quantiles suppressed.*")
            lines.append("")

        lines.append("#### Columns Profile")
        lines.append(
            "| Column | Inferred Dtype | Consistent? | Missing % (Count) | "
            "100% Empty Files | Stats Summary / Category Counts |"
        )
        lines.append("|:---|:---|:---|:---|:---|:---|")

        cols = fam.get("columns", {})
        for col_name, prof in cols.items():
            dt = prof.get("inferred_dtype", "unknown")
            cons = (
                "Yes"
                if prof.get("is_dtype_consistent")
                else f"Mixed ({prof.get('observed_dtypes')})"
            )
            mp = f"{prof.get('missing_percent')}% ({prof.get('missing_count'):,})"
            ef = prof.get("files_all_missing_count", 0)

            summary = "Suppressed"
            if prof.get("numeric_stats"):
                ns = prof.get("numeric_stats")
                summary = (
                    f"Min: {ns.get('min')}, Max: {ns.get('max')}, Mean: {ns.get('mean')}, "
                    f"Med: {ns.get('median')}, Zeros: {ns.get('zero_count'):,}, "
                    f"Sentinels: {ns.get('sentinel_counts')}"
                )
            elif prof.get("categorical_stats"):
                cs = prof.get("categorical_stats")
                if cs.get("is_identifier_or_path_or_text"):
                    summary = f"Card: {cs.get('cardinality')} (Path/ID/Text: Values Suppressed)"
                else:
                    summary = (
                        f"Card: {cs.get('cardinality')}, Categories: {cs.get('category_counts')}"
                    )
            elif prof.get("is_stats_suppressed"):
                summary = f"Suppressed ({prof.get('suppression_reason')})"

            lines.append(f"| `{col_name}` | `{dt}` | {cons} | {mp} | {ef} | {summary} |")
        lines.append("")

    # Timeseries Analysis
    ts_analysis = report_data.get("timeseries_analysis", {})
    if ts_analysis:
        lines.append("## Timeseries & Timestamp Analysis")
        lines.append(
            "| Family | Column | Parse Rate | Min Timestamp | Max Timestamp | "
            "Mode Delta | % Mode | Median | Gaps | Dups | Non-Mono |"
        )
        lines.append("|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|")
        for fid, profiles in ts_analysis.items():
            for p in profiles:
                min_t = p.get("min_timestamp") or "N/A"
                max_t = p.get("max_timestamp") or "N/A"
                lines.append(
                    f"| `{fid}` | `{p.get('column_name')}` | "
                    f"{p.get('parse_success_rate') * 100:.1f}% | "
                    f"{min_t} | {max_t} | "
                    f"{p.get('mode_delta_seconds')}s | {p.get('mode_delta_percent')}% | "
                    f"{p.get('median_delta_seconds')}s | {p.get('gap_count'):,} | "
                    f"{p.get('duplicate_count'):,} | {p.get('non_monotonic_count'):,} |"
                )
        lines.append("")

    # Dictionary Conformance
    dict_reports = report_data.get("dictionary_conformance", [])
    if dict_reports:
        lines.append("## Data Dictionary Conformance")
        for dr in dict_reports:
            lines.append(
                f"### Dictionary: `{dr.get('dictionary_file')}` (Family: `{dr.get('family_id')}`)"
            )
            lines.append(f"- **Matched Columns**: {len(dr.get('matched_columns', []))}")
            lines.append(f"- **Documented but Missing**: {dr.get('documented_but_missing', [])}")
            lines.append(
                f"- **Observed but Undocumented**: {dr.get('observed_but_undocumented', [])}"
            )
            if dr.get("near_miss_suggestions"):
                lines.append(
                    f"- **Possible Near-Misses (Unconfirmed)**: {dr.get('near_miss_suggestions')}"
                )

            rcs = dr.get("range_checks", [])
            if rcs:
                lines.append("#### Range Verification")
                lines.append("| Column | Range | Observed | Out-of-Range | Out % |")
                lines.append("|:---|:---|:---|:---|:---|")
                for rc in rcs:
                    lines.append(
                        f"| `{rc.get('column_name')}` | `{rc.get('documented_range')}` | "
                        f"{rc.get('total_observed'):,} | "
                        f"{rc.get('out_of_range_count'):,} | {rc.get('out_of_range_percent')}% |"
                    )
            lines.append("")

    # Checksum Verification
    chk = report_data.get("checksum_verification")
    if chk:
        lines.append("## Checksum Verification")
        lines.append(f"- **Status**: `{chk.get('status')}`")
        lines.append(f"- **Matched Files**: {chk.get('matched_count', 0)}")
        lines.append(f"- **Mismatched Files**: {chk.get('mismatched_count', 0)}")
        lines.append(f"- **Missing Files**: {chk.get('missing_count', 0)}")
        if chk.get("mismatched_files"):
            lines.append(f"- **Mismatched List**: `{chk.get('mismatched_files')}`")
        if chk.get("missing_files"):
            lines.append(f"- **Missing List**: `{chk.get('missing_files')}`")
        lines.append("")

    # Warnings
    warnings = report_data.get("warnings", [])
    if warnings:
        lines.append("## Warnings & Ambiguities")
        for w in warnings:
            lines.append(f"- [WARNING] {w}")
        lines.append("")

    # Mandatory What This Audit Does NOT Verify Section
    lines.append("## What This Audit Does NOT Verify")
    for item in report_data.get("what_this_audit_does_not_verify", []):
        lines.append(f"- {item}")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
