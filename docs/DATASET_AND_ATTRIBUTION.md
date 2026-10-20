# Dataset Source, Attribution & Data Governance

## 1. Primary Dataset Overview

The experiments in this repository are developed and evaluated using the **CGMacros** dataset, an open-access multimodal dataset containing continuous glucose monitoring (CGM), physical activity, and macronutrient logging from free-living individuals.

- **Repository Source**: [PhysioNet: CGMacros (Version 1.0.0)](https://physionet.org/content/cgmacros/1.0.0/)
- **DOI**: [10.13026/0m1y-h241](https://doi.org/10.13026/0m1y-h241)
- **Publication Reference**: Bent, B., Wang, K., Grzesik, P. et al. *CGMacros: A multimodal dataset of continuous glucose monitoring, macronutrients, and physical activity in free-living conditions*. **Scientific Data** 12, 187 (2025). [https://doi.org/10.1038/s41597-025-05851-7](https://doi.org/10.1038/s41597-025-05851-7)

---

## 2. Cohort Characteristics

The analyzed cohort comprises **45 adult participants** stratified across metabolic health categories:

| Diagnostic Stratum | Participant Count ($N$) | Definition | Clinical Relevance |
| :--- | :---: | :--- | :--- |
| **Normal** | 15 | Baseline normoglycemic controls | Fasting blood glucose &lt; 100 mg/dL, HbA1c &lt; 5.7% |
| **Prediabetes** | 16 | Impaired fasting glucose / glucose intolerance | Fasting glucose 100–125 mg/dL, HbA1c 5.7–6.4% |
| **Type 2 Diabetes** | 14 | Overt diabetic metabolic phenotype | Fasting glucose &ge; 126 mg/dL, HbA1c &ge; 6.5% |
| **Total Cohort** | **45** | Free-living continuous monitoring (~10 days/subject) | 123,599 eligible origins (+30m); 123,164 (+60m) |

---

## 3. Data Governance & Licensing Terms

### Separation of Code vs. Data Licenses
1. **Repository Software (MIT License)**: All source code, analysis workflows, visualization tools, and documentation created in this repository are licensed under the permissive [MIT License](../LICENSE).
2. **CGMacros Dataset (CC-BY-NC-SA 4.0)**: The CGMacros dataset is governed independently under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/) license. Usage of the dataset must adhere to PhysioNet's terms:
   - Attribution to the original authors must be preserved.
   - Non-commercial research and educational use only.
   - Derived datasets must share-alike under compatible licensing.

### Public Repository Privacy Safeguards
To comply with HIPAA Safe Harbor and data protection standards, this public repository **does not redistribute the raw CGMacros dataset or individual-level patient records**:
- Raw data files (`data/cgmacros/`) are excluded via `.gitignore`.
- Row-level glucose measurements and participant-level time series are strictly omitted from git tracking.
- Out-of-fold prediction archives (`*.csv.gz`) are excluded from tracking.
- All published benchmarks report cohort-level and diagnostic subgroup aggregate statistics only.

---

## 4. How to Obtain the Dataset for Full Replication

To reproduce the model training from raw data from scratch:

1. Visit the official PhysioNet page: [https://physionet.org/content/cgmacros/1.0.0/](https://physionet.org/content/cgmacros/1.0.0/)
2. Create or log into your free PhysioNet account and accept the standard Data Use Agreement.
3. Download the data archive (e.g. `CGMacros_dateshifted365.zip`).
4. Extract the contents into the repository's `data/` directory:
   ```
   data/
   └── cgmacros/
       └── CGMacros/
           ├── bio.csv
           ├── CGMacros-001/
           │   └── CGMacros-001.csv
           ├── CGMacros-002/
           │   └── CGMacros-002.csv
           └── ... (CGMacros-049)
   ```
5. Run the verified pipeline commands described in [README.md](../README.md).
