# Interactive Research Dashboard Guide

The **Glucose Digital Twin Research Dashboard** provides an interactive platform for exploring the project's empirical benchmark results and chronological residual personalization dynamics.

---

## Quick Start (Local Launch)

### 1. Clone & Setup Environment
```bash
git clone https://github.com/DMounas/personalized-glucose-digital-twin.git
cd personalized-glucose-digital-twin

# Create virtual environment
python -m venv .venv

# Activate on Linux/macOS:
source .venv/bin/activate
# Activate on Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Install dependencies (including dashboard requirements)
pip install -r requirements.txt
pip install -e .
```

### 2. Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
The application will automatically open in your default browser at `http://localhost:8501`.

---

## Dashboard Architecture & Sections

The dashboard is structured into four dedicated analytical sections:

### 1. Project Overview
- **Executive KPI Cards**: Summarizes cohort dimensions (45 participants), evaluation design (50 disjoint folds), population skill (+11.85%), and 6-day personalization impact (-1.81 mg/dL, 88.9% improved).
- **The Ambulatory Challenge**: Documents the three core failure modes of clinical CGM forecasting: telemetry interpolation bleed, intra-subject identity leakage, and high metabolic heterogeneity.
- **End-to-End System Architecture**: High-resolution workflow diagram illustrating raw ingestion, lattice grid alignment ($\phi = 0$), guarded feature matrix construction ($R^{20}$ space), and dual-tier model evaluation.
- **Clinical Non-Intervention Disclaimer**: Prominent notice clarifying research and educational scope.

### 2. Global Forecasting Explorer
- **Interactive Horizon Toggle**: Switch seamlessly between **+30-Minute** and **+60-Minute** forecast horizons.
- **Model Ladder Plotly Visualizer**: Interactive horizontal bar chart comparing Rungs 0 through 6 with asymmetric 95% bootstrap confidence intervals and persistence reference lines.
- **Linear Ridge vs. Nonlinear GBDT Deep-Dive**: Direct side-by-side comparison explaining why Rung 5 Ridge is the selected global foundation, and why GBDT does not demonstrate a statistically significant overall advantage over Ridge across the full cohort.
- **Clinical Subgroup Stratification**: Tabular breakdowns across Normal, Prediabetes, and Type 2 Diabetes cohorts.

### 3. Personalization Lab
- **Dual Parameter Selection**: Select both the forecast horizon (+30m vs. +60m) and the individual adaptation window (2, 4, or 6 study days).
- **Matched Global Baseline Comparison**: Evaluates personalization against a matched global baseline strictly on identical post-purge evaluation timestamps.
- **Transparent Significance Indicators**: Real-time disclosure banners highlighting when confidence intervals cross zero (as in all +30m windows) vs. when they strictly exclude zero (as in +60m 4-day and 6-day windows).
- **Dose-Response Trajectory**: Plotly charts demonstrating the monotonic error reduction as adaptation expands from 2 to 6 days.
- **Phenotypic Excursion Dynamics**: Demonstrates why Type 2 Diabetic subjects experience the greatest absolute error reduction ($-2.34\text{ mg/dL}$ at +60m under 6-day adaptation).

### 4. Methodology & Guard-Band Explorer
- **Temporal Guard-Band Diagram**: Visual schematic of the 13 guarded history lags ($y(t-65) \dots y(t-5)$), the 5-minute zero-input gap, and the forecast horizons.
- **Five Architectural Safeguards**: Comprehensive guide to interpolation protection, participant-disjoint cross-validation, and the 120-minute chronological purge buffer.
- **Evaluation Protocol Differentiation**: Tabular guide contrasting population benchmark evaluation vs. personalization evaluation.

---

## Deployment Guide (Streamlit Community Cloud)

The application is fully pre-configured for one-click deployment on [Streamlit Community Cloud](https://share.streamlit.io/):

1. **Sign in** to [Streamlit Community Cloud](https://share.streamlit.io/) with your GitHub account (`DMounas`).
2. Click **"New app"**.
3. Fill in the repository settings:
   - **Repository**: `DMounas/personalized-glucose-digital-twin`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Expand **Advanced settings**:
   - **Python version**: Select `3.10`, `3.11`, or `3.12`.
5. Click **"Deploy!"**.

Streamlit Cloud will read `requirements.txt`, install dependencies, and launch the application on a public URL (e.g., `https://personalized-glucose-digital-twin.streamlit.app/`).

---

## Data Privacy & Zero Local Storage Guarantee

The hosted dashboard strictly complies with research privacy protocols:
- **No Raw Data Dependency**: Runs entirely from the public canonical aggregate reports in `docs/reports/`.
- **Zero Protected Health Information (PHI)**: Displays only cohort-level and subgroup summary statistics ($N=45$).
- **No Prediction File Leakage**: Raw out-of-fold CSV archives (`*.csv.gz`) are strictly excluded by `.gitignore` and never loaded by the UI.
