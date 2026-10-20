<div align="center">

![Glucose Digital Twin](assets/hero_banner.svg)

# Personalized Glucose Digital Twin for Type 2 Diabetes

[![Tests: 118 passed](https://img.shields.io/badge/tests-118%20passed-brightgreen.svg)](#-reproducibility--experiment-execution)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Dataset: PhysioNet CGMacros](https://img.shields.io/badge/PhysioNet-CGMacros%201.0.0-cyan.svg)](https://physionet.org/content/cgmacros/1.0.0/)

**A leak-free, physiological continuous glucose forecasting framework and participant-specific calibration engine.**

[Overview](#-overview) • [Key Results](#-key-results) • [Architecture](#-architecture) • [Temporal Guard Band](#-temporal-guard-band-architecture) • [Benchmarks](#-global-forecasting-benchmarks) • [Personalization](#-stage-3-personalization-dynamics) • [Quick Start](#-quick-start) • [Reproducibility](#-reproducibility--experiment-execution) • [Limitations](#-limitations--responsible-use) • [Citation](#-citation--references)

</div>

---

## 📌 Overview

Continuous Glucose Monitoring (CGM) offers transformative potential for managing Type 2 Diabetes, but machine learning models in ambulatory glucose forecasting routinely fail due to **telemetry interpolation leakage**, **intra-participant sample bleed**, and **high inter-individual metabolic heterogeneity**.

This repository provides an open-source research-engineering digital twin framework evaluated on the open-access **CGMacros cohort** (45 participants spanning normoglycemic controls, prediabetes, and overt type 2 diabetes). The system incorporates:

1. **A 5-Minute History Guard Band**: Enforces a strict separation between permitted history and forecast issuance, eliminating boundary interpolation artifacts without assuming unverified hardware clock alignment.
2. **An 8-Rung Population Forecasting Ladder**: Progressively benchmarks persistence, trend extrapolation, autoregressive lags, physical activity, meal timing/macronutrients, static clinical covariates, and nonlinear gradient boosting under **10 repeated 5-fold participant-disjoint cross-validation** ($50$ independent evaluation folds, $K=45$).
3. **Stage 3 Residual Personalization Engine**: Adapts global population forecasters to individual physiology using a regularized Ridge residual-correction model across 2, 4, and 6 study days with mandatory **$\ge 120$-minute temporal purge buffers**.

> **Research Disclaimer**: This software is a machine learning research and benchmarking framework. It is not an FDA-cleared medical device, does not provide clinical diagnosis or insulin dosing guidance, and is not a substitute for professional medical care.

---

## 📊 Key Results

<div align="center">

| Metric | Horizon +30 min | Horizon +60 min | Validation Standard |
| :--- | :---: | :---: | :--- |
| **Best Global RMSE** | **18.85 mg/dL** | **25.45 mg/dL** | Population Rung 5 Ridge (45 unseen participants) |
| **Global Forecasting Skill** | **+11.82%** vs Persistence | **+11.85%** vs Persistence | Participant-level skill score $1 - \frac{\text{RMSE}}{\text{RMSE}_{\text{pers}}}$ |
| **6-Day Personalization $\Delta\text{RMSE}$** | **-0.83 mg/dL** [95% CI: -1.72, +0.59] (n.s.) | **-1.81 mg/dL** [95% CI: -2.43, -1.09] | Paired bootstrap difference vs matched global baseline |
| **Personalization Improvement Rate** | **41 / 45 Subjects (91.1%)** | **40 / 45 Subjects (88.9%)** | Fraction of participants experiencing lower error |
| **Data Leakage Countermeasures** | 5-min Guard Band | 120-min Temporal Purge | Zero intra-subject cross-validation contamination |

</div>

---

## 🏗️ Architecture

![System Architecture](assets/system_architecture.svg)

The framework is decoupled into five modular layers:
1. **Raw Ingestion & Verification** ([`timeaxis.py`](src/dtwin/timeaxis.py)): Enforces $\Delta t = 60\,\text{s}$ contiguous run segmentation, integer timestamps, and primary lattice grid alignment ($\phi = 0$).
2. **Guarded Feature Extraction** ([`dataset.py`](src/dtwin/modeling/dataset.py)): Extracts 13 autoregressive lags, 3 meal-timing features, and 4 static baseline clinical covariates into an aligned $\mathbb{R}^{20}$ matrix.
3. **Global Model Ladder** ([`runner.py`](src/dtwin/modeling/runner.py)): Evaluates 8 model rungs via repeated `StratifiedGroupKFold` cross-validation with inner-fold hyperparameter tuning on training participants only.
4. **Stage 3 Personalization Engine** ([`personalization.py`](src/dtwin/modeling/personalization.py)): Fits participant-specific Ridge residual-correction models on early telemetry with label cutoff guards and temporal purge boundaries.
5. **Statistical Verification** ([`metrics.py`](src/dtwin/modeling/metrics.py)): Aggregates repetitions at the participant level and computes non-parametric bootstrap confidence intervals across the 45 independent subjects ($B = 2,000$).

---

## ⏱️ Temporal Guard-Band Architecture

![Temporal Guard Band](assets/guard_band_timeline.svg)

Ambulatory CGMs often report smoothed or interpolated readings. If an algorithm uses glucose observations recorded at time $t$ to predict $y(t+30)$, subsequent sensor filtering can leak future trajectory information into the input.

To establish a defensible baseline:
- **Forecast Issuance Point ($t$)**: The deterministic time coordinate where predictions are generated.
- **Permitted Glucose History**: 13 lags sampled at 5-minute increments strictly prior to the guard band:
  $$\mathbf{x}_{\text{glucose}} = [y(t-5), y(t-10), y(t-15), \dots, y(t-65)]^T \in \mathbb{R}^{13}$$
- **Guard Band ($[t-5, t]$)**: A 5-minute zero-input zone immediately preceding issuance.
- **Effective Prediction Horizons**: Targets remain $y(t+30)$ and $y(t+60)$ from issuance time $t$, corresponding to 35 and 65 minutes from the most recently permitted glucose observation.

---

## 📈 Global Forecasting Benchmarks

![Global Benchmark](assets/global_benchmark.png)

Evaluated across **123,599 origins (+30m)** and **123,164 origins (+60m)** on 45 independent participants:

| Model Rung | Description | +30m RMSE | +30m Skill | +30m Imp. | +60m RMSE | +60m Skill | +60m Imp. |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Rung 0** | Guarded Persistence ($y(t-5)$) | 21.55 mg/dL | 0.00% | 0 / 45 (0.0%) | 29.32 mg/dL | 0.00% | 0 / 45 (0.0%) |
| **Rung 1** | Damped Trend Extrapolation | 21.39 mg/dL | +0.32% | 28 / 45 (62.2%) | 29.33 mg/dL | -0.15% | 22 / 45 (48.9%) |
| **Rung 2** | Guarded Ridge (13 Autoregressive Lags) | 19.87 mg/dL | +7.17% | 41 / 45 (91.1%) | 26.97 mg/dL | +7.02% | 39 / 45 (86.7%) |
| **Rung 3** | + Physiological Activity (HR & METs) | 19.85 mg/dL | +7.30% | 40 / 45 (88.9%) | 26.97 mg/dL | +6.94% | 38 / 45 (84.4%) |
| **Rung 4** | + Meal Context (Full Macronutrients) | 19.19 mg/dL | +10.26% | 41 / 45 (91.1%) | 27.03 mg/dL | +7.02% | 36 / 45 (80.0%) |
| **Rung 4b** | + Meal Context (Timing Only Ablation) | 19.18 mg/dL | +10.32% | 41 / 45 (91.1%) | 26.26 mg/dL | +9.06% | 39 / 45 (86.7%) |
| **Rung 5** | **+ Baseline Covariates (Age, Sex, BMI, HbA1c)** | **18.85 mg/dL** | **+11.82%** | **42 / 45 (93.3%)** | **25.45 mg/dL** | **+11.85%** | **43 / 45 (95.6%)** |
| **Rung 6** | Fixed Gradient Boosting (`HistGradientBoosting`) | 19.15 mg/dL | +11.06% | 40 / 45 (88.9%) | 25.64 mg/dL | +12.30% | 41 / 45 (91.1%) |

### Key Benchmark Takeaways
- **Clinical Covariates Matter**: Augmenting meal-timing Ridge with 4 static baseline covariates (Age, Sex, BMI, HbA1c) yields the highest performing linear model (Rung 5), reducing RMSE to 18.85 mg/dL (+30m) and 25.45 mg/dL (+60m).
- **Linear Ridge vs. Nonlinear GBDT**: The fixed `HistGradientBoostingRegressor` (depth 4, 100 trees) achieves 19.15 mg/dL (+30m) and 25.64 mg/dL (+60m). Across the full cohort, GBDT is statistically indistinguishable from linear Ridge ($\Delta\text{RMSE} = +0.29\text{ mg/dL}$ at +30m; $+0.19\text{ mg/dL}$ at +60m; both 95% CIs span zero). GBDT excels in normoglycemic controls (16.37 vs 16.97 mg/dL at +30m), while linear Ridge demonstrates greater robustness in diabetic subjects.

---

## 🎯 Stage 3 Personalization Dynamics

![Personalization Dashboard](assets/personalization_dashboard.png)

Personalization tests whether adapting the global Rung 5 model to an individual's early telemetry improves forecasts on their later unseen days. To ensure fair evaluation, every adaptation window is compared against a **freshly matched global baseline evaluated on identical post-purge timestamps**:

| Adaptation Window | Horizon | Matched Global RMSE | Personalized RMSE | Paired $\Delta\text{RMSE}$ (mg/dL) | 95% Bootstrap CI | Pct Reduction | Improved Subjects |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2 Study Days** | +30 min | 18.55 mg/dL | 18.84 mg/dL | +0.289 mg/dL | [-0.666, +1.687] | -1.74% | 28 / 45 (62.2%) |
| **4 Study Days** | +30 min | 18.17 mg/dL | 17.74 mg/dL | -0.428 mg/dL | [-1.346, +1.009] | +2.12% | 38 / 45 (84.4%) |
| **6 Study Days** | +30 min | 17.92 mg/dL | **17.10 mg/dL** | -0.825 mg/dL | [-1.724, +0.587] | +4.67% | **41 / 45 (91.1%)** |
| **2 Study Days** | +60 min | 25.19 mg/dL | 25.17 mg/dL | -0.025 mg/dL | [-0.917, +0.972] | +0.22% | 31 / 45 (68.9%) |
| **4 Study Days** | +60 min | 24.53 mg/dL | **23.38 mg/dL** | **-1.146 mg/dL** | **[-1.804, -0.405]** | **+4.76%** | **35 / 45 (77.8%)** |
| **6 Study Days** | +60 min | 24.07 mg/dL | **22.26 mg/dL** | **-1.811 mg/dL** | **[-2.431, -1.087]** | **+8.00%** | **40 / 45 (88.9%)** |

### Critical Scientific Insights
- **The Dose-Response Relationship**: A clear monotonic improvement emerges as calibration expands from 2 to 6 days. At 2 days, residual correction overfits sparse telemetry. By 6 days, personalized models reduce +60m RMSE by **$1.811\text{ mg/dL}$ (8.00%)** with **40 of 45 participants improving**.
- **Transparent Uncertainty & Significance Reporting**: At $+30$ minutes, the paired bootstrap 95% confidence intervals across all three windows (2-day $[-0.666, +1.687]$, 4-day $[-1.346, +1.009]$, and 6-day $[-1.724, +0.587]$) **all cross zero**; therefore, short-horizon residual adaptation does not reach statistical significance despite high participant improvement fractions (up to $91.1\%$). In contrast, at $+60$ minutes, both the 4-day ($[-1.804, -0.405]$) and 6-day ($[-2.431, -1.087]$) paired confidence intervals **strictly exclude zero**, establishing statistically robust, clinically meaningful error reductions.
- **Clinical Phenotype Impact**: At +60m under 6-day adaptation, Type 2 Diabetic subjects experience an average error reduction of **$-2.34\text{ mg/dL}$ ($7.63\%$)**, dropping from $30.58$ to $28.24\text{ mg/dL}$ ($12/14$ improved).

---

## ⚡ Quick Start

### 1. Clone & Environment Setup
```bash
git clone https://github.com/DMounas/personalized-glucose-digital-twin.git
cd personalized-glucose-digital-twin

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install package and dev dependencies
pip install --upgrade pip
pip install -e ".[dev]"
```

### 2. Run Test Suite & Quality Gates
```bash
# Run 118 unit and regression tests
pytest tests/ -v

# Run linting and static type checking
ruff check src tests
ruff format --check src tests
mypy src tests
```

### 3. Regenerate Visual Assets
Regenerate all figures and charts directly from the canonical aggregate benchmark JSONs without downloading raw data:
```bash
python scripts/generate_readme_assets.py
```

---

## 🔬 Reproducibility & Experiment Execution

To replicate the model training pipelines from raw sensor telemetry:

1. **Obtain Dataset**: Download the [CGMacros Version 1.0.0](https://physionet.org/content/cgmacros/1.0.0/) archive from PhysioNet and extract to `data/cgmacros/CGMacros/`. See [Dataset & Attribution Guide](docs/DATASET_AND_ATTRIBUTION.md) for detailed layout.
2. **Execute Stage 2 Population Benchmarks (Rungs 0–6)**:
   ```bash
   python -m dtwin.modeling.runner --data-dir data/cgmacros/CGMacros --bio-path data/cgmacros/CGMacros/bio.csv
   ```
   Generates `docs/reports/stage2_baseline_metrics.json` and out-of-fold prediction archives.
3. **Execute Stage 3 Personalization (2, 4, and 6 Study Days)**:
   ```bash
   python -m dtwin.modeling.personalization_runner --data-dir data/cgmacros/CGMacros --bio-path data/cgmacros/CGMacros/bio.csv
   ```
   Generates `docs/reports/stage3_personalization_metrics.json`.

---

## 🔒 Limitations & Responsible Use

- **Research Artifact Only**: This repository is designed to benchmark physiological time-series algorithms and data leakage mitigations. It does not provide medical advice, diagnosis, treatment, or insulin delivery control.
- **Cohort Generalizability**: The CGMacros cohort ($N=45$) represents free-living adults in the United States. Findings may not generalize to pediatric populations, gestational diabetes, type 1 diabetes, or hospitalized patients.
- **Sensor Hardware Invariance**: Guard-band intervals mitigate algorithmic interpolation leakage, but cannot correct for raw sensor enzyme latency, subcutaneous fluid delay, or physical sensor compression artifacts.
- **Privacy Assurance**: In accordance with HIPAA Safe Harbor and ethical research standards, no raw participant records, row-level continuous glucose measurements, or identifiable patient data are tracked or redistributed in this repository.

---

## 📜 Citation & References

If you build upon this codebase or reference the benchmarking methodology, please cite this repository:

```bibtex
@software{Mounas_Glucose_Digital_Twin_2026,
  author = {Mounas, Debangshu},
  title = {{Personalized Glucose Digital Twin for Type 2 Diabetes}},
  url = {https://github.com/DMounas/personalized-glucose-digital-twin},
  version = {1.0.0},
  year = {2026}
}
```

### Primary Dataset Citation
```bibtex
@article{bent2025cgmacros,
  title = {CGMacros: A multimodal dataset of continuous glucose monitoring, macronutrients, and physical activity in free-living conditions},
  author = {Bent, Brinna and Wang, Kelly and Grzesik, Peter and others},
  journal = {Scientific Data},
  volume = {12},
  number = {1},
  pages = {187},
  year = {2025},
  doi = {10.1038/s41597-025-05851-7}
}
```

---

## 📄 License & Attribution

- **Source Code**: Licensed under the [MIT License](LICENSE) &copy; 2026 Debangshu Mounas.
- **Dataset**: The CGMacros dataset is governed independently by the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC-BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/) license as published on PhysioNet.
