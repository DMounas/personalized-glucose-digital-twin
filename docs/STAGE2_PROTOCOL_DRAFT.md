# Stage 2 Predictive Modeling Protocol (Draft v0.1.0)

**Protocol Version:** 0.1.0-draft  
**Status:** PREREGISTERED PROTOCOL DRAFT FOR INDEPENDENT REVIEW  
**Dependencies:** `configs/stage1b.yaml`, `docs/reports/stage1b_r3_results.json`, `docs/reports/canonical_metrics.json`  

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

### 3.2 Preregistered Phase Sensitivity Evaluation
Candidate-origin counts exhibit remarkable balance across fixed phases (123,647 to 123,683 origins at +30m, $<0.03\%$ variation). However, this balance reflects candidate-origin sample counts across the five candidate sampling lattices only; it is **not** an empirical forecasting accuracy or model performance result. 

To guarantee that model performance is not an artifact of native phase selection:
1. **Primary Evaluation:** Evaluated on session-specific inferred phase $\phi_s$ (Time Semantics T6). T6 inference remains diagnostic and must **never** select the primary test phase using future or test-set observations.
2. **Phase Sensitivity Suite:** Evaluated across all five possible fixed phase offsets $\phi \in \{0, 1, 2, 3, 4\}$.
3. **Consequential Variation Stopping Rule:**
   - If performance across the 5 phases exhibits variation $> 10\%$ in RMSE or $> 2.0\text{ mg/dL}$ in absolute RMSE delta, the model is flagged as sensitive to interpolation phase and cannot claim hardware-lattice invariance.

---

## 4. Cross-Validation Architecture & Sample Size Hierarchies

### 4.1 Nested Sample Size Hierarchy
Statistical power and evaluation counts are defined strictly across nested hierarchical levels:
- **Level 1 (Independent Units):** $K = 45$ participants (15 Normal, 16 Prediabetes, 14 Type 2 Diabetes).
- **Level 2 (Contiguous Runs within Participants):** 1,200 runs of contiguous timestamps ($\Delta t = 60\text{ s}$); 1,202 runs of non-null Dexcom readings.
- **Level 3 (Candidate Forecast Origins Across Architectures):**
  - **Candidate 5-Minute Native Lattice Vertices (13-point history, $L=60\text{ min}$):**
    - +30 min horizon ($h=30$): **123,709 candidate origins** cohort-wide (Normal: 41,806; Prediabetes: 42,410; Diabetes: 39,493).
    - +60 min horizon ($h=60$): **123,266 candidate origins** cohort-wide (Normal: 41,665; Prediabetes: 42,218; Diabetes: 39,383).
    - Fixed phases sensitivity (+30m / +60m): $\phi=0$ (123,682 / 123,233), $\phi=1$ (123,683 / 123,243), $\phi=2$ (123,653 / 123,216), $\phi=3$ (123,647 / 123,207), $\phi=4$ (123,650 / 123,210).
  - **1-Minute Grid with 60-Minute Autoregressive History ($L=60\text{ min}$, 61 points):**
    - +30 min horizon ($h=30$): **618,236 candidate origins** cohort-wide (Normal: 209,006; Prediabetes: 211,800; Diabetes: 197,430).
    - +60 min horizon ($h=60$): **616,029 candidate origins** cohort-wide (Normal: 208,297; Prediabetes: 210,862; Diabetes: 196,870).
  - **Historical Descriptive Offset Pairs ($L=0$, no input history requirement):**
    - +30 min horizon ($h=30$): **625,098 valid pairs** ($682,871\text{ in-run candidate slots} - 57,773\text{ null endpoint pairs}$).
    - +60 min horizon ($h=60$): **622,078 valid pairs** ($679,773\text{ in-run candidate slots} - 57,695\text{ null endpoint pairs}$).
    - Candidate slots represent $\sum_r \max(0, \text{len}(r) - h)$ across all 1,200 timestamp runs (687,580 recorded rows).
- **Runs and windows are nested units within participants**, not independent subjects.

### 4.2 Grouped Cross-Validation Scheme
- **Cross-Validation Scheme:** 5-fold `StratifiedGroupKFold`.
- **Grouping Unit:** Participant cluster ($K = 45$). Zero intra-participant leakage between training and testing partitions.
- **Stratification Target:** Clinical baseline HbA1c stratum (Normal, Prediabetes, Type 2 Diabetes).
- **Session Purging:** Multi-minute timestamp gaps serve as natural segment boundaries; no window or sequence bridges across a gap.

---

## 5. Secondary Candidate Tasks & Feasibility Bounds

### 5.1 Hyperglycemia Excursion Feasibility Check (>180 mg/dL)
- **Status:** **FEASIBILITY CHECK ONLY** (secondary to continuous regression).
- **Formal Persistence Semantics & Conventions:**
  - **Primary Clinical Convention (Convention B — Interval-Bin Duration):**
    Each discrete sample represents a measurement epoch of duration $\Delta t$. Total elevation exposure equals $N \cdot \Delta t \ge 15\text{ minutes}$, and release duration equals $M \cdot \Delta t \ge 10\text{ minutes}$.
    - On 1-minute interpolated grid ($\Delta t = 1\text{m}$): $N = 15\text{ consecutive points}$ ($15\text{ min}$ exposure), $M = 10\text{ consecutive points} \le 175\text{ mg/dL}$ ($10\text{ min}$ release).
    - On 5-minute native lattice ($\Delta t = 5\text{m}$): $N = 3\text{ consecutive points}$ ($15\text{ min}$ exposure), $M = 2\text{ consecutive points} \le 175\text{ mg/dL}$ ($10\text{ min}$ release).
    - *Observed Cohort Distribution (Convention B):*
      - 1-minute grid: **678 total episodes (17 boundary-censored)**.
        - Normal: 105 (2 censored); Prediabetes: 236 (2 censored); Diabetes: 337 (13 censored).
      - 5-minute native lattice: **714 total episodes (14 boundary-censored)**.
        - Normal: 112 (2 censored); Prediabetes: 251 (3 censored); Diabetes: 351 (9 censored).
  - **Sensitivity Convention (Convention A — Point-to-Point Elapsed Duration):**
    Requires strict timestamp elapsed difference $t_{\text{end}} - t_{\text{start}} \ge 15\text{ minutes}$ and $t_{\text{rel\_end}} - t_{\text{rel\_start}} \ge 10\text{ minutes}$.
    - On 1-minute interpolated grid: $N = 16\text{ consecutive points}$ ($t_{15} - t_0 = 15\text{m}$ elapsed), $M = 11\text{ consecutive points} \le 175\text{ mg/dL}$ ($10\text{m}$ elapsed). Yields **667 total episodes (17 boundary-censored)** (Normal: 101, Prediabetes: 234, Diabetes: 332).
    - On 5-minute native lattice: $N = 4\text{ consecutive points}$ ($t_3 - t_0 = 15\text{m}$ elapsed), $M = 3\text{ consecutive points} \le 175\text{ mg/dL}$ ($10\text{m}$ elapsed). Yields **642 total episodes (13 boundary-censored)** (Normal: 94, Prediabetes: 227, Diabetes: 321).
- **Subject Coverage & Diagnostic Imbalance:**
  - Participant coverage: 42/45 participants have $\ge 1$ episode; 40/45 have $\ge 3$ episodes; 33/45 have $\ge 5$ episodes; 27/45 have $\ge 10$ episodes.
  - In Type 2 Diabetes, 14/14 participants (100%) have $\ge 10$ episodes.
  - In Normal, only 4/15 participants (26.7%) have $\ge 10$ episodes (extreme event scarcity in normoglycemic subjects).
- **Missingness & Censoring Semantics:** Missing sensor values reset entry persistence. Boundary-censored episodes (active at run termination or truncated by $>5\text{ min}$ of missing sensor values) are explicitly tracked for censored likelihood/survival evaluation.

### 5.2 Hypoglycemia Classification (<70 mg/dL): DEFERRED
- **Status:** **DEFERRED.**
- **Rationale:** Only 43 total hypoglycemia episodes occur on Dexcom cohort-wide across 45 participants (with 0 in most participants). Event scarcity is too extreme to support a standalone supervised classification task in Stage 2 without severe synthetic oversampling or clinical pooling.
