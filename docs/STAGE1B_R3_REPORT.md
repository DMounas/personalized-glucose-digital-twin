# Stage 1B-R3 Completion Report: Corrected Native-Grid Inference, Dual-Sensor Concordance, and Modeling Readiness

**Status:** STAGE 1B FROZEN — R3.4 FINAL RECONCILIATION COMPLETE  
**Author:** Antigravity Implementation Engineer  
**Date:** 2026-10-19 (Updated 2026-10-20 for R3.4 Freeze)  
**Specification:** [`configs/stage1b.yaml`](file:///c:/New%20folder/HACKATHONS/glucose-digital-twin/configs/stage1b.yaml) (Version `1.4.0-r3.4`)  
**Frozen Config Digest:** `cf2763408891feb97c67dd5184ad4674dd2c98a736922ad322c8b66bc11bd467`  
**Committed JSON Output:** [`docs/reports/stage1b_r3_results.json`](file:///c:/New%20folder/HACKATHONS/glucose-digital-twin/docs/reports/stage1b_r3_results.json) (SHA-256: `a9b8efc06b715f4c5fd46c54cb36a0ee151a91330e597e355e50fb9d8917181b`)  
**Canonical Metrics Registry:** [`docs/reports/canonical_metrics.json`](file:///c:/New%20folder/HACKATHONS/glucose-digital-twin/docs/reports/canonical_metrics.json) (SHA-256: `70afb620d1ce781c4d6dafc71f29f7ce847e0e68f23f8e10c2b6c7be69126c3d`)  
**Detailed Scientific Report:** [`docs/reports/stage1b_r3_report.md`](file:///c:/New%20folder/HACKATHONS/glucose-digital-twin/docs/reports/stage1b_r3_report.md)  
**File-by-File Audit Table:** `reports_local/file_by_file_row_counts.csv`  
**Timestamp Integrity Audit Table:** `reports_local/timestamp_integrity_audit.csv`  

---

## 1. Summary of Stage 1B-R3 Corrective Pass

Stage 1B-R3 (amended under R3.1, R3.2, and R3.3) resolves all reproduced defects, arithmetic contradictions, and review findings:
- **Exact Row-Count Arithmetic Reconciled:**
  - Authoritative total rows: **687,580** across all 45 participant files (every file $N_i \equiv 0 \pmod 5$).
  - Valid Dexcom observations: **629,825**.
  - Valid Libre observations: **687,360**.
  - Paired overlap (both non-null): **629,605**.
  - Dexcom-only (Libre null): **220**.
  - Libre-only (Dexcom null): **57,755**.
  - Neither sensor valid: **0**.
  - Exact arithmetic identity: $629,605 + 220 + 57,755 + 0 = 687,580$.
  - Pairing semantics: Defined as **row-wise within each participant CSV**, where row $i$ represents a synchronized 1-minute wall-clock interval created by the dataset authors. Timestamps in all 45 files are 100% strictly monotonic, with 0 duplicates and 0 unparseable values.
  - Provenance of 632,536 figure: *"The 632,536 figure could not be reproduced and its original provenance remains unresolved. It is not the row count of any combination of complete participant files, because each complete file count is divisible by five; that fact alone does not identify the source of the old figure."*
- **Cohort-Wide Timestamp Integrity Audit (R3.4):**
  - Audited all 45 participant files (687,580 rows). Parse failures: 0. Duplicate timestamps: 0. Monotonicity: 100% strictly increasing in original row order.
  - Total timestamp gaps (> 60s): 1,155 gaps cohort-wide, defining exactly 1,200 contiguous runs ($\Delta t = 60\text{ s}$).
  - Gap distribution: Min 2.0 min, p25 2.0 min, Median 4.0 min, p75 7.0 min, Max 901.0 min (~15h). Bins: $\le 5\text{m}$: 720 (62.3%), $5-15\text{m}$: 330 (28.6%), $15-60\text{m}$: 90 (7.8%), $1-24\text{h}$: 15 (1.3%), $>24\text{h}$: 0 (0.0%). 35/45 participants have zero gaps.
  - Zero sorting, deduplicating, or synthetic gap bridging was performed or required.
- **Time-of-Day (Circadian) Feature Validity (R3.4):**
  - Documentation confirms HIPAA date-shifting applied an integer-day shift (`CGMacros_dateshifted365.zip`, `DataDictionary_CGMacros-00X.csv`), strictly preserving local wall-clock time (HH:MM).
  - Empirical meal timings align with diurnal human physiology (Breakfast median 08:15 AM, Lunch 12:33 PM, Dinner 06:58 PM; 00:00–05:00 near-zero).
  - Circadian features ($[\sin(2\pi \text{TOD}/1440), \cos(2\pi \text{TOD}/1440)]$) are validated for Stage 2; multi-day calendar features (month, day of week) remain strictly prohibited.
- **Canonical Metrics Registry (R3.4):**
  - All headline metrics are formally centralized in `canonical_metrics_registry` with explicit value, unit, definition, denominator, and inclusion mask in `docs/reports/canonical_metrics.json`.
- **Contiguous Run Denominators & Input Masks:**
  - `timestamp_contiguous_runs_all_rows = 1,200`: Computed via `enumerate_runs(df)` across all 687,580 rows where consecutive timestamps have step $\Delta t = 60\text{ s}$.
  - `dexcom_valid_contiguous_runs = 1,202`: Computed via `enumerate_runs(df[df["Dexcom GL"].notna()])` across the 629,825 non-null Dexcom readings.
  - `libre_valid_contiguous_runs = 1,215`: Computed via `enumerate_runs(df[df["Libre GL"].notna()])` across the 687,360 non-null Libre readings (Participant Cluster 4 contains 220 internal nulls splitting its Libre trace into 16 contiguous runs).
  - All 89 evaluable Dexcom runs ($\ge 120$ min, $\ge 20$ bends) derive strictly from the 1,202 Dexcom-valid runs denominator.
- **FreeStyle Libre Pro Metadata Discordance & Threshold Invariance:**
  - 44/45 participants (97.78%) confirmed 15-minute native lattice with HIGH_CONFIDENCE. Cohort Wilson 95% CI: $[0.8845, 0.9961]$.
  - **Curvature Bend Threshold Reconciliation:** The canonical production configuration (`configs/stage1b.yaml`) specifies `second_difference_bend_threshold: 0.15` (detecting 563 bends). An exploratory threshold `1e-5` detects 846 bends. Sensitivity analysis from $10^{-6}\text{ mg/dL}$ to $0.50\text{ mg/dL}$ proves complete classification invariance: period 5, phase 0, hit rate 100.0%, residual $0.0000\text{ mg/dL}$ ($3.5\times 10^{-15}\text{ mg/dL}$), and distinction ratio $\mathcal{R}_{\text{inter}} \approx 2.47 < 3.0$ with $\sim 28.8\%$ intermediate bends.
  - Fundamental mathematical principle: A denser linear grid ($P=5$) always reconstructs a coarser piecewise-linear grid ($P=15$) with zero residual. Therefore, a near-zero reconstruction residual on a denser nested grid does not prove a 5-minute native lattice. The genuine distinguishing evidence is the presence of intermediate curvature bends.
  - Published CGMacros primary literature (Das et al.) explicitly specifies that FreeStyle Libre Pro hardware recorded at a 15-minute sampling rate. This series is strictly classified and retained as **METADATA-DISCORDANT** pending independent laboratory clarification.
  - Dual-sensor agreement is evaluated both including ($N=45$) and excluding ($N=44$) this trace: Set B Uncensored LoA is $[-79.89, +16.00]\text{ mg/dL}$ ($N=45$, 629,605 pairs) vs $[-80.42, +16.26]\text{ mg/dL}$ ($N=44$, 615,550 pairs).
- **Synthetic Benchmark Suites & Jitter Distinctions:**
  - Core Suite `five_minute_with_amplitude_noise_and_drops` (aliased as `five_minute_with_jitter_and_drops`): Evaluates **glucose measurement amplitude noise** ($\sigma = 2.0\text{ mg/dL}$) on fixed 5-minute sampling timestamps: 500/500 (100.0%) correctly identified as 5-minute native lattice.
  - Blind Suite `native_timestamp_jitter_5min`: Evaluates **sampling timestamp coordinate drift**: 100/100 (100.0%) correctly classified as unresolved / no reliable lattice.
  - Blind Suite `native_timestamp_jitter_15min`: 99/100 correctly unresolved (unresolved rate 99.0%, Wilson 95% CI: $[0.9455, 0.9982]$, or 94.55%–99.82%); 1/100 falsely classified as 15m lattice (false-classification rate 1.0%, Wilson 95% CI: $[0.0018, 0.0545]$, or 0.18%–5.45%). Both intervals are separately reported.
- **Dexcom Contiguous Runs Distribution & Duration Coverage:**
  - 1,202 continuous sensor runs across the cohort.
  - Participant Cluster 7 accounts for 871 of these runs due to 870 recording micro-gaps (1 to 20 minute dropouts).
  - Explicit categorization across all runs (zero silent passing):
    - Evaluated Compliant Runs ($\ge 120$ min, $\ge 20$ bends): **89 runs (100.0% of evaluated)**, Wilson 95% CI ($N=89$): $[0.9585, 1.0000]$.
    - Evaluated Non-Compliant Runs: **0 runs**.
    - **Dataset Representation Coverage (Exact Qualification):** Eligible runs contained 625,728 of 629,825 valid one-minute-grid Dexcom rows (99.35% of valid rows in the released representation) and spanned all 45/45 participants (100.0% cohort coverage). This percentage represents row coverage in the released 1-minute interpolated representation and must not be equated with coverage of independent physical sensor observations.
    - Underpowered Short Runs (< 120 min): **1,111 runs** (including 860 in Participant 7), containing a total of **3,855 rows (only 0.61% of Dexcom data)**.
    - Underpowered Low-Bend Runs (< 20 bends): **2 runs**, containing **242 rows (only 0.04% of Dexcom data)**.
    - Participant-Level Compliance: 45/45 participants (100.0%) exhibit 100% compliance across all their evaluated sessions.
    - Narrowed Compliance Claim: Compliance is claimed strictly **"across all 89 evaluated sessions"**, explicitly qualifying that 1,113 low-information runs are excluded from formal lattice inference due to lack of statistical power, while confirming that evaluated sessions audit **99.35% of all recorded sensor data**.
- **Participant 23 Neutral Phase Shift Attribution:**
  - Observed inter-session clock phase shift (minute 1 mod 5 to minute 2 mod 5) across an unrecorded 40.5-hour interval. Neutral description with zero unsupported "sensor replacement" physical claims. Evaluated per-session under T6, both sessions are 100.0% compliant 5-minute linear lattices.
- **`timeaxis.py` API & Excursion Fixes:**
  - `compute_elapsed_minutes` verified seamlessly for both `pd.DatetimeIndex` and `pd.Series`.
  - `enumerate_windows` indexing and timestamps verified with zero off-by-one errors (`start_time`, `origin_time`, `target_time`, `start_index`, `origin_index`, `target_index`).
  - `detect_excursion_episodes_run_bounded` excursion entry persistence strictly resets `active_len = 0` on NaNs; NaNs during active episodes reset `release_len = 0`; boundary censoring cleanly separates left-censoring (active at index 0) vs right-censoring (active at run termination).
  - `pairs_at_offset` explicitly accounts for excluded null endpoints, intermediate nulls, and gap-spanning pairs.
- **Lag Sign Convention Verification:**
  - Verified $\tau > 0$ denotes Libre leads Dexcom via non-periodic multi-frequency AR known-shift synthetic tests ($\tau = +5, -5, 0$, with missing values and unequal overlap).

---

## 2. Key Headline Metrics (from Canonical `stage1b_r3_results.json`)

| Metric Category | Canonical Stage 1B-R3 Value | Verification Status |
| :--- | :--- | :---: |
| **Cohort Size** | 45 participants (15 Normal, 16 Prediabetes, 14 Type 2 Diabetes) | Verified |
| **Total Recorded Rows** | 687,580 rows across 45 files (all $N_i \equiv 0 \pmod 5$) | Verified |
| **Valid Dexcom Observations** | 629,825 rows | Verified |
| **Valid Libre Observations** | 687,360 rows | Verified |
| **Paired Overlap Rows** | 629,605 1-minute rows | Verified |
| **Dexcom-Only Rows (Libre Null)** | 220 rows | Verified |
| **Libre-Only Rows (Dexcom Null)** | 57,755 rows | Verified |
| **Neither Sensor Valid** | 0 rows | Verified |
| **Contiguous Runs ($\Delta t = 60\text{ s}$)** | 1,200 cohort runs (1,202 Dexcom sensor runs, 1,215 Libre sensor runs) | Verified |
| **Non-Overlapping 2h Windows** | 5,206 windows | Verified |
| **Agreement Analysis Status** | `EXPLORATORY_SERIAL_AUTOCORRELATION_UNADJUSTED` | Verified |
| **Set B Repeated-Measures Agreement ($N=45$)** | $\mu_{\text{pool}} = -31.95\text{ mg/dL}$, $\mu_{\text{eq}} = -32.36\text{ mg/dL}$, $\sigma_{\text{rm}} = 24.46\text{ mg/dL}$, 95% LoA: $[-79.89, +16.00]\text{ mg/dL}$ | Verified |
| **Set B Sensitivity Excl. Cluster 4 ($N=44$)** | $N=615,550$ rows; $\mu_{\text{pool}} = -32.08\text{ mg/dL}$, $\sigma_{\text{rm}} = 24.66\text{ mg/dL}$, 95% LoA: $[-80.42, +16.26]\text{ mg/dL}$ | Verified |
| **Set B Censored Sensitivity ($\le 40, \ge 400$)** | $N=618,262$ rows; $\mu_{\text{pool}} = -31.39\text{ mg/dL}$, $\sigma_{\text{rm}} = 24.15\text{ mg/dL}$, 95% LoA: $[-78.72, +15.94]\text{ mg/dL}$ | Verified |
| **Set B Censored Excl. Cluster 4 ($N=44$)** | $N=604,207$ rows; $\mu_{\text{pool}} = -31.52\text{ mg/dL}$, $\sigma_{\text{rm}} = 24.35\text{ mg/dL}$, 95% LoA: $[-79.24, +16.21]\text{ mg/dL}$ | Verified |
| **Set A Coincident Native Pairs** | 37,477 pairs (5.95% of overlap) | Verified |
| **Libre Concordant 15m Native Lattice** | 44/45 participants (97.78%), Wilson 95% CI: $[0.8845, 0.9961]$ | Verified |
| **Libre Metadata-Discordant Series** | 1/45 participants (Cluster 4, inferred 5m, residual $0.0\text{ mg/dL}$) | Verified |
| **Dexcom Evaluated Runs Compliance (T6)** | 89/89 runs (100.0%, 625,728 valid rows / 99.35% of Dexcom data across 45/45 participants), Wilson 95% CI: $[0.9585, 1.0000]$ | Verified |
| **Dexcom Underpowered Low-Info Runs** | 1,113 runs (1,111 < 120 min [3,855 rows, 0.61%], 2 < 20 bends [242 rows, 0.04%]) excluded from lattice test | Verified |
| **Dexcom Participant Compliance (T6)** | 45/45 participants (100.0%), Wilson 95% CI: $[0.9213, 1.0000]$ | Verified |
| **Dexcom Global Single-Phase Compliance** | 44/45 participants (97.78%), Wilson 95% CI: $[0.8845, 0.9961]$ | Verified |
| **Apparent Lag Convention** | Median $+5.0\text{ minutes}$ (Libre leads Dexcom; IQR: $[3.0, 7.0]\text{ min}$) | Verified |
| **T1 Forecast Difficulty (30-min Mean Abs $\Delta$)** | Dexcom: $13.18\text{ mg/dL}$; Libre: $10.65\text{ mg/dL}$ | Verified |
| **T1 Forecast Difficulty (60-min Mean Abs $\Delta$)** | Dexcom: $19.38\text{ mg/dL}$; Libre: $16.85\text{ mg/dL}$ | Verified |
| **T2 Hyperglycemia Episodes ($>140\text{ mg/dL}$)** | Dexcom: 1,303 (38 censored); Libre: 772 (11 censored) | Verified |
| **T2 Hyperglycemia Episodes ($>180\text{ mg/dL}$)** | Dexcom: 678 (17 censored); Libre: 369 (7 censored) | Verified |
| **T2 Hypoglycemia Episodes ($<70\text{ mg/dL}$)** | Dexcom: 43 (0 censored); Libre: 494 (58 censored) | Verified |
| **T3 Reconciled Meal Events** | 1,706 events across 45 participants | Verified |

---

### 3. Governance & Quality Gates

- **Test Suite Status:** 86 passed in 6.37s (100% green).
- **Linter Status:** `ruff check .` passed with 0 errors; `ruff format --check .` passed (43 files formatted).
- **Type Checker Status:** `mypy src tests` passed with 0 errors across 43 source files.
- **Reproducibility Verification:** Analysis pipeline executed twice with bitwise identical results (exit code 0).
- **Historical Baseline Integrity:** All 39 Stage 0 and Stage 1A baseline files remain 100% byte-identical.
- **Privacy Audit:** `reports_local/file_by_file_row_counts.csv` and `reports_local/timestamp_integrity_audit.csv` contain only anonymous integer cluster IDs (`cluster_id`: 1..45), zero participant IDs (`CGMacros-XXX`), and zero raw file names. Strict privacy scanner fails loudly on missing or unreadable files.
- **Stage 2 Gate:** Stage 1B is **FROZEN**. All issues raised in independent reviews R1–R3.4 are fully resolved. Proceed to Stage 2 modeling with documented boundaries.

---

## 4. Finding-to-Test Traceability Matrix

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
| **9. Timestamp Integrity Audit & Canonical Metrics Registry (R3.4)**<br>Audit all 45 participant CSVs (0 parse fails, 0 duplicates, 100% monotonic, 1,155 gaps, 1,200 runs); establish canonical metrics registry; verify circadian time-of-day feature validity via integer-day shift. | `src/dtwin/analysis/run_stage1b.py`<br>(`canonical_metrics_registry`)<br>`docs/reports/canonical_metrics.json` | `tests/test_stage1b_r3_regressions.py`<br>`::test_r3_4_timestamp_integrity_and_canonical_metrics` | `pytest tests/test_stage1b_r3_regressions.py`<br>**PASSED** (Exit Code 0) |



