# Preprocessing Decisions and Rationales: CGMacros Digital Twin

> **Stage**: STAGE 1A — Data Integrity, Canonical Schema and Participant Join  
> **Date**: 2026-10-19  
> **Status**: FORMALLY RATIFIED AND TEST-VERIFIED  

---

## 1. Decision Log Summary

| Decision ID | Area | Decision Taken | Key Justification |
|:---|:---|:---|:---|
| **DEC-01** | **Gate G1 Mapping** | Formal pass (`GATE_G1_PASSED`). Join established via folder/file ID `CGMacros-{s:03d}` $\leftrightarrow$ `bio.csv.subject`. | 100% bijective match across 45 participants; explicitly confirmed in Das et al. (2025) Data Records section. |
| **DEC-02** | **1-Minute Cadence** | Ingest uniform 1-minute timeseries as linear interpolation by study authors; do not infer native sensor grids in Stage 1A. | Primary literature confirms authors linearly interpolated 15-min Libre Pro and 5-min Dexcom G6 Pro to 1-minute grid. |
| **DEC-03** | **Relative Time** | Calculate relative elapsed time ($t - t_0$) in seconds, minutes, and fractional days. Strictly forbid calendar features. | HIPAA Safe Harbor date-shifting ($\pm N$ days, $365 < N < 720$) makes calendar month, day-of-week, and day-of-year synthetic noise. |
| **DEC-04** | **Schema Resolution** | Name-based alias mapping via `configs/schema_aliases.yaml`; fail loudly in strict mode unless explicitly approved. | 9 distinct header families exist across 45 participants. Positional indexing is fragile and causes silent data corruption. |
| **DEC-05** | **Duplicate Columns** | Map repeated `Time (t)` in `bio.csv` to sequential `fingerstick_time_1`, `fingerstick_time_2`, `fingerstick_time_3`. | Raw `bio.csv` contains identical headers for 3 fingerstick observation times. Name disambiguation prevents overwrite. |
| **DEC-06** | **Ignorable Columns** | Automatically drop approved ignorable columns (`Unnamed: 0`, `RecordIndex`). | Index dumps and internal logging pointers carry no clinical or physiological meaning. |
| **DEC-07** | **Optional Activity Fields** | Support optional columns (`intensity`, `steps`, `sugar`, `amount_consumed`) without dropping records. | Hardware variation: 10 files record `Intensity` instead of `METs`; 1 file records `Steps`; 2 files lack `Amount Consumed`. |
| **DEC-08** | **Clinical Sentinels** | Preserve error sentinels (`LDL = 800`, `VLDL = 400`, `Cho/HDL = 400`) in raw data; mask to `NaN` with error flag in clinical stats. | Distinguishes sensor/lab calculation failure from extreme physiological hyperlipidemia. |
| **DEC-09** | **Meal Encoding** | Treat meal events as discrete single-row impulses at minute of consumption; do not artificially forward-fill macros. | Nutritional inputs act as bolus impulse drivers in metabolic physiological models. |

---

## 2. Detailed Decision Rationales

### 2.1 Gate G1: Participant-to-Baseline Join Rationale
- **The Ambiguity**: Participant CSV files (`CGMacros-001.csv` .. `CGMacros-049.csv`) do NOT contain an internal `participant_id` or `subject` column in their headers.
- **The Investigation**:
  1. We enumerated all 45 participant folders in `data/cgmacros/CGMacros/` and extracted integer IDs from `CGMacros-{s:03d}`. The resulting set of integers spans 1 to 49 with exactly 4 missing IDs: `[24, 25, 37, 40]`.
  2. We inspected `bio.csv` and confirmed its `subject` column contains exactly the same 45 integers, with the exact same missing IDs `[24, 25, 37, 40]`.
  3. We checked `microbes.csv` and confirmed its `subject` column contains the exact same 45 integers.
  4. We checked `gut_health_test.csv` (47 rows) and verified it includes subjects 24 and 25, confirming they completed microbiome sampling but dropped out before CGM monitoring.
  5. We inspected the primary literature publication (*Scientific Data* 12, 1391, 2025), which explicitly states:
     > *"The dataset consists of 45 main CSV files (CGMacros-#.csv), where # denotes participant number, and three supplementary CSV files... The supplementary spreadsheet (bio.csv) contains demographics... for each study participant."*
- **Conclusion**: The folder and filename structure is the author-designated primary key. The bijection between `CGMacros-{s:03d}` and `bio.csv.subject` is 100% (45/45 matches, 0 collisions, 0 missing). Gate G1 is formally **PASSED**.

---

### 2.2 Uniform 1-Minute Sampling and Author Linear Interpolation
- **The Observation**: Every participant timeseries records strictly at 1-minute intervals (`mode_delta = 60.0s`, `median_delta = 60.0s`, 99.98%–100% of deltas at mode).
- **The Literature Discovery**: Das et al. (2025, Data Records section) authoritatively state:
  > *"Since the Abbott and Dexcom CGM devices have different sampling rates, we used linear interpolation to obtain a uniform sampling rate of one minute. For the Abbott FreeStyle Libre Pro, we took the two consecutive CGM readings separated by 15 minutes and linearly interpolated between them to obtain CGM readings every minute. Similarly, for the Dexcom G6 Pro, we linearly interpolated between consecutive readings separated by 5 minutes."*
- **Preprocessing Decision**: Stage 1A ingests this published 1-minute uniform grid as-is, preserving all values. We do not attempt to undo or infer the unobserved native points in this stage. Detailed analysis of interpolation slopes and dual-sensor agreement is scheduled for Stage 1B.

---

### 2.3 Elimination of Calendar Features
- **The HIPAA De-identification Constraint**: Study timestamps were date-shifted by an undisclosed random number of days $\pm N$ ($365 < N < 720$).
- **The Hazard**: Feature engineering pipelines often naively extract calendar features: `df['day_of_week']`, `df['month']`, `df['is_weekend']`. Under HIPAA date shifting, these features reflect synthetic noise rather than physical reality (e.g. a Monday could be shifted to a Thursday).
- **Preprocessing Decision**: All temporal modeling uses relative elapsed coordinates from the participant's first valid timestamp $t_0$:
  - `relative_time_seconds` = $(t - t_0)$ in seconds
  - `relative_time_minutes` = $(t - t_0) / 60.0$
  - `day_offset` = $(t - t_0) / 86400.0$
- Calendar extraction functions are strictly prohibited in the ingestion code.

---

### 2.4 Name-Based Resolution Across 9 Header Families
- Across 45 participant CSVs, 9 distinct header layouts were discovered (e.g., column ordering swapped in `CGMacros-004`, `Unnamed: 0` in some files, `Steps` in `CGMacros-007`, `Intensity` in 11 files, `Sugar` in `CGMacros-013`, `Amount Consumed` missing in `CGMacros-028` and `029`).
- **Preprocessing Decision**: Positional column indexing is banned. Column mapping is executed strictly by column name matching against `configs/schema_aliases.yaml`.
- Unknown columns in strict mode trigger a loud `SchemaValidationError`.

---

### 2.5 Clinical Sentinels Policy
- `DataDictionary_Bio.csv` documents that `LDL (Cal) = 800` and `VLDL (Cal) = 400` indicate calculation errors.
- Stage 0 audit detected 1 occurrence each of `LDL = 800`, `VLDL = 400`, and `Cho/HDL Ratio = 400`.
- **Preprocessing Decision**: Sentinels are preserved in the raw canonical table to prevent silent data alteration, but masked to `NaN` when computing clinical summary statistics or feeding downstream loss functions, accompanied by a boolean error flag.

---

### 2.6 Discrete Meal Impulse Structure
- Across 687,580 participant rows, exactly 1,706 meal events exist (0.248% row sparsity).
- Only 5 instances exist where a meal row is immediately followed by another meal row (multi-part meal logging).
- **Preprocessing Decision**: Meal macronutrients and calorie quantities are represented as discrete impulse events at the minute of intake. We do not forward-fill or spread macronutrients over arbitrary postprandial windows during ingestion; physiological digestion decay curves belong in Stage 2 feature engineering.
