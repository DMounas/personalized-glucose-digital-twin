# Data Provenance and Dataset Audit Specification

> **Status**: SOURCE-CLAIMED — pending local verification via repository audit tooling.

## 1. Sources and Verification
Live web verification conducted on 2026-10-18:
- **Dataset Landing Page**: [https://physionet.org/content/cgmacros/1.0.0/](https://physionet.org/content/cgmacros/1.0.0/) (Retrieved 2026-10-18)
- **Data Dictionaries**: `DataDictionary_CGMacros-00X.csv` and `DataDictionary_Bio.csv` (hosted on PhysioNet)
- **DOI v1.0.0**: [10.13026/3z8q-x658](https://doi.org/10.13026/3z8q-x658)
- **Associated Publication**: [https://www.nature.com/articles/s41597-025-05851-7](https://www.nature.com/articles/s41597-025-05851-7)
  - *Web Verification Note*: On the PhysioNet dataset landing page, the associated publication is listed as *"Scientific Data (under review)"*. Live retrieval of the Nature publication confirms it has since been formally published on 2025-09-25 (*Scientific Data*, Volume 12, Article Number 1391) under the title *"CGMacros: a pilot scientific dataset for personalized nutrition and diet monitoring"* by Anurag Das, David Kerr, Namino Glantz, Wendy Bevier, Rony Santiago, Ricardo Gutierrez-Osuna, and Bobak J. Mortazavi.

## 2. Source-Claimed Facts
*(All facts below are documented as SOURCE-CLAIMED — pending local verification)*:
- **Access Tier**: Open access; anyone may download subject to licence terms.
- **Licence**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0).
  - *Note*: The `LICENSE.txt` file distributed in the repository is 0 bytes; legal terms are governed by the CC BY-NC-SA 4.0 licence URL provided on PhysioNet.
- **Publication Date & Version**: Published 2025-01-28, Version 1.0.0.
- **Payload Volume**: 627.9 MB uncompressed (ZIP archive `CGMacros_dateshifted365.zip` is ~626.7 MB / 627.1 MB).
- **Distribution Files**:
  - `CGMacros_dateshifted365.zip`
  - `DataDictionary.pdf`
  - `DataDictionary_Bio.csv`
  - `DataDictionary_CGMacros-00X.csv`
  - `DataDictionary_Gut_Health_Test.csv`
  - `DataDictionary_Microbes.csv`
  - `LICENSE.txt`
  - `SHA256SUMS.txt`
- **Cohort Composition**: 45 total participants:
  - 15 healthy controls (HbA1c < 5.7%)
  - 16 individuals with pre-diabetes (5.7% <= HbA1c <= 6.4%)
  - 14 individuals with Type 2 Diabetes (HbA1c > 6.4%)
  - Age range: 18–69 years; BMI range: 21–46 kg/m²
  - Recruited at Sansum Diabetes Research Institute (Santa Barbara, CA), 2021–2024.
- **Study Protocol & Sensors**:
  - Duration: ~10 consecutive days per participant in free-living conditions.
  - Abbott FreeStyle Libre Pro CGM (15-min factory sampling, placed on upper arm, blinded).
  - Dexcom G6 Pro CGM (5-min factory sampling, placed on abdomen, blinded).
  - Fitbit Sense smartwatch logging heart rate and activity metrics.
  - Controlled meals: Breakfast = protein shakes of known varying macronutrients; Lunch = fast-casual restaurant (Chipotle Mexican Grill) with known macro variations; Dinner = participant's unconstrained choice.
  - Macronutrients: Documented as estimates based on standardized recipes and nutritional panels.
  - De-identification date shifting: Full timestamps are date-shifted by $\pm N$ days ($365 < N < 720$) per HIPAA Safe Harbor regulations.

## 3. Documented Field Schemas
### Documented Per-Participant Columns (`CGMacros-00X.csv`)
1. `Timestamp`
2. `Libre GL`
3. `Dexcom GL`
4. `HR`
5. `Calories (Activity)`
6. `Mets`
7. `Meal Type`
8. `Calories`
9. `Carbs`
10. `Protein`
11. `Fat`
12. `Fiber`
13. `Amount Consumed`
14. `Image Path`

### Documented Baseline Biological Fields (`bio.csv`)
1. `Age`
2. `Gender`
3. `BMI`
4. `Body weight`
5. `Height`
6. `Self-identify`
7. `A1c PDL (Lab)`
8. `Fasting GLU - PDL (Lab)`
9. `Insulin`
10. `Triglycerides`
11. `Cholesterol`
12. `HDL`
13. `Non HDL`
14. `LDL (Cal)`
15. `VLDL (Cal)`
16. `Cho/HDL Ratio`
17. `Collection time PDL (Lab)`
18. Three fingerstick glucose readings with recorded observation times.

## 4. Licence Obligations and Handling Rules
- **Attribution and Citation**: Any derivative work, model, or report must formally cite the PhysioNet dataset DOI (`10.13026/3z8q-x658`) and the Nature Scientific Data publication (`10.1038/s41597-025-05851-7`).
- **Non-Commercial Restriction**: The project and all outputs must strictly adhere to non-commercial usage.
- **ShareAlike (Copyleft)**: All downstream modifications, pipelines, and derivative artifacts must be shared under the same CC BY-NC-SA 4.0 terms.
- **Zero Raw Data Commits**: Raw dataset files, participant CSVs, and photographic images must NEVER be committed to this git repository. Users must acquire data directly from PhysioNet.
- **Aggregate-Only Repository Policy**: The repository may host only source code, configuration files, and aggregate-only audit reports.
- **Strict Anti-Re-identification Guard**: Under no circumstances may participant records be linked with outside data or subjected to re-identification attempts.

## 5. Documentation Inconsistencies and Local Audit Findings
The following issues were extracted from source documentation and tested against the downloaded dataset via `dtwin-audit`:
1. **[RESOLVED VIA LOCAL AUDIT] Sampling Frequency Discrepancy**: Audit confirmed that all participant timeseries CSVs record at strictly 1-minute intervals (`mode_delta = 60.0s`, `median_delta = 60.0s`, 99.98%–100% of deltas at mode). This confirms data was resampled/interpolated prior to release.
2. **[RESOLVED VIA LOCAL AUDIT] Participant Directory ID Range**: Audit confirmed that exactly 45 participant folders and 45 rows in `bio.csv` exist across the 1–49 range. The numeric sequence has missing folders for IDs 14, 18, 20, and 24, perfectly reconciling the 45 completed participants.
3. **[RESOLVED VIA LOCAL AUDIT] HbA1c Units and Value Range**: Audit confirmed `A1c PDL (Lab)` values range from 4.6 to 8.5 (mean 6.12, median 5.9). This resolves the unit ambiguity: the values are NGSP percentage units (`%`), **NOT** `mmol/mol`.
4. **[RESOLVED VIA LOCAL AUDIT] Extreme Error Sentinel Values in Blood Panels**: Audit detected and safely counted the documented error sentinels: `LDL (Cal)` contains 800 (1 count), `VLDL (Cal)` contains 400 (1 count), and `Cho/HDL Ratio` contains 400 (1 count).
5. **[RESOLVED VIA LOCAL AUDIT] Metabolic Equivalent (METs) Scaling**: Audit confirmed `METs` in participant activity streams has a minimum of 10.0 and median of 11.0–12.0, confirming that values are pre-multiplied by 10 (standard resting MET is 1.0).
6. **[RESOLVED VIA LOCAL AUDIT] Microbiome File Naming Discrepancy**: The extracted file is `microbes.csv` (Family 12), containing 45 rows and 1,980 columns (the `subject` ID plus 1,979 bacterial species indicator columns).
7. **[UNRESOLVED / SCHEDULED FOR STAGE 1] CGM Dual-Sensor Concordance**: FreeStyle Libre Pro vs Dexcom G6 Pro sensor concordance, relative drift, and gold-standard reference designation remain to be evaluated in Stage 1 exploratory analysis.
