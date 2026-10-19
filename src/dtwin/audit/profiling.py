"""Tabular profiling module.

Performs schema signature grouping into families, aggregates missingness,
computes numeric statistics, detects suspicious sentinels, and applies small-cell
and small-table privacy protections.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from dtwin.audit.privacy import (
    is_identifier_or_path_or_text,
    suppress_category_counts,
)


@dataclass
class NumericStats:
    count: int
    missing_count: int
    missing_percent: float
    non_finite_count: int
    zero_count: int
    sentinel_counts: dict[str, int]
    min: float | None
    max: float | None
    mean: float | None
    median: float | None
    quantiles: dict[str, float]  # e.g. "0.05": val


@dataclass
class CategoricalStats:
    total_count: int
    missing_count: int
    missing_percent: float
    cardinality: int
    is_identifier_or_path_or_text: bool
    category_counts: dict[str, int] | None  # None if identifier/path or suppressed


@dataclass
class ColumnProfile:
    name: str
    inferred_dtype: str
    is_dtype_consistent: bool
    observed_dtypes: list[str]
    missing_count: int
    missing_percent: float
    files_all_missing_count: int
    numeric_stats: NumericStats | None = None
    categorical_stats: CategoricalStats | None = None
    is_stats_suppressed: bool = False
    suppression_reason: str | None = None


@dataclass
class SchemaFamily:
    family_id: str
    column_signature: list[str]
    file_count: int
    files: list[str]
    total_rows: int
    rows_per_file: dict[str, float]  # min, median, max, total
    is_dominant_family: bool
    columns: dict[str, ColumnProfile]
    is_small_table_suppressed: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_table_chunks(
    file_path: Path,
    delimiter: str = ",",
    chunk_size: int = 50000,
    chunk_size_bytes_threshold: int = 52428800,
    force_chunked: bool = False,
):
    """Yield DataFrame chunks, chunking if file exceeds byte threshold or if forced."""
    file_size = file_path.stat().st_size
    should_chunk = force_chunked or (file_size >= chunk_size_bytes_threshold)

    if file_path.suffix.lower() == ".parquet":
        df = pd.read_parquet(file_path)
        yield df
        return

    if should_chunk:
        reader = pd.read_csv(
            file_path,
            sep=delimiter,
            chunksize=chunk_size,
            low_memory=False,
            encoding="utf-8",
            on_bad_lines="warn",
        )
        yield from reader
    else:
        df = pd.read_csv(
            file_path,
            sep=delimiter,
            low_memory=False,
            encoding="utf-8",
            on_bad_lines="warn",
        )
        yield df


def get_column_signature(file_path: Path, delimiter: str = ",") -> list[str]:
    """Read the header row to extract column signature without reading entire file."""
    if file_path.suffix.lower() == ".parquet":
        df = pd.read_parquet(file_path)
        return list(df.columns)

    df = pd.read_csv(
        file_path,
        sep=delimiter,
        nrows=0,
        encoding="utf-8",
        on_bad_lines="warn",
    )
    return list(df.columns)


def group_schema_families(
    data_dir: Path,
    tabular_files: list[str],
    tabular_delimiters: dict[str, str],
) -> dict[tuple[str, ...], list[str]]:
    """Group tabular files by identical column signature (ordered column list)."""
    families: dict[tuple[str, ...], list[str]] = {}
    for rel_path in tabular_files:
        full_path = data_dir / rel_path
        delim = tabular_delimiters.get(rel_path, ",")
        try:
            sig = tuple(get_column_signature(full_path, delim))
            families.setdefault(sig, []).append(rel_path)
        except Exception:
            # File unreadable or empty
            families.setdefault((), []).append(rel_path)
    return families


def profile_schema_family(
    family_id: str,
    column_signature: list[str],
    files: list[str],
    data_dir: Path,
    delimiters: dict[str, str],
    config: dict[str, Any],
    is_dominant: bool = False,
    force_chunked: bool = False,
) -> SchemaFamily:
    """Profile a schema family in an aggregate-only, privacy-preserving manner."""
    small_cell_threshold = int(config.get("small_cell_threshold", 5))
    min_rows_for_stats = int(config.get("min_rows_for_stats", 5))
    chunk_size = int(config.get("chunk_size", 50000))
    chunk_threshold = int(config.get("chunk_size_bytes_threshold", 52428800))
    suspicious_sentinels = [
        float(s) for s in config.get("suspicious_sentinels", [-999, -1, 400, 800, 9999])
    ]
    quantiles_to_calc = [float(q) for q in config.get("quantiles", [0.05, 0.25, 0.5, 0.75, 0.95])]

    file_row_counts: list[int] = []
    col_dtypes_across_files: dict[str, set[str]] = {c: set() for c in column_signature}
    col_null_counts: Counter[str] = Counter()
    col_empty_file_counts: Counter[str] = Counter()

    # Per-column accumulators
    numeric_values: dict[str, list[np.ndarray]] = {c: [] for c in column_signature}
    numeric_non_finite: Counter[str] = Counter()
    numeric_zeros: Counter[str] = Counter()
    numeric_sentinel_counts: dict[str, Counter[float]] = {c: Counter() for c in column_signature}

    categorical_counters: dict[str, Counter[str]] = {c: Counter() for c in column_signature}
    categorical_unique_sets: dict[str, set[str]] = {c: set() for c in column_signature}
    sample_values_map: dict[str, list[Any]] = {c: [] for c in column_signature}
    warnings: list[str] = []

    for rel_path in files:
        full_path = data_dir / rel_path
        delim = delimiters.get(rel_path, ",")
        file_rows = 0
        file_col_nulls: Counter[str] = Counter()

        try:
            chunks = read_table_chunks(
                full_path,
                delimiter=delim,
                chunk_size=chunk_size,
                chunk_size_bytes_threshold=chunk_threshold,
                force_chunked=force_chunked,
            )
            for chunk in chunks:
                n_chunk = len(chunk)
                file_rows += n_chunk

                for col in column_signature:
                    if col not in chunk.columns:
                        continue
                    series = chunk[col]
                    col_dtypes_across_files[col].add(str(series.dtype))

                    # Missingness
                    nulls = int(series.isna().sum())
                    file_col_nulls[col] += nulls
                    col_null_counts[col] += nulls

                    # Samples for privacy heuristics
                    if len(sample_values_map[col]) < 20:
                        non_null_samples = series.dropna().head(10).tolist()
                        sample_values_map[col].extend(non_null_samples)

                    # Numeric check
                    if pd.api.types.is_numeric_dtype(series):
                        valid_num = pd.to_numeric(series, errors="coerce")
                        # Non-finite (inf or -inf)
                        inf_count = int(np.isinf(valid_num).sum())
                        numeric_non_finite[col] += inf_count

                        clean_num = valid_num.dropna()
                        if not clean_num.empty:
                            arr = clean_num.values.astype(np.float64)
                            arr_finite = arr[np.isfinite(arr)]
                            numeric_values[col].append(arr_finite)

                            # Zero count
                            zeros = int((arr_finite == 0.0).sum())
                            numeric_zeros[col] += zeros

                            # Sentinels
                            for s in suspicious_sentinels:
                                s_count = int((arr_finite == s).sum())
                                if s_count > 0:
                                    numeric_sentinel_counts[col][s] += s_count
                    else:
                        # Categorical / string
                        clean_str = series.dropna().astype(str)
                        if not clean_str.empty:
                            # Keep unique set bounded
                            if len(categorical_unique_sets[col]) < 50000:
                                categorical_unique_sets[col].update(clean_str.unique())
                            # Count categories
                            counts = clean_str.value_counts().to_dict()
                            for k, v in counts.items():
                                categorical_counters[col][k] += v

            file_row_counts.append(file_rows)
            for col in column_signature:
                if file_rows > 0 and file_col_nulls[col] == file_rows:
                    col_empty_file_counts[col] += 1

        except Exception as e:
            warnings.append(f"Failed to profile file '{rel_path}': {type(e).__name__}")
            file_row_counts.append(0)

    total_rows = sum(file_row_counts)

    # Compute row counts per file
    if file_row_counts:
        sorted_counts = sorted(file_row_counts)
        n = len(sorted_counts)
        median_rc = (
            sorted_counts[n // 2]
            if n % 2 != 0
            else (sorted_counts[n // 2 - 1] + sorted_counts[n // 2]) / 2.0
        )
        rows_per_file = {
            "min": float(sorted_counts[0]),
            "median": float(median_rc),
            "max": float(sorted_counts[-1]),
            "total": float(total_rows),
        }
    else:
        rows_per_file = {"min": 0.0, "median": 0.0, "max": 0.0, "total": 0.0}

    # Small table protection check
    is_small_table = total_rows < min_rows_for_stats

    # Build column profiles
    columns_profiled: dict[str, ColumnProfile] = {}

    for col in column_signature:
        observed_dtypes = sorted(col_dtypes_across_files[col])
        is_consistent = len(observed_dtypes) <= 1
        inferred_dtype = observed_dtypes[0] if observed_dtypes else "unknown"

        missing_count = col_null_counts[col]
        missing_pct = (missing_count / total_rows * 100.0) if total_rows > 0 else 0.0
        empty_files = col_empty_file_counts[col]

        if is_small_table:
            # Small table suppression: only row count, dtypes, missingness
            columns_profiled[col] = ColumnProfile(
                name=col,
                inferred_dtype=inferred_dtype,
                is_dtype_consistent=is_consistent,
                observed_dtypes=observed_dtypes,
                missing_count=missing_count,
                missing_percent=round(missing_pct, 2),
                files_all_missing_count=empty_files,
                numeric_stats=None,
                is_stats_suppressed=True,
                suppression_reason=(
                    f"Small table suppression: family total rows ({total_rows}) "
                    f"< min_rows_for_stats ({min_rows_for_stats})"
                ),
            )
            continue

        # Check if numeric
        is_num = any("int" in dt or "float" in dt for dt in observed_dtypes)
        if is_num and numeric_values[col]:
            all_arr = (
                np.concatenate(numeric_values[col])
                if numeric_values[col]
                else np.array([], dtype=np.float64)
            )
            count_obs = len(all_arr)

            sentinel_map = {
                f"{s:g}": int(numeric_sentinel_counts[col].get(s, 0)) for s in suspicious_sentinels
            }

            if count_obs > 0:
                min_val = float(np.min(all_arr))
                max_val = float(np.max(all_arr))
                mean_val = float(np.mean(all_arr))
                median_val = float(np.median(all_arr))

                q_dict = {
                    f"{q:g}": round(float(np.quantile(all_arr, q)), 4) for q in quantiles_to_calc
                }
            else:
                min_val, max_val, mean_val, median_val = None, None, None, None
                q_dict = {}

            num_stats = NumericStats(
                count=count_obs,
                missing_count=missing_count,
                missing_percent=round(missing_pct, 2),
                non_finite_count=numeric_non_finite[col],
                zero_count=numeric_zeros[col],
                sentinel_counts=sentinel_map,
                min=round(min_val, 4) if min_val is not None else None,
                max=round(max_val, 4) if max_val is not None else None,
                mean=round(mean_val, 4) if mean_val is not None else None,
                median=round(median_val, 4) if median_val is not None else None,
                quantiles=q_dict,
            )

            columns_profiled[col] = ColumnProfile(
                name=col,
                inferred_dtype=inferred_dtype,
                is_dtype_consistent=is_consistent,
                observed_dtypes=observed_dtypes,
                missing_count=missing_count,
                missing_percent=round(missing_pct, 2),
                files_all_missing_count=empty_files,
                numeric_stats=num_stats,
                categorical_stats=None,
                is_stats_suppressed=False,
            )
        else:
            # Categorical / string profile
            cardinality = len(categorical_unique_sets[col])
            is_id_or_path = is_identifier_or_path_or_text(
                column_name=col,
                unique_count=cardinality,
                total_count=total_rows - missing_count,
                sample_values=sample_values_map[col],
            )

            if is_id_or_path:
                cat_counts = None  # suppressed for privacy!
            else:
                raw_counts = dict(categorical_counters[col].most_common(20))
                cat_counts = suppress_category_counts(raw_counts, threshold=small_cell_threshold)

            cat_stats = CategoricalStats(
                total_count=total_rows - missing_count,
                missing_count=missing_count,
                missing_percent=round(missing_pct, 2),
                cardinality=cardinality,
                is_identifier_or_path_or_text=is_id_or_path,
                category_counts=cat_counts,
            )

            columns_profiled[col] = ColumnProfile(
                name=col,
                inferred_dtype=inferred_dtype,
                is_dtype_consistent=is_consistent,
                observed_dtypes=observed_dtypes,
                missing_count=missing_count,
                missing_percent=round(missing_pct, 2),
                files_all_missing_count=empty_files,
                numeric_stats=None,
                categorical_stats=cat_stats,
                is_stats_suppressed=False,
            )

    return SchemaFamily(
        family_id=family_id,
        column_signature=column_signature,
        file_count=len(files),
        files=files,
        total_rows=total_rows,
        rows_per_file=rows_per_file,
        is_dominant_family=is_dominant,
        columns=columns_profiled,
        is_small_table_suppressed=is_small_table,
        warnings=warnings,
    )
