# Stage 1A Completion Report: Data Integrity, Canonical Schema, and Participant Join

> **Stage**: STAGE 1A — Data Integrity, Canonical Schema and Participant Join  
> **Date**: 2026-10-19  
> **Gate G1 Status**: **GATE_G1_PASSED** ([ESTABLISHED])  
> **Dataset**: CGMacros v1.0.0 (PhysioNet & Nature *Scientific Data*)  
> **Overall Ingestion Status**: **VERIFIED & READY FOR STAGE 1B**

---

## 1. Executive Summary
Stage 1A completes foundational data integrity, canonical schema standardization, cryptographic provenance, and participant-to-baseline mapping for the Type 2 Diabetes Glucose Digital Twin project. All operations executed directly against the real CGMacros v1.0.0 dataset (`data/cgmacros/`):

- **Cryptographic Integrity**: Generated local SHA-256 manifest `extracted_sha256sums.txt` covering all 3502 extracted files (667.54 MB), streaming byte chunks without decoding photographs. Verification status: **PASSED** (0 mismatched, 0 missing).
- **Primary Literature Verification**: Formally verified published source statements in Nature *Scientific Data* (Das et al., 2025, DOI: `10.1038/s41597-025-05851-7`). Authoritatively confirmed that uniform 1-minute sampling was produced via **linear interpolation** (15-min intervals for FreeStyle Libre Pro, 5-min for Dexcom G6 Pro).
- **Gate G1 (Participant Join)**: Formally **DEMONSTRATED & PASSED**. The 45 participant folders (`CGMacros-001` through `CGMacros-049`, missing IDs [24, 25, 37, 40]) achieve 100% bijective alignment with the 45 rows in `bio.csv.subject` (45/45 matched, 0 unmatched).
- **Schema Standardization**: Authored `configs/schema_aliases.yaml` mapping all 9 observed participant header families to canonical snake_case columns. Enforces name-based resolution, whitespace normalization, ignorable column stripping (`Unnamed: 0`, `RecordIndex`), and strict mode failure on unexpected columns.
- **Relative Time Calculation**: Processed all 687,580 records across 45 participants, computing relative elapsed time ($t - t_0$) in seconds, minutes, and fractional days. Strictly zero calendar features (no month, day of week, or season) were generated, preventing artificial leakage from de-identification date-shifting.
- **Meal Encoding & Sparsity**: Profiled 1,706 discrete meal impulse events across the cohort (0.2481% row sparsity). Verified 96.37% of meals include meal photo paths. Summarized nutritional macro distributions using aggregate-only statistics.

---

## 2. Gate G1 Formal Assessment: Participant-to-Baseline Mapping

| Evaluation Metric | Observed Value | Gate Criterion | Assessment |
|:---|:---|:---|:---|
| Participant Timeseries Folders | `45` folders | 45 study completers | **PASSED** |
| Baseline Demographics (`bio.csv`) | `45` rows | 45 study completers | **PASSED** |
| Bijective Mapping Count | `45 / 45` | 45 / 45 (100%) | **PASSED** |
| Missing Sequence IDs | `[24, 25, 37, 40]` | Exactly `[24, 25, 37, 40]` | **PASSED** |
| Mapping Key Mechanism | Directory/Filename ID (`CGMacros-{s:03d}`) | Documented by authors | **PASSED** |
| **Gate G1 Final Status** | **GATE_G1_PASSED** | Unanimous pass | **[ESTABLISHED]** |

> **Gate G1 Finding**: Although individual participant CSVs lack an internal participant ID column, the primary source publication (*Scientific Data* 12, 1391) and the directory structure establish that folder/filename `CGMacros-0XX` maps bijectively to `bio.csv.subject`. Gate G1 is formally **PASSED**, permitting baseline joins.

---

## 3. Primary Literature & Source Verification

Live inspection of Das et al., *Scientific Data* 12, Article 1391 (published 2025-09-25; DOI: `10.1038/s41597-025-05851-7`):

1. **Sampling Frequency & Interpolation (Inconsistency 1 [CONFIRMED])**:
   > *"Since the Abbott and Dexcom CGM devices have different sampling rates, we used linear interpolation to obtain a uniform sampling rate of one minute. For the Abbott FreeStyle Libre Pro, we took the two consecutive CGM readings separated by 15 minutes and linearly interpolated between them to obtain CGM readings every minute. Similarly, for the Dexcom G6 Pro, we linearly interpolated between consecutive readings separated by 5 minutes."* (Data Records section)
2. **Participant Cohort Composition (Inconsistency 2 [CONFIRMED])**:
   > *"The dataset consists of 45 main CSV files (CGMacros-#.csv), where # denotes participant number, and three supplementary CSV files... Forty-five participants completed the study, ages 18–69, and body mass index (BMI) 21–46 kg/m²."*
3. **Meal Encoding Structure (OQ-10 [CONFIRMED])**:
   > *"At the appropriate time stamp (i.e., row) from WhatsApp photographs, we also report the total caloric content and carbohydrate, protein, fat, and fiber amounts of each meal, the type of meal (breakfast, lunch, dinner) and a path to the file containing the corresponding photograph."*
4. **Sensor Concordance Baseline (Inconsistency 7 [ESTABLISHED])**:
   > *"The average glucose from the Abbott Freestyle device was 84.89 mg/dL for healthy adults, 105.2 mg/dL for pre-diabetes, and 138.04 mg/dL for T2D. The average glucose from the Dexcom G6 device was 122.36 mg/dL for healthy adults, 135.1 mg/dL for pre-diabetes, and 165.7 mg/dL for T2D... Dexcom G6 glucose readings being higher by up to 58.7 mg/dL."*

---

## 4. Local Cryptographic Manifest Verification

| Manifest Metric | Result |
|:---|:---|
| Manifest File Path | `extracted_sha256sums.txt` |
| Total Extracted Files Hashed | `3502` files |
| Total Extracted Payload Bytes | `699,967,761` bytes (~667.5 MB) |
| Streaming Mode | Binary chunked (64 KB chunks, zero image decoding) |
| Self-Exclusion Verified | Manifest file excluded from its own digest calculation |
| Independent Verification Status | **PASSED** (0 mismatched, 0 missing) |

---

## 5. Schema Standardization and Header Families

All 45 participant CSV files were successfully mapped under `configs/schema_aliases.yaml`. The 9 observed header families are:

| Family ID | Files Count | Key Distinguishing Features | Canonical Resolution |
|:---|:---|:---|:---|
| **Family 1** | 1 file (001) | Has `Unnamed: 0`, trailing space in `Amount Consumed ` | Dropped index; mapped `amount_consumed` |
| **Family 2** | 6 files (002, 003, 005, 006, 009, 010) | Has `Unnamed: 0`, standard headers | Dropped index; mapped 14 columns |
| **Family 3** | 1 file (004) | Has `Unnamed: 0`, swapped order (`Dexcom GL` before `Libre GL`) | Name-based mapping resolves cleanly |
| **Family 4** | 1 file (007) | Has `Steps` instead of `Calories (Activity)`, has `RecordIndex` | Mapped `steps`, dropped `RecordIndex` |
| **Family 5** | 22 files (008, 012, 014..027, etc.) | Standard 14-column layout without extra index | Canonical baseline layout |
| **Family 6** | 10 files (011, 015..023, etc.) | Has `Intensity` instead of `METs` | Mapped `intensity` to optional column |
| **Family 7** | 1 file (013) | Has extra `Sugar` column (39 meal values) | Mapped `sugar` to optional column |
| **Family 8** | 2 files (028, 029) | Lacks `Amount Consumed` column entirely | Handled as optional nullable column |
| **Family 9** | 1 file (033) | Has `Unnamed: 0` AND `Intensity` | Dropped index; mapped `intensity` |

---

## 6. Timeseries and Sensor Coverage Profile

| Timeseries Attribute | Aggregate Cohort Statistic |
|:---|:---|
| Cohort Size | `45` participants |
| Total Timeseries Records | `687,580` rows |
| Records per Participant | Mean: `15,279.56` (Median: `14,805.0`, Min: `5,655.0`, Max: `18,735.0`) |
| Recording Duration | Mean: `10.9` days (Min: `7.23` d, Max: `19.15` d) |
| FreeStyle Libre Pro Availability | **99.97%** present (Missingness: `0.03%`) |
| Dexcom G6 Pro Availability | **92.24%** present (Missingness: `7.76%`) |
| Dual CGM Overlap (Both Active) | **92.21%** of all recorded minutes |
| Fitbit Heart Rate Availability | **89.08%** present (Missingness: `10.92%`) |

---

## 7. Meal-Field Encoding and Nutrition Profile

| Meal Feature | Aggregate Value |
|:---|:---|
| Total Meal Events Logged | `1,706` meal events |
| Row Sparsity | `0.2481%` of timeseries rows contain a meal |
| Encoding Pattern | `Mixed impulse/interval` (consecutive meal rows: `5`) |
| Meals with Photo Paths | `1,644` of `1,706` (96.37%) |

### Meal Types Breakdown
| Meal Type Category | Events Count | Proportion |
|:---|:---|:---|
| **Dinner** | `492` | 28.8% |
| **Breakfast** | `436` | 25.6% |
| **Lunch** | `435` | 25.5% |
| **Snack** | `343` | 20.1% |

### Macronutrient Distribution Across All Logged Meals
| Nutrient | Valid Count | Mean ± Std | Median (IQR) | Min - Max |
|:---|:---|:---|:---|:---|
| Energy (kcal) | `1,706` | 505.86 ± 329.44 | 448.0 (268.0 - 712.0) | 0.0 - 2826.0 |
| Carbohydrates (g) | `1,706` | 52.08 ± 40.05 | 50.0 (24.0 - 73.0) | 0.0 - 761.0 |
| Protein (g) | `1,706` | 29.25 ± 25.65 | 22.0 (10.0 - 44.0) | 0.0 - 148.0 |
| Total Fat (g) | `1,706` | 19.78 ± 20.75 | 14.0 (10.0 - 30.0) | 0.0 - 508.0 |
| Dietary Fiber (g) | `1,705` | 17.9 ± 143.63 | 4.0 (0.0 - 7.0) | 0.0 - 2830.0 |
| Sugar (g, P13 only) | `39` | 6.87 ± 10.64 | 0.0 (0.0 - 12.0) | 0.0 - 50.0 |
| Amount Consumed (%) | `1,642` | 97.87 ± 91.64 | 100.0 (100.0 - 100.0) | 0.0 - 900.0 |

---

## 8. Baseline Cohort Stratification and Biological Quality

- **Cohort Size**: 45 study completers.
- **Metabolic Status Distribution** (ADA Diagnostic Criteria based on NGSP HbA1c):
  - **Healthy Controls** (HbA1c < 5.7%): `15` participants (33.3%)
  - **Pre-Diabetes** (5.7% ≤ HbA1c ≤ 6.4%): `16` participants (35.6%)
  - **Type 2 Diabetes** (HbA1c > 6.4%): `14` participants (31.1%)
- **Error Sentinel Values Detected and Preserved**:
  - `LDL (Cal) = 800`: `1` occurrence
  - `VLDL (Cal) = 400`: `1` occurrence
  - `Cho/HDL Ratio = 400`: `1` occurrence

---

## 9. What Stage 1A Does NOT Do or Claim

> [!IMPORTANT]
> 1. **No Predictive Modeling**: Stage 1A trains zero machine learning, deep learning, or statistical forecasting models.
> 2. **No Native Grid Inference**: Stage 1A does NOT resample, reconstruct, or infer native CGM timestamps; it ingests the 1-minute uniform series as linearly interpolated by study authors.
> 3. **No Dual-Sensor Resolution**: Stage 1A documents sensor missingness and overlap, but does not fit calibration regression or declare one CGM sensor as gold-standard ground truth (deferred to Stage 1B).
> 4. **No Participant Traces or Raw Records**: No individual patient time series, names, photograph pixels, or raw identifiers are committed to git or exposed in reports.
> 5. **No Clinical Claims for Indian Demographics**: The CGMacros cohort was recruited in Santa Barbara, California. Any application to South Asian / Indian cohorts must be marked explicitly as **[SYNTHETIC DEMO]**.

---

## 10. Stage 1A Sign-Off and Readiness for Stage 1B
- **Manifest**: SHA-256 local manifest verified for 3,502 files.
- **Schema**: Canonical aliases configuration tested and validated across all 45 participant files.
- **Gate G1**: Formally PASSED with 100% bijective directory-to-baseline mapping.
- **Provenance**: Primary literature interpolation confirmed and documented.
- **Next Stage (Stage 1B)**: Dual-sensor agreement analysis (Bland-Altman, Clarke Error Grid), native grid investigation, and glucose reference target designation.
