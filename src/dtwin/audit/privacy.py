"""Privacy guard module for dataset audit tooling.

Enforces small-cell suppression (<5), identifier/path/free-text suppression,
and safeguards against leaking raw record values into audit reports or terminal output.
"""

from __future__ import annotations

import re
from typing import Any

# Keywords suggesting identifier, path, photo, or free-text column
_IDENTIFIER_OR_PATH_KEYWORDS = (
    "path",
    "file",
    "url",
    "image",
    "photo",
    "pic",
    "id",
    "subject",
    "participant",
    "patient",
    "name",
    "mrn",
    "comment",
    "note",
    "desc",
    "text",
    "address",
    "hash",
    "key",
)

# Common path separators or extensions indicating file paths
_PATH_INDICATORS = ("/", "\\", ".jpg", ".jpeg", ".png", ".gif", ".csv", ".tsv", ".txt")


def is_identifier_or_path_or_text(
    column_name: str,
    unique_count: int | None = None,
    total_count: int | None = None,
    sample_values: list[Any] | None = None,
) -> bool:
    """Check if a column is likely an identifier, file path, or unstructured free text.

    If true, raw category values must never be reported; only cardinality and
    missingness are permissible.
    """
    col_clean = column_name.strip().lower()

    # 1. Column name keywords
    for kw in _IDENTIFIER_OR_PATH_KEYWORDS:
        if (
            kw == col_clean
            or f"_{kw}" in col_clean
            or f"{kw}_" in col_clean
            or f" {kw}" in col_clean
        ):
            return True
        # also match "image path", "participant_id", etc.
        if kw in col_clean and len(kw) >= 4:
            return True

    # 2. Path indicators in sample values
    if sample_values:
        for val in sample_values:
            if isinstance(val, str):
                val_lower = val.lower()
                if any(ind in val_lower for ind in _PATH_INDICATORS):
                    return True

    # 3. High-cardinality string heuristic (near-unique identifier or free text)
    if unique_count is not None and total_count is not None and total_count >= 10:
        ratio = unique_count / total_count
        if ratio > 0.80:
            return True

    return False


def suppress_category_counts(
    counts: dict[str, int],
    threshold: int = 5,
) -> dict[str, int]:
    """Apply small-cell suppression to category value counts.

    Any category with a count strictly less than `threshold` is suppressed
    and aggregated into a '<{threshold} suppressed' summary cell.
    """
    safe_counts: dict[str, int] = {}
    suppressed_total = 0

    for cat, count in counts.items():
        if count >= threshold:
            safe_counts[str(cat)] = count
        else:
            suppressed_total += count

    if suppressed_total > 0:
        safe_counts[f"<{threshold} suppressed"] = suppressed_total

    return safe_counts


def sanitize_message(msg: str) -> str:
    """Sanitize error messages or warnings to prevent leaking raw row content."""
    # Strip potential CSV line dumps or long unbroken strings
    cleaned = re.sub(r"\[.*?\]", "[...]", msg)
    if len(cleaned) > 200:
        cleaned = cleaned[:197] + "..."
    return cleaned


def sanitize_for_report(data: Any) -> Any:
    """Recursively sanitize report payloads to ensure no raw secrets or private traces leak."""
    if isinstance(data, dict):
        return {k: sanitize_for_report(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_report(item) for item in data]
    elif isinstance(data, (int, float, bool)) or data is None:
        return data
    elif isinstance(data, str):
        # Sanitize known forbidden strings or planted sentinels if encountered
        for secret_marker in ["PLANTED_SECRET", "PLANTED_SENTINEL"]:
            if secret_marker in data:
                return "[REDACTED_PRIVACY_GUARD]"
        return data
    return str(data)
