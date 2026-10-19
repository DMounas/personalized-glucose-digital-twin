# Project Brief: Patient-Adaptive Glucose Digital Twin

## 1. Project Goal
The primary objective of this project is to build a proof-of-concept healthcare "Digital Twin" for type 2 diabetes mellitus (T2D). The system combines clinical baseline markers with dynamic wearable continuous glucose monitoring (CGM) and lifestyle data to forecast short-term glucose excursions (hyperglycemia and hypoglycemia risk) and simulate bounded "what-if" counterfactual scenarios (e.g., changes in meal macronutrient balance or postprandial physical activity) via a conceptual clinician dashboard.

## 2. Competition Requirements
This project is engineered to satisfy the specific requirements of the chronic health digital twin challenge:
- **Chronic Condition Focus**: Type 2 diabetes mellitus (T2D) in the contextual framework of India's dual chronic disease burden.
- **Multimodal Data Fusion**: Fusing static/historical data (demographics, anthropometrics, lipid panels, HbA1c, baseline metabolic profiles) with dynamic sensor data (CGM sensor streams, continuous heart rate, metabolic activity, and meal timing/macronutrients).
- **Adverse Event Forecasting**: Predicting future acute adverse events (severe postprandial glycemic excursions: hyperglycemia >180 mg/dL or acute hypoglycemia <70 mg/dL).
- **Conceptual Clinician Dashboard**: A user-centric interface illustrating patient trajectories, uncertainty intervals, risk alerts, and what-if counterfactual explorations for clinician decision support.
- **Deliverables**: Public GitHub repository with comprehensive README, system architecture diagram, slide deck presentation, 20-minute walkthrough video, and clean reproducible code.
- **Data Governance**: Strict adherence to open-source, anonymized, and synthetic data streams without clinical patient re-identification or unvetted external health data leakage.

## 3. Provisional Concept
> **Provisional Architecture**: A patient-adaptive, uncertainty-aware glucose Digital Twin combining clinical baseline data with dynamic glucose/lifestyle data to forecast glucose excursions and explore carefully bounded what-if scenarios.

The digital twin models the patient's individual glycemic response by establishing personalized baseline sensitivity curves, adjusting dynamically for carbohydrate and macronutrient intake, and quantifying prediction uncertainty to ensure clinical interpretability.

## 4. Explicit Non-Goals
To maintain scientific rigor and engineering integrity, the following boundaries are strictly enforced:
- **NOT a Diagnostic or Treatment Tool**: This software is an engineering proof-of-concept; it is not certified as a medical device (SaMD) and must never be used for clinical diagnosis, treatment decisions, or insulin dose titration.
- **No Clinical Validation Claims**: No claim is made regarding clinical efficacy or diagnostic accuracy in live patient populations.
- **No Unsubstantiated Geographic Transferability**: No claim is made that synthetic data or North American cohort data validates predictive accuracy for populations in India. The Indian chronic disease dimension is explored as an explicit **[SYNTHETIC DEMO]** scenario.
- **No Distractive Decoration**: No ungrounded LLM chatbots, blockchain ledgers, or buzzword federated-learning modules that do not directly advance the core engineering challenge of glucose forecasting and simulation.

## 5. Planned Stage Sequence (Stages 0–8)
All stages are gated by automated testing, reproducible tooling, and verification reports:
- **Stage 0 (Current)**: Repository scaffold, data provenance, cross-platform dataset-audit tooling, and documentation. *(PLANNED / IN PROGRESS)*
- **Stage 1**: Exploratory data analysis, CGM sensor comparison (Libre vs Dexcom), and signal cleaning. *(PLANNED)*
- **Stage 2**: Data ingestion pipeline, multimodal alignment, and standardized feature representation. *(PLANNED)*
- **Stage 3**: Baseline statistical and machine learning forecasting models (ARIMA, LightGBM/XGBoost). *(PLANNED)*
- **Stage 4**: Uncertainty quantification and conformal prediction intervals for excursion forecasting. *(PLANNED)*
- **Stage 5**: Hybrid physiological metabolic modelling (e.g., modified Bergman minimal model) *(conditional on evidence from earlier stages)*. *(PLANNED)*
- **Stage 6**: What-if counterfactual simulation engine (macronutrient variation, physical activity shifts). *(PLANNED)*
- **Stage 7**: Conceptual clinician dashboard prototype and scenario visualizer. *(PLANNED)*
- **Stage 8**: Comprehensive benchmarking, presentation artifacts, video recording, and final release. *(PLANNED)*

## 6. Evidence-Labelling Convention
To maintain clarity across all technical documentation, code comments, and reports, all statements of fact, assumptions, and findings must be prefixed with one of the following four tags:

- **[ESTABLISHED]**: Information backed by a cited primary scientific publication, formal clinical trial, or verified documentation.
- **[HYPOTHESIS]**: An engineering hypothesis, design idea, or untested modelling assumption.
- **[SYNTHETIC DEMO]**: Illustrative demonstration data or synthetic profiles generated for pedagogical or interface testing, not evidence of real-world clinical accuracy.
- **[VERIFIED RESULT]**: An empirical result generated by an executed command within this repository, with the exact command, parameters, and git commit hash recorded.
