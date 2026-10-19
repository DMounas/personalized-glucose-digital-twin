"""Command-line interface and orchestrator for dtwin-audit."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from dtwin.audit.checksums import verify_sha256sums
from dtwin.audit.dictionary import check_family_conformance
from dtwin.audit.discovery import discover_directory
from dtwin.audit.profiling import group_schema_families, profile_schema_family
from dtwin.audit.report import (
    ACQUISITION_GUIDANCE,
    build_audit_data_structure,
    write_json_report,
    write_markdown_report,
)
from dtwin.audit.timeseries import analyze_timeseries_column, detect_candidate_columns

DEFAULT_CONFIG: dict[str, Any] = {
    "small_cell_threshold": 5,
    "min_rows_for_stats": 5,
    "chunk_size": 50000,
    "chunk_size_bytes_threshold": 52428800,  # 50 MB
    "datetime_column_hints": ["time", "date", "timestamp"],
    "datetime_parse_threshold": 0.8,
    "gap_multiplier": 3.0,
    "suspicious_sentinels": [-999, -1, 400, 800, 9999],
    "quantiles": [0.05, 0.25, 0.5, 0.75, 0.95],
}


def load_and_validate_config(config_path: Path) -> dict[str, Any]:
    """Load YAML config and validate required fields and types."""
    if not config_path.exists():
        # Fall back to default config if default file missing, or error if custom
        if config_path.name == "audit.default.yaml":
            return DEFAULT_CONFIG.copy()
        raise FileNotFoundError(f"Specified configuration file '{config_path}' does not exist.")

    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict):
            raise ValueError(f"Config file '{config_path}' must be a YAML dictionary.")
    except Exception as e:
        raise ValueError(f"Failed to parse config file '{config_path}': {e}") from e

    merged = DEFAULT_CONFIG.copy()
    merged.update(cfg)

    # Validate constraints
    if not isinstance(merged["small_cell_threshold"], int) or merged["small_cell_threshold"] < 1:
        raise ValueError("Config error: 'small_cell_threshold' must be an integer >= 1.")
    if not isinstance(merged["min_rows_for_stats"], int) or merged["min_rows_for_stats"] < 1:
        raise ValueError("Config error: 'min_rows_for_stats' must be an integer >= 1.")
    if not isinstance(merged["chunk_size"], int) or merged["chunk_size"] < 10:
        raise ValueError("Config error: 'chunk_size' must be an integer >= 10.")
    if (
        not isinstance(merged["chunk_size_bytes_threshold"], int)
        or merged["chunk_size_bytes_threshold"] <= 0
    ):
        raise ValueError("Config error: 'chunk_size_bytes_threshold' must be an integer > 0.")
    if not isinstance(merged["datetime_column_hints"], list) or not all(
        isinstance(h, str) for h in merged["datetime_column_hints"]
    ):
        raise ValueError("Config error: 'datetime_column_hints' must be a list of strings.")
    if not (0.0 <= float(merged["datetime_parse_threshold"]) <= 1.0):
        raise ValueError(
            "Config error: 'datetime_parse_threshold' must be a float between 0.0 and 1.0."
        )
    if float(merged["gap_multiplier"]) <= 1.0:
        raise ValueError("Config error: 'gap_multiplier' must be a float > 1.0.")
    if not isinstance(merged["suspicious_sentinels"], list):
        raise ValueError("Config error: 'suspicious_sentinels' must be a list of numbers.")
    if not isinstance(merged["quantiles"], list) or not all(
        0.0 <= float(q) <= 1.0 for q in merged["quantiles"]
    ):
        raise ValueError("Config error: 'quantiles' must be a list of floats between 0.0 and 1.0.")

    return merged


def run_audit(
    data_dir: Path | str,
    output_dir: Path | str = "docs/reports",
    config_path: Path | str = "configs/audit.default.yaml",
    participant_regex: str | None = None,
    dictionary_paths: list[str | Path] | None = None,
    verify_checksums_flag: bool = False,
    max_files: int | None = None,
    output_format: str = "both",
    fail_on_empty: bool = True,
    force_chunked: bool = False,
) -> int:
    """Run full dataset audit workflow."""
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    config_path = Path(config_path)

    # 1. Load config
    try:
        config = load_and_validate_config(config_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # 2. Discover files
    discovery = discover_directory(
        data_dir_path=data_dir,
        max_files=max_files,
        participant_regex=participant_regex,
    )

    fingerprint = {
        "total_files": discovery.total_files,
        "total_bytes": discovery.total_bytes,
        "fingerprint_sha256": discovery.fingerprint_sha256,
    }

    truncation_info = {
        "is_truncated": discovery.is_truncated,
        "max_files_limit": discovery.max_files_limit,
    }

    # 3. Check for NO DATA
    if not discovery.exists or discovery.is_empty or len(discovery.tabular_files) == 0:
        report_data = build_audit_data_structure(
            status="NO DATA FOUND",
            data_dir_path=str(data_dir),
            fingerprint=fingerprint,
            config_in_effect=config,
            discovery_result=discovery.to_dict(),
            warnings=discovery.warnings,
            truncation_info=truncation_info,
        )

        if output_format in {"json", "both"}:
            write_json_report(report_data, output_dir / "audit_report.json")
        if output_format in {"md", "both"}:
            write_markdown_report(report_data, output_dir / "audit_report.md")

        print("================================================================================")
        print(" [AUDIT RESULT] STATUS: NO DATA FOUND")
        print("================================================================================")
        print(f"Target directory: {data_dir}")
        print("No supported tabular data files (.csv, .tsv, .txt, .parquet) were detected.")
        print("")
        print(ACQUISITION_GUIDANCE)
        print("================================================================================")
        return 2

    # 4. Group into schema families
    grouped_families = group_schema_families(
        data_dir=data_dir,
        tabular_files=discovery.tabular_files,
        tabular_delimiters=discovery.tabular_delimiters,
    )

    # Determine dominant family
    dominant_sig = max(grouped_families.keys(), key=lambda k: len(grouped_families[k]))

    schema_family_reports = []
    timeseries_reports: dict[str, list[dict[str, Any]]] = {}
    all_warnings = list(discovery.warnings)

    fam_idx = 1
    family_profile_objects = {}

    for sig, files in grouped_families.items():
        fid = f"Family_{fam_idx}"
        fam_idx += 1
        is_dom = sig == dominant_sig

        fam_prof = profile_schema_family(
            family_id=fid,
            column_signature=list(sig),
            files=files,
            data_dir=data_dir,
            delimiters=discovery.tabular_delimiters,
            config=config,
            is_dominant=is_dom,
            force_chunked=force_chunked,
        )
        schema_family_reports.append(fam_prof.to_dict())
        family_profile_objects[fid] = fam_prof
        all_warnings.extend(fam_prof.warnings)

        # Timeseries analysis on candidate columns
        hints = config.get("datetime_column_hints", ["time", "date", "timestamp"])
        candidates = detect_candidate_columns(list(sig), hints)
        fam_ts_list = []
        for cand_col in candidates:
            ts_prof = analyze_timeseries_column(
                col_name=cand_col,
                files=files,
                data_dir=data_dir,
                delimiters=discovery.tabular_delimiters,
                config=config,
            )
            if ts_prof:
                fam_ts_list.append(ts_prof.to_dict())
                all_warnings.extend(ts_prof.warnings)

        if fam_ts_list:
            timeseries_reports[fid] = fam_ts_list

    # 5. Data dictionary conformance (if requested)
    dict_reports = []
    if dictionary_paths:
        for dpath_str in dictionary_paths:
            dpath = Path(dpath_str)
            for fid, fam_prof in family_profile_objects.items():
                d_rep = check_family_conformance(
                    dict_path=dpath,
                    family_id=fid,
                    observed_columns=fam_prof.column_signature,
                    column_profiles=fam_prof.columns,
                )
                dict_reports.append(d_rep.to_dict())
                all_warnings.extend(d_rep.warnings)

    # 6. Checksums (if requested)
    checksum_report_dict = None
    if verify_checksums_flag:
        chk_rep = verify_sha256sums(data_dir)
        checksum_report_dict = chk_rep.to_dict()
        all_warnings.extend(chk_rep.warnings)

    # 7. Assemble report
    report_data = build_audit_data_structure(
        status="DATA PRESENT",
        data_dir_path=str(data_dir),
        fingerprint=fingerprint,
        config_in_effect=config,
        discovery_result=discovery.to_dict(),
        schema_families=schema_family_reports,
        timeseries_profiles=timeseries_reports,
        dictionary_reports=dict_reports,
        checksum_report=checksum_report_dict,
        warnings=all_warnings,
        truncation_info=truncation_info,
    )

    # 8. Write reports
    if output_format in {"json", "both"}:
        write_json_report(report_data, output_dir / "audit_report.json")
    if output_format in {"md", "both"}:
        write_markdown_report(report_data, output_dir / "audit_report.md")

    print("================================================================================")
    print(" [AUDIT RESULT] STATUS: DATA PRESENT")
    print("================================================================================")
    print(f"Target directory: {data_dir}")
    print(f"Total files: {discovery.total_files:,} ({discovery.total_bytes:,} bytes)")
    print(
        f"Tabular files profiled: {len(discovery.tabular_files):,} across "
        f"{len(grouped_families)} schema families."
    )
    if discovery.archives:
        print(f"Archives detected: {len(discovery.archives)} (manual extraction required).")
    if discovery.image_count:
        print(f"Images inventoried: {discovery.image_count} (unopened).")
    print(f"Reports written to: {output_dir}")
    print("================================================================================")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for dtwin-audit."""
    parser = argparse.ArgumentParser(
        prog="dtwin-audit",
        description="Dataset audit and privacy-preserving profiling tool.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.environ.get("DTWIN_DATA_DIR"),
        help="Path to dataset directory (defaults to DTWIN_DATA_DIR environment variable).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/reports",
        help="Directory to save audit_report.json and audit_report.md (default: docs/reports).",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/audit.default.yaml",
        help="Path to YAML configuration file (default: configs/audit.default.yaml).",
    )
    parser.add_argument(
        "--participant-regex",
        type=str,
        default=None,
        help="Custom regex to extract participant identifier from relative path.",
    )
    parser.add_argument(
        "--dictionary",
        dest="dictionaries",
        action="append",
        type=str,
        default=None,
        help="Path to official data dictionary CSV (repeatable for multiple dictionaries).",
    )
    parser.add_argument(
        "--verify-checksums",
        action="store_true",
        default=False,
        help="Verify files against SHA256SUMS.txt if present in data directory.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum number of files to process before truncating discovery.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "md", "both"],
        default="both",
        help="Output report format (default: both).",
    )
    parser.add_argument(
        "--fail-on-empty",
        action="store_true",
        default=True,
        help="Exit with non-zero exit code 2 if no tabular files are found (default: True).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI main function."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.data_dir:
        parser.print_usage(sys.stderr)
        print(
            "Error: --data-dir PATH is required unless DTWIN_DATA_DIR environment variable is set.",
            file=sys.stderr,
        )
        return 1

    return run_audit(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        config_path=args.config,
        participant_regex=args.participant_regex,
        dictionary_paths=args.dictionaries,
        verify_checksums_flag=args.verify_checksums,
        max_files=args.max_files,
        output_format=args.format,
        fail_on_empty=args.fail_on_empty,
    )


if __name__ == "__main__":
    sys.exit(main())
