# Comprehensive Benchmark & Personalization Results

All metrics reported herein are derived directly from the canonical machine-readable experimental artifacts:
- Stage 2 Benchmarks: [`docs/reports/stage2_baseline_metrics.json`](reports/stage2_baseline_metrics.json)
- Stage 3 Personalization: [`docs/reports/stage3_personalization_metrics.json`](reports/stage3_personalization_metrics.json)

---

## 1. Stage 2 Global Forecasting Benchmark

Evaluated across **45 independent participants** using 10 repeated runs of 5-fold participant-disjoint stratified cross-validation ($N_{\text{origins}} = 123,599$ at $+30\text{m}$; $123,164$ at $+60\text{m}$).

### Horizon +30-Minute Results

| Model Rung | Architecture / Features | Mean RMSE (mg/dL) | Median RMSE (mg/dL) | 95% Bootstrap CI (Mean RMSE) | Mean Skill vs. Persistence | Participants Improved |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Rung 0** | Guarded Persistence ($y(t-5)$) | 21.554 | 20.847 | [20.022, 23.209] | 0.00% | 0 / 45 (0.0%) |
| **Rung 1** | Damped Trend Extrapolation | 21.394 | 20.719 | [19.954, 22.946] | +0.32% | 28 / 45 (62.2%) |
| **Rung 2** | Guarded Ridge (13 Lags) | 19.866 | 18.558 | [18.567, 21.327] | +7.17% | 41 / 45 (91.1%) |
| **Rung 3** | + Activity (HR & METs) | 19.849 | 18.661 | [18.535, 21.325] | +7.30% | 40 / 45 (88.9%) |
| **Rung 4** | + Meals (Full Macronutrients) | 19.191 | 17.905 | [17.937, 20.596] | +10.26% | 41 / 45 (91.1%) |
| **Rung 4b** | + Meals (Timing Only Ablation) | 19.181 | 17.926 | [17.921, 20.590] | +10.32% | 41 / 45 (91.1%) |
| **Rung 5** | **+ Baseline Covariates (Best Linear)** | **18.853** | **18.246** | **[17.620, 20.175]** | **+11.82%** | **42 / 45 (93.3%)** |
| **Rung 6** | Fixed HistGradientBoosting | 19.146 | 18.209 | [17.732, 20.674] | +11.06% | 40 / 45 (88.9%) |

### Horizon +60-Minute Results

| Model Rung | Architecture / Features | Mean RMSE (mg/dL) | Median RMSE (mg/dL) | 95% Bootstrap CI (Mean RMSE) | Mean Skill vs. Persistence | Participants Improved |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Rung 0** | Guarded Persistence ($y(t-5)$) | 29.321 | 27.134 | [26.598, 32.230] | 0.00% | 0 / 45 (0.0%) |
| **Rung 1** | Damped Trend Extrapolation | 29.332 | 27.238 | [26.636, 32.216] | -0.15% | 22 / 45 (48.9%) |
| **Rung 2** | Guarded Ridge (13 Lags) | 26.966 | 24.514 | [24.648, 29.604] | +7.02% | 39 / 45 (86.7%) |
| **Rung 3** | + Activity (HR & METs) | 26.974 | 24.516 | [24.681, 29.643] | +6.94% | 38 / 45 (84.4%) |
| **Rung 4** | + Meals (Full Macronutrients) | 27.032 | 24.369 | [24.607, 29.853] | +7.02% | 36 / 45 (80.0%) |
| **Rung 4b** | + Meals (Timing Only Ablation) | 26.257 | 24.205 | [24.097, 28.752] | +9.06% | 39 / 45 (86.7%) |
| **Rung 5** | **+ Baseline Covariates (Best Linear)** | **25.452** | **22.830** | **[23.339, 27.740]** | **+11.85%** | **43 / 45 (95.6%)** |
| **Rung 6** | Fixed HistGradientBoosting | 25.642 | 23.507 | [23.154, 28.235] | +12.30% | 41 / 45 (91.1%) |

---

## 2. Stage 3 Personalization Results across Adaptation Windows

Evaluated against a matched global Rung 5 Ridge baseline evaluated on strictly identical post-purge evaluation timestamps.

### Summary Across Windows ($W \in \{2, 4, 6\}$ Study Days)

| Horizon | Window | Adapt Origins | Eval Origins | Matched Global RMSE | Personalized RMSE | Paired $\Delta\text{RMSE}$ (mg/dL) | 95% Bootstrap CI ($\Delta\text{RMSE}$) | Pct Reduction | Improved Subjects |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **+30m** | 2 Days | 23,314 | 99,100 | 18.549 | 18.838 | +0.289 | [-0.666, +1.687] | -1.74% | 28 / 45 (62.2%) |
| **+30m** | 4 Days | 48,101 | 74,251 | 18.166 | 17.738 | -0.428 | [-1.346, +1.009] | +2.12% | 38 / 45 (84.4%) |
| **+30m** | 6 Days | 72,448 | 49,933 | 17.921 | 17.096 | -0.825 | [-1.724, +0.587] | +4.67% | **41 / 45 (91.1%)** |
| **+60m** | 2 Days | 22,999 | 98,734 | 25.192 | 25.167 | -0.025 | [-0.917, +0.972] | +0.22% | 31 / 45 (68.9%) |
| **+60m** | 4 Days | 47,738 | 73,921 | 24.529 | 23.383 | **-1.146** | **[-1.804, -0.405]** | **+4.76%** | **35 / 45 (77.8%)** |
| **+60m** | 6 Days | 72,073 | 49,621 | 24.073 | 22.262 | **-1.811** | **[-2.431, -1.087]** | **+8.00%** | **40 / 45 (88.9%)** |

*Note on Statistical Significance*: Negative $\Delta\text{RMSE}$ denotes performance improvement from personalization. At the $+60$-minute horizon, the paired bootstrap confidence intervals for both the 4-day and 6-day adaptation windows strictly exclude zero, confirming a statistically robust, reproducible benefit. At $+30$ minutes, though 91.1% of subjects improve at 6 days, the cohort confidence interval includes zero due to high baseline predictability.

---

## 3. Secondary Subgroup Breakdown (Clinical Phenotype)

| Subgroup | Horizon | Window | Matched Global RMSE | Personalized RMSE | $\Delta\text{RMSE}$ | Mean Pct Reduction | Improved Subjects |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Normal** ($N=15$) | +30m | 6 Days | 16.113 | 16.071 | -0.042 mg/dL | +1.34% | 14 / 15 (93.3%) |
| **Normal** ($N=15$) | +60m | 6 Days | 19.546 | 17.980 | -1.566 mg/dL | +8.58% | 14 / 15 (93.3%) |
| **Prediabetes** ($N=16$) | +30m | 6 Days | 17.203 | 16.164 | -1.039 mg/dL | +5.87% | 15 / 16 (93.8%) |
| **Prediabetes** ($N=16$) | +60m | 6 Days | 22.622 | 21.043 | -1.579 mg/dL | +7.77% | 14 / 16 (87.5%) |
| **Type 2 Diabetes** ($N=14$) | +30m | 6 Days | 20.678 | 19.258 | -1.420 mg/dL | +6.86% | 12 / 14 (85.7%) |
| **Type 2 Diabetes** ($N=14$) | +60m | 6 Days | 30.580 | 28.243 | -2.338 mg/dL | +7.63% | 12 / 14 (85.7%) |
