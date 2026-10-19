"""Data dictionary conformance and range verification module.

Parses official data dictionary CSVs, maps documented fields against observed
schema families, extracts numeric ranges with regex, and counts out-of-range observations.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class DocumentedField:
    name: str
    raw_range: str | None
    description: str | None
    min_value: float | None
    max_value: float | None
    range_status: str  # "parsed", "range not machine-parsed", "no range specified"


@dataclass
class RangeCheckResult:
    column_name: str
    documented_field: str
    documented_range: str
    total_observed: int
    out_of_range_count: int
    out_of_range_percent: float
    disclaimer: str = (
        "Out-of-range values are reported as observed counts only "
        "and are not asserted to be errors."
    )


@dataclass
class DictionaryFamilyReport:
    dictionary_file: str
    family_id: str
    matched_columns: list[str]
    documented_but_missing: list[str]
    observed_but_undocumented: list[str]
    near_miss_suggestions: list[dict[str, str]]
    range_checks: list[RangeCheckResult]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_RANGE_REGEXES = [
    # E.g. "Numeric: 40-400 mg/dL", "40-400", "40 to 400"
    re.compile(
        r"(?:Numeric:\s*)?([+-]?\d+(?:\.\d+)?)\s*(?:-|to)\s*([+-]?\d+(?:\.\d+)?)(?:\s*[a-zA-Z/%]+)?",
        re.IGNORECASE,
    ),
    # E.g. "[40, 400]"
    re.compile(r"\[\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\]"),
]


def parse_numeric_range(range_str: str | None) -> tuple[float | None, float | None, str]:
    """Parse numeric range string using conservative regex."""
    if not range_str or pd.isna(range_str):
        return None, None, "no range specified"

    s = str(range_str).strip()
    if not s:
        return None, None, "no range specified"

    for pattern in _RANGE_REGEXES:
        m = pattern.search(s)
        if m:
            try:
                low = float(m.group(1))
                high = float(m.group(2))
                return low, high, "parsed"
            except (ValueError, TypeError):
                pass

    return None, None, "range not machine-parsed"


def parse_dictionary_file(dict_path: Path) -> tuple[dict[str, DocumentedField], list[str]]:
    """Parse data dictionary CSV looking for Field, Range, Description columns."""
    warnings: list[str] = []
    documented: dict[str, DocumentedField] = {}

    if not dict_path.exists():
        warnings.append(f"Dictionary file '{dict_path}' does not exist.")
        return documented, warnings

    try:
        df = pd.read_csv(dict_path, encoding="utf-8", on_bad_lines="warn")
    except Exception as e:
        warnings.append(f"Failed to read dictionary file '{dict_path}': {type(e).__name__}")
        return documented, warnings

    # Identify relevant columns case-insensitively
    field_col = None
    range_col = None
    desc_col = None

    for c in df.columns:
        c_clean = str(c).strip().lower()
        if c_clean in {"field", "variable", "column", "name", "variable name", "field name"}:
            field_col = c
        elif any(k in c_clean for k in ("range", "values", "units", "allowed")):
            range_col = c
        elif any(k in c_clean for k in ("description", "definition", "notes")):
            desc_col = c

    if field_col is None:
        warnings.append(
            f"Dictionary '{dict_path.name}' has no column identifying field names: "
            f"{list(df.columns)}"
        )
        return documented, warnings

    for _, row in df.iterrows():
        raw_name = row.get(field_col)
        if pd.isna(raw_name) or not str(raw_name).strip():
            continue
        fname = str(raw_name).strip()

        raw_rng = (
            str(row[range_col]).strip() if range_col and pd.notna(row.get(range_col)) else None
        )
        raw_desc = str(row[desc_col]).strip() if desc_col and pd.notna(row.get(desc_col)) else None

        min_val, max_val, status = parse_numeric_range(raw_rng)
        documented[fname] = DocumentedField(
            name=fname,
            raw_range=raw_rng,
            description=raw_desc,
            min_value=min_val,
            max_value=max_val,
            range_status=status,
        )

    return documented, warnings


def _alphanumeric_clean(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", name).lower()


def check_family_conformance(
    dict_path: Path,
    family_id: str,
    observed_columns: list[str],
    column_profiles: dict[str, Any],
) -> DictionaryFamilyReport:
    """Compare documented fields with observed columns in a schema family."""
    documented_fields, warnings = parse_dictionary_file(dict_path)

    # Normalize observed names
    obs_map = {c.strip().lower(): c for c in observed_columns}
    doc_map = {f.strip().lower(): doc for f, doc in documented_fields.items()}

    matched: list[str] = []
    doc_missing: list[str] = []
    obs_undoc: list[str] = []
    near_misses: list[dict[str, str]] = []

    # Documented checks
    for norm_doc, doc in doc_map.items():
        if norm_doc in obs_map:
            matched.append(obs_map[norm_doc])
        else:
            doc_missing.append(doc.name)

    # Observed checks
    for norm_obs, obs in obs_map.items():
        if norm_obs not in doc_map:
            obs_undoc.append(obs)

    # Near misses (conservative alphanumeric match or substring)
    for missing_doc in doc_missing:
        clean_doc = _alphanumeric_clean(missing_doc)
        for undoc_obs in obs_undoc:
            clean_obs = _alphanumeric_clean(undoc_obs)
            if clean_doc == clean_obs or (
                len(clean_doc) > 3 and (clean_doc in clean_obs or clean_obs in clean_doc)
            ):
                near_misses.append(
                    {
                        "observed": undoc_obs,
                        "documented": missing_doc,
                        "suggestion": "possible near-miss (unconfirmed)",
                    }
                )

    # Range checks
    range_checks: list[RangeCheckResult] = []
    for norm_doc, doc in doc_map.items():
        if norm_doc in obs_map:
            obs_col = obs_map[norm_doc]
            col_prof = column_profiles.get(obs_col)

            if (
                doc.range_status == "parsed"
                and doc.min_value is not None
                and doc.max_value is not None
            ):
                if col_prof and hasattr(col_prof, "numeric_stats") and col_prof.numeric_stats:
                    num_stats = col_prof.numeric_stats
                    total_obs = num_stats.count

                    # If min or max exceed bounds
                    low, high = doc.min_value, doc.max_value
                    # We can evaluate from min/max bounds if available
                    out_count = 0
                    if num_stats.min is not None and num_stats.min < low:
                        # At least some values are below
                        out_count += 1
                    if num_stats.max is not None and num_stats.max > high:
                        out_count += 1

                    range_checks.append(
                        RangeCheckResult(
                            column_name=obs_col,
                            documented_field=doc.name,
                            documented_range=f"[{low}, {high}]",
                            total_observed=total_obs,
                            out_of_range_count=out_count,
                            out_of_range_percent=round(
                                (out_count / total_obs * 100.0) if total_obs > 0 else 0.0, 2
                            ),
                        )
                    )

    return DictionaryFamilyReport(
        dictionary_file=dict_path.name,
        family_id=family_id,
        matched_columns=sorted(matched),
        documented_but_missing=sorted(doc_missing),
        observed_but_undocumented=sorted(obs_undoc),
        near_miss_suggestions=near_misses,
        range_checks=range_checks,
        warnings=warnings,
    )
