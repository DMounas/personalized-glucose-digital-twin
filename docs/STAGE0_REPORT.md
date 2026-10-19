# Stage 0 Completion Report: Repository Scaffold, Data Provenance, and Audit Tooling

> **Stage**: STAGE 0 — Repository scaffold, data provenance, and dataset-audit tooling  
> **Date**: 2026-10-19  
> **Status**: COMPLETED & VERIFIED ON REAL DATASET (CGMacros v1.0.0)

---

## 1. Executive Summary
Stage 0 establishes the engineering foundations for the Type 2 Diabetes (T2D) Glucose Digital Twin project. All requirements of this foundation stage have been fulfilled and verified against the real CGMacros v1.0.0 dataset:
- Initialized clean git repository and cross-platform Python environment.
- Configured minimal, strictly justified dependencies (`pandas`, `numpy`, `PyYAML`, and dev tools `pytest`, `ruff`) with zero machine learning or dashboard bloat.
- Penned 5 foundational documentation artifacts establishing project boundaries, source-claimed data provenance (verified live against PhysioNet and Nature *Scientific Data*), acquisition guides for Linux/macOS and Windows, open research questions, and project overview.
- Designed and implemented a modular, schema-agnostic, privacy-preserving dataset audit tool (`dtwin-audit` / `python -m dtwin.audit`).
- Engineered comprehensive unit and integration tests (26 passed out of 26) proving schema family detection, numeric profiling, sentinels, sampling mode analysis, data dictionary conformance, checksum verification, small-table suppression, chunking equivalence, and strict privacy leakage prevention against planted sentinels.
- Audited the real CGMacros v1.0.0 dataset in `data/cgmacros/`: verified 7/7 checksums, profiled 52 tabular files across 14 schema families, inventoried 3,454 meal photographs (unopened), and resolved key documentation inconsistencies.

---

## 2. Files Created and Modified

### Configuration & Tooling
- `.gitignore`: Excludes `data/`, virtual environments (`.venv/`), raw archives (`*.zip`, `*.tar*`, `*.gz`), image files outside `docs/`, test/lint caches, and safety-net `docs/reports/raw/`.
- `pyproject.toml`: Project metadata, dependencies, ruff lint/format configuration (line length 100), and console script entry point `dtwin-audit`.
- `configs/audit.default.yaml`: Configurable privacy thresholds, streaming chunk limits, suspicious sentinels, quantiles, and datetime detection hints.

### Documentation (`docs/`)
- `docs/PROJECT_BRIEF.md`: Vision, competition constraints, non-goals, stages 0–8 roadmap, and evidence labels (**[ESTABLISHED]**, **[HYPOTHESIS]**, **[SYNTHETIC DEMO]**, **[VERIFIED RESULT]**).
- `docs/DATA_PROVENANCE.md`: PhysioNet v1.0.0 provenance, verified Nature publication status (published online 2025-09-25 in *Scientific Data*, doi: `10.1038/s41597-025-05851-7`), CC BY-NC-SA 4.0 obligations, schemas, and 7 documentation inconsistencies evaluated.
- `docs/DATA_ACQUISITION.md`: Step-by-step acquisition guide for Linux/macOS and Windows PowerShell (browser, `wget`, AWS S3 sync), extraction instructions, and checksum verification.
- `docs/OPEN_QUESTIONS.md`: Living tracker for 14 research questions, evaluation constraints, and technical ambiguities.
- `docs/STAGE0_REPORT.md`: This completion report.
- `docs/reports/audit_report.json`: Machine-readable audit report generated from the real CGMacros dataset.
- `docs/reports/audit_report.md`: Human-readable audit report with executive tables, schema family profiles, and disclaimers.
- `README.md`: High-level summary, clinical disclaimer, evidence convention, setup guide for both OSes, audit CLI instructions, and documentation links.

### Source Code (`src/dtwin/`)
- `src/dtwin/__init__.py`: Package root exporting `__version__ = "0.1.0"`.
- `src/dtwin/audit/__init__.py`: Audit package root.
- `src/dtwin/audit/__main__.py`: Module execution entrypoint (`python -m dtwin.audit`).
- `src/dtwin/audit/privacy.py`: Central privacy guard enforcing small-cell suppression (<5), identifier/path/text masking, and error sanitization.
- `src/dtwin/audit/discovery.py`: Deterministic inventory, extension profiling, unopened image counts, non-extracting archive inspection, participant ID extraction, and directory fingerprint calculation.
- `src/dtwin/audit/profiling.py`: Schema family grouping, missingness aggregation, numeric statistics, sentinel detection, small table suppression, and chunked streaming reader.
- `src/dtwin/audit/timeseries.py`: Candidate datetime detection, parse success rates, mode delta and median sampling intervals, gap tracking (>3x mode), duplicates, non-monotonic ordering, and format/timezone ambiguity alerts.
- `src/dtwin/audit/dictionary.py`: Parser for official data dictionary CSVs, field mapping, regex range extraction, and out-of-range counts with non-judgmental disclaimers.
- `src/dtwin/audit/checksums.py`: Cryptographic SHA-256 verification against `SHA256SUMS.txt` using streaming reads.
- `src/dtwin/audit/report.py`: JSON and Markdown report generation with stable schema, metadata, and mandatory "What this audit does NOT verify" disclaimers.
- `src/dtwin/audit/cli.py`: CLI parser (`argparse`), config validation, error reporting, and orchestration.

### Test Suite (`tests/`)
- `tests/__init__.py`: Test package definition.
- `tests/conftest.py`: Programmatic synthetic dataset fixtures with planted sentinels (`PLANTED_SECRET_SENTINEL_PATIENT_Z9`, `PLANTED_SECRET_PATH_X7Q/patient_photo_01.jpg`, `PLANTED_SECRET_NAME_ALICE_SMITH`), archives, dictionaries, and checksums.
- `tests/test_discovery.py`: Unit tests for deterministic sorting, extension counting, zip inspection, image enumeration, empty/missing dirs, and participant ID extraction.
- `tests/test_profiling.py`: Unit tests for schema family grouping, missingness, numeric statistics, sentinel counts, small table suppression, and chunked vs in-memory parity.
- `tests/test_timeseries.py`: Unit tests for 5-minute sampling, 15-minute intervals, gap detection, duplicate timestamps, non-monotonic rows, and unparsable columns.
- `tests/test_dictionary.py`: Unit tests for dictionary parsing, regex range matching, documented/observed mapping, and out-of-range detection.
- `tests/test_checksums.py`: Unit tests for checksum match, mismatch, missing files, and missing manifest handling.
- `tests/test_privacy.py`: End-to-end assertions ensuring planted patient names, photo paths, and secrets never leak into JSON, Markdown, stdout, or stderr.
- `tests/test_cli.py`: Unit tests for exit code 0 on valid data, exit code 2 on missing data, env var configuration, and file capping.
- `tests/test_report.py`: Assertions verifying JSON schema key stability, Markdown status banners, and mandatory disclaimers.

---

## 3. Key Findings from Auditing the Real CGMacros Dataset

The audit tool executed against the real extracted dataset in `data/cgmacros/`:
```bash
python -m dtwin.audit --data-dir "data/cgmacros" \
  --dictionary "data/cgmacros/DataDictionary_CGMacros-00X.csv" \
  --dictionary "data/cgmacros/DataDictionary_Bio.csv" \
  --dictionary "data/cgmacros/DataDictionary_Gut_Health_Test.csv" \
  --dictionary "data/cgmacros/DataDictionary_Microbes.csv" \
  --verify-checksums --output-dir "docs/reports"
```

### Verified Dataset Facts:
1. **Payload Volume & Files**: 3,510 total files occupying 1,358,372,223 bytes (~1.36 GB total, including archive). Directory fingerprint (SHA-256): `6832708dab205b63f0244ca65685aff8bfc72f4f3826c6476b42303fe5e88904`.
2. **Cryptographic Integrity**: 7/7 files in `SHA256SUMS.txt` matched their SHA-256 digests perfectly (Status: `PASSED`, 0 mismatched, 0 missing).
3. **Images**: Exactly 3,454 meal photographs were inventoried by extension and size without opening them.
4. **Timeseries Sampling Interval (Inconsistency 1 [RESOLVED])**: All participant timeseries CSVs record at strictly **1-minute intervals** (`mode_delta = 60.0s`, `median_delta = 60.0s`, `mode_delta_percent = 99.98% - 100.0%`, `duplicates = 0`, `non_monotonic = 0`). Because physical hardware sampled at 5 min (Dexcom) and 15 min (Libre), this confirms data was resampled/interpolated prior to release.
5. **Participant Numbers & Directory IDs (Inconsistency 2 [RESOLVED])**: Exactly 45 participant files and 45 rows in `bio.csv` exist, with participant folder IDs spanning 1–49. Folder IDs 14, 18, 20, 24 are absent from the sequence, explaining why 45 participants complete the 1–49 range.
6. **HbA1c Units (Inconsistency 3 [RESOLVED])**: `A1c PDL (Lab)` values range from 4.6 to 8.5 (mean 6.12, median 5.9). This resolves the unit ambiguity: values are DCCT/NGSP percentage (`%`), **NOT** `mmol/mol`.
7. **Sentinel Values (Inconsistency 4 [RESOLVED])**: The audit detected the exact documented sentinel codes without crashing: `LDL (Cal)` has a value of 800 (1 count), `VLDL (Cal)` has a value of 400 (1 count), and `Cho/HDL Ratio` has a value of 400 (1 count).
8. **METs Scaling (Inconsistency 5 [RESOLVED])**: In participant activity streams, `METs` has a minimum of 10.0 and median of 11.0–12.0, confirming that values are pre-multiplied by 10 (standard resting MET is 1.0).
9. **Microbiome File (Inconsistency 6 [RESOLVED])**: The extracted file is `microbes.csv` (Family 12), containing 45 rows and 1,980 columns (the `subject` ID plus 1,979 bacterial species indicator columns).
10. **Schema Variations**: Discovered 14 schema families across 52 tabular files. Differences include `Unnamed: 0` index columns in some files, swapped column ordering between `Libre GL` and `Dexcom GL`, `Steps` replacing `Calories (Activity)` in one participant, and trailing whitespace in column names (`Amount Consumed `). This validates our design decision to avoid hardcoded column names.

---

## 4. Test Results and Code Quality

### Pytest Verification
```text
pytest -q
26 passed in 2.77s
```

### Ruff Verification
```text
ruff check .           -> All checks passed!
ruff format --check .  -> 28 files already formatted
```

---

## 5. Deviations from Prompt
- **None**: All scope boundaries and constraints were strictly maintained. No models were trained, no pipelines were built, and no dashboard code was introduced.

---

## 6. Next Steps for Stage 1
With Stage 0 foundations completely in place and the real CGMacros v1.0.0 dataset fully audited and verified:
1. **Dual-Sensor Analysis (Inconsistency 7)**: Evaluate concordance between FreeStyle Libre Pro and Dexcom G6 Pro, quantify sensor drift, and define the reference standard.
2. **Resampling Reconstruction**: Investigate the exact interpolation structure of the 1-minute time series.
3. **Data Preprocessing & Alignment**: Clean whitespace column discrepancies and handle blood panel sentinel values identified in the Stage 0 audit report.
