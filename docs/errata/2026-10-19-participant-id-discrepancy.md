# Erratum: Participant ID Reconciliation and Discrepancy Resolution

**Date**: 2026-10-19  
**Status**: Resolved / Verified  
**Scope**: Historical reports (`docs/STAGE0_REPORT.md`, `docs/reports/audit_report.*`), schema configuration, and ingestion pipelines.  
**Related Documents**: `docs/STAGE0_REPORT.md`, `docs/reports/stage1a_report.md`, `docs/OPEN_QUESTIONS.md`

---

## 1. Description of Discrepancy

In the initial exploratory Stage 0 dataset audit (`docs/STAGE0_REPORT.md` and `docs/reports/audit_report.json`), the list of missing participant IDs within the cohort sequence (IDs 1 through 49) was erroneously documented as:
$$\text{Incorrect (Stage 0): } [14, 18, 20, 24]$$

Subsequent physical verification during Stage 1A and systematic preflight audit in Stage 1B revealed that the actual missing participant IDs are:
$$\text{Verified Ground Truth: } [24, 25, 37, 40]$$

Participants `CGMacros-014`, `CGMacros-018`, and `CGMacros-020` exist, are physically present in the dataset, contain complete sensor records, and correspond to active study completers.

---

## 2. Multi-Source Evidence and Verification

The reconciliation is confirmed across four independent primary sources:

### A. Physical File System Directory Inspection
Physical enumeration of `data/cgmacros/CGMacros/` confirms exactly 45 participant subdirectories formatted as `CGMacros-001` through `CGMacros-049`:
- Directories `CGMacros-014` (14,357 records), `CGMacros-018` (14,085 records), and `CGMacros-020` (14,375 records) exist and contain valid 1-minute continuous timeseries CSVs.
- Directories `CGMacros-024`, `CGMacros-025`, `CGMacros-037`, and `CGMacros-040` do not exist on disk.
- Total directory count: **45**.

### B. Baseline Demographics Table (`bio.csv`)
Inspection of `data/cgmacros/CGMacros/bio.csv` reveals exactly 45 rows with subject IDs:
$$\text{Unique Subjects: } \{1, \dots, 49\} \setminus \{24, 25, 37, 40\}$$
- Subjects 14, 18, and 20 are present with complete clinical baseline panels (Age, Gender, BMI, HbA1c, Lipids).
- Subjects 24, 25, 37, and 40 are absent.
- The mapping between physical timeseries directories `CGMacros-0XX` and `bio.csv.subject` is **100% bijective** (45 / 45 matches).

### C. Gut Health and Microbiome Assay Tables
- `microbes.csv` contains exactly 45 subjects, matching `bio.csv` bijectively ($\{1..49\} \setminus \{24, 25, 37, 40\}$).
- `gut_health_test.csv` contains 47 subjects: it includes subjects **24 and 25** in addition to the 45 study completers (missing only 37 and 40).
- This clinical discrepancy demonstrates that participants 24 and 25 enrolled and provided stool samples for microbiome profiling, but subsequently withdrew or dropped out prior to the baseline lab draw (`bio.csv`) and CGM monitoring (`CGMacros-0XX/`).

### D. Official Author Repository (`PSI-TAMU/CGMacros`)
Inspection of the author repository (`parse_data.ipynb`) reveals the author's primary ingestion loop:
```python
# From parse_data.ipynb (lines 144-150)
for i in range(1, 50):
    if i in [24, 25, 37, 40]:
        continue
    # Process participant CGMacros-{i:03d}
```
The study authors explicitly hard-coded `[24, 25, 37, 40]` as the excluded non-completers.

---

## 3. Root Cause Analysis of Stage 0 Error

The Stage 0 error originated during initial shell globbing and string matching in exploratory scripts. Folders `014`, `018`, and `020` were inadvertently skipped or misparsed due to pattern handling in an early one-liner script, leading to false-negative directory detection. The error was recorded in `docs/STAGE0_REPORT.md` before formal pipeline validation.

---

## 4. Preservation Policy and Impact

1. **Preservation**: In accordance with scientific data governance and pipeline immutability principles, historical report files `docs/STAGE0_REPORT.md` and `docs/reports/stage1a_report.md` remain unaltered.
2. **Authoritative Reference**: All downstream stages, including Stage 1B, Stage 2 (sensor concordance), and Stage 3 (digital twin modeling), must rely on this erratum and `docs/reports/stage1b_preflight_results.json` as the verified ground truth.
3. **Pipeline Health**: `src/dtwin/ingestion/pipeline.py` and `src/dtwin/ingestion/canonical_schema.py` have already incorporated the verified list `[24, 25, 37, 40]`, achieving 100% bijective participant join (Gate G1: PASSED).
