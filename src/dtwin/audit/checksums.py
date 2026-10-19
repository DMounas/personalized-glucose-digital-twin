"""Checksum verification module.

Compares files in data directory against SHA256SUMS.txt manifest using
streamed cryptographic reads, reporting match/mismatch/missing counts without aborting.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ChecksumReport:
    status: str  # "PASSED", "DISCREPANCIES_FOUND", "CHECKSUM_FILE_NOT_FOUND"
    checksum_file_path: str | None
    matched_count: int
    mismatched_count: int
    missing_count: int
    total_manifest_entries: int
    mismatched_files: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SHA256_LINE_REGEX = re.compile(r"^([a-fA-F0-9]{64})\s+[*]?(.+)$")


def compute_file_sha256(file_path: Path, block_size: int = 65536) -> str:
    """Stream compute SHA-256 digest of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(block_size):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def verify_sha256sums(
    data_dir: Path,
    checksum_file_name: str = "SHA256SUMS.txt",
) -> ChecksumReport:
    """Verify files against SHA256SUMS.txt in data_dir."""
    target_manifest = data_dir / checksum_file_name
    if not target_manifest.exists():
        # Check case variation
        for alt_name in ("sha256sums.txt", "SHA256SUMS", "sha256sum.txt"):
            alt_path = data_dir / alt_name
            if alt_path.exists():
                target_manifest = alt_path
                break

    if not target_manifest.exists():
        return ChecksumReport(
            status="CHECKSUM_FILE_NOT_FOUND",
            checksum_file_path=None,
            matched_count=0,
            mismatched_count=0,
            missing_count=0,
            total_manifest_entries=0,
            warnings=[f"Checksum file '{checksum_file_name}' not found in '{data_dir}'."],
        )

    matched = 0
    mismatched = 0
    missing = 0
    mismatched_files: list[str] = []
    missing_files: list[str] = []
    warnings: list[str] = []
    total_entries = 0

    try:
        with open(target_manifest, encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line or clean_line.startswith("#"):
                    continue

                m = _SHA256_LINE_REGEX.match(clean_line)
                if not m:
                    warnings.append(
                        f"Line {line_no} in '{target_manifest.name}' invalid format: "
                        f"'{clean_line[:25]}...'"
                    )
                    continue

                expected_hash = m.group(1).lower()
                rel_file_str = m.group(2).strip().lstrip("./").lstrip(".\\")
                # Normalize path separators
                rel_path = Path(rel_file_str.replace("\\", "/"))
                full_path = data_dir / rel_path
                total_entries += 1

                if not full_path.exists():
                    missing += 1
                    missing_files.append(rel_path.as_posix())
                    continue

                try:
                    computed_hash = compute_file_sha256(full_path)
                    if computed_hash == expected_hash:
                        matched += 1
                    else:
                        mismatched += 1
                        mismatched_files.append(rel_path.as_posix())
                except Exception as e:
                    mismatched += 1
                    mismatched_files.append(rel_path.as_posix())
                    warnings.append(
                        f"Error reading file '{rel_path.as_posix()}' for checksum: "
                        f"{type(e).__name__}"
                    )

    except Exception as e:
        warnings.append(
            f"Failed to read checksum manifest '{target_manifest.name}': {type(e).__name__}"
        )
        return ChecksumReport(
            status="CHECKSUM_READ_ERROR",
            checksum_file_path=str(target_manifest),
            matched_count=0,
            mismatched_count=0,
            missing_count=0,
            total_manifest_entries=0,
            warnings=warnings,
        )

    status = "PASSED" if (mismatched == 0 and missing == 0) else "DISCREPANCIES_FOUND"
    if status == "DISCREPANCIES_FOUND":
        warnings.append(
            f"Checksum verification noted {mismatched} mismatched and {missing} missing files."
        )

    return ChecksumReport(
        status=status,
        checksum_file_path=target_manifest.name,
        matched_count=matched,
        mismatched_count=mismatched,
        missing_count=missing,
        total_manifest_entries=total_entries,
        mismatched_files=mismatched_files,
        missing_files=missing_files,
        warnings=warnings,
    )
