# Formal Erratum Notice: Stage 1B Analysis Corrections (Stage 1B-R2 & Stage 1B-R3)

**Publication Date:** 2026-10-19  
**Status:** CORRECTED REVISION — PENDING INDEPENDENT REVIEW  
**Supersedes in Part:** `docs/STAGE1B_REPORT.md` and `docs/reports/stage1b_report.md`  
**Related Audit:** [`docs/errata/STAGE1B_CORRECTION_AUDIT_2026-10-19.md`](file:///c:/New%20folder/HACKATHONS/glucose-digital-twin/docs/errata/STAGE1B_CORRECTION_AUDIT_2026-10-19.md)  
**Frozen Config Digest:** `1f91445a8b9c3dd8fb6e37ce66e369f13940347f4f7f9fa63d5090af50464c59` (Version `1.3.0-r3.3`)

---

## 1. Executive Summary & Retraction Statement

A rigorous code audit of the initial Stage 1B release identified six methodological defects in time series handling, variance estimation, and pairing logic. While the primary strategic recommendation—selecting Dexcom G6 Pro as the primary target for predictive modeling due to its higher native sampling rate and lower temporal lag—remains scientifically sound, several headline statistics and methodological claims in the initial Stage 1B reports are formally retracted and superseded by the corrected values in Stage 1B-R2.

### Retracted Claims:
1. **Set A Native Pairing Composition:** The prior report asserted that all 37,030 paired observations in Set A represented "simultaneous native measurements." In reality, FreeStyle Libre Pro samples every 15 minutes while Dexcom G6 Pro samples every 5 minutes. True coincident native pairing requires alignment of both sampling phases ($\phi_L \equiv \phi_D \pmod 5$). In Stage 1B-R2, Set A is formally partitioned into:
   - **Coincident Native Pairs:** 37,477 pairs (both sensors at native sampling instants).
   - **Libre-Native / Dexcom-Interpolated Pairs:** 4,568 pairs (Libre native, Dexcom interpolated).
   - **Total Libre-Native Pairs:** 42,045 pairs across all 45 participants.
2. **Repeated-Measures ANOVA Formulation:** The previous between-subject variance component $\sigma_b^2$ was computed as the naive sample variance of participant means, neglecting the unbalanced sample sizes ($n_i$) per participant. Stage 1B-R2 applies the standard one-way random-effects ANOVA with Bland-Altman (1999, 2007) $n_0$ correction ($n_0 = 13,988.59$), explicitly reporting both the pooled grand mean ($\mu_{\text{pool}}$) and equal-weighted subject mean ($\mu_{\text{eq}}$).
3. **Gap-Bridging in Forecast Difficulty & Deltas:** The exploratory scripts and preliminary task functions used `.dropna()` followed by positional slicing `s[h:] - s[:-h]`. Across participant session breaks and missing data gaps (some exceeding 15 hours), this erroneously paired points across gaps as if they were 30 or 60 minutes apart. Stage 1B-R2 enforces strict elapsed-time pairing $(t, t+h)$ within contiguous runs ($\Delta t = 60\text{ s}$).
4. **Excursion Episode Bridging & Hysteresis:** Prior excursion episode counting merged hyper- and hypoglycemic events across absent sensor gaps and lacked hysteresis release margins. Stage 1B-R2 enforces run-bounded episode detection, requiring a $5\text{ mg/dL}$ hysteresis margin, 10-minute sustained release, and explicit tracking of boundary-censored episodes.
5. **Lag Convention & Physiological Causation Claims:** The prior reporting inverted the sign convention of the cross-correlation lag and made speculative physiological claims regarding subcutaneous transport and enzyme kinetics. Stage 1B-R2 establishes the verified convention (positive lag indicates Libre leads Dexcom; median $+5.0\text{ min}$) and restricts interpretation to observed mathematical disagreement across resampled time series without unverified biological attribution.
6. **Window Enumeration Without Gap Accounting:** Prior estimates of non-overlapping 2-hour windows simply divided total row counts by 120 ($687,580 / 120 = 5,729$). Stage 1B-R2 enforces deterministic enumeration strictly within contiguous runs of $\ge 120$ continuous minutes, yielding exactly 5,206 valid windows.

---

## 2. Quantitative Old-vs-New Traceability Matrix

The following table provides exhaustive numerical traceability between initial Stage 1B metrics and corrected Stage 1B-R2 metrics:

| Metric Category | Specific Estimand | Old Stage 1B Value | Stage 1B-R2 Corrected | Absolute Difference | Methodological Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Agreement (Set B)** | Grand Mean Difference ($\mu_{\text{pool}}$) | $-31.95\text{ mg/dL}$ | **$-31.95\text{ mg/dL}$** | $0.00\text{ mg/dL}$ | Pooled weighted difference $\sum d_{ij} / N$. |
| **Agreement (Set B)** | Equal-Weighted Mean ($\mu_{\text{eq}}$) | *Not Reported* | **$-32.36\text{ mg/dL}$** | N/A | Unweighted participant mean $\sum \bar{d}_i / K$. |
| **Agreement (Set B)** | $SD_{\text{between}}$ ($\sigma_b$) | $16.42\text{ mg/dL}$ | **$16.25\text{ mg/dL}$** | $-0.17\text{ mg/dL}$ | Corrected using ANOVA $n_0$ multiplier ($n_0=13,988.59$). |
| **Agreement (Set B)** | $SD_{\text{within}}$ ($\sigma_w$) | $18.30\text{ mg/dL}$ | **$18.28\text{ mg/dL}$** | $-0.02\text{ mg/dL}$ | Calculated via Mean Squares Within ($MSW$). |
| **Agreement (Set B)** | $SD_{\text{repeated\_measures}}$ ($\sigma_{\text{rm}}$) | $24.59\text{ mg/dL}$ | **$24.46\text{ mg/dL}$** | $-0.13\text{ mg/dL}$ | $\sqrt{\sigma_b^2 + \sigma_w^2}$ under unbalanced ANOVA. |
| **Agreement (Set B)** | Lower Limit of Agreement (95%) | $-80.14\text{ mg/dL}$ | **$-79.89\text{ mg/dL}$** | $+0.25\text{ mg/dL}$ | $\mu_{\text{pool}} - 1.96 \cdot \sigma_{\text{rm}}$. |
| **Agreement (Set B)** | Upper Limit of Agreement (95%) | $+16.24\text{ mg/dL}$ | **$+16.00\text{ mg/dL}$** | $-0.24\text{ mg/dL}$ | $\mu_{\text{pool}} + 1.96 \cdot \sigma_{\text{rm}}$. |
| **Agreement (Set B)** | 95% Bootstrap Mean CI | $[-37.14, -27.11]$ | **$[-36.72, -26.60]$** | Shifted | Clustered bootstrap recalculating full ANOVA estimator. |
| **Agreement (Set B)** | 95% Bootstrap Lower LoA CI | $[-88.43, -73.10]$ | **$[-87.69, -72.37]$** | Shifted | Clustered bootstrap recalculating full ANOVA estimator. |
| **Agreement (Set B)** | 95% Bootstrap Upper LoA CI | $[+6.32, +27.18]$ | **$[+6.38, +27.26]$** | Shifted | Clustered bootstrap recalculating full ANOVA estimator. |
| **Censored Sensitivity** | Censored Set B Paired Points | *Not Analyzed* | **$618,262$** | $-11,343$ pts | Excludes sensor saturation limits ($\le 40, \ge 400\text{ mg/dL}$). |
| **Censored Sensitivity** | Censored Grand Mean ($\mu_{\text{pool}}$) | *Not Analyzed* | **$-31.39\text{ mg/dL}$** | $+0.56\text{ mg/dL}$ | Removes saturation boundary clipping effects. |
| **Censored Sensitivity** | Censored $SD_{\text{repeated\_measures}}$ | *Not Analyzed* | **$24.15\text{ mg/dL}$** | $-0.31\text{ mg/dL}$ | Confirms robust agreement outside saturation margins. |
| **Pairing Sets** | Coincident Native Pairs | $37,030$ | **$37,477$** | $+447$ pts | Both Libre (15m) and Dexcom (5m) at native lattice. |
| **Pairing Sets** | Libre-Native / Dex-Interp Pairs | *Not Partitioned* | **$4,568$** | N/A | Libre at 15m native; Dexcom linearly interpolated. |
| **Pairing Sets** | Dex-Native / Libre-Interp Pairs | *Not Partitioned* | **$85,721$** | N/A | Dexcom at 5m native; Libre linearly interpolated. |
| **Pairing Sets** | Both Interpolated 1-min Points | *Not Partitioned* | **$501,839$** | N/A | 1-minute intervening linear interpolation points. |
| **Forecast Diff. (T1)** | Dexcom 30-min Mean Abs $\Delta$ | $13.21\text{ mg/dL}$ | **$13.18\text{ mg/dL}$** | $-0.03\text{ mg/dL}$ | Run-bounded pairing eliminates cross-gap false deltas. |
| **Forecast Diff. (T1)** | Dexcom 60-min Mean Abs $\Delta$ | $19.41\text{ mg/dL}$ | **$19.38\text{ mg/dL}$** | $-0.03\text{ mg/dL}$ | Run-bounded pairing eliminates cross-gap false deltas. |
| **Forecast Diff. (T1)** | Libre 30-min Mean Abs $\Delta$ | $10.67\text{ mg/dL}$ | **$10.65\text{ mg/dL}$** | $-0.02\text{ mg/dL}$ | Run-bounded pairing eliminates cross-gap false deltas. |
| **Forecast Diff. (T1)** | Libre 60-min Mean Abs $\Delta$ | $16.87\text{ mg/dL}$ | **$16.85\text{ mg/dL}$** | $-0.02\text{ mg/dL}$ | Run-bounded pairing eliminates cross-gap false deltas. |
| **Excursions (T2)** | Dexcom Hyper $>140\text{ mg/dL}$ | $1,228$ | **$1,314$** (49 cens.) | $+86$ episodes | Run-bounded detection with $5\text{ mg/dL}$ hysteresis. |
| **Excursions (T2)** | Dexcom Hyper $>180\text{ mg/dL}$ | $654$ | **$683$** (21 cens.) | $+29$ episodes | Run-bounded detection with $5\text{ mg/dL}$ hysteresis. |
| **Excursions (T2)** | Dexcom Hypo $<70\text{ mg/dL}$ | $41$ | **$43$** (0 cens.) | $+2$ episodes | Run-bounded detection with $5\text{ mg/dL}$ hysteresis. |
| **Excursions (T2)** | Libre Hyper $>140\text{ mg/dL}$ | $779$ | **$772$** (11 cens.) | $-7$ episodes | Run-bounded detection with $5\text{ mg/dL}$ hysteresis. |
| **Excursions (T2)** | Libre Hyper $>180\text{ mg/dL}$ | $369$ | **$369$** (7 cens.) | $0$ episodes | Run-bounded detection with $5\text{ mg/dL}$ hysteresis. |
| **Excursions (T2)** | Libre Hypo $<70\text{ mg/dL}$ | $498$ | **$494$** (58 cens.) | $-4$ episodes | Run-bounded detection with $5\text{ mg/dL}$ hysteresis. |
| **Sample Size** | Contiguous Runs ($\Delta t = 60\text{ s}$) | *Not Enumerated* | **$1,200$ runs** | N/A | Fundamental unit of valid temporal analysis. |
| **Sample Size** | Non-overlapping 2h Windows | $5,729$ | **$5,206$ windows** | $-523$ windows | Windows strictly bounded within runs of $\ge 120\text{ min}$. |
| **Apparent Lag** | Cross-correlation Peak | $-4.0\text{ min}$ (inverted) | **$+5.0\text{ min}$** | Sign fixed | Positive lag indicates Libre leads Dexcom. |

---

## 3. Root Cause Analysis of Specific Defects

1. **Unbalanced ANOVA Variance Components:**
   In unbalanced repeated measures where participant $i$ contributes $n_i$ pairs, the effective sample size per cluster is $n_0 = \frac{1}{K-1} \left( N - \frac{\sum n_i^2}{N} \right)$. In CGMacros, $N = 629,605$, $K = 45$, and $n_i$ ranges from 5,099 to 18,720. Calculating $s_b^2$ simply as the sample variance of the 45 participant means overestimated between-subject variance because each mean has sampling variance $\sigma_w^2 / n_i$. Correcting for $n_0$ yielded $SD_{\text{between}} = 16.25\text{ mg/dL}$ instead of $16.42\text{ mg/dL}$, adjusting the limits of agreement accordingly.

2. **Positional Slicing Across Session Breaks:**
   CGMacros time series contain unrecorded overnight and multi-day breaks where sensor recording halted. Positional slicing on `.dropna()` arrays assumed every row increment represented exactly 1 minute. Slicing row index $k$ against $k+30$ across a 15-hour session gap calculated a 15-hour delta as a 30-minute delta. While only ~0.8% of row pairs spanned such gaps, this violated fundamental time semantics. Enforcing `pairs_at_offset` strictly within runs corrected this flaw.

3. **Lattice Modulo Drift from Absent Gaps:**
   When evaluating candidate native sampling lattices via `(np.arange(n) % 15) == phase`, any absent data gap of duration $g$ minutes where $g \not\equiv 0 \pmod{15}$ caused the modulo grid to drift relative to true elapsed time. Furthermore, taking second differences across concatenated segments generated artificial bend spikes at gap boundaries. Stage 1B-R2 computes second differences strictly intra-run and evaluates phases against true elapsed minutes from participant origin $t_0$.

4. **Participant Privacy Compliance (C6):**
   Committed Stage 1B artifacts inadvertently contained direct participant identifiers linked to clinical outliers and sensor coverage anomalies. All committed Stage 1B-R2 artifacts, reports, and JSON schemas have been stripped of direct identifiers, small-cell counts ($<5$) have been suppressed, and detailed per-participant diagnostics have been relocated to the gitignored `reports_local/` directory.

---

## 4. Verification & Validation Governance

All corrected algorithms have been verified against:
1. **Red Regression Tests:** Six automated regression tests in `tests/test_stage1b_r2_regressions.py` reproducing each defect and verifying its elimination.
2. **Analytical Proofs:** Hand-calculated unit tests in `tests/test_dual_sensor_r2.py` verifying the unbalanced ANOVA $n_0$ formulas against exact theoretical expectations.
3. **Detector-Blind Benchmark Suite:** 15 synthetic ground-truth scenarios in `src/dtwin/analysis/benchmark_generator.py` evaluated across 1,500 test series, with Wilson 95% confidence intervals confirming 100% sensitivity on true linear lattices and 0% false positive rate on continuous negative controls.
4. **Historical Byte-Identity Verification:** Cryptographic SHA-256 baseline verification confirming that all 39 Stage 0 and Stage 1A files remain 100% byte-identical.

---

## 5. Stage 1B-R3 Review Defect Reconciliation

Following the independent review of Stage 1B-R2, eight additional corrective items were reconciled:

1. **Window Timestamps & Indices (`timeaxis.py`):**
   `enumerate_windows` previously lacked timestamp fields and had off-by-one elapsed-minute indices. Fixed by adding explicit `start_time`, `origin_time`, `target_time`, `start_index`, `origin_index`, `target_index`, and exact bounds `start + s + L - 1`.
2. **Excursion Persistence Null-Reset & Durations (`timeaxis.py`):**
   `detect_excursion_episodes_run_bounded` previously skipped NaNs during episode persistence. Fixed by resetting `active_len = 0` whenever `np.isnan(val)` occurs, recalculating Dexcom hyperglycemia episodes (>140: 1,303; >180: 678) and Libre episodes (>140: 772; >180: 369; <70: 494). Duration tracking and boundary censoring are recorded in `ExcursionDetectionResult`.
3. **Dynamic T2 Narrative String:**
   Hardcoded transcription numbers (`1,228 / 779 / 498 / 41`) were replaced with dynamic string formatting from computed dictionary counts (`1,303 / 772 / 494 / 43`).
4. **Dexcom Participant Status Resolved:**
   Participant 23 (Cluster 24) exhibits an inter-session sensor replacement across a 40.5-hour gap, shifting the sampling clock phase from minute $\equiv 1 \pmod 5$ (Session 1, 1,124 bends) to minute $\equiv 2 \pmod 5$ (Session 2, 1,257 bends). While a forced global single-phase yields 52.8% hit rate (<60%), per-session inference (T6) confirms 100.0% 5-minute linear lattice compliance in both sessions.
5. **Cohort Wilson Score Intervals Corrected:**
   Corrected clinical cohort Wilson intervals for $N=45$ (45/45 = $[0.9213, 1.0000]$; 44/45 = $[0.8845, 0.9961]$) and distinguished from synthetic $N=500$ benchmark intervals ($[0.9924, 1.0000]$).
6. **File-by-File Row-Count Reconciliation:**
   Documented file-by-file audit in `reports_local/file_by_file_row_counts.csv` proving all 45 files have $N_i \equiv 0 \pmod 5$, summing to 687,580 rows, and proving why scratch note $632,536 \equiv 1 \pmod 5$ is impossible.
7. **Neutral Lag Characterization:**
   Restated apparent lag strictly as observed empirical displacement across resampled signals without causal or filtering latency claims.
8. **Participant-Level Grouped Validation:**
   Retained `StratifiedGroupKFold` cross-validation in `docs/MODELING_SPEC_R3.md`.

---

## 6. Stage 1B-R3.1 Reconciliation Amendments

Following independent review of Stage 1B-R3, the following final reconciliation items were resolved:

1. **Cohort Row-Count Arithmetic Identity Resolved:**
   - Prior draft reports contained an arithmetic contradiction by citing 633,803 valid Dexcom rows, 686,720 valid Libre rows, and 629,605 paired rows ($629,605 + 4,198 + 57,115 = 690,918 \neq 687,580$).
   - A complete file-by-file audit established the exact, incontrovertible cohort truth:
     - **Total Recorded Rows:** 687,580
     - **Total Valid Dexcom Rows:** 629,825
     - **Total Valid Libre Rows:** 687,360
     - **Paired Usable Overlap Rows:** 629,605
     - **Dexcom-Only Rows (Libre Null):** 220
     - **Libre-Only Rows (Dexcom Null):** 57,755
     - **Neither Sensor Valid:** 0
     - **Exact Identity:** $629,605 + 220 + 57,755 + 0 = 687,580$.
   - **Pairing Semantics:** Defined strictly as **row-wise within each participant CSV**, where row $i$ represents a synchronized 1-minute wall-clock interval created by the original authors. Timestamps in all 45 files are 100% strictly monotonic, with 0 duplicates and 0 unparseable values.
   - **Exclusions:** Excluded rows comprise strictly missing sensor readings ($57,755 + 220 = 57,975$ rows).

2. **FreeStyle Libre Pro Metadata Discordance Clarification:**
   - Participant Cluster 4 exhibits 162 intermediate 5-minute curvature bends ($\mathcal{R}_{\text{inter}} = 2.47 < 3.0$) and satisfies a 5-minute linear lattice mathematically (residual $3.5\times 10^{-15}\text{ mg/dL}$).
   - However, published CGMacros literature (Das et al., *Nature Scientific Data* / PhysioNet) explicitly specifies that FreeStyle Libre Pro recorded at a 15-minute sampling rate.
   - **Resolution:** This series is classified as **METADATA-DISCORDANT** pending independent laboratory clarification. We do NOT speculate or claim unverified hardware replacement, alternative firmware, or protocol modifications without primary source documentation.
   - 44/45 participants (97.78%) confirmed concordant 15-minute native lattice, Wilson 95% CI: $[0.8845, 0.9961]$.

3. **Dexcom Contiguous Runs Distribution & Participant 7 Micro-Gaps:**
   - 1,202 total continuous Dexcom runs exist across the cohort.
   - Participant Cluster 7 accounts for 871 runs due to 870 non-1-minute timestamp steps (recording dropouts) that fragment 5,655 rows into short micro-runs (mean length 6.5 minutes).
   - **Zero Silent Passing:**
     - 89 evaluated sessions ($\ge 120$ min, $\ge 20$ bends): 89/89 (100.0%) confirmed 5-minute linear lattice, Wilson 95% CI: $[0.9585, 1.0000]$.
     - 0 non-compliant evaluated sessions.
     - 1,111 underpowered short sessions (< 120 min, including 860 in Participant 7).
     - 2 underpowered low-bend sessions (< 20 bends).
     - Compliance is claimed strictly **"across all 89 evaluated sessions"**, explicitly qualifying that 1,113 low-information runs are excluded from formal lattice inference.

4. **Neutral Phase Shift Attribution for Participant Cluster 23:**
   - Retracted unsupported physical "sensor replacement" speculation. Neutrally reported as an observed 1-minute clock phase shift (minute 1 mod 5 to minute 2 mod 5) across an unrecorded 40.5-hour recording interval. Under T6 per-session inference, both sessions are 100.0% compliant 5-minute linear lattices.

5. **`timeaxis.py` API & Censoring Polish:**
   - Enhanced `compute_elapsed_minutes` to natively handle both `pd.DatetimeIndex` and `pd.Series`.
   - Added synthetic shift unit tests verifying lag sign convention ($\tau > 0$ denotes Libre leads Dexcom).
   - Clarified left-censoring (active at index 0 of contiguous run) vs right-censoring (active at run termination) in `ExcursionDetectionResult`.
   - Verified `pairs_at_offset` exclusion accounting metadata.

6. **Privacy Enforcement:**
   - `reports_local/file_by_file_row_counts.csv` anonymized with integer cluster IDs (`cluster_id`: 1..45), completely removing participant IDs (`CGMacros-XXX`) and raw file names.

---

## 7. Stage 1B-R3.2 Reconciliation Amendments

Following the Stage 1B-R3.2 independent review, six final reconciliation items were formalized:

1. **Separation of Contiguous Run Denominators & Exact Input Masks:**
   - Prior draft reports conflated run denominators across different masks. The authoritative run counts are strictly delineated:
     - `timestamp_contiguous_runs_all_rows = 1,200`: Computed via `enumerate_runs(df)` across all 687,580 rows where consecutive timestamps have step $\Delta t = 60\text{ s}$.
     - `dexcom_valid_contiguous_runs = 1,202`: Computed via `enumerate_runs(df[df["Dexcom GL"].notna()])` across the 629,825 non-null Dexcom readings (89 evaluable, 1,111 short, 2 low bends).
     - `libre_valid_contiguous_runs = 1,215`: Computed via `enumerate_runs(df[df["Libre GL"].notna()])` across the 687,360 non-null Libre readings (54 evaluable 15m, 1,143 short, 18 low bends). Participant Cluster 4 contains 220 internal nulls that fragment its Libre trace into 16 runs.
   - All 89 evaluable Dexcom runs derive strictly from the 1,202 Dexcom-valid runs denominator.

2. **FreeStyle Libre Pro Metadata Discordance & Nested Lattice Principle:**
   - **Nested Lattice Principle:** A denser linear grid ($P=5$) always reconstructs a coarser piecewise-linear grid ($P=15$) with zero residual. Therefore, a near-zero reconstruction residual on a denser nested grid does **not** prove a 5-minute native lattice. The genuine distinguishing evidence is the presence of intermediate curvature bends ($\mathcal{R}_{\text{inter}} = 2.47 < 3.0$ and 162 intermediate bends).
   - In Participant Cluster 4 (563 total curvature bends):
     - Candidate $P=5$: Phase 0 matches 563/563 bends (100.0%), residual $0.0000\text{ mg/dL}$ ($3.5\times 10^{-15}\text{ mg/dL}$).
     - Candidate $P=15$: Phase 5 matches 401/563 bends (71.2%), residual $0.1559\text{ mg/dL}$, with 162 intermediate bends.
   - Published CGMacros primary literature (Das et al.) states FreeStyle Libre Pro sampled every 15 minutes. This series is classified as **METADATA-DISCORDANT** pending independent laboratory clarification.
   - **Dual-Sensor Agreement Sensitivity:** Agreement is evaluated both including ($N=45$) and excluding ($N=44$) Cluster 4:
     - Full cohort ($N=45$, 629,605 pairs): $\mu_{\text{pool}} = -31.95\text{ mg/dL}$, $\sigma_{\text{rm}} = 24.46\text{ mg/dL}$, 95% LoA: $[-79.89, +16.00]\text{ mg/dL}$.
     - Excluding Cluster 4 ($N=44$, 615,550 pairs): $\mu_{\text{pool}} = -32.08\text{ mg/dL}$, $\sigma_{\text{rm}} = 24.66\text{ mg/dL}$, 95% LoA: $[-80.42, +16.26]\text{ mg/dL}$.

3. **Verbatim Historical 632,536 Row Count Reconciliation:**
   - The historical 632,536 figure is formally reconciled with the exact mandated wording:
     *"The 632,536 figure could not be reproduced and its original provenance remains unresolved. It is not the row count of any combination of complete participant files, because each complete file count is divisible by five; that fact alone does not identify the source of the old figure."*

4. **Clarification of Jitter Scenarios Across Benchmark Suites:**
   - Core Suite `five_minute_with_jitter_and_drops`: Evaluates **glucose measurement amplitude noise** ($\sigma = 2.0\text{ mg/dL}$) on fixed 5-minute sampling timestamps: 500/500 (100.0%) correctly identified as 5-minute native lattice.
   - Blind Suite `native_timestamp_jitter_5min`: Evaluates **sampling timestamp coordinate drift**: 100/100 (100.0%) correctly classified as unresolved / no reliable lattice.
   - Blind Suite `native_timestamp_jitter_15min`: 99/100 correctly unresolved; 1/100 falsely classified as 15m lattice (1.0% error rate, Wilson CI: $[0.9455, 0.9982]$).

5. **Exploratory Status of Repeated-Measures Agreement:**
   - Repeated-measures limits of agreement are designated with status **`EXPLORATORY_SERIAL_AUTOCORRELATION_UNADJUSTED`** because 1-minute interpolated pairs exhibit strong serial autocorrelation, meaning standard unadjusted ANOVA variance assumptions underestimate true estimator variance.

6. **Behavioral Null-Reset Excursion & Non-Periodic Lag Regression Tests:**
   - Added unit tests verifying excursion entry null-resets, active episode null tolerance up to `max_null_min`, release persistence null-resets, and boundary censoring.
   - Added synthetic tests for lag cross-correlation on non-periodic multi-frequency autoregressive traces with missing values and unequal overlap.

---

## 8. Stage 1B-R3.3 Reconciliation Amendments

Following the Stage 1B-R3.2 independent review, eight specific reconciliation items were addressed:

1. **Wilson Confidence Interval Separation for 15m Jitter:**
   - Corrected the confidence interval for the 1/100 false confident 15m classification in the blind 15-minute jitter benchmark scenario:
     - **False-Classification Rate (1/100):** 1.0%, Wilson 95% CI: $[0.0018, 0.0545]$ (0.18%–5.45%).
     - **Unresolved Rate (99/100):** 99.0%, Wilson 95% CI: $[0.9455, 0.9982]$ (94.55%–99.82%).
   - Both intervals are reported separately with exact binomial coverage.

2. **Neutral Modeling Differentiation from Published Baseline:**
   - Revised `MODELING_SPEC_R3.md` and related documentation to remove the unsupported claim that the published CGMacros XGBoost baseline "suffered from interpolation leakage."
   - Neutrally described our methodological difference: while the published baseline evaluated predictions on 1-minute uniform interpolated data, our Digital Twin formulation evaluates step-ahead forecasting on physical hardware native lattices ($h=30\text{ min}$ and $60\text{ min}$) to anchor clinical decision support directly to genuine sensor measurement vertices.

3. **Canonical Curvature Threshold Pinning (`0.15`) & Sensitivity Invariance:**
   - Confirmed canonical configuration parameter `second_difference_bend_threshold: 0.15` in `configs/stage1b.yaml` (563 bends detected) and reconciled with exploratory machine-precision threshold `1e-5` (846 bends detected).
   - Documented complete classification invariance across a 500,000-fold variation from $10^{-6}\text{ mg/dL}$ to $0.50\text{ mg/dL}$: period is strictly 5, phase is strictly 0, reconstruction residual is $0.0000\text{ mg/dL}$ ($3.5\times 10^{-15}\text{ mg/dL}$), and distinction ratio is $\mathcal{R}_{\text{inter}} \approx 2.47 < 3.0$ with $\sim 28.8\%$ intermediate bends. Retained as **`METADATA-DISCORDANT`**.

4. **Dexcom Duration & Participant Coverage Statistics:**
   - Preserved the narrow 89/89 compliant run claim while adding full data duration and participant coverage statistics:
     - **89 Evaluated Runs ($\ge 120$ min, $\ge 20$ bends):** Contain **625,728 valid rows (99.35% of all valid Dexcom data)** across all **45 out of 45 participants (100.0% cohort coverage)**.
     - **1,111 Short Runs (< 120 min):** Contain only **3,855 rows (0.61% of Dexcom data)** (micro-dropouts, 860 in Participant 7).
     - **2 Low-Bend Runs (< 20 bends):** Contain only **242 rows (0.04% of Dexcom data)**.
     - **Total Dexcom Data:** 629,825 valid rows (100.0%).

5. **Benchmark Scenario Renaming:**
   - Formally renamed `five_minute_with_jitter_and_drops` to `five_minute_with_amplitude_noise_and_drops` (retaining an alias for backward compatibility), clarifying that it evaluates measurement amplitude noise ($\sigma = 2.0\text{ mg/dL}$) on fixed sampling timestamps rather than coordinate drift.

6. **Strict Privacy Scanning & Historical Baseline Preservation:**
   - Updated privacy verification so scanners fail loudly on missing or unreadable files. Confirmed zero participant identifiers (`CGMacros-\d{3}`) across shareable documents and verified that all 39 Stage 0 / Stage 1A baseline files remain 100% byte-identical against `reports_local/pre_change_baseline_sha256.json`.

7. **Exploratory Status of Dual-Sensor Agreement Limits:**
   - Designated repeated-measures Bland-Altman limits of agreement ($[-79.89, +16.00]\text{ mg/dL}$) as exploratory due to unadjusted temporal serial autocorrelation. Clarified that observed sensor differences reflect empirical trace disagreement rather than proven hardware bias or clinical ground truth.

8. **Exhaustive Finding-to-Test Traceability Matrix:**
   - Published a comprehensive traceability matrix linking all 8 defect areas to production modules, automated regression tests, and verification commands across 86 test cases (100% green).

---

## 9. Stage 1B-R3.4 Final Reconciliation & Stage 1B Freeze Amendments

In response to independent strategic review, Stage 1B was finalized and frozen under R3.4:

1. **Cohort-Wide Timestamp Integrity Audit:**
   - Completed a file-by-file audit of all 45 participant CSVs (687,580 rows). Verified:
     - Parse failures: 0.
     - Timestamp inversions / subminute steps: 0.
     - Duplicate timestamps: 0.
     - Monotonicity: 100% strictly increasing in original row order.
     - Timestamp gaps (> 60s): Exactly 1,155 gaps cohort-wide, defining 1,200 contiguous runs ($\Delta t = 60\text{ s}$).
     - Gap distribution: Min 2.0 min, p25 2.0 min, Median 4.0 min, p75 7.0 min, Max 901.0 min (~15h). 35 of 45 files have 0 gaps.
     - Saved full anonymized audit table to `reports_local/timestamp_integrity_audit.csv`.
     - Zero sorting, deduplicating, or synthetic gap bridging was performed or required.

2. **Time-of-Day (Circadian) Feature Validity:**
   - Verified date-shifting protocol: Primary data dictionary (`DataDictionary_CGMacros-00X.csv`) explicitly notes *"Randomly shifted time stamps for days in the study"*; source archive is named `CGMacros_dateshifted365.zip`. The de-identification protocol applied an integer-day shift, preserving local wall-clock time (HH:MM).
   - Verified empirical meal timings across 1,706 logged meal events:
     - Breakfast ($N=436$): Median 08:15 AM (IQR: [07:31, 09:11]).
     - Lunch ($N=435$): Median 12:33 PM (IQR: [11:57, 13:15]).
     - Dinner ($N=492$): Median 06:58 PM (IQR: [17:45, 20:04]).
     - Snack ($N=343$): Median 05:45 PM (IQR: [16:00, 20:52]).
     - Nocturnal hours (00:00–05:00) contain near-zero meal events.
   - Stage 2 Implication: Circadian features ($[\sin(2\pi \text{TOD}/1440), \cos(2\pi \text{TOD}/1440)]$) are legitimate and represent genuine diurnal physiology. Calendar features (month, day of week) remain strictly prohibited.

3. **Canonical Metrics Registry:**
   - Established `canonical_metrics_registry` in `src/dtwin/analysis/run_stage1b.py`, exported to `docs/reports/canonical_metrics.json` (SHA-256: `70afb620d1ce781c4d6dafc71f29f7ce847e0e68f23f8e10c2b6c7be69126c3d`) and embedded in `stage1b_r3_results.json`. Every entry defines `value`, `unit`, `definition`, `denominator`, and `inclusion_mask`.

4. **Published Modeling Baseline Distinction:**
   - Corrected `MODELING_SPEC_R3.md` Section 2.5: The published CGMacros baseline (Das et al.) predicted meal-level 2-hour postprandial glucose AUC/iAUC using meal macronutrients and clinical covariates via XGBoost and Random Forest. Our proposed Stage 2 Task T1 is continuous multi-horizon sequential glucose forecasting ($h=30\text{ min}, 60\text{ min}$) evaluated directly on physical hardware native lattices (5-min Dexcom, 15-min Libre). This is an entirely distinct task; no claim of interpolation leakage applies to their published work.

5. **Dexcom Dataset Representation Coverage Qualification:**
   - Pinned exact required qualification:
     *"Eligible runs contained 625,728 of 629,825 valid one-minute-grid Dexcom rows (99.35% of valid rows in the released representation) and spanned all 45/45 participants (100.0% cohort coverage). This percentage represents row coverage in the released 1-minute interpolated representation and must not be equated with coverage of independent physical sensor observations."*

6. **Stage 1B Freeze:**
   - Configuration `configs/stage1b.yaml` frozen at v`1.4.0-r3.4` (SHA-256: `cf2763408891feb97c67dd5184ad4674dd2c98a736922ad322c8b66bc11bd467`).
   - All quality gates passed (86 tests, ruff, mypy, checksums, privacy). Stage 1B is formally frozen.




