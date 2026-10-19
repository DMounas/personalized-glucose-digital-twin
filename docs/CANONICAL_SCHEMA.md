# Canonical Schema Specification: CGMacros Digital Twin

> **Status**: ESTABLISHED & VERIFIED ON REAL DATASET (Stage 1A)  
> **Source Standard**: PhysioNet CGMacros v1.0.0 & Nature *Scientific Data* (Das et al., 2025)  
> **Configuration**: `configs/schema_aliases.yaml`  

---

## 1. Overview and Design Principles

The CGMacros dataset combines dual continuous glucose monitoring, smartwatch telemetry, nutritional meal logging with photographs, baseline clinical biomarkers, and gut microbiome sequencing across 45 participants.

Because the raw dataset exhibits 9 distinct header layout families, trailing whitespace in column names, duplicate column headers (`Time (t)`), and optional participant-specific activity fields, this Canonical Schema standardizes all inputs under the following principles:

1. **Name-Based Resolution**: Columns are never accessed or mapped by position. Mappings are resolved strictly by column name via `configs/schema_aliases.yaml`.
2. **Whitespace and Case Normalization**: Trailing spaces (`Amount Consumed `, `Body weight `) and case variations (`Meal Type` vs `Meal type`, `Image path` vs `Image Path`) are normalized deterministically.
3. **Approved Ignorable Columns**: Raw artifacts such as index dumps (`Unnamed: 0`) and internal logging pointers (`RecordIndex`) are explicitly classified as ignorable and safely stripped during canonical ingestion.
4. **Strict vs Permissive Modes**: In strict mode, unapproved columns fail loudly (`SchemaValidationError`). In permissive mode, unmapped columns are preserved with sanitization.
5. **Privacy and De-Identification Integrity**: Date-shifted timestamps are transformed into relative elapsed time without generating calendar features (month, day of week, season). Raw patient records or photos are never exposed.

---

## 2. Table Specifications

### 2.1 Per-Participant Timeseries (`participant_timeseries`)

Primary continuous time series recorded at a uniform 1-minute cadence. As confirmed in Das et al. (*Scientific Data* 12, 1391, 2025), uniform 1-minute intervals were produced via **linear interpolation** from physical hardware sampling at 15 minutes (Abbott FreeStyle Libre Pro) and 5 minutes (Dexcom G6 Pro).

| Canonical Field Name | Data Type | Units | Sensor / Source | Valid Range | Nullable | Description & Notes |
|:---|:---|:---|:---|:---|:---|:---|
| `participant_id` | `int64` | ID | Directory name | 1–49 | No | Subject integer ID extracted from folder name `CGMacros-{s:03d}`. |
| `timestamp` | `datetime64[ns]` | ISO 8601 | Device clock | Date-shifted | No | Observation timestamp shifted by $\pm N$ days ($365 < N < 720$) per HIPAA. |
| `relative_time_seconds` | `float64` | seconds | Derived ($t - t_0$) | $\ge 0.0$ | No | Elapsed seconds from participant's first valid timestamp $t_0$. |
| `relative_time_minutes` | `float64` | minutes | Derived ($t - t_0$) | $\ge 0.0$ | No | Elapsed minutes from $t_0$ ($\text{seconds} / 60.0$). Core continuous time coordinate. |
| `day_offset` | `float64` | days | Derived ($t - t_0$) | $\ge 0.0$ | No | Elapsed fractional days from $t_0$ ($\text{seconds} / 86400.0$). |
| `libre_gl` | `float64` | mg/dL | FreeStyle Libre Pro | 40–400 | Yes (0.03%) | Interstitial glucose reading. Interpolated across 15-min sensor steps. |
| `dexcom_gl` | `float64` | mg/dL | Dexcom G6 Pro | 40–400 | Yes (7.76%) | Interstitial glucose reading. Interpolated across 5-min sensor steps. |
| `heart_rate` | `float64` | bpm | Fitbit Sense | 30–176 | Yes (10.92%) | Mean heart rate over the past minute. |
| `calories_activity` | `float64` | kcal | Fitbit Sense | 0–16.18 | Yes | Estimated energy expenditure in the past minute. (Missing in Family 4 / P07). |
| `mets` | `float64` | scaled MET | Fitbit Sense | 10–176 | Yes | Metabolic Equivalent of Task pre-scaled by 10 (resting = 10.0). Missing in Family 6 & 9. |
| `intensity` | `float64` | level | Fitbit Sense | $\ge 0$ | Yes | Alternative activity intensity present in 11 participant files (Families 6 & 9). |
| `steps` | `float64` | steps | Fitbit Sense | $\ge 0$ | Yes | Step count logged in `CGMacros-007` (Family 4) in place of activity calories. |
| `meal_type` | `string` | category | MyFitnessPal / WhatsApp | Enum | Yes (99.75%) | Canonical meal start event: `breakfast`, `lunch`, `dinner`, `snack`. Null for non-meal rows. |
| `meal_calories` | `float64` | kcal | Nutritional panel | 0–2826 | Yes | Estimated caloric content of the logged meal. Sparse impulse. |
| `meal_carbs` | `float64` | g | Nutritional panel | 0–761 | Yes | Estimated carbohydrate mass in consumed meal. Sparse impulse. |
| `meal_protein` | `float64` | g | Nutritional panel | 0–148 | Yes | Estimated protein mass in consumed meal. Sparse impulse. |
| `meal_fat` | `float64` | g | Nutritional panel | 0–508 | Yes | Estimated total fat mass in consumed meal. Sparse impulse. |
| `meal_fiber` | `float64` | g | Nutritional panel | 0–2830 | Yes | Estimated dietary fiber mass in consumed meal. Sparse impulse. |
| `sugar` | `float64` | g | Nutritional panel | 0–50 | Yes | Optional sugar content recorded specifically in `CGMacros-013` (Family 7). |
| `amount_consumed` | `float64` | % | Participant log | 0–100% | Yes | Estimated percentage of meal consumed. (Column absent in P28 & P29 / Family 8). |
| `image_path` | `string` | path | WhatsApp log | String | Yes | Relative file path to meal photograph in participant `photos/` folder. |

---

### 2.2 Baseline Demographics and Clinical Labs (`bio_baseline`)

Extracted from `bio.csv`, recording Day 1 participant demographics, anthropometrics, fasting clinical labs, and oral glucose challenge fingersticks.

| Canonical Field Name | Raw Field Header | Data Type | Units | Valid Range | Error Sentinels | Description |
|:---|:---|:---|:---|:---|:---|:---|
| `participant_id` | `subject` | `int64` | ID | 1–49 | None | Study participant number (45 study completers). |
| `age_years` | `Age` | `float64` | years | 18–69 | None | Age at study enrollment. |
| `gender` | `Gender` | `string` | factor | `M`, `F` | None | Biological sex. |
| `bmi` | `BMI` | `float64` | kg/m² | 20.69–49.09 | None | Body Mass Index calculated at baseline. |
| `weight_lbs` | `Body weight ` | `float64` | lbs | 116.8–284.6 | None | Body weight at enrollment. |
| `height_inches` | `Height ` | `float64` | inches | 59–72 | None | Height at enrollment. |
| `ethnicity_self_identified` | `Self-identify ` | `string` | factor | String | None | Self-identified race / ethnicity. |
| `hba1c_percent` | `A1c PDL (Lab)` | `float64` | NGSP % | 4.6–8.5 | None | Glycated hemoglobin. (Confirms % units, NOT mmol/mol). |
| `fasting_glucose_mg_dl` | `Fasting GLU - PDL (Lab)` | `float64` | mg/dL | 79–218 | None | Fasting plasma glucose measured in clinical laboratory. |
| `fasting_insulin_mcu_ml` | `Insulin ` | `float64` | mcU/mL | 2.5–46.4 | None | Fasting serum insulin. |
| `triglycerides_mg_dl` | `Triglycerides` | `float64` | mg/dL | 40–1150 | None | Fasting serum triglycerides. |
| `total_cholesterol_mg_dl` | `Cholesterol` | `float64` | mg/dL | 91–345 | None | Fasting total serum cholesterol. |
| `hdl_mg_dl` | `HDL` | `float64` | mg/dL | 24–106 | None | Fasting high-density lipoprotein cholesterol. |
| `non_hdl_mg_dl` | `Non HDL ` | `float64` | mg/dL | 38–283 | None | Fasting non-HDL cholesterol. |
| `ldl_calculated_mg_dl` | `LDL (Cal)` | `float64` | mg/dL | 21–260 | **800** | Calculated LDL cholesterol. Sentinel 800 indicates calculation failure. |
| `vldl_calculated_mg_dl` | `VLDL (Cal)` | `float64` | mg/dL | 8–78 | **400** | Calculated VLDL cholesterol. Sentinel 400 indicates calculation failure. |
| `cholesterol_hdl_ratio` | `Cho/HDL Ratio` | `float64` | ratio | 1.7–400 | **400** | Total cholesterol to HDL ratio. Sentinel 400 indicates invalid. |
| `lab_collection_time` | `Collection time PDL (Lab)` | `string` | HH:MM | Time | None | Clock time of blood specimen collection. |
| `fingerstick_glu_1_mg_dl` | `#1 Contour Fingerstick GLU` | `float64` | mg/dL | 80–220 | None | First capillary fingerstick glucose reading. |
| `fingerstick_time_1` | `Time (t)` [1st instance] | `string` | HH:MM | Time | None | Observation time for fingerstick #1. |
| `fingerstick_glu_2_mg_dl` | ` #2 Contour Fingerstick GLU` | `float64` | mg/dL | 73–314 | None | Second capillary fingerstick glucose reading. |
| `fingerstick_time_2` | `Time (t)` [2nd instance] | `string` | HH:MM | Time | None | Observation time for fingerstick #2. |
| `fingerstick_glu_3_mg_dl` | `#3 Contour Fingerstick GLU` | `float64` | mg/dL | 67–247 | None | Third capillary fingerstick glucose reading. |
| `fingerstick_time_3` | `Time (t)` [3rd instance] | `string` | HH:MM | Time | None | Observation time for fingerstick #3. |
| `metabolic_status` | Derived | `string` | factor | Enum | None | ADA diagnostic category: `healthy` (<5.7%), `pre_diabetes` (5.7–6.4%), `type_2_diabetes` (>6.4%). |

---

### 2.3 Viome Gut Health Scores (`gut_health`)

Extracted from `gut_health_test.csv` (47 participants; includes subjects 24 and 25). Coded as ordinal integers: `1 = Not Optimal`, `2 = Average`, `3 = Good`.

| Canonical Field Name | Raw Field Header | Range | Description |
|:---|:---|:---|:---|
| `participant_id` | `\ufeffsubject` / `subject` | 1–49 | Participant identifier. |
| `gut_lining_health` | `Gut Lining Health` | 1–3 | Mucosal barrier integrity score. |
| `lps_biosynthesis_pathways` | `LPS Biosynthesis Pathways` | 1–3 | Lipopolysaccharide endotoxin synthesis activity. |
| `biofilm_chemotaxis_virulence_pathways` | `Biofilm, Chemotaxis, and Virulence Pathways` | 1–3 | Pro-inflammatory microbial virulence pathways. |
| `tma_production_pathways` | `TMA Production Pathways` | 1–3 | Trimethylamine production pathways. |
| `ammonia_production_pathways` | `Ammonia Production Pathways` | 1–3 | Microbial ammonia production. |
| `metabolic_fitness` | `Metabolic Fitness` | 1–3 | Functional pathways associated with blood glucose and insulin resistance. |
| `active_microbial_diversity` | `Active Microbial Diversity` | 1–3 | Percentile of active microbial species detected. |
| `butyrate_production_pathways` | `Butyrate Production Pathways` | 1–3 | Short-chain fatty acid (butyrate) synthesis activity. |
| `flagellar_assembly_pathways` | `Flagellar Assembly Pathways` | 1–3 | Microbial mobility and flagellar synthesis. |
| `putrescine_production_pathways` | `Putrescine Production Pathways` | 1–3 | Putrescine polyamine synthesis pathways. |
| `uric_acid_production_pathways` | `Uric Acid Production Pathways` | 1–3 | Urate degradation and production pathways. |
| `bile_acid_metabolism_pathways` | `Bile Acid Metabolism Pathways` | 1–3 | Secondary bile acid conversion activity. |
| `inflammatory_activity` | `Inflammatory Activity` | 1–3 | Environmental gut inflammation reflection. |
| `gut_microbiome_health` | `Gut Microbiome Health` | 1–3 | Overall microbiome balance and diversity score. |
| `digestive_efficiency` | `Digestive Efficiency` | 1–3 | Gastrointestinal digestive breakdown efficiency. |
| `protein_fermentation` | `Protein Fermentation` | 1–3 | Proteolytic fermentation metabolites. |
| `gas_production` | `Gas Production` | 1–3 | Overall microbial gas generation. |
| `methane_gas_production_pathways` | `Methane Gas Production Pathways` | 1–3 | Methanogenic archaea pathways. |
| `sulfide_gas_production_pathways` | `Sulfide Gas Production Pathways` | 1–3 | Hydrogen sulfide pathway activity. |
| `oxalate_metabolism_pathways` | `Oxalate Metabolism Pathways` | 1–3 | Oxalate degradation pathways. |
| `salt_stress_pathways` | `Salt Stress Pathways` | 1–3 | Osmotic and sodium stress response pathways. |
| `microbiome_induced_stress` | `Microbiome-Induced Stress` | 1–3 | Systemic microbial stress burden score. |

---

### 2.4 Microbiome Species Indicators (`microbes`)

Extracted from `microbes.csv` (45 participants, 1,980 columns).
- `participant_id` (`subject`): Integer ID (1–49).
- 1,979 binary indicator columns: `0 = Absent`, `1 = Present` for sequenced bacterial taxa.
- Trailing whitespace in species column headers is stripped during ingestion.

---

## 3. Derivations and Transformations

### 3.1 Relative Time Coordinates
Because timestamps were randomly shifted by $\pm N$ days ($365 < N < 720$) per HIPAA Safe Harbor de-identification:
- $t_0$ is defined as the first valid observation timestamp in the participant's timeseries.
- $\text{relative\_time\_seconds} = (t - t_0).\text{total\_seconds()}$
- $\text{relative\_time\_minutes} = \frac{\text{relative\_time\_seconds}}{60.0}$
- $\text{day\_offset} = \frac{\text{relative\_time\_seconds}}{86400.0}$
- **Prohibited Derivations**: `day_of_week`, `day_of_month`, `month_of_year`, `calendar_year`, `is_weekend`, `season`.

### 3.2 Meal Type Normalization
Raw meal entries contain mixed casing (`Breakfast`, `breakfast`, `Dinner`, `dinner`, `Snacks`, `snack`, `snack 1`). Canonical normalization resolves these to:
- `breakfast` (436 events)
- `lunch` (435 events)
- `dinner` (492 events)
- `snack` (343 events)

### 3.3 Clinical Error Sentinel Masking
When computing descriptive clinical statistics, error sentinels (`LDL = 800`, `VLDL = 400`, `Cho/HDL = 400`) are masked to `NaN` while preserving raw error flags in metadata:
$$\text{LDL}_{\text{clinical}} = \begin{cases} \text{NaN} & \text{if } \text{LDL} \ge 800 \\ \text{LDL} & \text{otherwise} \end{cases}$$
