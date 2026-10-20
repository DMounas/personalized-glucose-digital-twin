# Stage 3 Protocol Addendum: Participant-Specific Residual-Correction Personalization

**Protocol Version**: 1.0.0  
**Status**: FROZEN PRIOR TO MODEL FITTING  
**Date**: October 2026  
**Scope**: Stage 3 Downstream Personalization Study (CGMacros Cohort, $K = 45$)  
**Parent Protocol**: Stage 2 Protocol v1.0.0 (`docs/STAGE2_PROTOCOL_DRAFT.md`)

---

## 1. Objective & Scope

This protocol addendum governs the Stage 3 Personalization Experiment for the Glucose Digital Twin project.
The objective is to rigorously determine whether adapting a population-level global model to an individual participant's early study data yields improved glucose forecast accuracy on their later, unseen study data.

Under Section 6 of the frozen Stage 2 Protocol, personalization is evaluated as an independent downstream investigation.
Personalized results must never be conflated with general population zero-shot generalization.

---

## 2. Chronological Ordering & Study-Day Definition

In accordance with the project's data provenance specifications (`docs/DATA_PROVENANCE.md`), all 45 participant time series CSVs in `CGMacros` contain strictly monotonically increasing 1-minute records. De-identification date shifting preserves intra-participant intervals, circadian cadence, and relative chronological ordering.

- **Baseline Anchor ($t_0$):** The first recorded timestamp in the participant's data file.
- **Elapsed Time Coordinate ($m(t)$):** Deterministic elapsed minutes from $t_0$:
  $$m(t) = \text{round}\left(\frac{t - t_0}{60\,\text{s}}\right) \in \mathbb{Z}_{\ge 0}$$
- **Study Day Definition:** One study day is defined as exactly 1,440 elapsed minutes (24 continuous hours):
  $$\text{Study Day}(t) = \left\lfloor \frac{m(t)}{1440} \right\rfloor + 1$$
- **Prespecified Adaptation Windows ($W$):**
  1. **Window 1 (2 Study Days):** $T_{\text{cutoff}} = 2 \times 1,440 = 2,880\,\text{minutes}$.
  2. **Window 2 (4 Study Days):** $T_{\text{cutoff}} = 4 \times 1,440 = 5,760\,\text{minutes}$.
  3. **Window 3 (6 Study Days):** $T_{\text{cutoff}} = 6 \times 1,440 = 8,640\,\text{minutes}$.

---

## 3. Sample Partitioning, Label Boundaries & Purge Gap

To prevent temporal leakage and label bleed, the adaptation and evaluation subsets for held-out participant $p$ are partitioned as follows:

### 3.1 Adaptation Origin Set ($\mathcal{D}_{\text{adapt}, p}$)
An eligible Stage 2 origin at issuance time $t$ belongs to $\mathcal{D}_{\text{adapt}, p}$ if and only if:
$$m(t) + h \le T_{\text{cutoff}}$$
where $h \in \{30, 60\}$ minutes is the forecast horizon.
- **Label Cutoff Rule:** Requiring $m(t) + h \le T_{\text{cutoff}}$ guarantees that the observed target label $y(t+h)$ occurs strictly within the adaptation period and never crosses into the purge or evaluation window.

### 3.2 Purge Interval
A mandatory purge buffer of at least 120 minutes is enforced immediately following the adaptation window cutoff:
$$\text{Purge Window} = [T_{\text{cutoff}}, \, T_{\text{cutoff}} + 120\,\text{min})$$
No forecast origins within this interval may be used for either adaptation or evaluation.

### 3.3 Evaluation Origin Set ($\mathcal{D}_{\text{eval}, p}$)
An eligible Stage 2 origin at issuance time $t$ belongs to $\mathcal{D}_{\text{eval}, p}$ if and only if:
$$m(t) \ge T_{\text{cutoff}} + 120\,\text{minutes}$$
- **Feature Separation Guard:** For any $t \in \mathcal{D}_{\text{eval}, p}$, the earliest input history lag $t - 65$ satisfies:
  $$m(t) - 65 \ge T_{\text{cutoff}} + 120 - 65 = T_{\text{cutoff}} + 55 > T_{\text{cutoff}}$$
  This guarantees an absolute minimum temporal gap of 55 minutes between the latest adaptation target label ($\le T_{\text{cutoff}}$) and the earliest evaluation feature observation, eliminating feature/target autocorrelation overlap.

---

## 4. Modeling Architecture

### 4.1 Global Population Model (Rung 5 Ridge)
- **Architecture:** Linear Ridge regression with 20 input features:
  - 13 guarded autoregressive lags: $[y(t-5), y(t-10), \dots, y(t-65)]$
  - 3 meal-timing features: $[t - t_{\text{meal\_start}}, I_{\text{meal\_in\_60m}}, I_{\text{no\_recent\_meal}}]$
  - 4 static baseline covariates: $[\text{Age}, \text{Gender}, \text{BMI}, \text{Baseline\_HbA1c}]$
- **Training:** Fitted strictly on outer training participants ($N=36$) with training-fold-only `MealPreprocessor`, `CovariatePreprocessor`, and `StandardScaler`.
- **Regularization ($\alpha_{\text{global}}$):** Selected via inner 4-fold participant-grouped cross-validation on training participants.

### 4.2 Participant-Specific Residual-Correction Model
- **Target:** Residual error of the global model on the participant's adaptation observations:
  $$r(t) = y(t+h) - \hat{y}_{\text{global}}(t+h) \quad \text{for } t \in \mathcal{D}_{\text{adapt}, p}$$
- **Feature Vector ($\mathbf{z}(t) \in \mathbb{R}^{16}$):**
  Uses the 13 guarded glucose history lags and 3 meal-timing features. Static baseline covariates are excluded as they are invariant for a single participant.
- **Preprocessing:** Scaled using the training fold's fitted `StandardScaler` parameters for the corresponding 16 features, preserving global regularization scale.
- **Regularization:** Reuses the training fold's optimal $\alpha_{\text{global}}$. No post-hoc tuning or hyperparameter searching against held-out or future data is permitted.
- **Estimator:**
  $$\hat{\mathbf{w}}_{\text{corr}}, \hat{\beta}_0 = \arg\min_{\mathbf{w}, \beta} \sum_{t \in \mathcal{D}_{\text{adapt}, p}} \left(r(t) - (\beta + \mathbf{z}_{\text{scaled}}(t)^T \mathbf{w})\right)^2 + \alpha_{\text{global}} \|\mathbf{w}\|_2^2$$
- **Personalized Inference:**
  $$\hat{y}_{\text{pers}}(t+h) = \hat{y}_{\text{global}}(t+h) + \left(\hat{\beta}_0 + \mathbf{z}_{\text{scaled}}(t)^T \hat{\mathbf{w}}_{\text{corr}}\right) \quad \text{for } t \in \mathcal{D}_{\text{eval}, p}$$

---

## 5. Matched Baseline & Evaluation Protocol

### 5.1 Matched Global-Only Comparator
Because the evaluation set $\mathcal{D}_{\text{eval}, p}$ changes as the adaptation window expands from 2 to 6 days, comparisons must not be made against the full-period Stage 2 headline metrics.
For every window $W$ and horizon $h$, a matched global-only baseline is computed on **identical evaluation timestamps** $\mathcal{D}_{\text{eval}, p}$:
$$\text{RMSE}_{\text{global}, p} = \sqrt{\frac{1}{|\mathcal{D}_{\text{eval}, p}|} \sum_{t \in \mathcal{D}_{\text{eval}, p}} \left(y(t+h) - \hat{y}_{\text{global}}(t+h)\right)^2}$$
$$\text{RMSE}_{\text{pers}, p} = \sqrt{\frac{1}{|\mathcal{D}_{\text{eval}, p}|} \sum_{t \in \mathcal{D}_{\text{eval}, p}} \left(y(t+h) - \hat{y}_{\text{pers}}(t+h)\right)^2}$$

### 5.2 Performance Metrics
1. **Participant-Level Metrics:** Computed per participant and averaged across the 10 cross-validation repetitions:
   - Mean and median RMSE and MAE for global-only and personalized models.
   - Paired difference: $\Delta \text{RMSE}_p = \text{RMSE}_{\text{pers}, p} - \text{RMSE}_{\text{global}, p}$.
   - Percentage reduction: $\text{PctRed}_p = \frac{\text{RMSE}_{\text{global}, p} - \text{RMSE}_{\text{pers}, p}}{\text{RMSE}_{\text{global}, p}} \times 100\%$.
2. **Cohort Summary & Bootstrap:**
   - Resampling is strictly conducted over the **45 independent participants** ($B = 2,000$ iterations) to generate 95% non-parametric bootstrap confidence intervals.
   - Count and fraction of participants improved ($\Delta \text{RMSE}_p < 0$).
3. **Subgroup Analysis:** Secondary breakdown by clinical diagnostic group (Normal, Prediabetes, Diabetes).
4. **Data Privacy:** Public reporting conveys cohort-level and subgroup summaries only. No raw participant records or private identifiers are exposed.
