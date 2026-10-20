# Stage 1B-R2 Completion Report: Corrected Revision

**Stage:** Stage 1B-R2 (Corrective Revision)  
**Status:** **CORRECTED REVISION — PENDING INDEPENDENT REVIEW**  
*(Note: In accordance with governance instructions, this corrective revision is submitted for peer/independent review and is not self-certified as "PASSED" or "CERTIFIED".)*  
**Date:** 2026-10-19  
**Repository:** `glucose-digital-twin`  
**Frozen Config Digest:** `7e3d9b02c504146819218c68e8d4e93d160cb982043d5356613b861363b0833e`

---

## 1. Scope & Corrective Governance Overview

Following a comprehensive internal code audit ([`docs/errata/STAGE1B_CORRECTION_AUDIT_2026-10-19.md`](docs/errata/STAGE1B_CORRECTION_AUDIT_2026-10-19.md)), this revision (Stage 1B-R2) systematically resolved six confirmed methodological defects in the initial Stage 1B release without modifying historical Stage 0 or Stage 1A baseline files (verified byte-identical via cryptographic SHA-256 baseline).

### Key Corrective Implementations:
1. **Explicit Time Semantics (T1–T7):** Implemented in [`src/dtwin/timeaxis.py`](src/dtwin/timeaxis.py). Row index is never treated as a temporal coordinate. Contiguous runs ($\Delta t = 60\text{ s}$) serve as the atomic unit of analysis. Zero gap-bridging or positional slicing.
2. **Run-Bounded Native-Grid Inference (C1):** Curvature bends ($d_2$) and linear reconstruction residuals are computed strictly intra-run, eliminating gap-boundary false bends. Lattice selection uses true elapsed-time coordinates $m(t) \pmod P$.
3. **Disentangled Pairing (C1):** Partitioned Set A into 37,477 coincident native pairs, 4,568 Libre-native / Dexcom-interpolated pairs, 85,721 Dexcom-native / Libre-interpolated pairs, and 501,839 doubly-interpolated pairs.
4. **Run-Bounded Horizons & Excursions (C2):** Eliminated `dropna()` positional slicing (enforced by AST lint). Horizons $(t, t+h)$ evaluated strictly intra-run. Excursions detect 683 Dexcom events ($>180\text{ mg/dL}$) with $5\text{ mg/dL}$ hysteresis margins and tracking of boundary-censored events.
5. **Unbalanced Repeated-Measures ANOVA (C3):** Applied Bland-Altman $n_0$ correction ($n_0=13,988.59$), separating pooled grand mean ($\mu_{\text{pool}} = -31.95\text{ mg/dL}$) from equal-weighted subject mean ($\mu_{\text{eq}} = -32.36\text{ mg/dL}$). Recalculated full ANOVA estimator in 500 participant-clustered bootstrap replicates. Conducted censored sensitivity analysis ($\le 40, \ge 400\text{ mg/dL}$).
6. **Verified Lag Direction & Neutral Language (C4):** Established convention where positive lag indicates Libre leads Dexcom (median $+5.0\text{ min}$). Characterized differences strictly as observed systematic disagreement without unverified physiological causation.
7. **Detector-Blind Synthetic Benchmark Suite (C5):** Evaluated 15 independent scenarios across 1,500 test series with Wilson 95% CIs, demonstrating 100% sensitivity on true linear lattices and 100% specificity on continuous negative controls.
8. **Participant Privacy Safeguards (C6):** Zero direct participant identifiers in committed reports; small cells ($<5$) suppressed; individual diagnostics restricted to local gitignored storage (`reports_local/`).

---

## 2. Headline Scientific Metrics Summary

| Analysis Dimension | Metric Description | Numerical Finding | 95% Confidence Interval | Methodological Reference |
| :--- | :--- | :---: | :---: | :--- |
| **Cohort Coverage** | Total Participants | 45 | N/A | 15 Normal, 16 Prediabetes, 14 Diabetes |
| **Cohort Coverage** | Contiguous Runs ($\Delta t = 60\text{ s}$) | 1,200 | N/A | Atomic contiguous segments |
| **Cohort Coverage** | Total 1-min Recorded Rows | 687,580 | N/A | 45 participant files |
| **Cohort Coverage** | Paired 1-min Overlap Rows (Set B) | 629,605 | N/A | Usable paired recording |
| **Native Grid** | FreeStyle Libre Pro Native Rate | 15 minutes | $[0.992, 1.000]$ | 45/45 High Confidence ($0.0008\text{ mg/dL}$ res.) |
| **Native Grid** | Dexcom G6 Pro Native Rate | 5 minutes | $[0.992, 1.000]$ | 44/45 High Confidence ($0.0033\text{ mg/dL}$ res.) |
| **Set A Breakdown** | Coincident Native Pairs | 37,477 | N/A | Both devices at native lattice vertices |
| **Set A Breakdown** | Libre-Native / Dex-Interp Pairs | 4,568 | N/A | Libre native; Dexcom interpolated |
| **Agreement (Set B)** | Pooled Mean Difference ($\mu_{\text{pool}}$) | $-31.95\text{ mg/dL}$ | $[-36.72, -26.60]$ | Unbalanced ANOVA grand mean |
| **Agreement (Set B)** | Equal-Weighted Mean ($\mu_{\text{eq}}$) | $-32.36\text{ mg/dL}$ | $[-37.14, -27.11]$ | Unweighted participant mean |
| **Agreement (Set B)** | $SD_{\text{between}}$ ($\sigma_b$) | $16.25\text{ mg/dL}$ | N/A | Corrected using $n_0 = 13,988.59$ |
| **Agreement (Set B)** | $SD_{\text{within}}$ ($\sigma_w$) | $18.28\text{ mg/dL}$ | N/A | Derived from ANOVA MSW |
| **Agreement (Set B)** | $SD_{\text{repeated\_measures}}$ ($\sigma_{\text{rm}}$) | $24.46\text{ mg/dL}$ | N/A | Total repeated measures standard deviation |
| **Agreement (Set B)** | 95% Limits of Agreement | $[-79.89, +16.00]\text{ mg/dL}$ | $[-87.69, +27.26]$ | Clustered bootstrap percentile intervals |
| **Censored Sensitivity** | Censored Set B Paired Points | 618,262 | N/A | Excludes saturation ($\le 40, \ge 400\text{ mg/dL}$) |
| **Censored Sensitivity** | Censored Mean Diff ($\mu_{\text{pool}}$) | $-31.39\text{ mg/dL}$ | $[-35.95, -25.95]$ | Demonstrates stability outside saturation |
| **Apparent Lag** | Cross-correlation Peak | $+5.0\text{ minutes}$ | IQR: $[3.0, 7.0]$ | Positive lag indicates Libre leads Dexcom |
| **Task Feasibility** | Dexcom 30-min Mean Delta (T1) | $13.18\text{ mg/dL}$ | Median: $7.60$ | Descriptive, not a model |
| **Task Feasibility** | Dexcom 60-min Mean Delta (T1) | $19.38\text{ mg/dL}$ | Median: $11.00$ | Descriptive, not a model |
| **Task Feasibility** | Dexcom Hyper Episodes $>180$ (T2) | 683 | 21 censored | $5\text{ mg/dL}$ hysteresis margin |
| **Task Feasibility** | Reconciled Meal Events (T3) | 1,706 | N/A | Substrate for postprandial digital twin |

---

## 3. Verification & Quality Gates

The implementation passed all local automated quality gates:
- **Pytest:** 68 passed in 3.91s (`python -m pytest -q`).
- **AST Lint:** `test_lint_forbid_dropna_positional_slicing_in_analysis` passed (zero forbidden slices in `src/dtwin/analysis/`).
- **Code Style & Formatting:** Ruff check (`python -m ruff check .`) and format check (`python -m ruff format --check .`) passed with zero errors.
- **Static Type Checking:** Mypy (`python -m mypy src tests`) passed with zero issues across 42 source files.
- **Cryptographic Manifest:** All 3,502 raw dataset files match SHA-256 manifest exactly (exit code 0; error exit code 3 on tampering verified).
- **Baseline Historical Preservation:** All 39 Stage 0 and Stage 1A baseline files verified 100% byte-identical against `reports_local/pre_change_baseline_sha256.json`.
- **Privacy Scanner:** Automated regex scan confirms zero direct participant IDs in shareable reports or JSON.

---

## 4. Key Artifacts Generated in Stage 1B-R2

1. **Formal Erratum Notice:** [`docs/errata/ERRATUM_2026-10-19_stage1b_corrections.md`](docs/errata/ERRATUM_2026-10-19_stage1b_corrections.md)
2. **Technical Methodology Document:** [`docs/NATIVE_GRID_METHOD_R2.md`](docs/NATIVE_GRID_METHOD_R2.md)
3. **Stage 2 Modeling Specification:** [`docs/MODELING_SPEC_R2.md`](docs/MODELING_SPEC_R2.md)
4. **Machine-Readable Results JSON:** [`docs/reports/stage1b_r2_results.json`](docs/reports/stage1b_r2_results.json)
5. **Comprehensive Scientific Report:** [`docs/reports/stage1b_r2_report.md`](docs/reports/stage1b_r2_report.md)
