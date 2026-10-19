# Stage 1B-R3 Comprehensive Scientific Report: Corrected Native-Grid Inference, Dual-Sensor Concordance, and Modeling Readiness

**Status:** STAGE 1B FROZEN — R3.4 FINAL RECONCILIATION COMPLETE  
**Author:** Antigravity Implementation Engineer  
**Date:** 2026-10-19 (Updated 2026-10-20 for R3.4 Freeze)  
**Configuration File:** [`configs/stage1b.yaml`](file:///c:/New%20folder/HACKATHONS/glucose-digital-twin/configs/stage1b.yaml) (Version `1.4.0-r3.4`)  
**Frozen Config SHA-256:** `cf2763408891feb97c67dd5184ad4674dd2c98a736922ad322c8b66bc11bd467`  
**Committed Machine-Readable Results:** [`docs/reports/stage1b_r3_results.json`](file:///c:/New%20folder/HACKATHONS/glucose-digital-twin/docs/reports/stage1b_r3_results.json) (SHA-256: `a9b8efc06b715f4c5fd46c54cb36a0ee151a91330e597e355e50fb9d8917181b`)  
**Canonical Metrics Registry:** [`docs/reports/canonical_metrics.json`](file:///c:/New%20folder/HACKATHONS/glucose-digital-twin/docs/reports/canonical_metrics.json) (SHA-256: `70afb620d1ce781c4d6dafc71f29f7ce847e0e68f23f8e10c2b6c7be69126c3d`)  
**File-by-File Audit Table:** `reports_local/file_by_file_row_counts.csv`  
**Timestamp Integrity Audit Table:** `reports_local/timestamp_integrity_audit.csv`  
**Formal Erratum Notice:** [`docs/errata/ERRATUM_2026-10-19_stage1b_corrections.md`](file:///c:/New%20folder/HACKATHONS/glucose-digital-twin/docs/errata/ERRATUM_2026-10-19_stage1b_corrections.md)  

---

## Executive Summary

Stage 1B-R3 represents the definitive, test-gated corrective pass for the CGMacros v1.0.0 dataset (PhysioNet). This revision addresses all findings from the Stage 1B-R2 independent code audit and Stage 1B-R3.1 / R3.2 reviews:
1. **Window Timestamps & Indices in `timeaxis.py`:** Restored explicit `start_time`, `origin_time`, `target_time`, `start_index`, `origin_index`, and `target_index` fields with zero off-by-one errors.
2. **Excursion Persistence Null-Reset & Durations:** Resolved the null-persistence defect where NaNs were skipped during episode entry; NaNs now strictly reset `active_len = 0`, eliminating false excursion episodes. Excursion duration tracking, release null-resets, and boundary censoring (left- and right-censoring) are fully operational.
3. **Reconciled Benchmark Summaries & Jitter Distinctions:** Unified the frozen core 5-scenario suite (2,500 series) and detector-blind 15-scenario suite (1,500 series) under a unified `synthetic_benchmarks` structure. Clearly separated measurement amplitude noise (core suite, 500/500 = 100.0%) from sampling timestamp coordinate drift (blind suite, 100/100 = 100.0% unresolved; 1 false confident 15m classification in 15m jitter, 1.0% error rate).
4. **Dexcom Participant Status Resolved:** Participant 23's (Cluster 24) behavior is definitively explained: an inter-session 1-minute clock phase shift occurred across an unrecorded 40.5-hour interval without verifiable physical sensor-replacement metadata (Session 1: minute $\equiv 1 \pmod 5$; Session 2: minute $\equiv 2 \pmod 5$). Forcing a global single phase drops hit rate to 52.8%, whereas per-session inference (Time Semantics T6) proves **100.0% 5-minute linear lattice compliance** across both sessions.
5. **Cohort Wilson Score Intervals Corrected:** Cohort-level Wilson intervals for $N=45$ clinical participants are reported accurately (45/45 = $[0.9213, 1.0000]$; 44/45 = $[0.8845, 0.9961]$) and distinguished from synthetic $N=500$ benchmark intervals ($[0.9924, 1.0000]$).
6. **File-by-File Row-Count Reconciliation:** Verified that all 45 participant files have lengths strictly divisible by 5 ($N_i \equiv 0 \pmod 5$), yielding an authoritative cohort total of **687,580 rows**. The 632,536 figure could not be reproduced and its original provenance remains unresolved. It is not the row count of any combination of complete participant files, because each complete file count is divisible by five; that fact alone does not identify the source of the old figure.
7. **Neutral Lag Characterization:** Characterized cross-correlation lag strictly as observed empirical displacement across resampled signals without causal, physiological, or filtering latency claims, verified with non-periodic multi-frequency AR known-shift tests with NaNs and unequal overlap.
8. **Dynamic T2 Narrative:** Synchronized all finding strings dynamically to exact dictionary episode counts.
9. **Participant-Level Grouped Validation:** Enforced `StratifiedGroupKFold` cross-validation grouped by participant cluster in the modeling specification.

---

## Part 1: Dataset Provenance & File-by-File Reconciliation

The CGMacros v1.0.0 archive was audited file-by-file across all 45 participant CSV files:
- **Total Recorded Rows:** 687,580 rows across 45 files.
- **Divisibility Proof:** Every individual participant file length $N_i$ satisfies $N_i \equiv 0 \pmod 5$.
- **Arithmetic Identity of Cohort Sensor Rows:**
  - **Total Valid Dexcom Rows:** 629,825
  - **Total Valid Libre Rows:** 687,360
  - **Paired Usable Overlap Rows (Both Valid):** 629,605
  - **Dexcom-Only Rows (Libre Null):** 220
  - **Libre-Only Rows (Dexcom Null):** 57,755
  - **Neither Sensor Valid:** 0
  - **Arithmetic Partition:** $629,605 + 220 + 57,755 + 0 = 687,580$ (exact mathematical identity verified).
  - **Pairing Semantics:** Defined strictly as **row-wise within each participant CSV**, where row $i$ represents a pre-aligned 1-minute wall-clock interval created by the dataset authors. Timestamps across all 45 files are 100% strictly monotonically increasing, with 0 duplicates and 0 unparseable values.
  - **Exclusions:** Excluded rows comprise strictly missing sensor readings ($57,755 + 220 = 57,975$ rows).
- **Provenance of 632,536 Figure:** The 632,536 figure could not be reproduced and its original provenance remains unresolved. It is not the row count of any combination of complete participant files, because each complete file count is divisible by five; that fact alone does not identify the source of the old figure.
- **Contiguous Run Denominators & Input Masks:**
  - `timestamp_contiguous_runs_all_rows = 1,200`: Computed via `enumerate_runs(df)` across all 687,580 rows where consecutive timestamps have step $\Delta t = 60\text{ s}$.
  - `dexcom_valid_contiguous_runs = 1,202`: Computed via `enumerate_runs(df[df["Dexcom GL"].notna()])` across the 629,825 non-null Dexcom readings.
  - `libre_valid_contiguous_runs = 1,215`: Computed via `enumerate_runs(df[df["Libre GL"].notna()])` across the 687,360 non-null Libre readings (Participant Cluster 4 contains 220 internal nulls splitting its Libre trace into 16 contiguous runs).
  - All 89 evaluable Dexcom runs ($\ge 120$ min, $\ge 20$ bends) derive strictly from the 1,202 Dexcom-valid runs denominator.
- **Non-Overlapping 2-Hour Windows:** 5,206 windows bounded strictly within continuous runs of $\ge 120$ minutes.

### Cohort Demographics Summary:
- **Normal Glycemia ($\text{HbA1c} < 5.7\%$):** 15 participants, 211,480 paired overlap rows.
- **Prediabetes ($5.7\% \le \text{HbA1c} \le 6.4\%$):** 16 participants, 218,495 paired overlap rows.
- **Type 2 Diabetes ($\text{HbA1c} \ge 6.5\%$):** 14 participants, 199,630 paired overlap rows.

---

## Part 2: Native-Grid Inference & Synthetic Validation

### 2.1 Theoretical Foundations & Time Semantics (T1–T7)
Row index is never treated as a time coordinate. Second differences $d_2(t) = |y_{t+1} - 2y_t + y_{t-1}|$ are evaluated strictly on interior run points within contiguous 1-minute sequences, eliminating boundary false bends. Candidate periods (5-min and 15-min) are distinguished via run-bounded elapsed minutes $t_{\min} \pmod P$, intermediate bend ratios, and linear reconstruction residuals.

### 2.2 Reconciled Synthetic Benchmarks (Full Scenario-Level Tables)

#### Suite 1: Frozen Core 5-Scenario Suite (2,500 Traces, Seed 42)
| Scenario | Traces ($N$) | Inferred 5m | Inferred 15m | Inferred Unresolved | Target Metric | Success Rate | Wilson 95% CI |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: |
| `five_minute_native` | 500 | 500 | 0 | 0 | Sensitivity 5m | 100.0% | $[0.9924, 1.0000]$ |
| `fifteen_minute_native` | 500 | 0 | 500 | 0 | Sensitivity 15m | 100.0% | $[0.9924, 1.0000]$ |
| `continuous_one_minute_negative_control` | 500 | 0 | 0 | 500 | Specificity Control | 100.0% | $[0.9924, 1.0000]$ |
| `five_minute_with_amplitude_noise_and_drops` | 500 | 500 | 0 | 0 | Sensitivity 5m | 100.0% | $[0.9924, 1.0000]$ |
| `fifteen_minute_with_flat_stretches` | 500 | 0 | 500 | 0 | Sensitivity 15m | 100.0% | $[0.9924, 1.0000]$ |

*Note on Scenario Renaming:* `five_minute_with_amplitude_noise_and_drops` (formerly aliased as `five_minute_with_jitter_and_drops`) explicitly reflects that noise is injected into glucose measurement amplitude on fixed timestamps rather than perturbing coordinate timestamps.

#### Suite 2: Detector-Blind 15-Scenario Suite (1,500 Traces, Seed 42)
| Scenario | Traces ($N$) | Inferred 5m | Inferred 15m | Inferred Unresolved | Success Rate | Wilson 95% CI |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `true_5min_linear` | 100 | 100 | 0 | 0 | 100.0% | $[0.9630, 1.0000]$ |
| `true_15min_linear` | 100 | 0 | 100 | 0 | 100.0% | $[0.9630, 1.0000]$ |
| `true_5min_rounded` | 100 | 100 | 0 | 0 | 100.0% | $[0.9630, 1.0000]$ |
| `true_15min_rounded` | 100 | 0 | 100 | 0 | 100.0% | $[0.9630, 1.0000]$ |
| `native_timestamp_jitter_5min` | 100 | 0 | 0 | 100 | 100.0% | $[0.9630, 1.0000]$ |
| `native_timestamp_jitter_15min` | 100 | 0 | 1 | 99 | 99.0% | $[0.9455, 0.9982]$ |
| `dropped_native_bridged_5min` | 100 | 100 | 0 | 0 | 100.0% | $[0.9630, 1.0000]$ |
| `dropped_native_bridged_15min` | 100 | 0 | 100 | 0 | 100.0% | $[0.9630, 1.0000]$ |
| `dropped_native_nan_5min` | 100 | 100 | 0 | 0 | 100.0% | $[0.9630, 1.0000]$ |
| `absent_timestamp_gaps_15min` | 100 | 0 | 100 | 0 | 100.0% | $[0.9630, 1.0000]$ |
| `collinear_flat_periods` | 100 | 0 | 100 | 0 | 100.0% | $[0.9630, 1.0000]$ |
| `low_dynamic_range` | 100 | 100 | 0 | 0 | 100.0% | $[0.9630, 1.0000]$ |
| `alternative_resampling_cubic_pchip` | 100 | 0 | 0 | 100 | 100.0% | $[0.9630, 1.0000]$ |
| `alternative_resampling_nearest` | 100 | 0 | 0 | 100 | 100.0% | $[0.9630, 1.0000]$ |
| `physiological_simulator_continuous` | 100 | 0 | 0 | 100 | 100.0% | $[0.9630, 1.0000]$ |

**Clarification of Jitter Scenarios Across Suites:**
- Core Suite `five_minute_with_amplitude_noise_and_drops`: Tests **glucose measurement amplitude noise** ($\sigma = 2.0\text{ mg/dL}$) on fixed 5-minute sampling timestamps (with dropout points). The underlying sampling timestamps remain strictly on the 5-minute lattice. Observed classification: 500/500 (100.0%) 5-minute native lattice.
- Blind Suite `native_timestamp_jitter_5min`: Tests **sampling timestamp coordinate drift** (physical sampling intervals wander continuously away from uniform 5-minute grid). Expected: `UNRESOLVED / NO_RELIABLE_LATTICE`. Observed: 100/100 (100.0%) unresolved (Wilson 95% CI: $[0.9630, 1.0000]$).
- Blind Suite `native_timestamp_jitter_15min`: Tests sampling timestamp coordinate drift on 15-minute sampling. Expected: `UNRESOLVED`. Observed: 99/100 unresolved (unresolved rate 99.0%, Wilson 95% CI: $[0.9455, 0.9982]$, or 94.55%–99.82%); 1/100 falsely classified as 15m lattice (false-classification rate 1.0%, Wilson 95% CI: $[0.0018, 0.0545]$, or 0.18%–5.45%). Both intervals are reported separately with exact binomial coverage.

### 2.3 Cohort Native-Grid Inference, Libre Metadata Discordance & Run Distribution

#### FreeStyle Libre Pro & Metadata Discordance Investigation:
- **Concordant 15-Minute Grid:** 44/45 participants (97.78%) confirmed 15-minute native lattice with HIGH_CONFIDENCE. Wilson 95% CI: $[0.8845, 0.9961]$. Mean reconstruction residual: $0.0008\text{ mg/dL}$.
- **Metadata-Discordant Series (Participant Cluster 4 Detailed Investigation):**
  - **Curvature Bend Threshold Reconciliation:** The canonical production configuration (`configs/stage1b.yaml`) specifies `second_difference_bend_threshold: 0.15`, designed to reject sensor quantization steps ($\le 0.15\text{ mg/dL}$), detecting **563 curvature bends**. An exploratory machine-precision threshold (`1e-5`) was also evaluated, detecting **846 curvature bends** down to floating-point epsilon.
  - **Comprehensive Threshold Sensitivity Analysis:** Evaluated across a 500,000-fold variation from $10^{-6}\text{ mg/dL}$ to $0.50\text{ mg/dL}$, inference results are strictly invariant:
    - At `1e-5`: 846 bends, period 5, phase 0, hit rate 1.0000, residual $0.0000\text{ mg/dL}$ ($3.5\times 10^{-15}\text{ mg/dL}$), 244 intermediate bends, distinction ratio $\mathcal{R}_{\text{inter}} = 2.46 < 3.0$.
    - At `0.15` (canonical): 563 bends, period 5, phase 0, hit rate 1.0000, residual $0.0000\text{ mg/dL}$ ($3.5\times 10^{-15}\text{ mg/dL}$), 162 intermediate bends, distinction ratio $\mathcal{R}_{\text{inter}} = 2.47 < 3.0$.
    - At all thresholds, exactly $\sim 28.8\%$ of curvature bends fall at intermediate 5-minute phases (phases 0 and 10 mod 15), proving that the interpolated series contains informative vertices spaced at 5-minute intervals.
  - **Fundamental Nested Lattice Mathematical Principle:** A denser linear grid ($P=5$) always reconstructs a coarser piecewise-linear grid ($P=15$) with zero residual. Therefore, a near-zero reconstruction residual on a denser nested grid does **not** prove a 5-minute native lattice. The genuine distinguishing evidence is intermediate curvature bends ($\mathcal{R}_{\text{inter}} = 2.47 < 3.0$ and 162 intermediate bends).
  - **Scientific Classification:** Although the series satisfies a 5-minute linear lattice mathematically, published CGMacros primary literature (Das et al., *Nature Scientific Data* / PhysioNet) explicitly specifies that FreeStyle Libre Pro hardware recorded at a 15-minute sampling rate. In accordance with Stage 1B-R3.3 guidelines, this series is strictly classified and retained as **`METADATA-DISCORDANT`** pending independent laboratory clarification. We do NOT speculate or claim unverified hardware replacement, alternative firmware, or protocol modifications without primary source documentation.
  - Overall native lattice identification (any period): 45/45 participants (100.0%), Wilson 95% CI: $[0.9213, 1.0000]$.

#### Dexcom G6 Pro Run-Length Distribution & Transparent Compliance:
- **Total Continuous Runs Across Cohort:** 1,202 runs.
- **Participant Cluster 7 Micro-Gap Investigation:**
  - Participant Cluster 7 accounts for **871 of the 1,202 runs**.
  - Detailed inspection reveals 870 non-1-minute timestamp steps (1 to 20 minute dropouts/absent minutes) that fragment the 5,655 recorded points into short contiguous runs (mean length: 6.5 minutes; median length: 1.0 minute).
  - 860 runs are underpowered (< 120 minutes) and 2 runs have < 20 informative curvature bends.
  - The remaining 9 evaluated sessions are 100.0% compliant 5-minute linear lattices.
- **Cohort Run-Level Aggregation & Data Duration Coverage (Zero Silent Passing):**
  - **Evaluated Compliant Runs ($\ge 120$ min, $\ge 20$ bends):** **89 runs (100.0% of evaluated)**, Wilson 95% CI ($N=89$): $[0.9585, 1.0000]$.
  - **Dataset Representation Coverage (Exact Qualification):** Eligible runs contained 625,728 of 629,825 valid one-minute-grid Dexcom rows (99.35% of valid rows in the released representation) and spanned all 45/45 participants (100.0% cohort coverage). This percentage represents row coverage in the released 1-minute interpolated representation and must not be equated with coverage of independent physical sensor observations.
  - **Underpowered Short Runs (< 120 min):** 1,111 runs (including 860 in Participant 7), containing a total of **3,855 rows (only 0.61% of Dexcom data)**.
  - **Underpowered Low-Bend Runs (< 20 bends):** 2 runs, containing **242 rows (only 0.04% of Dexcom data)**.
  - **Total Runs Across Cohort:** 1,202 runs (625,728 + 3,855 + 242 = 629,825 valid rows, 100.0%).
  - **Narrowed Compliance Claim:** Compliance is claimed strictly **"across all 89 evaluated sessions"**, explicitly qualifying that 1,113 low-information runs are excluded from formal lattice inference due to lack of statistical power, while confirming that the evaluated sessions audit **99.35% of all valid recorded sensor data**.
- **Dexcom Global Single-Phase (44/45, 97.78%):**
  - Wilson 95% CI: $[0.8845, 0.9961]$.
  - **Neutral Attribution for Participant Cluster 23:** Participant Cluster 23 exhibits two multi-day recording sessions separated by an unrecorded 40.5-hour interval. Session 1 aligns to clock minute $\equiv 1 \pmod 5$ (1,124 bends, 100% on-grid). Session 2 aligns to clock minute $\equiv 2 \pmod 5$ (1,257 bends, 100% on-grid). An observed 1-minute clock phase shift occurred across the unrecorded 40.5-hour interval without verifiable physical sensor-replacement metadata. Evaluated per-session under Time Semantics T6, both sessions are 100.0% compliant 5-minute linear lattices.


---


## Part 3: Dual-Sensor Agreement (Repeated-Measures ANOVA)

> [!WARNING]
> **Agreement Analysis Status: `EXPLORATORY_SERIAL_AUTOCORRELATION_UNADJUSTED`**  
> Repeated-measures Bland-Altman limits of agreement are evaluated across 1-minute interpolated pairs without autoregressive adjustment. Because interpolated glucose traces exhibit strong positive serial autocorrelation across successive minutes, standard degrees-of-freedom and variance assumptions underestimate true estimator variance. These limits of agreement must be interpreted as exploratory descriptive bounds rather than valid independent tolerance intervals.
>
> **Empirical Disagreement vs. Hardware Bias Caveat:**  
> The observed mean paired difference ($-31.95\text{ mg/dL}$ pooled, $-32.36\text{ mg/dL}$ equal-weighted) represents an **empirical trace disagreement across resampled time series**. It must **NOT** be interpreted as a proven hardware bias, systematic sensor calibration error, or clinical ground truth, because serial temporal autocorrelation across successive 1-minute pairs has not been parametrically adjusted.

### 3.1 Unbalanced Random-Effects ANOVA Model
Accounting for unbalanced participant cluster sizes ($n_i$ paired points per participant), the effective multiplier for Set B Uncensored is $n_0 = 13,988.59$.
- **Mean Squares Within ($MSW$):** $\sigma_w^2 = (18.28\text{ mg/dL})^2 \implies \sigma_w = 18.28\text{ mg/dL}$.
- **Mean Squares Between ($MSB$):** $\sigma_b^2 = \max\left(0, \frac{MSB - MSW}{n_0}\right) = (16.25\text{ mg/dL})^2 \implies \sigma_b = 16.25\text{ mg/dL}$.
- **Total Repeated-Measures SD ($\sigma_{\text{rm}}$):** $\sqrt{\sigma_b^2 + \sigma_w^2} = 24.46\text{ mg/dL}$.

### 3.2 Repeated-Measures Agreement Table (Full Cohort & Sensitivity Excluding Cluster 4)

| Analysis Set | Cohort | Paired Points ($N$) | Mean Diff ($\mu_{\text{pool}}$) | Mean Diff ($\mu_{\text{eq}}$) | $SD_{\text{between}}$ | $SD_{\text{within}}$ | $SD_{\text{rm}}$ | 95% Limits of Agreement | Pearson $r$ | Spearman $\rho$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Set B (Uncensored)** | All ($N=45$) | 629,605 | $-31.95$ | $-32.36$ | $16.25$ | $18.28$ | $24.46$ | $[-79.89, +16.00]$ | 0.8298 | 0.7452 |
| **Set B (Uncensored)** | Excl. Cluster 4 ($N=44$) | 615,550 | $-32.08$ | $-32.50$ | $16.41$ | $18.41$ | $24.66$ | $[-80.42, +16.26]$ | 0.8292 | 0.7453 |
| **Set B (Censored $\le 40, \ge 400$)** | All ($N=45$) | 618,262 | $-31.39$ | $-32.02$ | $15.97$ | $18.12$ | $24.15$ | $[-78.72, +15.94]$ | 0.8292 | 0.7437 |
| **Set B (Censored $\le 40, \ge 400$)** | Excl. Cluster 4 ($N=44$) | 604,207 | $-31.52$ | $-32.15$ | $16.13$ | $18.24$ | $24.35$ | $[-79.24, +16.21]$ | 0.8285 | 0.7410 |
| **Set A Coincident Native** | $N=40$ | 37,477 | $-30.83$ | $-31.22$ | $16.77$ | $18.76$ | $25.16$ | $[-80.14, +18.48]$ | 0.8254 | 0.7439 |
| **Set A All Libre Native** | $N=45$ | 42,045 | $-31.99$ | $-32.37$ | $16.27$ | $18.38$ | $24.55$ | $[-80.10, +16.12]$ | 0.8295 | 0.7468 |

*Difference Convention: Libre GL minus Dexcom GL (mg/dL).*

### 3.3 Bootstrap Percentile Confidence Intervals (500 Replicates)
- **Set B Pooled Mean $\mu_{\text{pool}}$ 95% CI:** $[-36.72, -26.60]\text{ mg/dL}$
- **Set B Equal Mean $\mu_{\text{eq}}$ 95% CI:** $[-37.14, -27.11]\text{ mg/dL}$
- **Set B Lower LoA 95% CI:** $[-87.69, -72.37]\text{ mg/dL}$
- **Set B Upper LoA 95% CI:** $[+6.38, +27.26]\text{ mg/dL}$
- **Set B (Excl. Cluster 4) Pooled Mean $\mu_{\text{pool}}$ 95% CI:** $[-36.87, -27.36]\text{ mg/dL}$
- **Set B (Excl. Cluster 4) Lower LoA 95% CI:** $[-88.33, -73.06]\text{ mg/dL}$
- **Set B (Excl. Cluster 4) Upper LoA 95% CI:** $[+5.79, +27.62]\text{ mg/dL}$

### 3.4 Disentangled Set A Pairing Composition
- **Coincident Native Pairs (both on native vertex):** 37,477 (5.95%)
- **Libre-Native / Dexcom-Interpolated Pairs:** 4,568 (0.73%)
- **Dexcom-Native / Libre-Interpolated Pairs:** 85,721 (13.62%)
- **Doubly-Interpolated 1-Minute Points:** 501,839 (79.71%)

### 3.5 Apparent Lag Summary
Cross-correlation analysis on continuous overlapping segments indicates an observed systematic temporal displacement where Libre leads Dexcom with a median lag of $+5.0\text{ minutes}$ (mean: $+3.42\text{ min}$, IQR: $[3.0, 7.0]\text{ min}$). In accordance with Section C4, this represents observed device disagreement across resampled signals without claiming unverified physiological, transport, or sensor-filter causation.

---

## Part 4: Candidate Tasks & Corrected Excursion Detection

### Task T1: Multi-Horizon Glucose Forecasting (Descriptive Difficulty)
Evaluated strictly at elapsed-time offsets $(t, t+h)$ within contiguous runs:
- **Dexcom G6 Pro:**
  - 30-min horizon ($N=625,098$): Mean absolute delta $13.18\text{ mg/dL}$, Median $7.60\text{ mg/dL}$, 90th percentile $32.80\text{ mg/dL}$.
  - 60-min horizon ($N=622,078$): Mean absolute delta $19.38\text{ mg/dL}$, Median $11.00\text{ mg/dL}$, 90th percentile $48.20\text{ mg/dL}$.
- **FreeStyle Libre Pro:**
  - 30-min horizon ($N=682,609$): Mean absolute delta $10.65\text{ mg/dL}$, Median $6.27\text{ mg/dL}$, 90th percentile $26.20\text{ mg/dL}$.
  - 60-min horizon ($N=679,485$): Mean absolute delta $16.85\text{ mg/dL}$, Median $9.73\text{ mg/dL}$, 90th percentile $41.67\text{ mg/dL}$.

### Task T2: Excursion Episode Prediction (Corrected Null-Reset & Hysteresis)
With the excursion persistence null-reset fix active, NaNs during entry persistence reset the counter, preventing discontinuous points from falsely triggering an episode:
- **Dexcom G6 Pro:**
  - Hyperglycemia $>140\text{ mg/dL}$: **1,303 episodes** (38 boundary-censored)
  - Hyperglycemia $>180\text{ mg/dL}$: **678 episodes** (17 boundary-censored)
  - Hypoglycemia $<70\text{ mg/dL}$: **43 episodes** (0 boundary-censored)
- **FreeStyle Libre Pro:**
  - Hyperglycemia $>140\text{ mg/dL}$: **772 episodes** (11 boundary-censored)
  - Hyperglycemia $>180\text{ mg/dL}$: **369 episodes** (7 boundary-censored)
  - Hypoglycemia $<70\text{ mg/dL}$: **494 episodes** (58 boundary-censored)
- **Dynamic Finding:** Excursion episode detection shows substantial device-dependence reflecting observed systematic trace disagreement. Dexcom detects 1,303 hyperglycemia episodes (>140) vs Libre 772. Libre detects 494 hypoglycemia episodes (<70) vs Dexcom 43.

### Task T3: Postprandial Meal Response
1,706 reconciled meal events across 45 participants provide an adequate substrate for meal response modeling.

---

## Part 5: Effective Sample Size Architecture

The hierarchical sample size architecture for Stage 2 modeling is:
- **Independent Participants ($K$):** 45
- **Contiguous Runs ($\mathcal{R}$):** 1,200
- **Non-Overlapping 2-Hour Windows:** 5,206
- **Reconciled Meal Events:** 1,706
- **Paired Coincident Native Observations (Set A):** 37,477
- **Total Libre Native Observations:** 42,045
- **Dexcom Hyperglycemia Episodes ($>180\text{ mg/dL}$):** 678
- **Dexcom Hypoglycemia Episodes ($<70\text{ mg/dL}$):** 43

---

## Part 6: Modeling Readiness Decisions & Governance

1. **Primary Forecasting Target:** **Dexcom G6 Pro** is selected as the primary forecasting target due to its 3x higher native sampling density (5-min vs 15-min) and lower empirical lag.
2. **Cross-Device Sensitivity Requirement:** All predictive models developed in Stage 2 must include a mandatory re-evaluation on FreeStyle Libre Pro.
3. **Causal Real-Time Limitation:** Intervening 1-minute points are linearly interpolated from 5-min or 15-min endpoints. Real-time causal models cannot evaluate at arbitrary 1-minute steps without future leakage; model inputs and forecast horizons must strictly align to native sampling lattices.
4. **Validation Strategy:** In accordance with clinical machine learning standards, models must use participant-level grouped cross-validation (`StratifiedGroupKFold`) grouped by participant cluster, forbidding cross-participant leakage.
5. **Governance Status:** Stage 1B-R3 is complete and verified against 85 automated unit and regression tests. **Status remains CORRECTED REVISION — PENDING INDEPENDENT REVIEW.** Stage 2 modeling will commence only upon independent review acceptance.

---

## Part 7: Finding-to-Test Traceability Matrix

The following table provides exhaustive traceability between every code defect or methodological issue identified during independent review, its production resolution in `src/dtwin/`, the corresponding automated regression test in `tests/`, and the verification outcome:

| Defect / Review Finding Area | Production Location | Automated Regression Test | Verification Command & Outcome |
| :--- | :--- | :--- | :--- |
| **1. DatetimeIndex & Series Handling**<br>Ensure `compute_elapsed_minutes` accepts both `pd.DatetimeIndex` and `pd.Series` seamlessly. | `src/dtwin/timeaxis.py`<br>(`compute_elapsed_minutes`) | `tests/test_stage1b_r3_regressions.py`<br>`::test_r3_1_compute_elapsed_minutes_datetimeindex_and_series` | `pytest tests/test_stage1b_r3_regressions.py`<br>**PASSED** (Exit Code 0) |
| **2. Window Timestamps & Index Alignment**<br>Eliminate off-by-one errors in `enumerate_windows()`; supply explicit `start_time`, `origin_time`, `target_time`, `start_index`, `origin_index`, `target_index`. | `src/dtwin/timeaxis.py`<br>(`enumerate_windows`) | `tests/test_stage1b_r3_regressions.py`<br>`::test_reproduce_r3_window_timestamps_and_indices` | `pytest tests/test_stage1b_r3_regressions.py`<br>**PASSED** (Exit Code 0) |
| **3. Offset Pairing Gap & Null Exclusion**<br>Explicitly track and account for missing endpoints, intermediate nulls, and gap-spanning pairs in `pairs_at_offset()`. | `src/dtwin/analysis/dual_sensor.py`<br>(`pairs_at_offset`) | `tests/test_stage1b_r3_regressions.py`<br>`::test_r3_1_pairs_at_offset_exclusion_accounting` | `pytest tests/test_stage1b_r3_regressions.py`<br>**PASSED** (Exit Code 0) |
| **4. Timestamp Monotonicity & No Gap Bridging**<br>Ensure strict 100% timestamp monotonicity across all files and strictly forbid `.dropna()` followed by positional slicing. | `src/dtwin/timeaxis.py`<br>(`enumerate_runs`)<br>`src/dtwin/analysis/run_stage1b.py` | `tests/test_stage1b_r2_regressions.py`<br>`::test_reproduce_c1_gap_breaks_index_based_lattice`<br>`tests/test_stage1b_r2_regressions.py`<br>`::test_lint_forbid_dropna_positional_slicing_in_analysis`<br>`tests/test_stage1b_r3_regressions.py`<br>`::test_reproduce_r3_file_by_file_row_counts_reconciliation` | `pytest tests/test_stage1b_r2_regressions.py`<br>`pytest tests/test_stage1b_r3_regressions.py`<br>**PASSED** (Exit Code 0) |
| **5. Excursion Null Resets & Boundary Censoring**<br>Ensure NaNs during entry persistence reset `active_len = 0`; NaNs during active episode reset `release_len = 0`; track left/right boundary censoring. | `src/dtwin/timeaxis.py`<br>(`detect_excursion_episodes_run_bounded`) | `tests/test_stage1b_r3_regressions.py`<br>`::test_reproduce_r3_excursion_persistence_null_reset`<br>`tests/test_stage1b_r3_regressions.py`<br>`::test_reproduce_r3_excursion_duration_and_censoring`<br>`tests/test_stage1b_r3_regressions.py`<br>`::test_r3_2_excursion_episodes_behavioral_null_and_censoring` | `pytest tests/test_stage1b_r3_regressions.py`<br>**PASSED** (Exit Code 0) |
| **6. Lag Sign Convention & Autoregressive Validation**<br>Verify $\tau > 0$ denotes Libre leads Dexcom; validate on non-periodic multi-frequency AR signals with NaNs and unequal overlap; remove causal claims. | `src/dtwin/analysis/dual_sensor.py`<br>(`calculate_apparent_lag`) | `tests/test_stage1b_r2_regressions.py`<br>`::test_reproduce_c4_lag_sign_convention_verification`<br>`tests/test_stage1b_r3_regressions.py`<br>`::test_r3_1_lag_synthetic_positive_and_negative_shift`<br>`tests/test_stage1b_r3_regressions.py`<br>`::test_r3_2_lag_synthetic_non_periodic_autoregressive_with_nans_and_unequal_overlap`<br>`tests/test_stage1b_r3_regressions.py`<br>`::test_reproduce_r3_lag_language_no_causal_claims` | `pytest tests/test_stage1b_r2_regressions.py`<br>`pytest tests/test_stage1b_r3_regressions.py`<br>**PASSED** (Exit Code 0) |
| **7. Sensor Restart Phase Shifts & Time Semantics T6**<br>Resolve Participant Cluster 23 inter-session clock phase shift without speculating physical sensor replacement; evaluate runs dynamically. | `src/dtwin/analysis/native_grid.py`<br>`src/dtwin/timeaxis.py` | `tests/test_stage1b_r3_regressions.py`<br>`::test_reproduce_r3_dexcom_participant_session_phase_shift` | `pytest tests/test_stage1b_r3_regressions.py`<br>**PASSED** (Exit Code 0) |
| **8. Wilson CIs, Duration Coverage & Strict Privacy**<br>Correct Wilson CI for 1/100 false confident classification ($[0.0018, 0.0545]$ vs $[0.9455, 0.9982]$); verify 99.35% Dexcom data coverage across 45 participants; strict fail-loud privacy. | `src/dtwin/analysis/native_grid.py`<br>(`wilson_score_interval`)<br>`src/dtwin/analysis/run_stage1b.py` | `tests/test_stage1b_r3_regressions.py`<br>`::test_reproduce_r3_cohort_wilson_score_interval`<br>`tests/test_stage1b_r3_regressions.py`<br>`::test_r3_3_reconciliation_verifications`<br>`tests/test_stage1b_r3_regressions.py`<br>`::test_r3_1_anonymous_file_by_file_row_counts_privacy` | `pytest tests/test_stage1b_r3_regressions.py`<br>**PASSED** (Exit Code 0) |

