"""Tests for checksum verification against SHA256SUMS.txt."""

import hashlib
from pathlib import Path

from dtwin.audit.checksums import verify_sha256sums


def test_checksum_verification_full_pass(tmp_path: Path):
    d = tmp_path / "chk_test"
    d.mkdir()

    f1 = d / "file1.csv"
    f2 = d / "file2.csv"
    f1.write_text("col\n1\n", encoding="utf-8")
    f2.write_text("col\n2\n", encoding="utf-8")

    h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
    h2 = hashlib.sha256(f2.read_bytes()).hexdigest()

    manifest = d / "SHA256SUMS.txt"
    manifest.write_text(f"{h1}  file1.csv\n{h2}  file2.csv\n", encoding="utf-8")

    rep = verify_sha256sums(d)
    assert rep.status == "PASSED"
    assert rep.matched_count == 2
    assert rep.mismatched_count == 0
    assert rep.missing_count == 0


def test_checksum_mismatch_and_missing(tmp_path: Path):
    d = tmp_path / "chk_mismatch_test"
    d.mkdir()

    f1 = d / "file1.csv"
    f1.write_text("col\n1\n", encoding="utf-8")
    wrong_hash = "0" * 64

    manifest = d / "SHA256SUMS.txt"
    manifest.write_text(
        f"{wrong_hash}  file1.csv\n{wrong_hash}  non_existent_file.csv\n", encoding="utf-8"
    )

    rep = verify_sha256sums(d)
    assert rep.status == "DISCREPANCIES_FOUND"
    assert rep.matched_count == 0
    assert rep.mismatched_count == 1
    assert "file1.csv" in rep.mismatched_files
    assert rep.missing_count == 1
    assert "non_existent_file.csv" in rep.missing_files


def test_missing_checksum_manifest(tmp_path: Path):
    d = tmp_path / "no_manifest"
    d.mkdir()

    rep = verify_sha256sums(d)
    assert rep.status == "CHECKSUM_FILE_NOT_FOUND"
    assert rep.matched_count == 0
