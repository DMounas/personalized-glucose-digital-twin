# Contributing to Personalized Glucose Digital Twin

Thank you for your interest in contributing to the **Personalized Glucose Digital Twin** project.

This repository implements a rigorous ML research and forecasting framework evaluated on the open-access CGMacros continuous glucose monitoring cohort.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/DMounas/personalized-glucose-digital-twin.git
   cd personalized-glucose-digital-twin
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   ```

3. **Install editable package and development dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

## Code Quality Standards

All pull requests must pass the project's quality gates:

1. **Linting:**
   ```bash
   ruff check src tests
   ```

2. **Formatting:**
   ```bash
   ruff format --check src tests
   ```
   To auto-format: `ruff format src tests`

3. **Static Type Checking:**
   ```bash
   mypy src tests
   ```

4. **Automated Testing:**
   ```bash
   pytest tests/ -v
   ```

## Experimental Invariance & Scientific Integrity

- **Frozen Protocols:** Protocol specifications in `docs/STAGE2_PROTOCOL_DRAFT.md` and `docs/STAGE3_PERSONALIZATION_PROTOCOL.md` are frozen with tracked SHA-256 hashes. Do not modify frozen protocols without explicit justification and hash re-registration.
- **Zero Leakage:** Never allow intra-participant sample sharing between training and test sets. Cross-validation is strictly participant-disjoint.
- **Reporting Boundaries:** Do not mix participant-specific personalization results with zero-shot population generalization claims.

## Data Governance & Privacy

Never commit:
- Raw participant CSV files or biological records from the CGMacros dataset.
- Row-level clinical measurements or identifiable patient metadata.
- Large derived out-of-fold binary prediction archives (`*.csv.gz`).
