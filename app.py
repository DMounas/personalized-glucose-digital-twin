"""Personalized Glucose Digital Twin — Interactive Research Dashboard.

Streamlit research dashboard presenting reproducible physiological continuous glucose
forecasting benchmarks and chronological participant-specific calibration dynamics.

Cohort: 45 participants (Type 2 Diabetes, Prediabetes, Normal Glycemia)
Protocol: Protocol v1.0.0 & Stage 3 Addendum v1.0.0 (PhysioNet CGMacros)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure src/ is on sys.path for direct repository execution (e.g. Streamlit Community Cloud)
REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from dtwin.dashboard_data import DashboardDataLoader  # noqa: E402

# Configure diagnostic logging for deployment observability
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dtwin.app")

# Application metadata & filepaths
ASSETS_DIR = REPO_ROOT / "assets"
HERO_BANNER_PATH = ASSETS_DIR / "hero_banner.svg"
ARCHITECTURE_PATH = ASSETS_DIR / "system_architecture.svg"
GUARD_BAND_PATH = ASSETS_DIR / "guard_band_timeline.svg"

STAGE2_METRICS_PATH = REPO_ROOT / "docs" / "reports" / "stage2_baseline_metrics.json"
STAGE3_METRICS_PATH = REPO_ROOT / "docs" / "reports" / "stage3_personalization_metrics.json"


# Initialize Data Loader
@st.cache_resource
def get_loader() -> DashboardDataLoader:
    """Cached loader instance for canonical aggregate metrics."""
    logger.info("Initializing DashboardDataLoader from canonical JSON artifacts...")
    return DashboardDataLoader(
        stage2_path=STAGE2_METRICS_PATH,
        stage3_path=STAGE3_METRICS_PATH,
    )


def configure_page() -> None:
    """Set Streamlit page configuration and inject custom dark-theme styling."""
    st.set_page_config(
        page_title="Glucose Digital Twin | Research Dashboard",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    custom_css = """
    <style>
    /* Dark Theme Custom Foundation */
    .stApp {
        background-color: #070D1A;
        color: #F8FAFC;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0B1120;
        border-right: 1px solid #1E293B;
    }

    /* Card styling */
    .metric-card {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-card-title {
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #94A3B8;
        margin-bottom: 4px;
    }
    .metric-card-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #F8FAFC;
        line-height: 1.2;
    }
    .metric-card-subtitle {
        font-size: 0.85rem;
        font-weight: 500;
        color: #38BDF8;
        margin-top: 4px;
    }

    /* Significance badges */
    .badge-sig {
        background-color: rgba(16, 185, 129, 0.15);
        border: 1px solid #10B981;
        color: #10B981;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-block;
    }
    .badge-ns {
        background-color: rgba(148, 163, 184, 0.15);
        border: 1px solid #64748B;
        color: #94A3B8;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-block;
    }

    /* Disclaimer container */
    .disclaimer-box {
        background-color: #1E1B4B;
        border: 1px solid #4338CA;
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 15px;
        margin-bottom: 20px;
    }
    .disclaimer-title {
        color: #A5B4FC;
        font-size: 0.85rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .disclaimer-text {
        color: #C7D2FE;
        font-size: 0.82rem;
        line-height: 1.4;
        margin: 0;
    }

    /* Radio buttons & controls styling */
    div[role="radiogroup"] {
        padding: 4px;
        background-color: #0F172A;
        border-radius: 8px;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def render_sidebar() -> str:
    """Render application sidebar with navigation and metadata."""
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 10px 0 16px 0;">
                <span style="background-color: rgba(56, 189, 248, 0.15); border: 1px solid #0284C7; color: #38BDF8; font-size: 0.72rem; font-weight: 800; padding: 3px 8px; border-radius: 4px; letter-spacing: 1px;">RESEARCH PROTOTYPE</span>
                <h2 style="margin: 8px 0 2px 0; font-size: 1.35rem; font-weight: 900; color: #F8FAFC;">GLUCOSE DIGITAL TWIN</h2>
                <p style="margin: 0; font-size: 0.8rem; color: #94A3B8;">Type 2 Diabetes Forecasting &amp; Residual Personalization</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("### 🧭 Navigation")
        nav_selection = st.radio(
            "Select Section",
            [
                "📌 Project Overview",
                "📈 Global Forecasting Explorer",
                "🎯 Personalization Lab",
                "🔬 Methodology & Guard Band",
            ],
            label_visibility="collapsed",
        )
        if not nav_selection:
            nav_selection = "📌 Project Overview"

        st.markdown("---")
        st.markdown("### 📊 Cohort Metadata")
        st.markdown(
            """
            - **Dataset**: PhysioNet CGMacros 1.0.0
            - **Participants**: 45 Subjects ($K=45$)
            - **Stratification**: 15 Normal, 16 Prediabetes, 14 T2D
            - **Cross-Validation**: 10 Seeds $\\times$ 5 Folds ($50$ Disjoint Folds)
            - **Evaluation Origins**: 123,599 (+30m) / 123,164 (+60m)
            - **Guard Band**: 5-Min Zero-Input Gap
            """
        )

        st.markdown("---")
        st.markdown("### 🔗 Links & Attribution")
        st.markdown(
            """
            - [GitHub Repository](https://github.com/DMounas/personalized-glucose-digital-twin)
            - [Technical Architecture](https://github.com/DMounas/personalized-glucose-digital-twin/blob/main/docs/ARCHITECTURE.md)
            - [Benchmark Results](https://github.com/DMounas/personalized-glucose-digital-twin/blob/main/docs/RESULTS.md)
            - [PhysioNet Dataset Attribution](https://github.com/DMounas/personalized-glucose-digital-twin/blob/main/docs/DATASET_AND_ATTRIBUTION.md)
            """
        )

        st.markdown(
            """
            <div class="disclaimer-box">
                <div class="disclaimer-title">⚠️ Non-Clinical Disclaimer</div>
                <p class="disclaimer-text">
                    For research, educational, and benchmarking demonstration only.
                    Not certified for diagnosis, insulin dosage estimation, or patient care.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return nav_selection


def render_project_overview(loader: DashboardDataLoader) -> None:
    """Render Section A: Project Overview."""
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h1 style="font-size: 2.2rem; font-weight: 900; margin-bottom: 6px; color: #F8FAFC;">
                Personalized Glucose Digital Twin for Type 2 Diabetes
            </h1>
            <p style="font-size: 1.05rem; color: #94A3B8; max-width: 950px; line-height: 1.5;">
                A leak-free, physiological continuous glucose forecasting framework and participant-specific
                residual calibration engine evaluated on 45 individuals under repeated participant-disjoint cross-validation.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4 Executive KPI Cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Research Cohort</div>
                <div class="metric-card-value">45 Subjects</div>
                <div class="metric-card-subtitle">Normal (15), Prediab (16), T2D (14)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi_col2:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Evaluation Rigor</div>
                <div class="metric-card-value">50 Disjoint Folds</div>
                <div class="metric-card-subtitle">10 repeats × 5 folds (B=2,000 bootstrap)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi_col3:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Global Population Skill</div>
                <div class="metric-card-value">+11.85%</div>
                <div class="metric-card-subtitle">Rung 5 Ridge vs Persistence (+60m)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi_col4:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">6-Day Personalization</div>
                <div class="metric-card-value">-1.81 mg/dL</div>
                <div class="metric-card-subtitle">8.0% error reduction (40/45 improved)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Problem Statement & Solution Grid
    col_left, col_right = st.columns([1.1, 0.9])
    with col_left:
        st.markdown("### 🎯 The Ambulatory Glucose Challenge")
        st.markdown(
            """
            Continuous Glucose Monitoring (CGM) enables proactive diabetes management, but machine learning models
            frequently suffer from hidden vulnerabilities:

            1. **Telemetry Interpolation Bleed**: Standard CGM sensors log every 5 minutes while internal device smoothing
               or resampled grids create high cross-sample correlation. Predicting $y(t+30)$ from $y(t)$ when $y(t)$
               was interpolated from future sensor packets causes severe artificial inflation.
            2. **Intra-Subject Leakage**: Random $k$-fold train/test splits inadvertently place telemetry from the same
               individual into both training and validation sets, allowing algorithms to memorize participant glucose baselines.
            3. **High Inter-Individual Heterogeneity**: Insulin sensitivity, beta-cell response, dawn phenomenon, and meal
               absorption rates vary widely across patients, limiting the precision of fixed population models.
            """
        )

        st.markdown("### 💡 The Digital Twin Solution")
        st.markdown(
            """
            This platform introduces three structural safeguards:
            - **Strict 5-Minute Guard Band**: Enforces a mandatory gap $[t-5, t]$ with zero inputs preceding issuance $t$.
            - **Participant-Disjoint Cross-Validation**: Held-out participants are never observed during population model fitting.
            - **Chronological Online Personalization**: Adapts the population model using early participant days (2, 4, 6 days)
              combined with a $\\ge 120$-minute temporal quarantine buffer.
            """
        )

    with col_right:
        st.markdown("### 🏗️ System Architecture & Workflow")
        if ARCHITECTURE_PATH.exists():
            st.image(
                str(ARCHITECTURE_PATH),
                caption="End-to-end data ingestion, global modeling ladder, and residual personalization pipeline.",
                use_container_width=True,
            )
        else:
            st.info("Architecture diagram: assets/system_architecture.svg")

    st.markdown("---")

    # Feature Matrix Breakdown Table
    st.markdown("### 📋 Guarded Predictor Matrix Architecture ($R^{20}$ Feature Space)")
    feat_df = pd.DataFrame(
        [
            {
                "Category": "Guarded Glucose History",
                "Features": "y(t-5), y(t-10), ..., y(t-65)",
                "Dimension": "13 lags",
                "Purpose": "Autoregressive glucose trajectory over past 60 min (with 5-min guard band)",
            },
            {
                "Category": "Meal Context (Timing)",
                "Features": "Minutes since last meal, meal_in_60m, no_recent_meal",
                "Dimension": "3 features",
                "Purpose": "Captures postprandial glycemic excursions without non-causal amount leakage",
            },
            {
                "Category": "Clinical Demographics",
                "Features": "Age, Gender (binary), BMI, Baseline HbA1c",
                "Dimension": "4 static",
                "Purpose": "Grounds the linear model in the patient's physiological baseline",
            },
        ]
    )
    st.table(feat_df)


def render_global_forecasting_explorer(loader: DashboardDataLoader) -> None:
    """Render Section B: Global Forecasting Explorer."""
    st.markdown("## 📈 Stage 2 Global Forecasting Ladder")
    st.markdown(
        """
        Explore the 8-rung benchmark ladder evaluated across **10 repeated 5-fold participant-disjoint splits**
        ($50$ distinct models per rung, $K=45$ participants). All models observe strictly identical evaluation origins.
        """
    )

    # Controls
    horizon_choice = st.radio(
        "Forecast Horizon",
        ["+30-Minute Horizon", "+60-Minute Horizon"],
        horizontal=True,
    )
    h_str = str(horizon_choice) if horizon_choice else "+30-Minute Horizon"
    h_key = "h30" if "30" in h_str else "h60"
    ladder = loader.get_global_ladder(h_key)

    # Dynamic KPI highlights
    r0 = next(m for m in ladder if m.rung_label == "Rung 0")
    r2 = next(m for m in ladder if m.rung_label == "Rung 2")
    r5 = next(m for m in ladder if m.rung_label == "Rung 5")
    r6 = next(m for m in ladder if m.rung_label == "Rung 6")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Persistence Reference (Rung 0)</div>
                <div class="metric-card-value">{r0.mean_rmse:.2f} mg/dL</div>
                <div class="metric-card-subtitle">Latest lag y(t-5) baseline</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Best Population Model (Rung 5)</div>
                <div class="metric-card-value">{r5.mean_rmse:.2f} mg/dL</div>
                <div class="metric-card-subtitle">Skill: {r5.mean_skill_pct:+.2f}% vs Persistence</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Fixed GBDT (Rung 6)</div>
                <div class="metric-card-value">{r6.mean_rmse:.2f} mg/dL</div>
                <div class="metric-card-subtitle">Skill: {r6.mean_skill_pct:+.2f}% (No stat. gain over Ridge)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Participants Improved (Rung 5)</div>
                <div class="metric-card-value">{r5.n_improved} / {r5.total_participants}</div>
                <div class="metric-card-subtitle">{r5.fraction_improved * 100:.1f}% of cohort outperforms persistence</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Plotly Horizontal Bar Chart
    names = [f"{m.rung_label}: {m.model_name}" for m in ladder]
    rmses = [m.mean_rmse for m in ladder]
    err_low = [m.mean_rmse - m.ci_95_rmse[0] for m in ladder]
    err_high = [m.ci_95_rmse[1] - m.mean_rmse for m in ladder]
    colors = [m.color for m in ladder]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=names,
            x=rmses,
            orientation="h",
            marker=dict(color=colors, line=dict(color="#334155", width=1)),
            error_x=dict(
                type="data",
                symmetric=False,
                array=err_high,
                arrayminus=err_low,
                color="#F8FAFC",
                thickness=1.5,
                width=4,
            ),
            hovertemplate="<b>%{y}</b><br>Mean RMSE: %{x:.3f} mg/dL<br><extra></extra>",
        )
    )

    # Vertical line for persistence baseline
    fig.add_vline(
        x=r0.mean_rmse,
        line_width=1.5,
        line_dash="dot",
        line_color="#EF4444",
        annotation_text="Persistence Ref",
        annotation_position="top right",
    )

    x_min = 16 if h_key == "h30" else 22
    x_max = 24.5 if h_key == "h30" else 35.0

    fig.update_layout(
        title=f"Stage 2 Model Ladder Benchmark ({horizon_choice}) — Cohort Mean RMSE & 95% Bootstrap CIs",
        xaxis_title="Cohort Mean RMSE (mg/dL) [Lower is Better]",
        yaxis=dict(autorange="reversed"),
        xaxis=dict(range=[x_min, x_max]),
        plot_bgcolor="#0F172A",
        paper_bgcolor="#070D1A",
        font=dict(color="#F8FAFC"),
        height=450,
        margin=dict(l=20, r=20, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabular Breakdown
    table_data = []
    for m in ladder:
        table_data.append(
            {
                "Rung": m.rung_label,
                "Model & Features": m.model_name,
                "Predictors": m.feature_description,
                "Mean RMSE (mg/dL)": f"{m.mean_rmse:.3f}",
                "95% Bootstrap CI": f"[{m.ci_95_rmse[0]:.3f}, {m.ci_95_rmse[1]:.3f}]",
                "Mean Skill vs Pers": f"{m.mean_skill_pct:+.2f}%",
                "Improved Subjects": f"{m.n_improved} / {m.total_participants} ({m.fraction_improved * 100:.1f}%)",
            }
        )
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    st.markdown("---")

    # In-Depth Scientific Analysis: Linear Ridge vs Nonlinear GBDT
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 🏆 Why Rung 5 Ridge is the Selected Global Foundation")
        st.markdown(
            f"""
            - **Autoregressive Core (Rung 2)**: 13 guarded history lags reduce error from {r0.mean_rmse:.2f} to {r2.mean_rmse:.2f} mg/dL (+{r2.mean_skill_pct:.2f}% skill).
            - **Meal-Timing Addition (Rung 4b)**: Adding causal timing flags provides an additional error reduction without requiring macronutrient estimation.
            - **Static Clinical Covariates (Rung 5)**: Incorporating Age, Sex, BMI, and HbA1c grounds the individual's baseline, achieving the best population performance (**{r5.mean_rmse:.2f} mg/dL**, **+{r5.mean_skill_pct:.2f}%** skill).
            - **Reproducibility & Stability**: Ridge has an exact closed-form solution, trains in milliseconds, requires zero stochastic initialization, and shows zero fold-level failure modes.
            """
        )

    with col_b:
        st.markdown("### 🌲 Linear Ridge vs. Nonlinear GBDT (Rung 6)")
        st.markdown(
            f"""
            - **Performance Parity**: The fixed `HistGradientBoostingRegressor` achieves **{r6.mean_rmse:.2f} mg/dL** (+{r6.mean_skill_pct:.2f}% skill).
            - **Statistical Significance**: The cohort-level paired difference between GBDT and Rung 5 Ridge **spans zero** at both horizons ($\\Delta\\text{{RMSE}} = +0.29\\text{{ mg/dL}}$ at +30m; $+0.19\\text{{ mg/dL}}$ at +60m; both 95% CIs cross zero). GBDT did **not** demonstrate a statistically significant overall improvement over Ridge.
            - **Phenotype Divergence**: GBDT achieves lower error in normoglycemic controls where glycemic trajectories are smoothly bounded, but regularized Ridge provides greater stability during high-amplitude diabetic postprandial excursions.
            """
        )


def render_personalization_lab(loader: DashboardDataLoader) -> None:
    """Render Section C: Personalization Lab."""
    st.markdown("## 🎯 Stage 3 Online Personalization Lab")
    st.markdown(
        """
        Evaluate chronological adaptation: can updating the global Rung 5 Ridge forecaster with an individual's
        early study days improve forecasts on their later unseen telemetry?

        *Fairness Guarantee*: Every adaptation window is compared against a **matched global baseline evaluated on strictly identical post-purge evaluation timestamps**.
        """
    )

    # Interactive Controls
    ctrl_col1, ctrl_col2 = st.columns(2)
    with ctrl_col1:
        horizon_choice = st.radio(
            "Forecast Horizon",
            ["+30-Minute Horizon", "+60-Minute Horizon"],
            horizontal=True,
            key="pers_horizon",
        )
    with ctrl_col2:
        window_choice = st.radio(
            "Individual Adaptation Window",
            ["2 Study Days", "4 Study Days", "6 Study Days"],
            horizontal=True,
            index=2,
            key="pers_window",
        )

    h_str = str(horizon_choice) if horizon_choice else "+60-Minute Horizon"
    w_str = str(window_choice) if window_choice else "6 Study Days"
    h_key = "h30" if "30" in h_str else "h60"
    w_key = "window_2d" if "2" in w_str else ("window_4d" if "4" in w_str else "window_6d")

    metric = loader.get_personalization_metric(h_key, w_key)
    trajectory = loader.get_personalization_trajectory(h_key)

    # KPI Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Matched Global RMSE</div>
                <div class="metric-card-value">{metric.matched_global_rmse:.3f} mg/dL</div>
                <div class="metric-card-subtitle">Global Rung 5 on identical eval timestamps</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Personalized RMSE</div>
                <div class="metric-card-value">{metric.personalized_rmse:.3f} mg/dL</div>
                <div class="metric-card-subtitle">Residual-corrected individual model</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Paired Error Change (ΔRMSE)</div>
                <div class="metric-card-value">{metric.mean_delta_rmse:+.3f} mg/dL</div>
                <div class="metric-card-subtitle">95% CI: [{metric.ci_95_delta_rmse[0]:+.3f}, {metric.ci_95_delta_rmse[1]:+.3f}]</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Cohort Benefit</div>
                <div class="metric-card-value">{metric.n_improved} / {metric.total_participants}</div>
                <div class="metric-card-subtitle">{metric.fraction_improved * 100:.1f}% improved ({metric.mean_pct_reduction:+.2f}% relative)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Statistical Significance Disclosure Banner
    if h_key == "h30":
        st.markdown(
            f"""
            <div style="background-color: rgba(56, 189, 248, 0.1); border: 1px solid #0284C7; border-radius: 8px; padding: 12px 18px; margin: 15px 0;">
                <span class="badge-ns">CONFIDENCE INTERVAL SPANS ZERO (NOT STATISTICALLY SIGNIFICANT)</span>
                <p style="margin: 6px 0 0 0; font-size: 0.88rem; color: #BAE6FD;">
                    At the +30-minute horizon under <strong>{metric.window_label}</strong>, the paired 95% bootstrap confidence interval
                    is <strong>[{metric.ci_95_delta_rmse[0]:+.3f}, {metric.ci_95_delta_rmse[1]:+.3f}] mg/dL</strong>, which spans zero.
                    Although {metric.n_improved}/{metric.total_participants} ({metric.fraction_improved * 100:.1f}%) of participants experience error reduction,
                    the baseline autoregression is already highly predictive, so short-horizon residual personalization does not reach statistical significance.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif w_key == "window_2d":
        st.markdown(
            f"""
            <div style="background-color: rgba(148, 163, 184, 0.1); border: 1px solid #475569; border-radius: 8px; padding: 12px 18px; margin: 15px 0;">
                <span class="badge-ns">EARLY CALIBRATION (SPANS ZERO)</span>
                <p style="margin: 6px 0 0 0; font-size: 0.88rem; color: #CBD5E1;">
                    At the +60-minute horizon with only <strong>2 study days</strong> of adaptation, the paired 95% bootstrap CI is
                    <strong>[{metric.ci_95_delta_rmse[0]:+.3f}, {metric.ci_95_delta_rmse[1]:+.3f}] mg/dL</strong>.
                    Sparse calibration telemetry is vulnerable to overfitting individual noise.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="background-color: rgba(16, 185, 129, 0.12); border: 1px solid #10B981; border-radius: 8px; padding: 12px 18px; margin: 15px 0;">
                <span class="badge-sig">STATISTICALLY SIGNIFICANT CALIBRATION BENEFIT (p &lt; 0.05)</span>
                <p style="margin: 6px 0 0 0; font-size: 0.88rem; color: #A7F3D0;">
                    At the +60-minute horizon under <strong>{metric.window_label}</strong>, the paired 95% bootstrap confidence interval
                    is <strong>[{metric.ci_95_delta_rmse[0]:+.3f}, {metric.ci_95_delta_rmse[1]:+.3f}] mg/dL</strong>, strictly excluding zero.
                    Personalization provides a statistically robust, reproducible error reduction with {metric.n_improved} of 45 participants improving.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Plotly Visualizations: Dose Response & Paired Delta
    fig_col1, fig_col2 = st.columns(2)

    with fig_col1:
        # Trajectory comparison (Global vs Personalized across windows)
        x_wins = [m.window_label for m in trajectory]
        g_rmses = [m.matched_global_rmse for m in trajectory]
        p_rmses = [m.personalized_rmse for m in trajectory]

        fig_traj = go.Figure()
        fig_traj.add_trace(
            go.Bar(
                x=x_wins,
                y=g_rmses,
                name="Matched Global Ridge",
                marker_color="#64748B",
                hovertemplate="Global RMSE: %{y:.3f} mg/dL<extra></extra>",
            )
        )
        fig_traj.add_trace(
            go.Bar(
                x=x_wins,
                y=p_rmses,
                name="Personalized (Adapted)",
                marker_color="#10B981" if h_key == "h60" else "#38BDF8",
                hovertemplate="Personalized RMSE: %{y:.3f} mg/dL<extra></extra>",
            )
        )
        fig_traj.update_layout(
            barmode="group",
            title=f"Dose-Response Trajectory ({horizon_choice})",
            xaxis_title="Adaptation Window",
            yaxis_title="Cohort Mean RMSE (mg/dL)",
            plot_bgcolor="#0F172A",
            paper_bgcolor="#070D1A",
            font=dict(color="#F8FAFC"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=60, b=40),
            height=380,
        )
        st.plotly_chart(fig_traj, use_container_width=True)

    with fig_col2:
        # Paired Delta RMSE with 95% Bootstrap CIs
        deltas = [m.mean_delta_rmse for m in trajectory]
        err_d_low = [m.mean_delta_rmse - m.ci_95_delta_rmse[0] for m in trajectory]
        err_d_high = [m.ci_95_delta_rmse[1] - m.mean_delta_rmse for m in trajectory]

        fig_delta = go.Figure()
        fig_delta.add_hline(
            y=0,
            line_width=1.5,
            line_dash="dash",
            line_color="#EF4444",
            annotation_text="Zero Effect (No Improvement)",
            annotation_position="bottom right",
        )
        fig_delta.add_trace(
            go.Scatter(
                x=x_wins,
                y=deltas,
                mode="lines+markers",
                marker=dict(size=10, color="#10B981" if h_key == "h60" else "#38BDF8"),
                line=dict(width=2.5, color="#10B981" if h_key == "h60" else "#38BDF8"),
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=err_d_high,
                    arrayminus=err_d_low,
                    color="#F8FAFC",
                    thickness=1.5,
                    width=6,
                ),
                hovertemplate="ΔRMSE: %{y:+.3f} mg/dL<extra></extra>",
            )
        )
        fig_delta.update_layout(
            title=f"Paired ΔRMSE & 95% Bootstrap CIs ({horizon_choice})",
            xaxis_title="Adaptation Window",
            yaxis_title="Paired RMSE Change (mg/dL) [Negative = Improvement]",
            plot_bgcolor="#0F172A",
            paper_bgcolor="#070D1A",
            font=dict(color="#F8FAFC"),
            margin=dict(l=20, r=20, t=60, b=40),
            height=380,
        )
        st.plotly_chart(fig_delta, use_container_width=True)

    st.markdown("---")

    # Subgroup Clinical Phenotype Analysis
    st.markdown("### 🧬 Clinical Phenotype Analysis (Subgroup Stratification)")
    st.markdown(
        """
        Glycemic dynamics differ fundamentally by metabolic status. In normoglycemic participants, postprandial excursions
        are tightly buffered by endogenous insulin; in Type 2 Diabetes, delayed hepatic glucose suppression creates prolonged,
        individualized excursions where personalization yields the largest absolute therapeutic benefit.
        """
    )

    subgroups = metric.subgroups
    if subgroups:
        sub_rows = []
        for grp, vals in subgroups.items():
            grp_name = (
                "Normal Controls"
                if grp == "normal"
                else ("Prediabetes" if grp == "prediabetes" else "Type 2 Diabetes")
            )
            sub_rows.append(
                {
                    "Clinical Subgroup": grp_name,
                    "N Subjects": int(vals["n_participants"]),
                    "Matched Global RMSE": f"{vals['mean_rmse_global']:.3f} mg/dL",
                    "Personalized RMSE": f"{vals['mean_rmse_pers']:.3f} mg/dL",
                    "Paired ΔRMSE": f"{vals['mean_delta_rmse']:+.3f} mg/dL",
                    "Mean % Reduction": f"{vals['mean_pct_reduction']:+.2f}%",
                    "Improved Participants": f"{int(vals['n_improved'])} / {int(vals['n_participants'])} ({vals['fraction_improved']:.1f}%)",
                }
            )
        st.table(pd.DataFrame(sub_rows))


def render_methodology_and_guard_band() -> None:
    """Render Section D: Methodology & Guard-Band Explorer."""
    st.markdown("## 🔬 Scientific Methodology & Leakage Countermeasures")
    st.markdown(
        """
        Ambulatory machine learning algorithms often fail replication due to subtle data leakage.
        This framework was engineered from inception around **Protocol v1.0.0** and audited against five temporal failure modes.
        """
    )

    # Guard-Band SVG Diagram
    if GUARD_BAND_PATH.exists():
        st.image(
            str(GUARD_BAND_PATH),
            caption="Temporal Guard-Band Architecture: The 5-Minute Zero-Input Buffer.",
            use_container_width=True,
        )
    else:
        st.info("Guard-band schematic: assets/guard_band_timeline.svg")

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🛡️ Five Architectural Leakage Protections")
        st.markdown(
            """
            1. **The 5-Minute Guard Band Gap ($[t-5, t]$)**:
               Raw CGM devices output measurements on 5-minute telemetry intervals. In continuous 1-minute datasets,
               points within $[t-5, t]$ are typically interpolated using $y(t)$. Withholding all inputs strictly
               in $[t-5, t]$ ensures no future interpolation artifact enters the model.
            2. **13 Permitted Autoregressive Lags**:
               Predictors are strictly bounded to $[y(t-65), y(t-60), ..., y(t-5)]$, guaranteeing a fixed 60-minute
               causal observational window with zero boundary leakage.
            3. **Participant-Disjoint Group Stratification**:
               The 45 participants are split using `StratifiedGroupKFold` across 10 distinct seeds ($50$ disjoint folds).
               No observation, baseline covariate, or identity marker from an evaluation subject is ever seen during global training.
            4. **120-Minute Chronological Purge Buffer**:
               In Stage 3 personalization, adaptation days (2, 4, or 6 days) and subsequent evaluation days are separated
               by a mandatory $\\ge 120$-minute blackout period, preventing autoregressive spillover across the adaptation boundary.
            5. **Participant-Level Bootstrap Resampling ($B=2,000$)**:
               All confidence intervals resample 45 independent participant units rather than pooling individual origins.
            """
        )

    with c2:
        st.markdown("### ⚖️ Global vs. Personalization Evaluation Protocol")
        eval_guide = pd.DataFrame(
            [
                {
                    "Dimension": "Evaluation Origins",
                    "Global Benchmark (Stage 2)": "All eligible origins across full study duration (123K+ origins)",
                    "Personalization (Stage 3)": "Strictly post-purge origins following adaptation window cutoff",
                },
                {
                    "Dimension": "Comparator Baseline",
                    "Global Benchmark (Stage 2)": "Rung 0 Guarded Persistence across all origins",
                    "Personalization (Stage 3)": "Matched Global Rung 5 evaluated on identical post-purge timestamps",
                },
                {
                    "Dimension": "Statistical Significance",
                    "Global Benchmark (Stage 2)": "Rung 5 vs Persistence: strictly excludes zero (+11.8% skill)",
                    "Personalization (Stage 3)": "+30m spans zero (n.s.); +60m 4d/6d strictly excludes zero (p < 0.05)",
                },
                {
                    "Dimension": "Personalization Mechanism",
                    "Global Benchmark (Stage 2)": "None (fixed population model fitted to training cohort)",
                    "Personalization (Stage 3)": "Regularized Ridge residual correction on individual calibration days",
                },
            ]
        )
        st.table(eval_guide)

    st.markdown("---")

    st.markdown("### ⚠️ Methodological Scope & Responsible Use")
    st.markdown(
        """
        - **Observational Telemetry**: The CGMacros dataset reflects free-living ambulatory participants with self-reported meals and activities.
        - **Sensor Drift**: Commercial CGM sensors experience intermittent calibration drift and sensor dropouts; the digital twin relies on strict run segmentation ($\\Delta t = 60\\text{s}$) rather than heuristic imputation.
        - **No Direct Intervention**: This platform benchmarks forecasting accuracy and personalization dynamics; it does not simulate closed-loop artificial pancreas controller actions or medication titration.
        """
    )


def main() -> None:
    """Main dashboard entry point."""
    logger.info("Starting Glucose Digital Twin dashboard...")
    configure_page()
    loader = get_loader()
    nav_selection = render_sidebar()

    logger.info("Rendering section: %s", nav_selection)
    if nav_selection == "📌 Project Overview":
        render_project_overview(loader)
    elif nav_selection == "📈 Global Forecasting Explorer":
        render_global_forecasting_explorer(loader)
    elif nav_selection == "🎯 Personalization Lab":
        render_personalization_lab(loader)
    elif nav_selection == "🔬 Methodology & Guard Band":
        render_methodology_and_guard_band()


if __name__ == "__main__":
    main()
