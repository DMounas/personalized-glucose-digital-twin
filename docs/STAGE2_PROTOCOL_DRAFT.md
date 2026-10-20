# Stage 2 Predictive Modeling Protocol (Draft v0.1.0)

**Protocol Version:** 0.1.0-draft  
**Status:** PREREGISTERED PROTOCOL DRAFT FOR INDEPENDENT REVIEW  
**Dependencies:** `configs/stage1b.yaml`, `docs/reports/stage1b_r3_results.json`, `docs/reports/canonical_metrics.json`  

---

## 1. Scientific Objective & Primary Sensor Selection

### 1.1 Objective
The primary objective of Stage 2 is to develop, evaluate, and benchmark multi-horizon continuous sequential glucose forecasting models on the CGMacros v1.0.0 dataset. The initial focus is strictly placed on **continuous interstitial glucose regression** at forecast horizons $h = 30\text{ minutes}$ and $h = 60\text{ minutes}$.

### 1.2 Primary Sensor Target: Dexcom G6 Pro
**Dexcom G6 Pro** is designated as the primary modeling target primarily due to its **finer native measurement interval** (5-minute native lattice, ~288 points/day) compared to FreeStyle Libre Pro (15-minute native lattice, ~96 points/day). 
- Finer temporal resolution provides direct capture of postprandial glucose rates of change without relying on coarse multi-step linear interpolation.
- Sensor selection is justified solely by hardware sampling interval, **not** by unverified sensor-quality assertions, apparent lag differences, or threshold excursion count disparities.

### 1.3 FreeStyle Libre Pro Cross-Device Transfer (Deferred Sensitivity)
Cross-device transfer to FreeStyle Libre Pro is **not** a prerequisite for accepting the first Stage 2 model results. Because the two devices exhibit an observed systematic trace disagreement ($\mu_{\text{pool}} = -31.95\text{ mg/dL}$ with wide repeated-measures limits of agreement $[-79.89, +16.00]\text{ mg/dL}$), cross-device transfer is classified as an **optional secondary sensitivity analysis** to be conducted only after the primary Dexcom forecasting benchmark is frozen.

---

## 2. Feature Governance & Model Input Architecture

### 2.1 Input History & Native Vertex Anchoring
To avoid interpolation leakage, models are evaluated at candidate native sampling vertices:
- **Autoregressive Input History ($L = 60\text{ minutes}$):** 13 points sampled at 5-minute intervals: $[y_t, y_{t-5}, y_{t-10}, \dots, y_{t-60}]$.
- **Rate-of-Change Feature:** First-order difference $(y_t - y_{t-15}) / 15$.
- **Demographic & Baseline Covariates:** Age, Gender, BMI, baseline HbA1c (from `bio.csv`).

### 2.2 Time-of-Day / Circadian Features: EXCLUDED from Initial Model
- **Status:** **EXCLUDED from initial baseline model.**
- **Rationale:** While empirical meal timings follow diurnal human living patterns and the dataset filename references date shifting, the dataset documentation (`DataDictionary_CGMacros-00X.csv`) states only that timestamps are *"Randomly shifted time stamps for days in the study"* without explicitly confirming that the shift was an integer number of days or that local clock time (HH:MM) was strictly preserved. Because definitive primary-source documentation is inconclusive, diurnal circadian features ($[\sin(2\pi \cdot \text{TOD}/1440), \cos(2\pi \cdot \text{TOD}/1440)]$) are excluded from the initial model. They may only be evaluated as an exploratory sensitivity feature set in secondary experiments.
- **Calendar Features:** Day of week, month, and season remain **strictly prohibited**.

---

## 3. Native Grid & Phase Sensitivity Preregistration

### 3.1 Diagnostic Treatment of Native Grid Inferences
Stage 1B demonstrated that 99.35% of valid Dexcom data conform to a 5-minute piecewise-linear lattice. However, because raw sensor transmission telemetry and raw ADC counts were not published, inferred native vertices are treated as a **mathematical diagnostic** rather than proven physical sensor transmissions.

### 3.2 Preregistered Phase Sensitivity Evaluation
To guarantee that model performance is not an artifact of native phase selection, every candidate architecture must be evaluated across:
1. **Primary Evaluation:** Evaluated on session-specific inferred phase $\phi_s$ (Time Semantics T6).
2. **Phase Sensitivity Suite:** Evaluated across all five possible fixed phase offsets $\phi \in \{0, 1, 2, 3, 4\}$.
3. **Consequential Variation Stopping Rule:**
   - If performance across the 5 phases exhibits variation $> 10\%$ in RMSE or $> 2.0\text{ mg/dL}$ in absolute RMSE delta, the model is flagged as sensitive to interpolation phase and cannot claim hardware-lattice invariance.

---

## 4. Cross-Validation Architecture & Sample Size Hierarchies

### 4.1 Nested Sample Size Hierarchy
Statistical power and evaluation counts are defined strictly across nested hierarchical levels:
- **Level 1 (Independent Units):** $K = 45$ participants (15 Normal, 16 Prediabetes, 14 Type 2 Diabetes).
- **Level 2 (Contiguous Runs within Participants):** 1,200 runs of contiguous timestamps ($\Delta t = 60\text{ s}$); 1,202 runs of non-null Dexcom readings.
- **Level 3 (Candidate 5-Minute Native Origins):** 
  - +30 min horizon ($h=30$): **123,709 candidate origins** cohort-wide (Normal: 41,806; Prediabetes: 42,410; Diabetes: 39,493).
  - +60 min horizon ($h=60$): **123,266 candidate origins** cohort-wide (Normal: 41,665; Prediabetes: 42,218; Diabetes: 39,383).
- **Runs and windows are nested units within participants**, not independent subjects.

### 4.2 Grouped Cross-Validation Scheme
- **Cross-Validation Scheme:** 5-fold `StratifiedGroupKFold`.
- **Grouping Unit:** Participant cluster ($K = 45$). Zero intra-participant leakage between training and testing partitions.
- **Stratification Target:** Clinical baseline HbA1c stratum (Normal, Prediabetes, Type 2 Diabetes).
- **Session Purging:** Multi-minute timestamp gaps serve as natural segment boundaries; no window or sequence bridges across a gap.

---

## 5. Secondary Candidate Tasks & Feasibility Bounds

### 5.1 Hyperglycemia Excursion Feasibility Check (>180 mg/dL)
- **Status:** **FEASIBILITY CHECK ONLY** (secondary to continuous regression).
- **Target Event Definition:** Glucose exceeds $180\text{ mg/dL}$ for $\ge 15\text{ consecutive minutes}$ (or 3 consecutive 5-minute intervals), with persistence counter resetting on missing values (NaNs).
- **Release Criterion:** Glucose falls below $175\text{ mg/dL}$ ($5\text{ mg/dL}$ hysteresis) for $\ge 10\text{ consecutive minutes}$ (or 2 consecutive 5-minute intervals).
- **Observed Cohort Distribution:**
  - 678 total episodes (17 boundary-censored) detected on 1-minute series; 714 total episodes (14 boundary-censored) on 5-minute native lattice.
  - Participant coverage: 42/45 participants have $\ge 1$ episode; 40/45 have $\ge 3$ episodes; 33/45 have $\ge 5$ episodes; 27/45 have $\ge 10$ episodes.
  - In Type 2 Diabetes, 14/14 participants have $\ge 10$ episodes.
  - In Normal, only 4/15 participants have $\ge 10$ episodes (event scarcity in normoglycemic subjects).
- **Missingness & Censoring Semantics:** Boundary-censored episodes (active at run termination or truncated by $>5\text{ min}$ of missing sensor values) are explicitly reported and analyzed via censored survival/likelihood formulations.

### 5.2 Hypoglycemia Classification (<70 mg/dL): DEFERRED
- **Status:** **DEFERRED.**
- **Rationale:** Only 43 total hypoglycemia episodes occur on Dexcom cohort-wide across 45 participants (with 0 in most participants). Event scarcity is too extreme to support a standalone supervised classification task in Stage 2 without severe synthetic oversampling or clinical pooling.
