# System Architecture & Technical Design

## 1. Architectural Overview

The **Personalized Glucose Digital Twin** is designed as a modular, highly decoupled research engineering framework for continuous physiological time-series forecasting and downstream individual calibration.

```mermaid
flowchart TD
    subgraph S1["1. Raw Ingestion & Integrity"]
        A["CGMacros Sensor Feeds<br/>(1-min Dexcom GL, HR, METs, Meals)"] --> B["Contiguous Run Segmentation<br/>(delta = 60s verification)"]
        B --> C["Deterministic Lattice Grid<br/>m(t) = round((t-t0)/60s) mod 5 == 0"]
    end

    subgraph S2["2. Guarded Feature Construction"]
        C --> D["13 Guarded Lags: [y(t-5) ... y(t-65)]<br/>(5-min guard band eliminates boundary leakage)"]
        C --> E["Meal Context: [time_since, in_60m, no_recent]<br/>(Available strictly by issuance t)"]
        C --> F["Static Baseline Covariates:<br/>[Age, Gender, BMI, HbA1c]"]
        D & E & F --> G["Feature Assembly Matrix (R^20)"]
    end

    subgraph S3["3. Global Forecasting Ladder"]
        G --> H["Repeated 5-Fold Grouped CV (K=45)<br/>10 repeats across seeds 42-51"]
        H --> I["Inner CV Alpha Tuning<br/>(Outer train folds only)"]
        I --> J["Rung 5 Ridge Regressor<br/>(+11.8% skill vs Persistence)"]
        I --> K["Rung 6 Fixed HistGBDT<br/>(Fixed tree depth=4, no post-hoc tuning)"]
    end

    subgraph S4["4. Stage 3 Personalization"]
        J --> L["Held-Out Test Participant Split"]
        L --> M["Adaptation Window: 2d, 4d, or 6d<br/>(Label cutoff: m(t)+h <= T_cutoff)"]
        M --> N[">= 120-min Temporal Purge Gap"]
        N --> O["Residual Ridge Correction Model<br/>r(t) = y(t+h) - y_hat_global(t+h)"]
        O --> P["Personalized Inference on Unseen Days<br/>y_hat_pers = y_hat_global + r_hat"]
    end

    subgraph S5["5. Evaluation & Aggregation"]
        P --> Q["Participant-Level Aggregation across 10 Repeats"]
        Q --> R["Cohort Bootstrap (B=2,000 independent subjects)"]
        R --> S["Machine-Readable Reports & Visualizations"]
    end
```

---

## 2. Module Responsibilities

| Python Module | Package Path | Primary Responsibility |
| :--- | :--- | :--- |
| [`timeaxis.py`](../src/dtwin/timeaxis.py) | `dtwin.timeaxis` | Contiguous run segmentation, integer delta verification, deterministic minute elapsed time $m(t)$. |
| [`dataset.py`](../src/dtwin/modeling/dataset.py) | `dtwin.modeling.dataset` | Guard-band origin extraction, lag assembly, meal and activity alignment under $\phi = 0$. |
| [`baselines.py`](../src/dtwin/modeling/baselines.py) | `dtwin.modeling.baselines` | Rung 0 (Guarded Persistence) and Rung 1 (Damped Trend Extrapolation with $\gamma$ tuning). |
| [`ridge.py`](../src/dtwin/modeling/ridge.py) | `dtwin.modeling.ridge` | Rung 2 Guarded Ridge regression on 13 lags with inner participant-grouped CV. |
| [`activity.py`](../src/dtwin/modeling/activity.py) | `dtwin.modeling.activity` | Rung 3 Heart rate and METs rolling summary extraction and training-fold imputation. |
| [`meal.py`](../src/dtwin/modeling/meal.py) | `dtwin.modeling.meal` | Rung 4 Macronutrient and timing feature extraction, `MealPreprocessor` fit/transform. |
| [`covariates.py`](../src/dtwin/modeling/covariates.py) | `dtwin.modeling.covariates` | Rung 5 Static biological covariate loading, median/mode imputation, and feature matrix assembly. |
| [`boosting.py`](../src/dtwin/modeling/boosting.py) | `dtwin.modeling.boosting` | Rung 6 Native `HistGradientBoostingRegressor` with fixed prespecified hyperparameters. |
| [`personalization.py`](../src/dtwin/modeling/personalization.py) | `dtwin.modeling.personalization` | Stage 3 adaptation partitioning, label cutoff validation, residual-correction Ridge model. |
| [`personalization_runner.py`](../src/dtwin/modeling/personalization_runner.py) | `dtwin.modeling.personalization_runner` | End-to-end execution of Stage 3 across 2, 4, 6 study days and both horizons. |
| [`metrics.py`](../src/dtwin/modeling/metrics.py) | `dtwin.modeling.metrics` | Participant-level aggregation, skill scoring, paired differences, and 45-participant bootstrap CIs. |
| [`cv.py`](../src/dtwin/modeling/cv.py) | `dtwin.modeling.cv` | 10-repeat 5-fold stratified participant-disjoint partition generator (`StratifiedGroupKFold`). |

---

## 3. Data Leakage Countermeasures

1. **Intra-Participant Partitioning Isolation**: All cross-validation partitioning groups strictly by `participant_id`. Zero recordings from an evaluation participant are present in the training set during global model fitting.
2. **Deterministic Grid Isolation ($\phi = 0$)**: The forecasting lattice is fixed at a single deterministic grid phase $m(t) \pmod 5 = 0$, derived exclusively from the recording anchor $t_0$.
3. **Temporal Guard Band**: All glucose feature lags use $[t-65, \dots, t-5]$. The latest glucose input is strictly 5 minutes prior to forecast issuance $t$, eliminating interpolation contamination from sensor smoothing.
4. **Personalization Purge & Label Boundary**:
   - Adaptation samples must satisfy $m(t) + h \le T_{\text{cutoff}}$ (observed target label cannot cross the cutoff).
   - Minimum 120-minute purge buffer enforced immediately after $T_{\text{cutoff}}$.
   - Earliest evaluation history observation occurs at least 55 minutes after the latest adaptation target observation.
