"""Directory discovery and file classification module.

Inventories files deterministically, computes directory fingerprint,
classifies tabular/archive/image files, and extracts participant identifiers.
"""

from __future__ import annotations

import csv
import hashlib
import re
import tarfile
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Supported tabular file extensions
TABULAR_EXTENSIONS = {".csv", ".tsv", ".txt", ".parquet"}

# Archive file extensions
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz"}

# Image file extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}


@dataclass
class ArchiveInfo:
    relative_path: str
    size_bytes: int
    member_count: int | None
    uncompressed_bytes: int | None
    archive_type: str
    extraction_required_warning: str = (
        "Archive detected. Manual extraction into data directory is required before audit."
    )


@dataclass
class ParticipantSummary:
    rule_used_description: str
    rule_match_counts: dict[str, int]
    distinct_participant_count: int
    distinct_identifiers: list[str]
    files_without_id_count: int
    files_per_id_distribution: dict[str, float]  # min, median, max, total
    numeric_id_gaps: list[int]
    is_numeric_sequence: bool
    inference_note: str = (
        "Participant identifiers are inferred heuristically from file/directory paths, "
        "not from verified metadata."
    )


@dataclass
class DiscoveryResult:
    data_dir: str
    exists: bool
    is_empty: bool
    total_files: int
    total_bytes: int
    fingerprint_sha256: str
    is_truncated: bool
    max_files_limit: int | None
    extension_counts: dict[str, int]
    extension_bytes: dict[str, int]
    tabular_files: list[str]  # relative paths
    tabular_delimiters: dict[str, str]  # relative path -> delimiter
    unsupported_tabular_files: list[dict[str, str]]
    archives: list[ArchiveInfo]
    image_count: int
    image_counts_by_extension: dict[str, int]
    image_bytes_by_extension: dict[str, int]
    participant_summary: ParticipantSummary | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _sniff_delimiter(file_path: Path) -> str | None:
    """Sniff tabular delimiter without loading entire file into memory."""
    fname_lower = file_path.name.lower()
    if fname_lower.startswith(("sha256", "license", "readme", ".git")):
        return None

    ext = file_path.suffix.lower()
    if ext == ".tsv":
        return "\t"
    if ext == ".csv":
        return ","

    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            sample = f.read(4096)
        if not sample or "\n" not in sample:
            return None
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=",\t|;")
        return dialect.delimiter
    except Exception:
        return None


def _inspect_archive(file_path: Path, rel_path: str) -> ArchiveInfo:
    """Inspect archive member count and uncompressed size without extracting."""
    size_bytes = file_path.stat().st_size
    suffix = file_path.suffix.lower()
    member_count = None
    uncompressed_bytes = None
    archive_type = suffix.lstrip(".")

    try:
        if suffix == ".zip":
            archive_type = "zip"
            with zipfile.ZipFile(file_path, "r") as zf:
                infos = zf.infolist()
                member_count = len(infos)
                uncompressed_bytes = sum(z.file_size for z in infos)
        elif suffix in {".tar", ".tgz", ".bz2", ".xz"} or ".tar." in file_path.name.lower():
            archive_type = "tar"
            with tarfile.open(file_path, "r:*") as tf:
                members = tf.getmembers()
                member_count = len(members)
                uncompressed_bytes = sum(m.size for m in members)
        elif suffix == ".gz":
            archive_type = "gzip"
            # Cannot determine uncompressed size without reading
    except Exception:
        pass

    return ArchiveInfo(
        relative_path=rel_path,
        size_bytes=size_bytes,
        member_count=member_count,
        uncompressed_bytes=uncompressed_bytes,
        archive_type=archive_type,
    )


def extract_participant_id(
    rel_path: str,
    custom_regex: str | None = None,
) -> tuple[str | None, str]:
    """Extract participant identifier from relative path.

    Returns (participant_id, rule_name).
    """
    path_obj = Path(rel_path)

    # 1. Custom regex if provided
    if custom_regex:
        match = re.search(custom_regex, rel_path)
        if match:
            id_str = match.group(1) if match.groups() else match.group(0)
            return id_str, "custom_regex"
        return None, "custom_regex_unmatched"

    # 2. First run of digits in filename
    fname = path_obj.name
    match = re.search(r"(\d+)", fname)
    if match:
        return match.group(1), "filename_digits"

    # 3. Fallback: run of digits in parent directory name
    pname = path_obj.parent.name
    match = re.search(r"(\d+)", pname)
    if match:
        return match.group(1), "parent_dir_digits"

    return None, "none"


def summarize_participants(
    rel_paths: list[str],
    custom_regex: str | None = None,
) -> ParticipantSummary:
    """Analyze participant identifiers across relative paths."""
    rule_counts: Counter[str] = Counter()
    id_to_files: dict[str, list[str]] = {}
    files_without_id = 0

    rule_description = (
        f"Custom regex: '{custom_regex}'"
        if custom_regex
        else "Default: First run of digits in filename, falling back to parent directory"
    )

    for rel_path in rel_paths:
        pid, rule = extract_participant_id(rel_path, custom_regex)
        rule_counts[rule] += 1
        if pid is not None:
            id_to_files.setdefault(pid, []).append(rel_path)
        else:
            files_without_id += 1

    distinct_ids = sorted(
        id_to_files.keys(), key=lambda x: (int(x) if x.isdigit() else float("inf"), x)
    )

    # File counts per ID distribution
    counts = [len(f_list) for f_list in id_to_files.values()]
    if counts:
        counts_sorted = sorted(counts)
        n = len(counts_sorted)
        median_val = (
            counts_sorted[n // 2]
            if n % 2 != 0
            else (counts_sorted[n // 2 - 1] + counts_sorted[n // 2]) / 2.0
        )
        dist = {
            "min": float(counts_sorted[0]),
            "median": float(median_val),
            "max": float(counts_sorted[-1]),
            "total_files_with_id": float(sum(counts_sorted)),
        }
    else:
        dist = {"min": 0.0, "median": 0.0, "max": 0.0, "total_files_with_id": 0.0}

    # Numeric sequence gap detection
    numeric_gaps: list[int] = []
    is_numeric = False
    if distinct_ids and all(i.isdigit() for i in distinct_ids):
        is_numeric = True
        int_ids = sorted(int(i) for i in distinct_ids)
        min_id, max_id = int_ids[0], int_ids[-1]
        all_expected = set(range(min_id, max_id + 1))
        numeric_gaps = sorted(all_expected - set(int_ids))

    return ParticipantSummary(
        rule_used_description=rule_description,
        rule_match_counts=dict(rule_counts),
        distinct_participant_count=len(distinct_ids),
        distinct_identifiers=distinct_ids,
        files_without_id_count=files_without_id,
        files_per_id_distribution=dist,
        numeric_id_gaps=numeric_gaps,
        is_numeric_sequence=is_numeric,
    )


def discover_directory(
    data_dir_path: str | Path,
    max_files: int | None = None,
    participant_regex: str | None = None,
) -> DiscoveryResult:
    """Discover, classify, and fingerprint files in the target data directory."""
    data_dir = Path(data_dir_path)

    if not data_dir.exists():
        return DiscoveryResult(
            data_dir=str(data_dir),
            exists=False,
            is_empty=True,
            total_files=0,
            total_bytes=0,
            fingerprint_sha256="",
            is_truncated=False,
            max_files_limit=max_files,
            extension_counts={},
            extension_bytes={},
            tabular_files=[],
            tabular_delimiters={},
            unsupported_tabular_files=[],
            archives=[],
            image_count=0,
            image_counts_by_extension={},
            image_bytes_by_extension={},
            warnings=[f"Data directory '{data_dir}' does not exist."],
        )

    # Deterministic sorted inventory (relative paths normalized with forward slashes)
    all_files_raw = [p for p in data_dir.rglob("*") if p.is_file() and not p.name.startswith(".")]
    all_files_sorted = sorted(
        all_files_raw,
        key=lambda p: p.relative_to(data_dir).as_posix(),
    )

    if not all_files_sorted:
        return DiscoveryResult(
            data_dir=str(data_dir),
            exists=True,
            is_empty=True,
            total_files=0,
            total_bytes=0,
            fingerprint_sha256="",
            is_truncated=False,
            max_files_limit=max_files,
            extension_counts={},
            extension_bytes={},
            tabular_files=[],
            tabular_delimiters={},
            unsupported_tabular_files=[],
            archives=[],
            image_count=0,
            image_counts_by_extension={},
            image_bytes_by_extension={},
            warnings=[f"Data directory '{data_dir}' contains no files."],
        )

    # Compute data directory fingerprint over ALL files before truncation
    # Fingerprint is SHA256 of sorted relative_path:size lines
    fingerprint_hasher = hashlib.sha256()
    total_bytes = 0
    for p in all_files_sorted:
        rel = p.relative_to(data_dir).as_posix()
        sz = p.stat().st_size
        total_bytes += sz
        fingerprint_hasher.update(f"{rel}:{sz}\n".encode())
    fingerprint_sha256 = fingerprint_hasher.hexdigest()

    is_truncated = False
    files_to_process = all_files_sorted
    if max_files is not None and len(all_files_sorted) > max_files:
        files_to_process = all_files_sorted[:max_files]
        is_truncated = True

    # Check parquet support
    has_pyarrow = False
    try:
        import pyarrow  # type: ignore[import-not-found]  # noqa: F401

        has_pyarrow = True
    except ImportError:
        pass

    extension_counts: Counter[str] = Counter()
    extension_bytes: Counter[str] = Counter()
    tabular_files: list[str] = []
    tabular_delimiters: dict[str, str] = {}
    unsupported_tabular_files: list[dict[str, str]] = []
    archives: list[ArchiveInfo] = []
    image_count = 0
    image_counts_by_ext: Counter[str] = Counter()
    image_bytes_by_ext: Counter[str] = Counter()
    warnings: list[str] = []

    if is_truncated:
        warnings.append(
            f"Discovery truncated to {max_files} files "
            f"(out of {len(all_files_sorted)} total files)."
        )

    for p in files_to_process:
        rel = p.relative_to(data_dir).as_posix()
        ext = p.suffix.lower()
        sz = p.stat().st_size

        extension_counts[ext] += 1
        extension_bytes[ext] += sz

        if ext in IMAGE_EXTENSIONS:
            image_count += 1
            image_counts_by_ext[ext] += 1
            image_bytes_by_ext[ext] += sz
            # DO NOT OPEN IMAGES
        elif ext in ARCHIVE_EXTENSIONS or ".tar." in p.name.lower():
            arch_info = _inspect_archive(p, rel)
            archives.append(arch_info)
            warnings.append(
                f"Archive detected at '{rel}' ({sz:,} bytes). "
                "Must be manually extracted before audit."
            )
        elif ext in TABULAR_EXTENSIONS:
            if ext == ".parquet":
                if has_pyarrow:
                    tabular_files.append(rel)
                    tabular_delimiters[rel] = "parquet"
                else:
                    unsupported_tabular_files.append(
                        {
                            "file": rel,
                            "reason": "Parquet candidate detected but pyarrow is not installed.",
                        }
                    )
                    warnings.append(f"Parquet file '{rel}' skipped: pyarrow is not installed.")
            elif ext in {".csv", ".tsv"}:
                tabular_files.append(rel)
                tabular_delimiters[rel] = "\t" if ext == ".tsv" else ","
            elif ext == ".txt":
                delim = _sniff_delimiter(p)
                if delim in {",", "\t", "|", ";"}:
                    tabular_files.append(rel)
                    tabular_delimiters[rel] = delim

    # Participant summary across tabular and archive paths
    participant_summary = summarize_participants(
        [p.relative_to(data_dir).as_posix() for p in files_to_process],
        custom_regex=participant_regex,
    )

    return DiscoveryResult(
        data_dir=str(data_dir),
        exists=True,
        is_empty=False,
        total_files=len(all_files_sorted),
        total_bytes=total_bytes,
        fingerprint_sha256=fingerprint_sha256,
        is_truncated=is_truncated,
        max_files_limit=max_files,
        extension_counts=dict(extension_counts),
        extension_bytes=dict(extension_bytes),
        tabular_files=tabular_files,
        tabular_delimiters=tabular_delimiters,
        unsupported_tabular_files=unsupported_tabular_files,
        archives=archives,
        image_count=image_count,
        image_counts_by_extension=dict(image_counts_by_ext),
        image_bytes_by_extension=dict(image_bytes_by_ext),
        participant_summary=participant_summary,
        warnings=warnings,
    )
