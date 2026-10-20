# Stage 2 Predictive Modeling Protocol (Draft v0.3.0)

**Protocol Version:** 0.3.0-draft  
**Status:** REVISED WORKING DRAFT POST-CLAUDE STRATEGIC REVIEW (UNFROZEN)  
**Dependencies:** `configs/stage1b.yaml`, `docs/reports/stage1b_r3_results.json`, `docs/reports/canonical_metrics.json`, `docs/reports/stage2_aggregate_feasibility.json`  

> [!NOTE]
> This protocol is an **unfrozen working draft** revised in direct alignment with Claude's focused strategic review. It incorporates the primary 5-minute guard-band forecasting architecture, formalizes the fixed model ladder, mandates participant-disjoint repeated cross-validation, decouples personalization into a separate study, replaces individual participant listings with privacy-preserving aggregates, and defines explicit clinical and population claims boundaries. No Stage 2 predictive model training or benchmark execution will commence until independent review accepts this document.

---

## 1. Scientific Objective & Primary Sensor Selection

### 1.1 Objective
The primary objective of Stage 2 is to develop, evaluate, and benchmark multi-horizon continuous sequential glucose forecasting models on the CGMacros v1.0.0 dataset. Modeling is strictly formulated as **continuous interstitial glucose regression** evaluated at forecast horizons $h = 30\text{ minutes}$ and $h = 60\text{ minutes}$ from forecast issuance time $t$.

### 1.2 Primary Sensor Target: Dexcom G6 Pro
**Dexcom G6 Pro** is designated as the primary modeling target primarily due to its **finer native measurement interval** (5-minute native lattice, ~288 points/day) compared to FreeStyle Libre Pro (15-minute native lattice, ~96 points/day).
- Finer temporal resolution enables direct capture of postprandial glucose rates of change without reliance on multi-step linear interpolation.
- Sensor selection is justified solely by hardware sampling interval, **not** by unverified sensor-quality assertions, apparent lag differences, or threshold excursion count disparities.

### 1.3 FreeStyle Libre Pro Cross-Device Transfer (Deferred Sensitivity)
Cross-device transfer to FreeStyle Libre Pro is **not** a prerequisite for accepting Stage 2 model results. Because the two devices exhibit an observed systematic trace disagreement ($\mu_{\text{pool}} = -31.95\text{ mg/dL}$ with wide repeated-measures limits of agreement $[-79.89, +16.00]\text{ mg/dL}$), cross-device transfer is classified as an **optional secondary sensitivity analysis** to be conducted only after the primary Dexcom forecasting benchmark ladder is frozen.

---

## 2. Primary Phase / Interpolation Design & 5-Minute Guard-Band Architecture

### 2.1 Primary Forecasting Setup: 5-Minute History Guard-Band
To eliminate linear interpolation forward look-ahead by construction, the primary forecasting setup implements an explicit **5-minute history guard-band**:
- **Forecast Issuance Time:** Timestamp $t$.
- **Predictor Glucose History ($L = 60\text{ min}$ duration, 13 points):**
  $$[y(t-5), y(t-10), y(t-15), \dots, y(t-65)]$$
- **Target Outcomes:**
  $$y(t+30) \quad \text{and} \quad y(t+60)$$
- **Explicit Horizon Definitions:**
  - Horizons are strictly **30 minutes and 60 minutes from forecast issuance time $t$**.
  - Horizons are **35 minutes and 65 minutes from the latest permissible glucose input ($y_{t-5}$)**.
- **Rate-of-Change Feature:** First-order backward difference: $(y_{t-5} - y_{t-20}) / 15$.

### 2.2 Mathematical Proof of Guard-Band Look-Ahead Prevention
Under linear interpolation between native sampling vertices spaced at period $p = 5\text{ minutes}$ with native phase $\phi_s \in \{0, 1, 2, 3, 4\}$:
Let the elapsed minute coordinate be $m(t)$, and define $\delta = (m(t) - \phi_s) \pmod 5$.
The forward look-ahead of an interpolated point at time $t$ is:
$$\text{LookAhead}(\delta) = \begin{cases} 0 & \text{if } \delta = 0 \\ 5 - \delta & \text{if } \delta \in \{1, 2, 3, 4\} \end{cases}$$
- For $\delta = 0$: $t$ is on a native vertex; 0 minutes of forward look-ahead.
- For $\delta = 1$: $t = k + 1$; interpolation uses upcoming native vertex at $k+5 = t + 4$ (4-minute look-ahead).
- For $\delta = 2$: $t = k + 2$; interpolation uses upcoming native vertex at $k+5 = t + 3$ (3-minute look-ahead).
- For $\delta = 3$: $t = k + 3$; interpolation uses upcoming native vertex at $k+5 = t + 2$ (2-minute look-ahead).
- For $\delta = 4$: $t = k + 4$; interpolation uses upcoming native vertex at $k+5 = t + 1$ (1-minute look-ahead).

**Guard-Band Invariance:**  
In the primary guard-band setup, the latest glucose input is sampled at $t_{\text{input}} = t - 5$.  
Let $\delta_{-5} = (m(t - 5) - \phi_s) \pmod 5$.  
The forward native vertex required to construct $y(t - 5)$ occurs at:
$$t_{\text{vertex}} = (t - 5) + \text{LookAhead}(\delta_{-5})$$
Since $\text{LookAhead}(\delta_{-5}) \le 4$ for all $\delta_{-5}$, we have:
$$t_{\text{vertex}} \le (t - 5) + 4 = t - 1 < t$$
Therefore, the latest native vertex incorporated into any predictor occurred strictly before forecast issuance time $t$. The primary guard-band design completely prevents linear-interpolation look-ahead by construction across all possible underlying phases $\phi_s \in \{0, 1, 2, 3, 4\}$.

### 2.3 Diagnostic-Only Status of Time Semantics T6
- Session-specific T6 inferred phase $\phi_s$ is **strictly removed from primary test sample selection**.
- T6 inference relies on whole-run curvature statistics and must **never** determine test origins using future or test-set observations.
- T6 is retained exclusively as a post-hoc diagnostic to quantify trace characteristics and segment-level curvature alignment.

### 2.4 Removal of Architecture-Switching Rule
- The previously proposed post-hoc phase-sensitivity model-switching rule and its 2.0 mg/dL noise threshold rationale are **permanently removed**.
- Because the 5-minute guard band eliminates predictor look-ahead by construction, there is no technical justification for altering model classes post-hoc based on test-set phase variation.
- Sensitivity results across secondary phase suites will be reported transparently rather than triggering automated model switches.

### 2.5 Secondary Sensitivity Suites
1. **Unguarded History Ending at $t$ ($[y_t, y_{t-5}, \dots, y_{t-60}]$):**  
   Retained strictly as a secondary sensitivity comparison to quantify the empirical magnitude of interpolation look-ahead leakage against the primary guard-banded baseline.
2. **Fixed Phase Offsets ($\phi \in \{0, 1, 2, 3, 4\}$):**  
   Evaluated as prespecified sensitivity analyses across all five candidate lattices using identical participant-level folds. Per-participant skill and phase-to-phase variability will be documented; phase-specific models are recognized as evaluating distinct lattice targets and do not share identical target timestamps.

---

## 3. Feature Governance & Exclusions

### 3.1 Primary Model Input Exclusions
To maintain experimental rigor and prevent data leakage, the following features are **strictly excluded from the primary model**:
- **Amount Consumed:** Excluded due to uncalibrated self-report logging and widespread recording omissions.
- **Meal-End Information:** Excluded because meal-end timestamps are unknown at forecast issuance time $t$; only meal start context is permissible.
- **Microbiome Features:** Excluded due to sparse, cross-sectional unaligned sampling.
- **Calendar Fields:** Day of week, month, and season remain **strictly prohibited**.
- **1-Minute Interpolated Grid Models:** Deferred from the initial benchmark ladder.

### 3.2 Time-of-Day / Circadian Features: Prespecified Ablation Only
- **Status:** **EXCLUDED from the primary benchmark model; retained strictly as a prespecified secondary ablation.**
- **Registry Alignment & Provenance:** Official dataset documentation (`CGMacros_dateshifted365.zip`) confirms that recording and meal photo dates were shifted by a constant integer number of days, thereby preserving intra-day local clock time (HH:MM). This is supported by the 1,706 logged meal timing distributions in the Stage 1B canonical registry (breakfast median 8.4h, lunch 12.8h, dinner 19.1h).
- **Modeling Precaution:** Despite documented whole-day date shifting, time-of-day features are excluded from the primary model ladder to prevent any risk of circadian leakage, daylight savings discrepancies, or timezone confounding. Circadian harmonics ($[\sin(2\pi \cdot \text{TOD}/1440), \cos(2\pi \cdot \text{TOD}/1440)]$) will be evaluated strictly as an isolated ablation rung.

---

## 4. Stage 2 Model Progression Ladder

Modeling follows a disciplined, prespecified ladder where each rung introduces a single controlled architectural or feature component:

```
[Rung 0: Guarded Persistence]
       │
[Rung 1: Damped-Trend Baseline]
       │
[Rung 2: Guarded Ridge Regression (13 Lags)]
       │
[Rung 3: + Activity Summaries (HR, METs/10)]
       │
[Rung 4: + Meal Context & Macronutrients (with No-Macros Ablation)]
       │
[Rung 5: + Demographic & Baseline Covariates]
       │
[Rung 6: Small Gradient-Boosted Decision Tree (Fixed Hyperparameters)]
```

### 4.1 Rung 0 — Guarded Persistence Baseline
The reference benchmark for all subsequent rungs. Predicts no change from the latest available guard-banded glucose observation:
$$\hat{y}(t+h) = y(t-5) \quad \text{for } h \in \{30, 60\}$$

### 4.2 Rung 1 — Damped-Trend Baseline
Extrapolates recent rate of change with an estimated empirical damping factor:
$$\hat{y}(t+h) = y(t-5) + \gamma_h \cdot \left(\frac{y(t-5) - y(t-20)}{15}\right) \cdot h$$
where $\gamma_h \in [0, 1]$ is estimated strictly on training-fold participants via inner cross-validation.

### 4.3 Rung 2 — Guarded Ridge Regression (Autoregressive Lags)
Linear regularized regression on the 13 guard-banded glucose lags:
$$\mathbf{x}_{\text{autoreg}} = [y(t-5), y(t-10), \dots, y(t-65)]^T$$
- Regularization parameter $\alpha$ is selected via inner nested participant-grouped cross-validation.

### 4.4 Rung 3 — Physiological Activity Integration
Appends past-30-minute physical activity summaries:
$$\mathbf{x}_{\text{activity}} = [\text{mean\_HR}_{[t-30, t]}, \, \Delta\text{HR}_{[t-30, t]}, \, \text{mean\_METs/10}_{[t-30, t]}]^T$$
Missing activity values are imputed using participant training-fold medians with explicit missingness indicator flags.

### 4.5 Rung 4 — Meal Context & Macronutrients (Meal-Start Only)
Integrates nutritional information available at meal start:
- Time elapsed since last recorded meal start ($t - t_{\text{meal\_start}}$).
- Indicator variable for meal start occurring within $[t-60, t]$.
- Macronutrient contents: Total Carbs (g), Protein (g), Fat (g), Fiber (g).
- **Mandatory Ablation:** An explicit **no-macros ablation** (evaluating binary meal occurrence indicators without nutrient gram values) is evaluated alongside full macronutrients to isolate the specific value of self-reported dietary logs.

### 4.6 Rung 5 — Demographic & Baseline Covariates
Appends static participant covariates from `bio.csv`:
$$\mathbf{x}_{\text{static}} = [\text{Age}, \, \text{Gender}, \, \text{BMI}, \, \text{Baseline\_HbA1c}]^T$$
Evaluated as a separate rung to measure the incremental benefit of static biometric features over dynamic physiological signals.

### 4.7 Rung 6 — Small Gradient-Boosted Decision Tree (GBDT)
A compact non-linear model (LightGBM or XGBoost) trained with fixed, prespecified hyperparameters:
- `max_depth = 4`
- `n_estimators = 100`
- `learning_rate = 0.05`
- `min_child_samples = 50`
- `subsample = 0.8`
- `colsample_bytree = 0.8`
- **Audit Mandate:** Every model iteration and tuning experiment attempted must be logged in a machine-readable run log. Unconstrained hyperparameter searches and post-hoc tuning are strictly prohibited.

---

## 5. Cross-Validation Architecture & Evaluation Criteria

### 5.1 Participant-Disjoint Grouped Cross-Validation Scheme
- **Cross-Validation Scheme:** 5-fold `StratifiedGroupKFold`.
- **Grouping Unit:** Participant ID ($K = 45$). Zero intra-participant data leakage: all recording sessions from any individual participant reside strictly in either the training set or the test set within any fold.
- **Stratification Target:** Clinical baseline HbA1c diagnostic group (15 Normal, 16 Prediabetes, 14 Type 2 Diabetes). Each fold contains 3 Normal, 3–4 Prediabetes, and 2–3 Diabetes participants.
- **Fold Freezing:** The identical participant-to-fold assignments are frozen and reused across all model rungs and all phase sensitivity suites.
- **Hyperparameter Tuning:** Hyperparameters (e.g., Ridge $\alpha$, trend damping $\gamma_h$) are tuned strictly within training-fold participants using an inner 4-fold participant-grouped split.

### 5.2 Evaluation Metrics & Aggregation Hierarchy
Evaluation is structured hierarchically, prioritizing participant-level distribution over pooled aggregates:
1. **Per-Participant Error Metrics:**
   Compute RMSE and MAE separately for each participant $i$ in the test fold:
   $$\text{RMSE}_i(h) = \sqrt{\frac{1}{|\mathcal{Y}_{i}|} \sum_{t \in \mathcal{Y}_i} (y_{t+h} - \hat{y}_{i, t+h})^2}, \quad \text{MAE}_i(h) = \frac{1}{|\mathcal{Y}_{i}|} \sum_{t \in \mathcal{Y}_i} |y_{t+h} - \hat{y}_{i, t+h}|$$
2. **Per-Participant Skill Score Against Guarded Persistence:**
   $$\text{Skill}_i(h) = 1 - \frac{\text{RMSE}_i(\text{model}, h)}{\text{RMSE}_i(\text{persistence}, h)}$$
3. **Cohort Headline Reporting:**
   - **Median Participant Skill Score** and **Mean Participant Skill Score**.
   - **95% Confidence Intervals:** Derived from participant-level bootstrap ($B = 2,000$ iterations resampling participant error summaries).
   - **Fraction of Participants Improved:** Proportion of the 45 participants with $\text{Skill}_i(h) > 0$.
4. **Secondary Pooled Reporting:**
   Pooled cohort RMSE and MAE are reported strictly as secondary metrics to avoid overweighting participants with longer recording durations.

### 5.3 Predefined Criteria for Useful Forecasting Improvement
A candidate model rung is judged to deliver a scientifically useful improvement over persistence if and only if it satisfies the following prespecified criteria:
- **Horizon $h = 30\text{ min}$:**
  - Median participant skill score $\ge +5.0\%$ over guarded persistence.
  - Fraction of improved participants $\ge 60.0\%$ (at least 27 of 45 participants).
- **Horizon $h = 60\text{ min}$:**
  - Median participant skill score $\ge +10.0\%$ over guarded persistence.
  - Fraction of improved participants $\ge 65.0\%$ (at least 30 of 45 participants).

---

## 6. Personalization Experiment (Separate Prespecified Study)

Participant-specific adaptation is formulated as an independent downstream investigation, decoupled from general population evaluation:
- **Objective:** Quantify the incremental benefit of adapting a pretrained global model to an individual participant's early calibration data.
- **Protocol:**
  1. **Global Model:** Train the Rung 2 or Rung 6 architecture on $K - 1$ participants.
  2. **Target Adaptation Period:** Fit a lightweight adaptation layer (e.g., fine-tuning the Ridge bias/weights or calibration intercept) using the target participant's first **2, 4, or 6 recorded days**.
  3. **Purge Boundary:** Enforce a mandatory **$\ge 120\text{-minute}$ purge gap** immediately following the adaptation period. No samples from this gap may be used for adaptation or testing.
  4. **Evaluation:** Evaluate adapted predictions against frozen global-only predictions on **strictly identical test timestamps** during the remaining days.
- **Reporting Boundary:** Personalization results must **never** be combined or conflated with unseen-participant generalization claims. They will be reported in a dedicated standalone section.

---

## 7. Sample Size Hierarchy & Aggregate Cohort Provenance

### 7.1 Aggregate Cohort Characteristics (Privacy-Preserving)
In accordance with data governance standards, individual participant listings with unblinded clinical parameters are replaced with aggregate group statistics:

| Diagnostic Stratum | Participant Count ($N$) | Total Recorded Rows | Mean Rows/Participant (Range) | Baseline HbA1c Mean (Range) | Row Count Modulo 15 |
|:---|:---:|---:|:---:|:---:|:---:|
| **Normal** | 15 | 228,115 | 15,208 (13,725 – 17,340) | 5.2% (4.6% – 5.6%) | $\mathbf{10}$ (due solely to Participant 4) |
| **Prediabetes** | 16 | 240,930 | 15,058 (5,655 – 17,730) | 5.9% (5.7% – 6.4%) | $\mathbf{0}$ |
| **Type 2 Diabetes** | 14 | 218,535 | 15,610 (14,400 – 18,735) | 7.3% (6.5% – 8.5%) | $\mathbf{0}$ |
| **Cohort Total** | **45** | **687,580** | **15,280 (5,655 – 18,735)** | **6.1% (4.6% – 8.5%)** | $\mathbf{10}$ |

- **Modulo-15 Invariance:** 44 of 45 participant files have row counts exactly divisible by 15. Exactly one file (Participant 4, 14,275 rows) has $14,275 \pmod{15} = 10$.
- **Historical Scratch Counts Reconciliation:** The earlier unverified scratch figures of Prediabetes = 247,025 ($247,025 \pmod{15} = 5$) and Diabetes = 213,415 ($213,415 \pmod{15} = 10$) are mathematically impossible from whole files and are recorded as an **unresolved, non-reproducible artifact**.

### 7.2 Run-Bounded Origin Arithmetic (1,200 Contiguous Runs)
Candidate forecast origin slots across the 1,200 timestamp-contiguous runs (687,580 recorded rows) are strictly established:
- **Horizon $h = 30\text{ min}$:**
  - 1,079 runs have length $\le 30\text{ min}$ (accounting for 1,079 single-minute rows).
  - 121 runs have length $> 30\text{ min}$ (accounting for 686,501 rows).
  - Candidate slots: $\sum_r \max(0, \text{len}(r) - 30) = 686,501 - (121 \times 30) = \mathbf{682,871}$.
  - Subtracting 57,773 endpoint null pairs yields **625,098 valid evaluated pairs**.
- **Horizon $h = 60\text{ min}$:**
  - 1,103 runs have length $\le 60\text{ min}$ (accounting for 1,987 rows).
  - 97 runs have length $> 60\text{ min}$ (accounting for 685,593 rows).
  - Candidate slots: $\sum_r \max(0, \text{len}(r) - 60) = 685,593 - (97 \times 60) = \mathbf{679,773}$.
  - Subtracting 57,695 endpoint null pairs yields **622,078 valid evaluated pairs**.
- **Historical Run Count Reconciliation:** An earlier draft cited 94 runs $\le 30\text{ min}$ and 124 runs $\le 60\text{ min}$. These figures cannot be reproduced from canonical data and are formally marked **unresolved and non-reproducible**.
- **Removal of Case 2:** The exploratory 'Case 2' calculation (which cited 633,803 non-null Dexcom rows across 1,202 sensor runs) exceeded the canonical cohort total of 629,825 valid Dexcom rows and exhibited inconsistent trailing-slot arithmetic. Case 2 has been removed from the canonical feasibility report, and any retained historical references are labeled **noncanonical and unresolved**.

---

## 8. Secondary Tasks, Implementation Reporting & Claims Boundaries

### 8.1 Exploratory Nature of Threshold Excursions
Hyperglycemia (>180 mg/dL) and hypoglycemia (<70 mg/dL) excursion counts are evaluated strictly as **exploratory computational checks** derived from the released interpolated representation:
- Discrete points represent contiguous measurement epochs under the primary computational interval-bin convention (Convention B: 678 cohort episodes on 1-minute grid, 714 on candidate 5-minute lattice).
- These events are not physical clinical episodes and will not serve as standalone supervised classification targets in Stage 2.

### 8.2 Synthetic Benchmark Reporting & Neutral Terminology
- **Reporting Convention:** The synthetic validation suite is reported as **`2,500/2,500 implementation-consistency cases passed`**.
- Population confidence intervals (such as Wilson score intervals) are explicitly avoided for synthetic benchmarks because synthetic traces represent deterministic unit/integration test cases rather than random clinical samples.
- The former "compliance rate" terminology is replaced with neutral descriptive wording: **Percentage of evaluated contiguous runs satisfying 5-minute piecewise-linear lattice criteria**.
- Grouping units are consistently referred to as **participants** rather than "participant clusters".

### 8.3 Deferred Advanced Modeling
The following methodologies are deferred until the primary baseline ladder is completed and verified:
- Conformal prediction intervals and distribution-free uncertainty calibration.
- Complex recurrent or attention-based deep neural networks (e.g., LSTMs, Transformers).
- Neural ODEs and continuous-time state-space models.

### 8.4 Explicit Scientific & Clinical Claims Limitations
All dissemination, reports, and benchmark publications derived from this work are bound by the following explicit constraints:
1. **No Clinical Diagnosis or Treatment Claims:** The digital twin models developed under this protocol are mathematical forecasting benchmarks, not medical devices. They cannot be used to diagnose impaired glucose tolerance, calculate clinical insulin dosing, or guide real-time therapeutic decisions.
2. **No Causal Counterfactual Claims:** Observed statistical associations between logged nutritional macronutrients, physical activity, and postprandial glucose trajectories are purely correlational. They do not constitute counterfactual causal evidence for dietary or behavioral interventions.
3. **No Assertion of Population Transfer to Indian Populations:** The CGMacros v1.0.0 dataset was acquired from a US-based study cohort. Due to known differences in visceral adiposity, insulin resistance phenotypes, dietary composition, and metabolic kinetics, zero claims of transferability or validity to Indian or South Asian populations are asserted.
