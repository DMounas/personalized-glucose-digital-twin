"""Cryptographic SHA-256 local manifest generation and validation for extracted dataset files.

Streams file contents in binary chunks without decoding photographs or images.
Excludes the manifest itself from its own hash calculation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def hash_file_streaming(file_path: Path, chunk_size: int = 65536) -> str:
    """Calculate SHA-256 digest of a file by streaming binary chunks.

    Never loads entire file into memory or decodes images as pixels.
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_manifest(
    data_dir: Path,
    output_file: Path,
    chunk_size: int = 65536,
) -> dict[str, Any]:
    """Generate a deterministic local SHA-256 manifest of all files in data_dir.

    Args:
        data_dir: Base directory containing extracted dataset files.
        output_file: Destination path for the manifest text file.
        chunk_size: Byte size for streaming file reads.

    Returns:
        Summary dict containing counts and verification status.
    """
    data_dir = Path(data_dir).resolve()
    output_file = Path(output_file).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    records: list[tuple[str, str]] = []
    total_bytes = 0

    # Collect and sort all files deterministically
    all_files = sorted(
        [p for p in data_dir.rglob("*") if p.is_file()],
        key=lambda p: str(p.relative_to(data_dir).as_posix()),
    )

    for file_path in all_files:
        # Exclude the manifest itself from its own hash calculation
        if file_path.resolve() == output_file:
            continue

        digest = hash_file_streaming(file_path, chunk_size=chunk_size)
        rel_path = file_path.relative_to(data_dir).as_posix()
        records.append((digest, rel_path))
        total_bytes += file_path.stat().st_size

    with open(output_file, "w", encoding="utf-8", newline="\n") as out:
        for digest, rel_path in records:
            out.write(f"{digest}  {rel_path}\n")

    return {
        "manifest_path": str(output_file),
        "total_files": len(records),
        "total_bytes": total_bytes,
        "status": "CREATED",
    }


def verify_manifest(
    manifest_file: Path,
    base_dir: Path,
    chunk_size: int = 65536,
) -> dict[str, Any]:
    """Verify extracted files against an existing SHA-256 manifest.

    Args:
        manifest_file: Path to the SHA-256 manifest text file.
        base_dir: Base directory where files reside.
        chunk_size: Chunk size for binary streaming.

    Returns:
        Summary dict of verification results.
    """
    manifest_file = Path(manifest_file).resolve()
    base_dir = Path(base_dir).resolve()

    if not manifest_file.exists():
        return {
            "status": "ERROR",
            "error": f"Manifest file does not exist: {manifest_file}",
            "matched": 0,
            "mismatched": 0,
            "missing": 0,
            "total": 0,
        }

    matched = 0
    mismatched: list[str] = []
    missing: list[str] = []
    total = 0

    with open(manifest_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            expected_digest, rel_path = parts[0].strip(), parts[1].strip()
            # Clean up leading asterisk or spaces in standard sha256sum format
            rel_path = rel_path.lstrip("*").strip()
            target_path = base_dir / rel_path
            total += 1

            if not target_path.exists():
                missing.append(rel_path)
                continue

            actual_digest = hash_file_streaming(target_path, chunk_size=chunk_size)
            if actual_digest.lower() == expected_digest.lower():
                matched += 1
            else:
                mismatched.append(rel_path)

    status = "PASSED" if len(mismatched) == 0 and len(missing) == 0 else "FAILED"
    return {
        "status": status,
        "total": total,
        "matched": matched,
        "mismatched_count": len(mismatched),
        "missing_count": len(missing),
        "mismatched_samples": mismatched[:5] if mismatched else [],
        "missing_samples": missing[:5] if missing else [],
    }
