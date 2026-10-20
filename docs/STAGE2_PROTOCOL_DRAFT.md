# Stage 2 Predictive Modeling Protocol (Draft v0.2.0)

**Protocol Version:** 0.2.0-draft  
**Status:** WORKING DRAFT FOR CLAUDE'S FOCUSED STRATEGIC REVIEW (UNFROZEN)  
**Dependencies:** `configs/stage1b.yaml`, `docs/reports/stage1b_r3_results.json`, `docs/reports/canonical_metrics.json`, `docs/reports/stage2_aggregate_feasibility.json`  

> [!NOTE]
> This protocol is an **unfrozen working draft** prepared for Claude's focused strategic review. It incorporates the Stage 1B data-provenance freeze, native-grid diagnostics, run-bounded origin arithmetic, and empirical sample feasibility bounds. No Stage 2 predictive model training, fitting, or benchmark execution will commence until independent review accepts this protocol.

---

## 1. Scientific Objective & Primary Sensor Selection

### 1.1 Objective
The primary objective of Stage 2 is to develop, evaluate, and benchmark multi-horizon continuous sequential glucose forecasting models on the CGMacros v1.0.0 dataset. The initial focus is strictly placed on **continuous interstitial glucose regression** at forecast horizons $h = 30\text{ minutes}$ and $h = 60\text{ minutes}$.

### 1.2 Primary Sensor Target: Dexcom G6 Pro
**Dexcom G6 Pro** is designated as the primary modeling target primarily due to its **finer native measurement interval** (5-minute native lattice, ~288 points/day) compared to FreeStyle Libre Pro (15-minute native lattice, ~96 points/day). 
- Finer temporal resolution provides direct capture of postprandial glucose rates of change without relying on coarse multi-step linear interpolation.
- Sensor selection is justified solely by hardware sampling interval, **not** by unverified sensor-quality assertions, apparent lag differences, or threshold excursion count disparities.

### 1.3 FreeStyle Libre Pro Cross-Device Transfer (Deferred Sensitivity)
Cross-device transfer to FreeStyle Libre Pro is **not** a prerequisite for accepting the first Stage 2 model results. Because the two devices exhibit an observed systematic trace disagreement ($\mu_{\text{pool}} = -31.95\text{ mg/dL}$ with wide repeated-measures limits of agreement $[-79.89, +16.00]\text{ mg/dL}$), cross-device transfer is classified as an **optional secondary sensitivity analysis** to be conducted only after the primary Dexcom forecasting benchmark is frozen.

---

## 2. Feature Governance & Model Input Architecture

### 2.1 Input History & Native Vertex Anchoring
To avoid interpolation leakage, models are evaluated at candidate native sampling vertices:
- **Autoregressive Input History ($L = 60\text{ minutes}$):** 13 points sampled at 5-minute intervals: $[y_t, y_{t-5}, y_{t-10}, \dots, y_{t-60}]$.
- **Rate-of-Change Feature:** First-order difference $(y_t - y_{t-15}) / 15$.
- **Demographic & Baseline Covariates:** Age, Gender, BMI, baseline HbA1c (from `bio.csv`).

### 2.2 Time-of-Day / Circadian Features: EXCLUDED from Initial Model
- **Status:** **EXCLUDED from initial baseline model.**
- **Rationale:** While empirical meal timings follow diurnal human living patterns and the dataset filename references date shifting, the dataset documentation (`DataDictionary_CGMacros-00X.csv`) states only that timestamps are *"Randomly shifted time stamps for days in the study"* without explicitly confirming that the shift was an integer number of days or that local clock time (HH:MM) was strictly preserved. Because definitive primary-source documentation is inconclusive, diurnal circadian features ($[\sin(2\pi \cdot \text{TOD}/1440), \cos(2\pi \cdot \text{TOD}/1440)]$) are excluded from the initial model. They may only be evaluated as an exploratory sensitivity feature set in secondary experiments.
- **Calendar Features:** Day of week, month, and season remain **strictly prohibited**.

---

## 3. Native Grid & Phase Sensitivity Preregistration

### 3.1 Diagnostic Treatment of Native Grid Inferences
Stage 1B demonstrated that eligible contiguous runs contained 625,728 of 629,825 valid one-minute-grid Dexcom rows (99.35% of valid rows in the released representation). This percentage represents row coverage in the released 1-minute interpolated representation and must not be equated with coverage of independent physical sensor observations. Because raw device ADC telemetry and transmission logs were not published, inferred native vertices are treated strictly as a **mathematical diagnostic** of the released linear interpolation rather than proven physical sensor transmissions.

### 3.2 Preregistered Phase Sensitivity Evaluation & Operationalized Stopping Rule
Candidate-origin counts exhibit remarkable balance across fixed phases (123,647 to 123,683 origins at +30m, $<0.03\%$ variation). However, this balance reflects candidate-origin sample counts across the five candidate sampling lattices only; it is **not** an empirical forecasting accuracy or model performance result.

To guarantee that model performance is not an artifact of native phase selection, the evaluation protocol establishes the following:
1. **Primary Evaluation:** Evaluated on session-specific inferred phase $\phi_s$ (Time Semantics T6). T6 inference remains diagnostic and must **never** select the primary test phase using future or test-set observations.
2. **Phase Sensitivity Suite:** Evaluated across all five possible fixed phase offsets $\phi \in \{0, 1, 2, 3, 4\}$.
3. **Operationalized Stopping Rule (>10% RMSE Delta):**
   - **Target Metric:** Group-stratified 5-fold cross-validation test-set Root Mean Squared Error (RMSE) in mg/dL evaluated separately at forecast horizons $h = 30\text{ min}$ and $h = 60\text{ min}$.
   - **Reference Comparison Models:** 5 separate fixed-phase candidate models trained and evaluated on each fixed candidate lattice offset $\phi \in \{0, 1, 2, 3, 4\}$.
   - **Computational Formula:**
     $$\Delta_{\text{rel}} = \frac{\max_{\phi} \text{RMSE}(\phi) - \min_{\phi} \text{RMSE}(\phi)}{\min_{\phi} \text{RMSE}(\phi)} \times 100\%$$
     $$\Delta_{\text{abs}} = \max_{\phi} \text{RMSE}(\phi) - \min_{\phi} \text{RMSE}(\phi)$$
   - **Trigger Conditions:** An architecture triggers the phase-sensitivity failure condition if either:
     1. Relative variation exceeds 10.0%: $\Delta_{\text{rel}} > 10.0\%$, OR
     2. Absolute variation exceeds 2.0 mg/dL: $\Delta_{\text{abs}} > 2.0\text{ mg/dL}$.
   - **Protocol Action Upon Trigger:**
     - The architecture is formally classified as **phase-sensitive and dependent on linear-interpolation lattice alignment**.
     - All claims of hardware-lattice invariance are rejected.
     - Modeling must halt or transition to either a continuous-time formulation (e.g., Neural ODEs / Continuous-Time State Space Models) or an explicit marginalization across all phase offsets $\frac{1}{5} \sum_{\phi=0}^4 \hat{y}(t; \phi)$.

---

## 4. Cross-Validation Architecture & Sample Size Hierarchies

### 4.1 Nested Sample Size Hierarchy & Run-Bounded Origin Arithmetic
Statistical power and evaluation counts are defined strictly across nested hierarchical levels:
- **Level 1 (Independent Units):** $K = 45$ participants (15 Normal, 16 Prediabetes, 14 Type 2 Diabetes).
- **Level 2 (Contiguous Runs within Participants):**
  - **Timestamp Runs:** 1,200 runs of contiguous timestamps ($\Delta t = 60\text{ s}$, 687,580 recorded rows).
  - **Dexcom Valid Sensor Runs:** 1,202 runs of contiguous non-null Dexcom readings (633,803 valid rows).
- **Level 3 (Candidate Forecast Origins Across Architectures):**
  - **Candidate 5-Minute Native Lattice Vertices (13-point history, $L=60\text{ min}$):**
    - +30 min horizon ($h=30$): **123,709 candidate origins** cohort-wide (Normal: 41,806; Prediabetes: 42,410; Diabetes: 39,493).
    - +60 min horizon ($h=60$): **123,266 candidate origins** cohort-wide (Normal: 41,665; Prediabetes: 42,218; Diabetes: 39,383).
    - Fixed phases sensitivity (+30m / +60m): $\phi=0$ (123,682 / 123,233), $\phi=1$ (123,683 / 123,243), $\phi=2$ (123,653 / 123,216), $\phi=3$ (123,647 / 123,207), $\phi=4$ (123,650 / 123,210).
  - **1-Minute Grid with 60-Minute Autoregressive History ($L=60\text{ min}$, 61 points):**
    - +30 min horizon ($h=30$): **618,236 candidate origins** cohort-wide (Normal: 209,006; Prediabetes: 211,800; Diabetes: 197,430).
    - +60 min horizon ($h=60$): **616,029 candidate origins** cohort-wide (Normal: 208,297; Prediabetes: 210,862; Diabetes: 196,870).
  - **Historical Descriptive Offset Pairs ($L=0$, no input history requirement):**
    - **Derivation on 1,200 Timestamp Runs (Case 1):**
      - Total timestamp-contiguous runs: 1,200 (687,580 recorded rows).
      - At $h=30\text{ min}$:
        - 1,079 runs have length $\le 30\text{ min}$ (accounting for 1,079 rows total; isolated 1-minute rows).
        - 121 runs have length $> 30\text{ min}$ (accounting for 686,501 rows total).
        - Candidate slots: $\sum_r \max(0, \text{len}(r) - 30) = 686,501 - (121 \times 30) = \mathbf{682,871}$.
        - Endpoint null pairs: 57,773.
        - Valid pairs: $682,871 - 57,773 = \mathbf{625,098}$.
      - At $h=60\text{ min}$:
        - 1,103 runs have length $\le 60\text{ min}$ (accounting for 1,987 rows total).
        - 97 runs have length $> 60\text{ min}$ (accounting for 685,593 rows total).
        - Candidate slots: $\sum_r \max(0, \text{len}(r) - 60) = 685,593 - (97 \times 60) = \mathbf{679,773}$.
        - Endpoint null pairs: 57,695.
        - Valid pairs: $679,773 - 57,695 = \mathbf{622,078}$.
    - **Derivation on 1,202 Strictly Non-Null Dexcom Runs (Case 2):**
      - Total non-null Dexcom runs: 1,202 (633,803 valid rows).
      - At $h=30\text{ min}$: 1,063 runs $\le 30\text{ min}$ (5,041 rows); 139 runs $> 30\text{ min}$ (628,762 rows). Candidate slots: $628,762 - (139 \times 30) = 624,592$; valid in-run pairs: 618,493.
      - At $h=60\text{ min}$: 1,085 runs $\le 60\text{ min}$ (6,081 rows); 117 runs $> 60\text{ min}$ (627,722 rows). Candidate slots: $627,722 - (117 \times 60) = 620,939$; valid in-run pairs: 614,722.
- **Runs and windows are nested units within participants**, not independent subjects.

### 4.2 Grouped Cross-Validation Scheme
- **Cross-Validation Scheme:** 5-fold `StratifiedGroupKFold`.
- **Grouping Unit:** Participant cluster ($K = 45$). Zero intra-participant leakage between training and testing partitions.
- **Stratification Target:** Clinical baseline HbA1c stratum (Normal, Prediabetes, Type 2 Diabetes).
- **Session Purging:** Multi-minute timestamp gaps serve as natural segment boundaries; no window or sequence bridges across a gap.

### 4.3 Cohort Breakdown & Modulo-15 Provenance Audit
The CGMacros v1.0.0 cohort comprises 45 unique participant files. A systematic audit of row counts demonstrates that **44 of 45 participant files have row counts exactly divisible by 15** ($N_i \pmod{15} = 0$). Exactly **one participant file** (`CGMacros-004`, 14,275 rows) has a non-zero remainder ($14,275 \pmod{15} = 10$).

| Participant ID | Diagnostic Group | Baseline HbA1c | Row Count | Rows mod 15 |
|:---|:---|:---:|---:|:---:|
| `CGMacros-001` | Normal | 5.4% | 14,730 | 0 |
| `CGMacros-002` | Normal | 5.5% | 17,025 | 0 |
| `CGMacros-003` | Diabetes | 6.5% | 14,565 | 0 |
| `CGMacros-004` | Normal | 5.5% | 14,275 | 10 |
| `CGMacros-005` | Diabetes | 6.6% | 14,460 | 0 |
| `CGMacros-006` | Normal | 5.2% | 14,460 | 0 |
| `CGMacros-007` | Prediabetes | 5.9% | 5,655 | 0 |
| `CGMacros-008` | Prediabetes | 5.8% | 14,760 | 0 |
| `CGMacros-009` | Prediabetes | 5.7% | 14,370 | 0 |
| `CGMacros-010` | Prediabetes | 5.7% | 16,155 | 0 |
| `CGMacros-011` | Prediabetes | 5.7% | 14,805 | 0 |
| `CGMacros-012` | Diabetes | 7.1% | 14,655 | 0 |
| `CGMacros-013` | Prediabetes | 6.2% | 15,840 | 0 |
| `CGMacros-014` | Diabetes | 7.1% | 17,250 | 0 |
| `CGMacros-015` | Normal | 5.4% | 16,875 | 0 |
| `CGMacros-016` | Prediabetes | 5.8% | 16,290 | 0 |
| `CGMacros-017` | Normal | 5.0% | 16,185 | 0 |
| `CGMacros-018` | Normal | 5.4% | 14,085 | 0 |
| `CGMacros-019` | Normal | 5.6% | 14,430 | 0 |
| `CGMacros-020` | Prediabetes | 6.4% | 16,260 | 0 |
| `CGMacros-021` | Normal | 5.3% | 16,125 | 0 |
| `CGMacros-022` | Prediabetes | 5.9% | 17,625 | 0 |
| `CGMacros-023` | Prediabetes | 6.2% | 16,185 | 0 |
| `CGMacros-026` | Prediabetes | 5.9% | 16,320 | 0 |
| `CGMacros-027` | Normal | 4.7% | 14,535 | 0 |
| `CGMacros-028` | Diabetes | 7.0% | 18,735 | 0 |
| `CGMacros-029` | Prediabetes | 6.1% | 17,730 | 0 |
| `CGMacros-030` | Diabetes | 7.6% | 15,465 | 0 |
| `CGMacros-031` | Normal | 5.1% | 13,725 | 0 |
| `CGMacros-032` | Normal | 5.3% | 13,785 | 0 |
| `CGMacros-033` | Normal | 5.6% | 15,840 | 0 |
| `CGMacros-034` | Normal | 4.6% | 14,700 | 0 |
| `CGMacros-035` | Diabetes | 8.5% | 14,400 | 0 |
| `CGMacros-036` | Diabetes | 6.9% | 17,115 | 0 |
| `CGMacros-038` | Diabetes | 7.2% | 14,505 | 0 |
| `CGMacros-039` | Diabetes | 8.3% | 17,205 | 0 |
| `CGMacros-041` | Prediabetes | 6.3% | 14,310 | 0 |
| `CGMacros-042` | Diabetes | 7.1% | 14,520 | 0 |
| `CGMacros-043` | Prediabetes | 6.0% | 14,520 | 0 |
| `CGMacros-044` | Prediabetes | 6.0% | 14,535 | 0 |
| `CGMacros-045` | Prediabetes | 6.1% | 15,570 | 0 |
| `CGMacros-046` | Diabetes | 7.4% | 14,655 | 0 |
| `CGMacros-047` | Diabetes | 6.9% | 15,690 | 0 |
| `CGMacros-048` | Normal | 4.8% | 17,340 | 0 |
| `CGMacros-049` | Diabetes | 7.2% | 15,315 | 0 |

#### Diagnostic Group Sums & Modulo-15 Invariance
- **Normal (15 participants):** $228,115\text{ rows} \pmod{15} = \mathbf{10}$ (due entirely to `CGMacros-004`).
- **Prediabetes (16 participants):** $240,930\text{ rows} \pmod{15} = \mathbf{0}$.
- **Diabetes (14 participants):** $218,535\text{ rows} \pmod{15} = \mathbf{0}$.
- **Cohort Total (45 participants):** $687,580\text{ rows} \pmod{15} = \mathbf{10}$.

> [!IMPORTANT]
> **Reconciliation of Conflicting Historical Scratch Counts:**
> In earlier exploratory scratch scripts, unverified figures of Prediabetes = 247,025 and Diabetes = 213,415 were reported. Because $247,025 \pmod{15} = 5$ and $213,415 \pmod{15} = 10$, and because every Prediabetes and Diabetes CSV file in the repository has $N_i \pmod{15} = 0$, it is mathematically impossible for any combination of whole participant CSV files to sum to those values. Those historical counts are formally recorded as an **unresolved, non-reproducible artifact** arising from partial-run processing or ad-hoc filtering. The canonical group totals are strictly established as 228,115 (Normal), 240,930 (Prediabetes), and 218,535 (Diabetes).

---

## 5. Secondary Candidate Tasks & Feasibility Bounds

### 5.1 Hyperglycemia Excursion Feasibility Check (>180 mg/dL)
- **Status:** **EXPLORATORY FEASIBILITY CHECK ONLY** (secondary to continuous regression).
- **Exploratory Event Nature:** These excursion episodes are exploratory computational events derived from the released interpolated representation, not directly observed physical sensor recordings or clinical episodes.
- **Formal Persistence Semantics & Conventions:**
  - **Primary Computational Interval-Bin Convention (Convention B):**
    Discrete points represent contiguous measurement epochs of $\Delta t$ duration. Total elevation exposure equals $N \cdot \Delta t \ge 15\text{ minutes}$, and release duration equals $M \cdot \Delta t \ge 10\text{ minutes}$.
    - On 1-minute interpolated representation ($\Delta t = 1\text{m}$): $N = 15\text{ consecutive points}$ ($15\text{ min}$ exposure), $M = 10\text{ consecutive points} \le 175\text{ mg/dL}$ ($10\text{ min}$ release).
    - On Candidate 5-Minute Lattice ($\Delta t = 5\text{m}$): $N = 3\text{ consecutive points}$ ($15\text{ min}$ exposure), $M = 2\text{ consecutive points} \le 175\text{ mg/dL}$ ($10\text{ min}$ release).
    - *Observed Cohort Distribution (Convention B):*
      - 1-minute representation: **678 total episodes (17 boundary-censored)**.
        - Normal: 105 (2 censored); Prediabetes: 236 (2 censored); Diabetes: 337 (13 censored).
      - Candidate 5-minute lattice: **714 total episodes (14 boundary-censored)**.
        - Normal: 112 (2 censored); Prediabetes: 251 (3 censored); Diabetes: 351 (9 censored).
  - **Sensitivity Convention (Convention A — Point-to-Point Elapsed Duration):**
    Requires strict timestamp elapsed difference $t_{\text{end}} - t_{\text{start}} \ge 15\text{ minutes}$ and $t_{\text{rel\_end}} - t_{\text{rel\_start}} \ge 10\text{ minutes}$.
    - On 1-minute representation: $N = 16\text{ consecutive points}$ ($t_{15} - t_0 = 15\text{m}$ elapsed), $M = 11\text{ consecutive points} \le 175\text{ mg/dL}$ ($10\text{m}$ elapsed). Yields **667 total episodes (17 boundary-censored)** (Normal: 101, Prediabetes: 234, Diabetes: 332).
    - On Candidate 5-minute lattice: $N = 4\text{ consecutive points}$ ($t_3 - t_0 = 15\text{m}$ elapsed), $M = 3\text{ consecutive points} \le 175\text{ mg/dL}$ ($10\text{m}$ elapsed). Yields **642 total episodes (13 boundary-censored)** (Normal: 94, Prediabetes: 227, Diabetes: 321).
- **Subject Coverage & Diagnostic Imbalance:**
  - Participant coverage: 42/45 participants have $\ge 1$ episode; 40/45 have $\ge 3$ episodes; 33/45 have $\ge 5$ episodes; 27/45 have $\ge 10$ episodes.
  - In Type 2 Diabetes, 14/14 participants (100%) have $\ge 10$ episodes.
  - In Normal, only 4/15 participants (26.7%) have $\ge 10$ episodes (extreme event scarcity in normoglycemic subjects).
- **Missingness & Censoring Semantics:** Missing sensor values reset entry persistence. Boundary-censored episodes (active at run termination or truncated by $>5\text{ min}$ of missing sensor values) are explicitly tracked for censored likelihood/survival evaluation.

### 5.2 Hypoglycemia Classification (<70 mg/dL): DEFERRED
- **Status:** **DEFERRED.**
- **Rationale:** Only 43 total hypoglycemia episodes occur on Dexcom cohort-wide across 45 participants (with 0 in most participants). Event scarcity is too extreme to support a standalone supervised classification task in Stage 2 without severe synthetic oversampling or clinical pooling.
