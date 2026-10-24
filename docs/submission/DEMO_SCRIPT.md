# 15–20 Minute Hackathon Video Demonstration Script

**Project Title**: Personalized Glucose Digital Twin for Type 2 Diabetes  
**Team**: DMounas Lab (Debangshu Mounas, Solo)  
**Affiliation**: National Institute of Technology Silchar (NIT Silchar)  
**GitHub Repository**: https://github.com/DMounas/personalized-glucose-digital-twin  
**Target Video Duration**: 16–18 minutes  

---

## Video Outline & Timestamp Breakdown

| Section | Topic | Target Timestamp | Visual / Screen Focus |
| :--- | :--- | :--- | :--- |
| **1** | Title, Team & Problem Statement | 00:00 – 02:30 | Title slide & Clinical challenge slides |
| **2** | Healthcare Use Case & Patient Impact | 02:30 – 04:30 | Healthcare workflows & T2D physiology |
| **3** | Dataset & Data Quality Control | 04:30 – 06:45 | CGMacros cohort table & run segmentation |
| **4** | Leakage Countermeasures & Guard Band | 06:45 – 09:15 | Guard-band timeline diagram & 5 safeguards |
| **5** | Stage 2 Global Forecasting Benchmark | 09:15 – 12:00 | 8-rung benchmark ladder & Ridge vs GBDT |
| **6** | Stage 3 Chronological Personalization | 12:00 – 14:15 | Residual calibration dynamics & dose-response |
| **7** | Interactive Streamlit Dashboard Tour | 14:15 – 17:00 | Live `app.py` walkthrough across all 4 modules |
| **8** | Responsible AI, Limitations & Conclusion | 17:00 – 18:30 | Limitations, reproducible CLI & closing |

---

## Detailed Speaker Script & On-Screen Actions

### Section 1: Introduction, Team & Clinical Problem (00:00 – 02:30)

**[Visual: Title Slide — Project Name, Team DMounas Lab, NIT Silchar, GitHub URL]**

> "Hello judges and review committee. My name is Debangshu Mounas, presenting **DMounas Lab** from the **National Institute of Technology Silchar**.
>
> Today, I am presenting our project: **Personalized Glucose Digital Twin for Type 2 Diabetes** — a leak-free, physiological continuous glucose forecasting framework and participant-specific calibration engine.
>
> Over 537 million adults globally live with diabetes, predominantly Type 2 Diabetes. Continuous Glucose Monitoring (CGM) sensors have transformed care by logging interstitial glucose every 5 minutes. However, clinicians and patients face a fundamental challenge: **CGMs are inherently reactive**. They alert a patient only after hypoglycemia or severe hyperglycemia is already occurring.
>
> Predictive glucose digital twins aim to forecast glucose trajectories 30 to 60 minutes into the future, providing an actionable therapeutic window. Yet, across published biomedical machine learning literature, retrospective models routinely fail to translate into real-world practice. Why? Because of subtle, pervasive **temporal data leakage**."

**[Visual: Slide 3 — The Three Hidden Failure Modes]**

> "Our investigation identified three structural vulnerabilities in ambulatory CGM machine learning:
> 1. **Telemetry Interpolation Bleed**: Raw CGM sensors transmit every 5 minutes, but research datasets often resample to 1-minute intervals via interpolation. Using $y(t)$ to predict $y(t+30)$ when $y(t)$ was interpolated using future sensor packets creates severe artificial performance inflation.
> 2. **Intra-Participant Contamination**: Random $k$-fold cross-validation mixes readings from the same individual into both training and test sets. Algorithms memorize individual glucose baselines rather than learning transferable glycemic physiology.
> 3. **High Inter-Individual Metabolic Heterogeneity**: Differences in insulin sensitivity, hepatic glucose output, and beta-cell responsiveness mean fixed population models underperform when deployed on unseen patients."

---

### Section 2: Healthcare Use Case & Clinical Motivation (02:30 – 04:30)

**[Visual: Slide 4 & 5 — Healthcare Use Case & Clinical Value Chain]**

> "Let us look at the healthcare use case. In Type 2 Diabetes management, postprandial glucose spikes and delayed hypoglycemic events drive microvascular and macrovascular complications.
>
> Our Digital Twin serves three clinical and digital health tiers:
> - **Proactive Glycemic Alerts**: Giving patients 30 to 60 minutes of lead time before postprandial hyperglycemia peaks, enabling timely behavioral interventions like light walking or meal adjustments.
> - **Clinician Decision Support**: Allowing endocrinologists and diabetes educators to evaluate how well a global population model fits an individual patient, identifying whether that patient exhibits high residual variance.
> - **Zero-Retraining Personalization**: Rapidly calibrating the system within 6 days of sensor wear without retraining large black-box neural networks or sending private clinical data to centralized servers."

---

### Section 3: Dataset & Data Integrity (04:30 – 06:45)

**[Visual: Slide 6 — Dataset & Cohort Characterization]**

> "To benchmark this rigorously without synthetic shortcuts, we utilized the open-access **PhysioNet CGMacros cohort** (Bent et al., Scientific Data 2025).
>
> The cohort comprises **45 diverse individuals** across the metabolic spectrum:
> - 15 Normoglycemic controls
> - 16 Prediabetic individuals
> - 14 Individuals with diagnosed Type 2 Diabetes
>
> In total, this provides **123,599 strictly validated forecast issuance origins** across contiguous telemetry runs.
>
> Rather than heuristic interpolation across missing intervals, our ingestion pipeline enforces strict **$\Delta t = 60\text{ s}$ run segmentation**. If telemetry drops out for more than 60 seconds, the run terminates immediately, ensuring zero synthetic data points enter the evaluation matrix."

---

### Section 4: Architectural Leakage Safeguards (06:45 – 09:15)

**[Visual: Slide 7 & 8 — Temporal Guard-Band Diagram & 5 Safeguards]**

> "Now, let us examine our five architectural leakage protections:
>
> 1. **The 5-Minute Guard Band Gap ($[t-5, t]$)**:
>    Look closely at this timeline diagram. Between the latest permitted history lag at $t-5$ minutes and the forecast issuance point $t$, we enforce a mandatory 5-minute blackout zone with zero sensor inputs. This strictly prevents sensor-level smoothing filters from bleeding future information backwards.
> 2. **13 Permitted Autoregressive Lags**:
>    Predictors are strictly bounded to $[y(t-65), y(t-60), \dots, y(t-5)]$, defining a causal 60-minute observational window.
> 3. **Multimodal Feature Integration ($\mathbb{R}^{20}$ Space)**:
>    In addition to 13 glucose lags, we incorporate 3 causal meal-timing indicators (minutes since last meal, meal within 60 min, no recent meal) and 4 static clinical covariates (Age, Sex, BMI, and baseline HbA1c).
> 4. **Participant-Disjoint Cross-Validation**:
>    We evaluate across **10 repeated 5-fold splits** ($50$ disjoint folds). In every single fold, evaluation participants are completely withheld during model fitting and hyperparameter selection.
> 5. **Participant-Level Bootstrap Resampling ($B = 2,000$)**:
>    All confidence intervals are constructed by resampling 45 independent participant clusters, guaranteeing that standard errors reflect true between-patient variance."

---

### Section 5: Stage 2 Global Forecasting Benchmark (09:15 – 12:00)

**[Visual: Slide 9 & 10 — Global Benchmark Ladder & Results]**

> "We developed an **8-rung progressive benchmark ladder** to evaluate each incremental feature family under identical conditions:
>
> - **Rung 0 (Guarded Persistence)**: Sets our rigorous baseline — +30m RMSE is 21.55 mg/dL; +60m RMSE is 29.32 mg/dL.
> - **Rung 1 (Damped Trend Extrapolation)**: Yields minimal improvement (+0.7% skill), showing simple velocity extrapolation is insufficient.
> - **Rung 2 (Guarded Ridge Regression)**: 13 autoregressive lags reduce error significantly to 19.87 mg/dL at +30m and 26.97 mg/dL at +60m (+8.0% skill).
> - **Rung 3 & 4 (Physical Activity & Meal Timing)**: Adding causal meal timing further improves accuracy without requiring noisy manual macronutrient estimation.
> - **Rung 5 (Baseline Covariates Ridge)**: Incorporating Age, Sex, BMI, and HbA1c achieves our best population model:
>   - **+30-Minute RMSE: 18.85 mg/dL (+11.82% skill vs. persistence)**
>   - **+60-Minute RMSE: 25.45 mg/dL (+11.85% skill vs. persistence)**
>
> **Rung 6 (Nonlinear Gradient-Boosted Decision Trees)**:
> When we benchmarked `HistGradientBoostingRegressor` on the exact same 20 features, it achieved 19.15 mg/dL (+30m) and 25.64 mg/dL (+60m). The paired bootstrap difference between GBDT and Rung 5 Ridge **crosses zero at both horizons**. GBDT did not demonstrate a statistically significant overall advantage over linear Ridge, while Ridge trains in milliseconds with closed-form mathematical guarantees."

---

### Section 6: Stage 3 Chronological Personalization (12:00 – 14:15)

**[Visual: Slide 11 & 12 — Personalization Methodology & Results]**

> "Despite strong population performance, diabetes remains an individualized disease. In Stage 3, we tested online chronological adaptation.
>
> For each unseen participant:
> - We reserve their first **2, 4, or 6 study days** for adaptation.
> - We impose a **$\ge 120$-minute temporal purge buffer** between adaptation and evaluation to prevent autoregressive spillover.
> - We fit a regularized Ridge residual-correction model on the difference $y(t+h) - \hat{y}_{\text{global}}(t+h)$ using 16 dynamic features.
>
> **The Results**:
> - At **2 days**, telemetry is too sparse and the difference spans zero.
> - At **4 days**, paired error drops by $-1.15\text{ mg/dL}$ at +60m ($p < 0.05$).
> - At **6 days**, personalization achieves a headline **$-1.81\text{ mg/dL}$ paired error reduction** (from 22.71 to 20.90 mg/dL, an **8.0% relative error reduction**), with a 95% bootstrap CI of $[-2.43, -1.09]\text{ mg/dL}$ that strictly excludes zero.
> - **40 out of 45 participants (88.9%)** experience improved forecast accuracy.
> - In Type 2 Diabetic subjects, who exhibit the highest baseline glycemic excursions, absolute error reduction is greatest: $-2.34\text{ mg/dL}$."

---

### Section 7: Live Interactive Streamlit Dashboard Tour (14:15 – 17:00)

**[Action: Switch screen share to local browser running `streamlit run app.py` at `http://localhost:8501`]**

> "Let us explore the live research dashboard built with Streamlit and Plotly, designed in our mild green and white dual-tone clinical palette without distracting emojis.
>
> **Module 1: Project Overview**  
> Here we see the executive cohort metrics: 45 subjects, 50 disjoint cross-validation folds, +11.85% population skill, and $-1.81\text{ mg/dL}$ 6-day adaptation benefit. Below, the system architecture and the $\mathbb{R}^{20}$ feature matrix breakdown are displayed clearly.
>
> **Module 2: Global Forecasting Explorer**  
> [Click radio: 'Global Forecasting Explorer']  
> Here the user can interactively toggle between the +30-minute and +60-minute forecast horizons. The interactive Plotly bar chart plots all 8 rungs with their asymmetric 95% bootstrap confidence intervals and the red dashed persistence reference line. The table below details exact numerical metrics and fraction of improved participants.
>
> **Module 3: Personalization Lab**  
> [Click radio: 'Personalization Lab']  
> This is our core experimental interactive environment. Let's switch between 2 Days, 4 Days, and 6 Study Days. Notice the real-time statistical disclosure banner: at +30m, it transparently reminds researchers that the CI spans zero. But when we switch to +60m and 6 Study Days, the banner confirms a statistically significant benefit ($p < 0.05$). The dose-response trajectory bar chart and the paired $\Delta\text{RMSE}$ scatter chart illustrate the monotonic calibration trajectory. Below, the subgroup table breaks down results across Normal, Prediabetes, and T2D cohorts.
>
> **Module 4: Methodology & Guard Band**  
> [Click radio: 'Methodology & Guard Band']  
> Finally, this module presents our temporal guard-band schematic, contrasting the population benchmark protocol against the personalization protocol, alongside responsible use disclosures."

---

### Section 8: Technical Stack, Responsible AI & Conclusion (17:00 – 18:30)

**[Visual: Slide 14, 15, 16 & 17 — Tech Stack, Responsible Use & Closing]**

> "Under the hood, our technical stack emphasizes reproducibility and zero bloat:
> - **Python 3.10–3.12** supported natively.
> - **Scikit-learn, NumPy, Pandas, Plotly, Streamlit**.
> - **Strict Quality Gates**: 135 unit and integration tests passing (`pytest`), type-checked with `mypy`, formatted and linted with `ruff`, and verified via GitHub Actions CI across all three Python versions.
> - **Open-Source MIT License**: Code is fully open-source with explicit attribution to PhysioNet CGMacros.
>
> **Responsible AI & Limitations**:
> We reiterate that this is an ambulatory research framework. It is not an FDA-cleared device, does not establish causal physiological mechanisms, and must never be used for insulin titration or clinical treatment.
>
> In conclusion, our digital twin demonstrates that by pairing rigorous data hygiene — specifically the 5-minute guard band and temporal purge buffers — with lightweight regularized residual calibration, continuous glucose digital twins can achieve robust, personalized forecasting across diverse diabetic phenotypes.
>
> All code, documentation, architecture diagrams, and slide decks are publicly available on GitHub at `DMounas/personalized-glucose-digital-twin`.
>
> Thank you for your time, and I welcome your evaluation."

---

## Technical Checklist for Video Recording

- [ ] Ensure local dashboard is running: `streamlit run app.py`
- [ ] Set browser window to 1080p (1920x1080) at 100% zoom
- [ ] Display slides in full-screen presentation mode
- [ ] Record microphone audio with noise suppression
- [ ] Verify total recording time is between 15:00 and 19:30 minutes
- [ ] Export video in MP4 format (H.264/AAC, 1080p, 30fps)
- [ ] Upload to YouTube as **Unlisted** and update the README URL placeholder
