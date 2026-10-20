# Stage 2 Modeling Specification: Targets, Horizons, and Evaluation Governance (R3)

**Specification Version:** 3.4.0 (Stage 1B-R3.4 Frozen)  
**Status:** BOUNDED RECONCILIATION & STAGE 1B FREEZE (R3.4)  
**Supersedes:** `docs/MODELING_SPEC_R2.md` and `docs/MODELING_SPEC.md`  
**Dependencies:** [`docs/reports/stage1b_r3_results.json`](docs/reports/stage1b_r3_results.json), [`docs/reports/canonical_metrics.json`](docs/reports/canonical_metrics.json), [`docs/NATIVE_GRID_METHOD_R3.md`](docs/NATIVE_GRID_METHOD_R3.md)  

---

## 1. Primary Device Recommendation & Sensor Selection Governance

### 1.1 Primary Modeling Target: Dexcom G6 Pro
Based on comprehensive empirical findings from Stage 1B-R3, **Dexcom G6 Pro** is designated as the primary sensor target for all Stage 2 predictive modeling, digital twin forecasting, and what-if simulation experiments:
1. **Sampling Frequency:** Dexcom provides a 5-minute native sampling lattice (288 observations/day), compared to Libre's 15-minute lattice (96 observations/day). This yields 3x higher information density for capturing rapid postprandial glucose dynamics.
2. **Temporal Alignment:** Dexcom displays lower empirical temporal displacement across resampled signals (median lag $+5.0\text{ minutes}$ with Libre leading Dexcom).
3. **Hyperglycemia Event Sensitivity:** Dexcom detects 678 hyperglycemia episodes (>180 mg/dL) across the cohort compared to Libre's 369, providing a substantially richer event-prediction sample size.

### 1.2 Mandatory Sensitivity Analysis: FreeStyle Libre Pro
Because the two devices exhibit an observed systematic disagreement of $-31.95\text{ mg/dL}$ ($\mu_{\text{pool}}$) and $-32.36\text{ mg/dL}$ ($\mu_{\text{eq}}$) with repeated-measures limits of agreement $[-79.89, +16.00]\text{ mg/dL}$ (designated exploratory due to unadjusted temporal serial autocorrelation, reflecting observed trace differences rather than proven hardware bias or clinical ground truth), **models trained on Dexcom must never be assumed to transfer directly to Libre without adaptation**.
- Every Stage 2 model trained on Dexcom must undergo a mandatory cross-device sensitivity evaluation on FreeStyle Libre Pro.
- Cross-device evaluation must report performance under:
  (a) Raw zero-shot transfer (demonstrating performance degradation under sensor offset).
  (b) Median-recalibrated transfer (evaluating whether a simple baseline shift restores predictive validity).

---

## 2. Mandatory Modeling Safeguards & Methodological Boundaries

All Stage 2 predictive modeling and digital twin architectures must strictly adhere to five foundational safeguards:

### 2.1 Safeguard 1: Session-Specific Native Phase Tracking (Time Semantics T6)
Because recording halts and sensor restart events can introduce clock phase shifts (as demonstrated by Participant Cluster 23, where Session 1 aligns to minute $\equiv 1 \pmod 5$ and Session 2 aligns to minute $\equiv 2 \pmod 5$ across an unrecorded 40.5-hour interval), **models must never assume a static, cohort-wide, or file-wide native phase**.
- Every continuous run $\ge 120\text{ minutes}$ must determine its session-specific phase $\phi_s \in \{0, \dots, P-1\}$ dynamically via Time Semantics T6.
- Feature extraction windows and target horizons must be anchored strictly to $(t_{\text{anchor}} \equiv \phi_s \pmod P)$.

### 2.2 Safeguard 2: Strict Prohibition of Arbitrary 1-Minute Causal Evaluation
The 1-minute time series published in CGMacros are linearly interpolated from 5-minute (Dexcom) and 15-minute (Libre) hardware measurements.
> [!CAUTION]
> **Prohibition of Interpolated Causal Evaluation:**
> Evaluating a causal real-time forecasting model at arbitrary 1-minute intervals (e.g. at minute $t=7$ between native vertices $t=5$ and $t=10$) introduces future data leakage, because $y_7$ is constructed from $y_{10}$.
> **All Stage 2 predictive models must be evaluated strictly at native sampling vertices ($t \pmod 5 = \phi_D$ for Dexcom; $t \pmod{15} = \phi_L$ for Libre).**

### 2.3 Safeguard 3: Participant-Clustered `StratifiedGroupKFold` Cross-Validation
- **Zero Intra-Participant Random Splitting:** Rows or windows from the same participant must never appear in both train and test partitions.
- **Grouped Stratification:** All cross-validation must use 5-fold Participant-Clustered Cross-Validation (`StratifiedGroupKFold`) grouped by participant cluster ($K=45$) and stratified across the three clinical HbA1c cohorts (Normal $N=15$, Prediabetes $N=16$, Type 2 Diabetes $N=14$).
- **Session Purging:** When evaluating sequential models within participants, multi-hour gaps must serve as natural fold boundaries without interpolation bridging.

### 2.4 Safeguard 4: Strict Calibration / Test Separation in Cross-Device Transfer
When performing cross-device sensitivity transfer between Dexcom G6 Pro and FreeStyle Libre Pro:
- Any recalibration parameters (such as the median sensor offset $\mu_{\text{pool}} = -31.95\text{ mg/dL}$ or affine scale adjustments) must be fit **strictly on training/calibration folds**.
- Recalibrated models must then be evaluated out-of-sample on unseen test fold participants to verify generalization without data snooping.

### 2.5 Safeguard 5: Methodological Differentiation from Published CGMacros Baseline
The published benchmark on CGMacros (Das et al., *Nature Scientific Data* / PhysioNet) evaluated postprandial glucose dynamics by predicting meal-level 2-hour Area Under the Curve ($\text{AUC}_{2\text{h}}$ / $\text{iAUC}_{2\text{h}}$) using meal macronutrients, baseline glucose, and clinical covariates via tree-based models (XGBoost, Random Forest).
- **Methodological Distinction:** Our proposed Stage 2 Task T1 is continuous multi-horizon sequential glucose forecasting ($h = 30\text{ min}$ and $60\text{ min}$) evaluated directly on physical hardware native sampling lattices (5-minute Dexcom, 15-minute Libre), rather than postprandial summary metric prediction.
- **Rationale for Native Lattice Anchoring:** Anchoring sequential forecasts and evaluations to genuine measurement vertices ensures that model inputs, states, and targets represent true physical sensor readings without relying on intervening interpolation points. This provides direct clinical decision support anchored to genuine hardware measurements, differentiating our sequential formulation from published meal-level AUC modeling without asserting defects or leakage in the published baseline.

---

## 3. Candidate Task Specifications

### Task T1: Multi-Horizon Continuous Glucose Forecasting (Regression)
- **Objective:** Forecast future interstitial glucose concentration $y_{t+h}$ given historical observations up to time $t$.
- **Horizons ($h$):** $30\text{ minutes}$ (6 Dexcom native steps) and $60\text{ minutes}$ (12 Dexcom native steps).
- **Input Features:**
  - Autoregressive glucose history: $[y_t, y_{t-5}, y_{t-10}, \dots, y_{t-60}]$ (13 native points).
  - First-order rate of change: $(y_t - y_{t-15}) / 15$.
  - Circadian time: $[\sin(2\pi \text{TOD} / 1440), \cos(2\pi \text{TOD} / 1440)]$. **Permitted**: Empirical meal timings align with diurnal human routines (breakfast median 08:15 AM, lunch 12:33 PM, dinner 06:58 PM) and the HIPAA date-shifting protocol (`DataDictionary_CGMacros-00X.csv`, `CGMacros_dateshifted365.zip`) applies an integer-day shift that strictly preserves local wall-clock time (HH:MM). However, calendar features (month, day of week, season) remain strictly prohibited due to multi-day shifting.
  - Baseline covariates: Age, Gender, BMI, HbA1c.
- **Descriptive Difficulty Benchmarks (Descriptive, Not a Model):**
  - Dexcom 30-min absolute delta: Mean $13.18\text{ mg/dL}$, Median $7.60\text{ mg/dL}$, 90th percentile $32.80\text{ mg/dL}$ ($N=625,098$).
  - Dexcom 60-min absolute delta: Mean $19.38\text{ mg/dL}$, Median $11.00\text{ mg/dL}$, 90th percentile $48.20\text{ mg/dL}$ ($N=622,078$).
- **Primary Metrics:** RMSE (mg/dL), MAE (mg/dL), and Clarke Error Grid Analysis against Dexcom targets.

### Task T2: Excursion Episode Prediction (Classification)
- **Objective:** Predict the onset of a sustained excursion episode within a prediction horizon of $30\text{ minutes}$.
- **Target Definitions:**
  - **Hyperglycemia Event:** Glucose exceeds $180\text{ mg/dL}$ for $\ge 15\text{ consecutive minutes}$.
  - **Hypoglycemia Event:** Glucose drops below $70\text{ mg/dL}$ for $\ge 15\text{ consecutive minutes}$.
- **Hysteresis & Censoring Criteria:**
  - Release from an active episode requires glucose returning to the safe zone with a $5\text{ mg/dL}$ hysteresis margin (i.e. $< 175\text{ mg/dL}$ for hyperglycemia release) sustained for $\ge 10\text{ minutes}$.
  - Missing values (NaNs) during entry persistence strictly reset the counter, preventing discontinuous minutes from falsely triggering an episode.
  - Boundary-censored episodes (truncated by recording halts or sensor dropouts) must be explicitly flagged and analyzed via survival/censored likelihoods.
- **Cohort Observed Counts (Corrected Null-Reset):**
  - Dexcom: 1,303 hyper-140 (38 censored); 678 hyper-180 (17 censored); 43 hypo-70 (0 censored).
  - Libre: 772 hyper-140 (11 censored); 369 hyper-180 (7 censored); 494 hypo-70 (58 censored).
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
| **Hyperglycemia Episodes ($>180\text{ mg/dL}$)** | **678** (Dexcom) | Event instances for Task T2 classification (with 17 boundary-censored). |
| **Hypoglycemia Episodes ($<70\text{ mg/dL}$)** | **43** (Dexcom) | Rare event class; requires class re-weighting or anomaly detection. |

> [!NOTE]
> **Dexcom Dataset Representation Coverage:**
> Eligible runs contained 625,728 of 629,825 valid one-minute-grid Dexcom rows (99.35% of valid rows in the released representation) and spanned all 45/45 participants (100.0% cohort coverage). This percentage represents row coverage in the released 1-minute interpolated representation and must not be equated with coverage of independent physical sensor observations.

