# Experimental Methodology & Evaluation Design

## 1. Experimental Objectives

The goal of this project is to benchmark predictive continuous glucose monitoring models under realistic clinical and telemetry constraints:
1. **Global Population Forecasting (Stage 2)**: Train models on $K - 1$ participants and forecast future glucose trajectories at **+30 minutes** and **+60 minutes** on unseen participants.
2. **Individual Adaptation (Stage 3)**: Quantify the benefit of personalizing the global forecaster to an individual's early telemetry observations across varying calibration durations (2, 4, and 6 study days).

---

## 2. Invariant Origin Selection & Guard-Band Mechanics

In continuous glucose monitoring, raw recordings may have minor sensor jitter, communication lag, or device-internal smoothing. The Stage 2 protocol implements a **5-minute history guard band**:

- **Forecast Issuance Point**: Time $t$.
- **Permitted Glucose History**: Exactly 13 lags sampled at 5-minute intervals:
  $$\mathbf{x}_{\text{glucose}} = [y(t-5), y(t-10), y(t-15), \dots, y(t-65)]^T \in \mathbb{R}^{13}$$
- **Forecast Targets**:
  - Horizon +30m: $y(t + 30)$ (35 minutes from latest permitted glucose input)
  - Horizon +60m: $y(t + 60)$ (65 minutes from latest permitted glucose input)
- **Contiguous Run Requirement**: All 13 lags and the target outcome $y(t+h)$ must reside strictly within the same contiguous sensor run (where $\Delta t \equiv 60\,\text{s}$). No glucose interpolation across sensor dropouts is permitted.

---

## 3. Global Model Ladder (Rungs 0 through 6)

| Rung | Model | Mathematical Formulation | Features Used |
| :---: | :--- | :--- | :--- |
| **0** | **Guarded Persistence** | $\hat{y}(t+h) = y(t-5)$ | Latest available glucose lag |
| **1** | **Damped Trend** | $\hat{y}(t+h) = y(t-5) + \gamma_h \cdot \left(\frac{y(t-5) - y(t-20)}{15}\right) \cdot h$ | Rate of change over $[t-20, t-5]$, $\gamma \in [0, 1]$ tuned on train folds |
| **2** | **Guarded Ridge** | $\hat{y}(t+h) = \beta_0 + \mathbf{x}_{\text{lags}}^T \mathbf{w}$ | 13 guarded glucose history lags |
| **3** | **Activity-Augmented Ridge** | $\hat{y}(t+h) = \beta_0 + [\mathbf{x}_{\text{lags}}, \mathbf{x}_{\text{activity}}]^T \mathbf{w}$ | 13 lags + HR mean, HR delta, METs mean, missingness indicator (17 dims) |
| **4** | **Meal-Context Ridge** | $\hat{y}(t+h) = \beta_0 + [\mathbf{x}_{\text{lags}}, \mathbf{x}_{\text{meal}}]^T \mathbf{w}$ | 13 lags + time-since-meal, in-60m flag, macros (carbs, protein, fat, fiber) (20 dims) |
| **4b** | **Meal No-Macros (Ablation)** | $\hat{y}(t+h) = \beta_0 + [\mathbf{x}_{\text{lags}}, \mathbf{x}_{\text{timing}}]^T \mathbf{w}$ | 13 lags + time-since-meal, in-60m, no-recent-meal (16 dims) |
| **5** | **Baseline-Covariate Ridge** | $\hat{y}(t+h) = \beta_0 + [\mathbf{x}_{\text{lags}}, \mathbf{x}_{\text{timing}}, \mathbf{x}_{\text{covariates}}]^T \mathbf{w}$ | 13 lags + 3 meal timing + Age, Gender, BMI, HbA1c (20 dims) |
| **6** | **Fixed HistGBDT** | $\hat{y}(t+h) = \text{HistGradientBoosting}(\mathbf{x}_{\text{rung5}})$ | Exact Rung 5 feature matrix ($\mathbb{R}^{20}$), tree depth 4, 100 trees, no tuning |

---

## 4. Stage 3 Personalization Architecture

- **Pretrained Base**: Global Rung 5 Baseline-Covariate Ridge model trained on the outer cross-validation training fold ($N=36$).
- **Residual Correction Model**:
  $$r(t) = y(t+h) - \hat{y}_{\text{global}}(t+h) \quad \text{for } t \in \mathcal{D}_{\text{adapt}, p}$$
  A participant-specific Ridge regressor is fitted on 16 dynamic features (13 lags + 3 meal timing). Static covariates are omitted as they are zero-variance for an individual subject.
- **Matched Baseline Comparison**: The personalized model and an unchanged global model are evaluated on **identical evaluation timestamps** $\mathcal{D}_{\text{eval}, p}$ following a mandatory $\ge 120$-minute temporal purge buffer.

---

## 5. Statistical Rigor & Bootstrap Validation

- **Grouping Unit**: The participant ($K=45$).
- **Cross-Validation**: 10 repeated runs of 5-fold `StratifiedGroupKFold` across random seeds 42–51 ($10 \times 5 = 50$ distinct evaluation splits).
- **Metric Consolidation**: Predictions are averaged per participant across the 10 repetitions before cohort statistics are computed.
- **Bootstrap Confidence Intervals**: Non-parametric bootstrap resampling ($B = 2,000$ iterations) is conducted strictly over the **45 independent participants**. Origin pooling or repeat pooling is strictly prohibited.
