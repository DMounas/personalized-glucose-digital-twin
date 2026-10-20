# Stage 2 Modeling Specification: Targets, Horizons, and Evaluation Governance (R2)

**Specification Version:** 2.0.0 (Stage 1B-R2)  
**Status:** CORRECTED REVISION — PENDING INDEPENDENT REVIEW  
**Supersedes:** `docs/MODELING_SPEC.md`  
**Dependencies:** [`docs/reports/stage1b_r2_results.json`](docs/reports/stage1b_r2_results.json), [`docs/NATIVE_GRID_METHOD_R2.md`](docs/NATIVE_GRID_METHOD_R2.md)

---

## 1. Primary Device Recommendation & Sensor Selection Governance

### 1.1 Primary Modeling Target: Dexcom G6 Pro
Based on comprehensive empirical findings from Stage 1B-R2, **Dexcom G6 Pro** is designated as the primary sensor target for all Stage 2 predictive modeling, digital twin forecasting, and what-if simulation experiments:
1. **Sampling Frequency:** Dexcom provides a 5-minute native sampling lattice (288 observations/day), compared to Libre's 15-minute lattice (96 observations/day). This yields 3x higher information density for capturing rapid postprandial glucose dynamics.
2. **Temporal Alignment:** Dexcom displays lower temporal displacement relative to fast glucose surges, with cross-correlation peaks indicating a 5-minute lead relative to Libre's moving-average filtering.
3. **Hyperglycemia Event Sensitivity:** Dexcom detects 683 hyperglycemia episodes (>180 mg/dL) across the cohort compared to Libre's 369, providing a substantially richer event-prediction sample size.

### 1.2 Mandatory Sensitivity Analysis: FreeStyle Libre Pro
Because the two devices exhibit an observed systematic disagreement of $-31.95\text{ mg/dL}$ ($\mu_{\text{pool}}$) and $-32.36\text{ mg/dL}$ ($\mu_{\text{eq}}$) with repeated-measures limits of agreement $[-79.89, +16.00]\text{ mg/dL}$, **models trained on Dexcom must never be assumed to transfer directly to Libre without adaptation**.
- Every Stage 2 model trained on Dexcom must undergo a mandatory cross-device sensitivity evaluation on FreeStyle Libre Pro.
- Cross-device evaluation must report performance under:
  (a) Raw zero-shot transfer (demonstrating performance degradation under sensor offset).
  (b) Median-recalibrated transfer (evaluating whether a simple baseline shift restores predictive validity).

---

## 2. Hard Methodological Boundaries & Causal Real-Time Constraints

### 2.1 The Native-Lattice Evaluation Mandate
The 1-minute time series published in CGMacros are linearly interpolated from 5-minute (Dexcom) and 15-minute (Libre) measurements.
> [!CAUTION]
> **Strict Prohibition of Arbitrary 1-Minute Causal Evaluation:**
> Evaluating a causal real-time forecasting model at arbitrary 1-minute intervals (e.g. at minute $t=7$ between native vertices $t=5$ and $t=10$) introduces severe future data leakage, because $y_7$ is constructed from $y_{10}$.
> **All Stage 2 predictive models must be evaluated strictly at native sampling vertices ($t \pmod 5 = \phi_D$ for Dexcom; $t \pmod{15} = \phi_L$ for Libre).**

### 2.2 Cross-Validation & Participant Clustering
- **Zero Intra-Participant Random Splitting:** Rows or windows from the same participant must never be split across train and test folds.
- **Clustered Cross-Validation:** All cross-validation must use 5-fold Participant-Clustered Cross-Validation (`StratifiedGroupKFold` grouped by participant ID and stratified by HbA1c clinical group: normal, prediabetes, diabetes).
- **Session Purging:** If evaluating sequential models within participants, multi-hour gaps must serve as natural fold boundaries without interpolation bridging.

---

## 3. Candidate Task Specifications

### Task T1: Multi-Horizon Continuous Glucose Forecasting (Regression)
- **Objective:** Forecast future interstitial glucose concentration $y_{t+h}$ given historical observations up to time $t$.
- **Horizons ($h$):** $30\text{ minutes}$ (6 Dexcom native steps) and $60\text{ minutes}$ (12 Dexcom native steps).
- **Input Features:**
  - Autoregressive glucose history: $[y_t, y_{t-5}, y_{t-10}, \dots, y_{t-60}]$ (13 native points).
  - First-order rate of change: $(y_t - y_{t-15}) / 15$.
  - Circadian time: $[\sin(2\pi \text{TOD} / 1440), \cos(2\pi \text{TOD} / 1440)]$.
  - Baseline covariates: Age, Gender, BMI, HbA1c.
- **Descriptive Difficulty Benchmarks (Descriptive, Not a Model):**
  - Dexcom 30-min absolute delta: Mean $13.18\text{ mg/dL}$, Median $7.60\text{ mg/dL}$, 90th percentile $32.80\text{ mg/dL}$.
  - Dexcom 60-min absolute delta: Mean $19.38\text{ mg/dL}$, Median $11.00\text{ mg/dL}$, 90th percentile $48.20\text{ mg/dL}$.
- **Primary Metrics:** RMSE (mg/dL), MAE (mg/dL), and Clarke Error Grid Analysis against Dexcom targets.

### Task T2: Excursion Episode Prediction (Classification)
- **Objective:** Predict the onset of a sustained excursion episode within a prediction horizon of $30\text{ minutes}$.
- **Target Definitions:**
  - **Hyperglycemia Event:** Glucose exceeds $180\text{ mg/dL}$ for $\ge 15\text{ consecutive minutes}$.
  - **Hypoglycemia Event:** Glucose drops below $70\text{ mg/dL}$ for $\ge 15\text{ consecutive minutes}$.
- **Hysteresis & Censoring Criteria:**
  - Release from an active episode requires glucose returning to the safe zone with a $5\text{ mg/dL}$ hysteresis margin (i.e. $< 175\text{ mg/dL}$ for hyperglycemia release) sustained for $\ge 10\text{ minutes}$.
  - Boundary-censored episodes (truncated by recording halts or sensor dropouts) must be explicitly flagged and analyzed via survival/censored likelihoods.
- **Primary Metrics:** Precision, Recall, AUROC, AUPRC, and Brier Score.

### Task T3: Postprandial Meal Response & What-If Simulation
- **Objective:** Predict postprandial glucose trajectory and peak excursion following self-logged nutritional intake.
- **Cohort Size:** 1,706 reconciled meal events across 45 participants.
- **Input Covariates:**
  - Meal composition: Carbohydrates (g), Protein (g), Fat (g), Calories (kcal).
  - Preprandial state: Baseline glucose at $t_{\text{meal}}$, 30-min pre-meal trend.
  - Participant digital twin parameters: HbA1c stratum, BMI, fasting glucose.
- **Target Endpoints:**
  - Peak postprandial glucose ($C_{\max}$, mg/dL).
  - Time to peak ($T_{\max}$, minutes).
  - 2-hour postprandial incremental Area Under the Curve ($\text{iAUC}_{2\text{h}}$).
- **Primary Metrics:** Trajectory RMSE, $C_{\max}$ MAE, and Rank Correlation on meal carbohydrate sensitivity.

---

## 4. Effective Sample Size & Power Architecture

All statistical modeling must report sample size across multiple hierarchical levels:

| Hierarchical Level | Effective Count | Methodological Significance |
| :--- | :---: | :--- |
| **Independent Participants ($K$)** | **45** | Unit of independent clustering; dictates cross-validation fold size. |
| **Contiguous Runs ($\mathcal{R}$)** | **1,200** | Independent continuous recording segments ($\Delta t = 60\text{ s}$). |
| **Non-Overlapping 2-Hour Windows** | **5,206** | Feasible independent training/evaluation sequences without gap bridging. |
| **Reconciled Meal Events** | **1,706** | Ingestion-anchored events for postprandial digital twin training. |
| **Coincident Native Pairs (Set A)** | **37,477** | Simultaneous raw hardware measurements across both devices. |
| **Hyperglycemia Episodes ($>180\text{ mg/dL}$)** | **683** (Dexcom) | Event instances for Task T2 classification (with 21 boundary-censored). |
| **Hypoglycemia Episodes ($<70\text{ mg/dL}$)** | **43** (Dexcom) | Rare event class; requires class re-weighting or anomaly detection. |
