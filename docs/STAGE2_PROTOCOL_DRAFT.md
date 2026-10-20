# Stage 2 Predictive Modeling Protocol (Draft v1.0.0)

**Protocol Version:** 1.0.0-draft  
**Status:** FROZEN WORKING DRAFT READY FOR STAGE 2 TRANSITION  
**Dependencies:** `configs/stage1b.yaml`, `docs/reports/stage1b_r3_results.json`, `docs/reports/canonical_metrics.json`, `docs/reports/stage2_aggregate_feasibility.json`  

> [!NOTE]
> This protocol is a **strictly bounded working draft** ready to be frozen upon final review. It incorporates the primary 5-minute history guard-band forecasting architecture, specifies exact eligible origin counts on the primary $\phi=0$ grid, formalizes the fixed model ladder using dependencies already installed in the environment (`scikit-learn` `HistGradientBoostingRegressor`), mandates repeated 10-seed participant-disjoint cross-validation, decouples personalization into an independent study, removes individual participant row/provenance details in favor of privacy-preserving diagnostic group counts, and enforces rigorous scientific and clinical claims boundaries. No Stage 2 predictive model training or fitting will commence until this protocol is accepted.

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
- **Forecast Issuance Time:** Timestamp $t$ on the primary evaluation lattice ($m(t) \equiv 0 \pmod 5$).
- **Predictor Glucose History ($L = 60\text{ min}$ duration, 13 points):**
  $$[y(t-5), y(t-10), y(t-15), \dots, y(t-65)]$$
- **Target Outcomes:**
  $$y(t+30) \quad \text{and} \quad y(t+60)$$
- **Explicit Horizon Definitions:**
  - Horizons are strictly **30 minutes and 60 minutes from forecast issuance time $t$**.
  - Horizons are **35 minutes and 65 minutes from the latest permissible glucose input ($y_{t-5}$)**.
- **Rate-of-Change Feature:** First-order backward difference: $(y_{t-5} - y_{t-20}) / 15$.
- **Strict In-Run Non-Null Requirement:** All 13 glucose history values at $t-5$ through $t-65$ and the target at $t+h$ must be non-null and reside strictly within the same contiguous Dexcom run. **No glucose imputation is allowed in the primary experiment.**

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

### 2.5 Primary Grid Designation & Secondary Sensitivity Suites
1. **Primary Evaluation Grid ($\phi = 0$):**  
   The fixed five-minute phase $\phi = 0$, defined on a deterministic minute coordinate derived from canonical timestamps ($m(t) \equiv 0 \pmod 5$), is designated as the **primary evaluation grid**. No phase is claimed to represent verified hardware timing.
2. **Fixed Phase Offsets ($\phi \in \{1, 2, 3, 4\}$):**  
   Evaluated as prespecified sensitivity analyses across all other four candidate lattices using identical participant-level folds. Per-participant skill and phase-to-phase variability will be documented; phase-specific models are recognized as evaluating distinct lattice targets and do not share identical target timestamps.
3. **Unguarded History Ending at $t$ ($[y_t, y_{t-5}, \dots, y_{t-60}]$):**  
   Retained strictly as a secondary sensitivity comparison to quantify the empirical magnitude of interpolation look-ahead leakage against the primary guard-banded baseline.

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
- **Provenance & Unconfirmed Date-Shifting:** While the dataset archive filename references date shifting (`CGMacros_dateshifted365.zip`) and meal timestamps visually follow diurnal human living patterns, the precise mathematical date-shifting mechanism (e.g., whether it was a strict integer-day shift preserving local clock time HH:MM, or involved unrecorded timezone offsets or timestamp transformations) remains **unconfirmed by dataset-author primary documentation**.
- **Modeling Precaution:** Because primary-source documentation is inconclusive, time-of-day features are excluded from the primary model ladder to prevent any risk of circadian leakage, daylight savings discrepancies, or timezone confounding. Circadian harmonics ($[\sin(2\pi \cdot \text{TOD}/1440), \cos(2\pi \cdot \text{TOD}/1440)]$) will be evaluated strictly as an isolated ablation rung.

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
[Rung 6: HistGradientBoostingRegressor (scikit-learn, Fixed Settings)]
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

### 4.7 Rung 6 — Native HistGradientBoostingRegressor (Fixed Hyperparameters)
A compact non-linear model using the gradient-boosting implementation already available in project dependencies: `sklearn.ensemble.HistGradientBoostingRegressor` (from `scikit-learn` 1.8.0).
- **Exact Fixed Settings (No External Dependencies):**
  - `loss = 'squared_error'`
  - `learning_rate = 0.05`
  - `max_iter = 100` (number of boosting iterations)
  - `max_depth = 4`
  - `min_samples_leaf = 50`
  - `l2_regularization = 0.0`
  - `random_state = 42`
- **Library Restriction:** No alternative boosting libraries (LightGBM, XGBoost, CatBoost) will be installed or compared.
- **Audit Mandate:** Every model iteration and tuning experiment attempted must be logged in a machine-readable run log. Unconstrained hyperparameter searches and post-hoc tuning are strictly prohibited.

---

## 5. Cross-Validation Architecture & Evaluation Criteria

### 5.1 Repeated Participant-Disjoint Stratified Cross-Validation
- **Cross-Validation Scheme:** Exactly **10 repeated runs** of 5-fold `StratifiedGroupKFold` ($10 \times 5 = 50$ evaluation splits total).
- **Grouping Unit:** Participant ID ($K = 45$). Zero intra-participant data leakage: all recording sessions from any individual participant reside strictly in either the training set or the test set within any fold.
- **Stratification Target:** Clinical baseline HbA1c diagnostic group (15 Normal, 16 Prediabetes, 14 Type 2 Diabetes). Each fold contains 3 Normal, 3–4 Prediabetes, and 2–3 Diabetes participants.
- **Prespecified Seeds:** Exactly 10 integer seeds prespecified as `[42, 43, 44, 45, 46, 47, 48, 49, 50, 51]`.
- **Fold Freezing:** The identical 10-repeat participant-to-fold assignments are frozen and reused across all model rungs and all phase sensitivity suites.
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
A candidate model rung is judged to deliver a scientifically useful improvement over persistence if and only if it satisfies all of the following prespecified criteria across the 10 repeated cross-validation runs:
- **Horizon $h = 30\text{ min}$:**
  1. Median participant skill score $\ge +5.0\%$ over guarded persistence.
  2. Fraction of improved participants $\ge 60.0\%$ (at least 27 of 45 participants).
  3. Lower bound of the 95% participant-bootstrap confidence interval for mean participant skill is strictly positive:
     $$\text{CI}_{95\%}^{\text{lower}}(\overline{\text{Skill}}(h=30)) > 0.0\%$$
- **Horizon $h = 60\text{ min}$:**
  1. Median participant skill score $\ge +10.0\%$ over guarded persistence.
  2. Fraction of improved participants $\ge 65.0\%$ (at least 30 of 45 participants).
  3. Lower bound of the 95% participant-bootstrap confidence interval for mean participant skill is strictly positive:
     $$\text{CI}_{95\%}^{\text{lower}}(\overline{\text{Skill}}(h=60)) > 0.0\%$$

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

## 7. Primary Forecast Origins & Cohort Provenance

### 7.1 Diagnostic Group Participant Units (Privacy-Preserving)
In accordance with strict privacy-preserving data governance, all per-participant row counts, individual parameter ranges, and modulo provenance details are removed. Validation partitioning relies solely on the 45 independent participant units stratified by baseline clinical diagnostic group:

| Diagnostic Stratum | Participant Count ($N$) | Validation Role |
|:---|:---:|:---|
| **Normal** | 15 | Baseline normoglycemic control group (3 participants per fold) |
| **Prediabetes** | 16 | Impaired fasting glucose / glucose intolerance group (3–4 participants per fold) |
| **Type 2 Diabetes** | 14 | Overt diabetic metabolic phenotype (2–3 participants per fold) |
| **Cohort Total** | **45** | **Independent grouping units across 10 repeated 5-fold cross-validation runs** |

### 7.2 Primary Guard-Band Eligible Origin Counts ($\phi = 0$)
The primary evaluation grid is fixed at $\phi = 0$ on the deterministic minute coordinate ($m(t) \equiv 0 \pmod 5$). Eligible origins require all 13 glucose history lags at $t-5$ through $t-65$ and the target at $t+h$ to be non-null and within the same contiguous Dexcom run:

- **Horizon $h = 30\text{ min}$ (Issuance $t$, Target $t+30$):**
  - **Cohort Total:** **123,599 eligible origins**
  - **Normal:** 41,787
  - **Prediabetes:** 42,341
  - **Type 2 Diabetes:** 39,471
- **Horizon $h = 60\text{ min}$ (Issuance $t$, Target $t+60$):**
  - **Cohort Total:** **123,164 eligible origins**
  - **Normal:** 41,648
  - **Prediabetes:** 42,156
  - **Type 2 Diabetes:** 39,360

#### Fixed Phase Sensitivity Suites ($\phi \in \{0, 1, 2, 3, 4\}$)
Phases 1–4 are prespecified sensitivity analyses only; no phase is claimed to represent verified hardware timing. Eligible origin counts across all five candidate lattices exhibit balance:
- **Horizon $h = 30\text{ min}$:** $\phi=0$ (123,599), $\phi=1$ (123,606), $\phi=2$ (123,576), $\phi=3$ (123,568), $\phi=4$ (123,571).
- **Horizon $h = 60\text{ min}$:** $\phi=0$ (123,164), $\phi=1$ (123,176), $\phi=2$ (123,149), $\phi=3$ (123,140), $\phi=4$ (123,143).

### 7.3 Separation from Historical Descriptive Counts
The primary guard-band origin counts (123,599 / 123,164) are maintained strictly separate from historical baseline figures:
- **Descriptive Baseline Offset Pairs ($L = 0$, no input history requirement):** 625,098 valid pairs at +30 min; 622,078 valid pairs at +60 min across 1,200 timestamp runs.
- **Secondary Unguarded History Candidates ($L = 60$, ending at $t$):** 123,709 candidate origins at +30 min; 123,266 candidate origins at +60 min.
- **Historical Run Count & Case 2 Reconciliation:** Historical figures of 94 runs $\le 30$ min, 124 runs $\le 60$ min, and the 633,803-row Case 2 calculation are recorded as **noncanonical, unresolved, and removed** from all active Stage 2 modeling tables.

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
