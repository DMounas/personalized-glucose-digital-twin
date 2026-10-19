# Glucose Digital Twin: T2D Glucose Forecasting & What-If Simulation

A proof-of-concept healthcare Digital Twin for type 2 diabetes mellitus (T2D) designed to fuse clinical baseline metabolic data with dynamic continuous glucose monitor (CGM) sensor streams and lifestyle data. The system aims to forecast near-future glycemic excursions (hyperglycemia and hypoglycemia risk) and explore bounded "what-if" counterfactual scenarios (e.g., macronutrient adjustments, post-meal walking) through a conceptual clinician dashboard.

> **CRITICAL CLINICAL DISCLAIMER**: This software is an engineering proof-of-concept developed solely for research and hackathon demonstration purposes. It is **NOT** a certified Medical Device (SaMD), does **NOT** provide medical diagnosis or treatment recommendations, and must **NEVER** be used to guide insulin dosing or clinical therapy.

---

## Current Status: Stage 0
We are currently in **Stage 0: Repository scaffold, data provenance, and dataset-audit tooling**. This stage establishes the cross-platform engineering foundations, automated dataset discovery, privacy-preserving tabular profiling, timeseries sampling analysis, and data dictionary conformance tooling. No forecasting models or dashboards are implemented in this stage.

---

## Evidence-Labelling Convention
To maintain strict scientific and clinical integrity, all statements, metrics, and figures across this repository are labelled with one of the following tags:
- **[ESTABLISHED]**: Backed by a cited peer-reviewed primary source or official documentation.
- **[HYPOTHESIS]**: An engineering hypothesis, design idea, or untested assumption.
- **[SYNTHETIC DEMO]**: Illustrative synthetic data or scenario for demonstration, not evidence of real-world clinical efficacy.
- **[VERIFIED RESULT]**: An empirical result produced by an executed command within this repository, with the exact command and git commit hash recorded.

---

## Quick-Start Setup

This repository is fully cross-platform and supports both Windows PowerShell and Linux/macOS. Python $\ge 3.10$ is required.

### 1. Clone & Set Up Virtual Environment

#### Windows PowerShell:
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install package in editable mode with development tools
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

#### Linux / macOS:
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install package in editable mode with development tools
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 2. Run Linting and Tests

```bash
# Run code quality linting
ruff check .

# Verify formatting
ruff format --check .

# Run test suite
pytest -q
```

---

## Running the Dataset Audit Tool
The repository includes a dedicated CLI tool `dtwin-audit` (or `python -m dtwin.audit`) to audit dataset directories in a strictly aggregate, privacy-preserving manner without assuming fixed schemas or leaking patient records.

```bash
# Basic run pointing to an extracted dataset directory
python -m dtwin.audit --data-dir data/cgmacros

# Run with official data dictionaries and checksum verification
python -m dtwin.audit \
  --data-dir data/cgmacros \
  --dictionary data/cgmacros/DataDictionary_CGMacros-00X.csv \
  --dictionary data/cgmacros/DataDictionary_Bio.csv \
  --verify-checksums \
  --output-dir docs/reports

# Run using the registered console script
dtwin-audit --data-dir data/cgmacros
```

If the specified data directory is missing, empty, or contains no supported tabular files, the audit tool outputs clear data acquisition guidance, generates an audit report with status `NO DATA FOUND`, and exits with exit code `2`.

---

## Project Documentation
Detailed specifications and provenance notes are located in the `docs/` directory:
- [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md): Architecture overview, competition alignment, non-goals, and stage roadmap.
- [docs/DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md): Primary data source citations (PhysioNet, Nature Scientific Data), claimed facts, licence requirements (CC BY-NC-SA 4.0), and known documentation ambiguities.
- [docs/DATA_ACQUISITION.md](docs/DATA_ACQUISITION.md): Step-by-step instructions for downloading and extracting the CGMacros v1.0.0 dataset.
- [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md): Living table of unresolved technical and clinical questions.
- [docs/reports/](docs/reports/): Destination directory for generated aggregate audit reports (`audit_report.json` and `audit_report.md`).
