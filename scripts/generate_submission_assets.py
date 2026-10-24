"""Generate submission-ready architecture diagram and presentation assets in PDF and PPTX formats.

Produces:
- docs/submission/architecture.pdf
- docs/submission/architecture.pptx
- docs/submission/presentation.pdf
- docs/submission/presentation.pptx
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "docs" / "submission"

# Design Color Palette (Clinical Mild Green & White Dual-Tone)
COLOR_BG = RGBColor(248, 251, 249)  # #F8FBF9
COLOR_CARD_BG = RGBColor(255, 255, 255)  # #FFFFFF
COLOR_PRIMARY = RGBColor(20, 83, 45)  # #14532D Deep Forest Green
COLOR_ACCENT = RGBColor(22, 163, 74)  # #16A34A Mild Green
COLOR_TEXT_MAIN = RGBColor(30, 41, 59)  # #1E293B Dark Slate
COLOR_TEXT_MUTED = RGBColor(100, 116, 139)  # #64748B Muted Slate
COLOR_BORDER = RGBColor(214, 232, 220)  # #D6E8DC Soft Green Border
COLOR_PILL_BG = RGBColor(236, 253, 245)  # #ECFDF5 Mint Tint
COLOR_ALERT = RGBColor(220, 38, 38)  # #DC2626 Red

HEX_PRIMARY = "#14532D"
HEX_ACCENT = "#16A34A"
HEX_BG = "#F8FBF9"
HEX_CARD = "#FFFFFF"
HEX_BORDER = "#D6E8DC"
HEX_TEXT = "#1E293B"
HEX_MUTED = "#64748B"
HEX_PILL = "#ECFDF5"
HEX_ALERT = "#DC2626"


def create_architecture_pptx(output_path: Path) -> None:
    """Create polished architecture diagram deck in 16:9 widescreen PPTX."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    slide = prs.slides.add_slide(blank_layout)

    # Background shape
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_BG
    bg.line.color.rgb = COLOR_BORDER

    # Header Card
    hdr = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(0.5), Inches(12.133), Inches(1.1)
    )
    hdr.fill.solid()
    hdr.fill.fore_color.rgb = COLOR_CARD_BG
    hdr.line.color.rgb = COLOR_BORDER
    hdr.line.width = Pt(1.5)

    tf = hdr.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.3)
    tf.margin_top = Inches(0.15)
    p0 = tf.paragraphs[0]
    p0.text = "GLUCOSE DIGITAL TWIN — END-TO-END SYSTEM ARCHITECTURE"
    p0.font.bold = True
    p0.font.size = Pt(18)
    p0.font.color.rgb = COLOR_PRIMARY
    p0.font.name = "Arial"

    p1 = tf.add_paragraph()
    p1.text = "Leak-Free Ambulatory Glucose Forecasting Framework & Participant-Specific Residual Personalization Engine"
    p1.font.size = Pt(11)
    p1.font.color.rgb = COLOR_TEXT_MUTED
    p1.font.name = "Arial"

    # 4 Main Pipeline Columns (Cards)
    col_width = Inches(2.85)
    col_gap = Inches(0.24)
    top_pos = Inches(1.8)
    card_h = Inches(4.3)

    stages: list[dict[str, Any]] = [
        {
            "num": "01",
            "title": "DATA INGESTION & QC",
            "sub": "PhysioNet CGMacros (N=45)",
            "bullets": [
                "45 ambulatory participants across Normal (15), Prediabetes (16), T2D (14).",
                "Contiguous run segmentation with strict Delta t = 60s rule.",
                "Zero gap interpolation — runs truncate on missing telemetry.",
                "Lattice grid alignment: m(t) = round((t - t0) / 60s), issuance on m(t) mod 5 == 0.",
            ],
            "guard": "Zero boundary bleed; strict 1-min raw validation",
        },
        {
            "num": "02",
            "title": "GUARDED FEATURE MATRIX",
            "sub": "R^20 Multimodal Predictor Space",
            "bullets": [
                "Guarded Glucose History (13 lags): y(t-65) through y(t-5) over 60-min window.",
                "5-min Guard Band Gap: zero input permitted in [t-5, t] window.",
                "Meal-Timing Context (3 features): time since meal, meal in 60m, no recent meal.",
                "Clinical Demographics (4 static): Age, Sex, BMI, Baseline HbA1c.",
            ],
            "guard": "5-MIN GUARD BAND: prevents interpolation leakage",
        },
        {
            "num": "03",
            "title": "GLOBAL BENCHMARK",
            "sub": "Disjoint CV Ladder (Rungs 0-6)",
            "bullets": [
                "10 repeated 5-fold CV (50 disjoint folds, K=45 subjects).",
                "Train-only scaling & closed-form alpha hyperparameter selection.",
                "Rung 0: Guarded Persistence baseline (RMSE 21.55 / 29.32 mg/dL).",
                "Rung 5 Ridge: best global model (+11.8% skill at +30m & +60m).",
                "Rung 6 GBDT: nonlinear comparison (no stat. gain over Ridge).",
            ],
            "guard": "PARTICIPANT-DISJOINT: 0% intra-subject identity bleed",
        },
        {
            "num": "04",
            "title": "PERSONALIZATION & UI",
            "sub": "Stage 3 Residual Adaptation",
            "bullets": [
                "Chronological adaptation on early 2, 4, 6 study days.",
                "Ridge residual correction on r(t) = y(t+h) - y_hat_global.",
                "6-Day adaptation: -1.81 mg/dL (-8.0%) at +60m (40/45 improved).",
                "Streamlit Dashboard: interactive research exploration across 4 modules.",
            ],
            "guard": ">= 120-MIN PURGE BUFFER: prevents autoregressive spillover",
        },
    ]

    for idx, stg in enumerate(stages):
        left_pos = Inches(0.6) + idx * (col_width + col_gap)

        # Main Stage Card
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, top_pos, col_width, card_h
        )
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = COLOR_BORDER
        card.line.width = Pt(1.5)

        ctf = card.text_frame
        ctf.word_wrap = True
        ctf.margin_left = Inches(0.2)
        ctf.margin_right = Inches(0.2)
        ctf.margin_top = Inches(0.18)

        cp0 = ctf.paragraphs[0]
        cp0.text = f"STAGE {stg['num']}"
        cp0.font.bold = True
        cp0.font.size = Pt(9.5)
        cp0.font.color.rgb = COLOR_ACCENT
        cp0.font.name = "Arial"

        cp1 = ctf.add_paragraph()
        cp1.text = stg["title"]
        cp1.font.bold = True
        cp1.font.size = Pt(13)
        cp1.font.color.rgb = COLOR_PRIMARY
        cp1.font.name = "Arial"

        cp2 = ctf.add_paragraph()
        cp2.text = stg["sub"]
        cp2.font.size = Pt(9.5)
        cp2.font.color.rgb = COLOR_TEXT_MUTED
        cp2.font.name = "Arial"
        cp2.space_after = Pt(8)

        for b in stg["bullets"]:
            bp = ctf.add_paragraph()
            bp.text = f"• {b}"
            bp.font.size = Pt(9)
            bp.font.color.rgb = COLOR_TEXT_MAIN
            bp.font.name = "Arial"
            bp.space_after = Pt(4)

        # Safeguard callout badge at bottom of card
        badge = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            left_pos + Inches(0.15),
            top_pos + card_h - Inches(0.72),
            col_width - Inches(0.3),
            Inches(0.58),
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = COLOR_PILL_BG
        badge.line.color.rgb = COLOR_ACCENT
        badge.line.width = Pt(1)

        btf = badge.text_frame
        btf.word_wrap = True
        btf.margin_left = Inches(0.1)
        btf.margin_right = Inches(0.1)
        btf.margin_top = Inches(0.06)
        bp = btf.paragraphs[0]
        bp.text = f"LEAKAGE SAFEGUARD:\n{stg['guard']}"
        bp.font.bold = True
        bp.font.size = Pt(7.5)
        bp.font.color.rgb = COLOR_PRIMARY
        bp.font.name = "Arial"
        bp.alignment = PP_ALIGN.CENTER

    # Bottom Banner
    bot = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.6),
        Inches(6.25),
        Inches(12.133),
        Inches(0.75),
    )
    bot.fill.solid()
    bot.fill.fore_color.rgb = COLOR_CARD_BG
    bot.line.color.rgb = COLOR_BORDER
    bot.line.width = Pt(1.5)

    btf2 = bot.text_frame
    btf2.word_wrap = True
    btf2.margin_left = Inches(0.25)
    btf2.margin_top = Inches(0.12)
    bp0 = btf2.paragraphs[0]
    bp0.text = "CORE EMPIRICAL HIGHLIGHTS & VALIDATION GUARANTEES"
    bp0.font.bold = True
    bp0.font.size = Pt(10)
    bp0.font.color.rgb = COLOR_PRIMARY

    bp1 = btf2.add_paragraph()
    bp1.text = (
        "123,599 strictly evaluated origins | 50 disjoint folds | "
        "Global Skill: +11.82% (+30m), +11.85% (+60m) vs Persistence | "
        "6-Day Personalization: -1.81 mg/dL (-8.0% error, p < 0.05, 40/45 improved) | "
        "Zero data leakage"
    )
    bp1.font.size = Pt(9.5)
    bp1.font.color.rgb = COLOR_ACCENT
    bp1.font.bold = True

    prs.save(str(output_path))


def create_architecture_pdf(output_path: Path) -> None:
    """Create polished architecture diagram document in vector PDF."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ArchTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=HexColor(HEX_PRIMARY),
    )

    sub_style = ParagraphStyle(
        "ArchSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=HexColor(HEX_MUTED),
    )

    card_header = ParagraphStyle(
        "CardHdr",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        textColor=HexColor(HEX_PRIMARY),
    )

    card_num = ParagraphStyle(
        "CardNum",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=HexColor(HEX_ACCENT),
    )

    card_sub = ParagraphStyle(
        "CardSub",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=11,
        textColor=HexColor(HEX_MUTED),
    )

    card_body = ParagraphStyle(
        "CardBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=HexColor(HEX_TEXT),
    )

    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=HexColor(HEX_PRIMARY),
        alignment=1,  # Center
    )

    story: list[Any] = []

    # Title Box
    title_data = [
        [Paragraph("GLUCOSE DIGITAL TWIN — END-TO-END SYSTEM ARCHITECTURE", title_style)],
        [
            Paragraph(
                "Physiological Continuous Glucose Forecasting & Participant-Specific Residual Calibration Engine",
                sub_style,
            )
        ],
    ]
    title_table = Table(title_data, colWidths=[720])
    title_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor(HEX_CARD)),
                ("BOX", (0, 0), (-1, -1), 1.5, HexColor(HEX_BORDER)),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
            ]
        )
    )
    story.append(title_table)
    story.append(Spacer(1, 14))

    # 4 Columns Table
    stages = [
        {
            "num": "STAGE 01",
            "title": "DATA INGESTION & QC",
            "sub": "PhysioNet CGMacros (N=45)",
            "bullets": (
                "<b>Cohort:</b> 45 subjects (15 Normal, 16 Prediabetes, 14 T2D).<br/>"
                "<b>Contiguous Runs:</b> Delta t = 60s validation.<br/>"
                "<b>Zero Gap Imputation:</b> Runs end on missing data.<br/>"
                "<b>Lattice Grid:</b> m(t) = round((t-t0)/60s), issuance on m(t) mod 5 == 0."
            ),
            "guard": "<b>SAFEGUARD:</b> Zero boundary bleed; strict 1-min raw validation.",
        },
        {
            "num": "STAGE 02",
            "title": "GUARDED FEATURES",
            "sub": "R^20 Multimodal Matrix",
            "bullets": (
                "<b>History (13 lags):</b> y(t-65) through y(t-5).<br/>"
                "<b>5-Min Gap:</b> Zero input permitted in [t-5, t].<br/>"
                "<b>Meal Timing (3):</b> Minutes since meal, meal in 60m, no recent meal.<br/>"
                "<b>Clinical Demographics (4):</b> Age, Gender, BMI, baseline HbA1c."
            ),
            "guard": "<b>SAFEGUARD:</b> 5-min guard band prevents interpolation leakage.",
        },
        {
            "num": "STAGE 03",
            "title": "GLOBAL BENCHMARK",
            "sub": "Disjoint CV Ladder (Rungs 0-6)",
            "bullets": (
                "<b>Disjoint CV:</b> 10 repeats x 5 folds (50 folds, K=45).<br/>"
                "<b>Train-Only Tuning:</b> Closed-form Ridge alphas.<br/>"
                "<b>Persistence:</b> RMSE 21.55 (+30m), 29.32 (+60m).<br/>"
                "<b>Rung 5 Ridge:</b> RMSE 18.85 / 25.45 (+11.8% Skill).<br/>"
                "<b>Rung 6 GBDT:</b> Parity with Ridge (spans zero)."
            ),
            "guard": "<b>SAFEGUARD:</b> 0% intra-subject identity bleed.",
        },
        {
            "num": "STAGE 04",
            "title": "PERSONALIZATION",
            "sub": "Stage 3 Residual Calibration",
            "bullets": (
                "<b>Adaptation Days:</b> Early 2, 4, 6 study days.<br/>"
                "<b>Residual Model:</b> Ridge on r(t) = y(t+h) - y_hat.<br/>"
                "<b>6-Day Impact:</b> -1.81 mg/dL (-8.0% error, p &lt; 0.05).<br/>"
                "<b>Cohort Gain:</b> 40/45 improved (88.9%).<br/>"
                "<b>Streamlit UI:</b> 4 interactive research modules."
            ),
            "guard": "<b>SAFEGUARD:</b> &gt;= 120-min purge buffer prevents lag spillover.",
        },
    ]

    col_cells = []
    for stg in stages:
        content = [
            Paragraph(stg["num"], card_num),
            Paragraph(stg["title"], card_header),
            Paragraph(stg["sub"], card_sub),
            Spacer(1, 4),
            Paragraph(stg["bullets"], card_body),
            Spacer(1, 10),
            Table(
                [[Paragraph(stg["guard"], badge_style)]],
                colWidths=[162],
                style=[
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor(HEX_PILL)),
                    ("BOX", (0, 0), (-1, -1), 1, HexColor(HEX_ACCENT)),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ],
            ),
        ]
        col_cells.append(content)

    grid_table = Table([col_cells], colWidths=[175, 175, 175, 175])
    grid_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor(HEX_CARD)),
                ("BOX", (0, 0), (-1, -1), 1.5, HexColor(HEX_BORDER)),
                ("INNERGRID", (0, 0), (-1, -1), 1, HexColor(HEX_BORDER)),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(grid_table)
    story.append(Spacer(1, 14))

    # Bottom Summary Bar
    summary_data = [
        [
            Paragraph(
                "<b>BENCHMARK VERIFICATION GUARANTEES:</b> 123,599 valid origins across 45 participants | "
                "50 disjoint folds | Global Skill: +11.82% (+30m), +11.85% (+60m) vs Persistence | "
                "6-Day Personalization: -1.81 mg/dL (-8.0% error, p &lt; 0.05, 40/45 improved) | "
                "Zero data leakage",
                ParagraphStyle(
                    "BotText",
                    parent=styles["Normal"],
                    fontName="Helvetica-Bold",
                    fontSize=8.5,
                    leading=12,
                    textColor=HexColor(HEX_PRIMARY),
                    alignment=1,
                ),
            )
        ]
    ]
    bot_table = Table(summary_data, colWidths=[720])
    bot_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor(HEX_PILL)),
                ("BOX", (0, 0), (-1, -1), 1.5, HexColor(HEX_BORDER)),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(bot_table)

    doc.build(story)


def create_presentation_pptx(output_path: Path) -> None:
    """Create comprehensive 17-slide hackathon presentation in 16:9 widescreen PPTX."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    slides_content: list[dict[str, Any]] = [
        # Slide 1: Title
        {
            "title": "Personalized Glucose Digital Twin for Type 2 Diabetes",
            "subtitle": "Leak-Free Ambulatory Glucose Forecasting Framework & Participant-Specific Calibration Engine",
            "cards": [
                {
                    "title": "Hackathon Submission",
                    "bullets": [
                        "Team: DMounas Lab (Debangshu Mounas, Solo)",
                        "Affiliation: National Institute of Technology Silchar (NIT Silchar)",
                        "Track: Healthcare AI & Continuous Biomarker Intelligence",
                        "Repository: DMounas/personalized-glucose-digital-twin",
                    ],
                },
                {
                    "title": "Executive Summary",
                    "bullets": [
                        "Evaluated on 45 individuals from PhysioNet CGMacros cohort.",
                        "Enforces strict 5-minute guard band against telemetry leakage.",
                        "+11.85% population skill over persistence at both 30m & 60m horizons.",
                        "6-day online personalization achieves -1.81 mg/dL (8.0%) error reduction (40/45 improved).",
                    ],
                },
            ],
        },
        # Slide 2: Team Details
        {
            "title": "Team & Institutional Affiliation",
            "subtitle": "DMounas Lab — National Institute of Technology Silchar",
            "cards": [
                {
                    "title": "Debangshu Mounas (Solo Developer & Researcher)",
                    "bullets": [
                        "Role: Lead Machine Learning Researcher & Full-Stack System Architect.",
                        "Affiliation: National Institute of Technology Silchar (NIT Silchar).",
                        "GitHub Profile: @DMounas (https://github.com/DMounas).",
                        "Focus: Rigorous ML validation, leakage countermeasures, and physiological digital twins.",
                    ],
                },
                {
                    "title": "Core Values & Engineering Discipline",
                    "bullets": [
                        "Research Integrity: Preregistered protocols, zero data snooping, exact reproducibility.",
                        "Open Source: Complete public codebase under permissive MIT license.",
                        "Safety First: Prominent clinical non-intervention disclaimers and privacy compliance.",
                        "Quality Engineering: 135 automated unit/integration tests and multi-version CI (3.10-3.12).",
                    ],
                },
            ],
        },
        # Slide 3: Problem Statement
        {
            "title": "The Problem: Why Ambulatory Glucose ML Fails",
            "subtitle": "Three Pervasive Pitfalls in Continuous Glucose Monitoring Machine Learning",
            "cards": [
                {
                    "title": "Hidden Pitfalls in Published Literature",
                    "bullets": [
                        "1. Telemetry Interpolation Bleed: CGM hardware transmits every 5 min. Datasets interpolated to 1 min leak future packet values backwards.",
                        "2. Intra-Participant Contamination: Standard random K-fold CV mixes readings from the same subject across train and test folds.",
                        "3. High Inter-Individual Heterogeneity: Fixed population models fail to capture individual insulin sensitivity and hepatic response.",
                    ],
                },
                {
                    "title": "The Digital Twin Solution",
                    "bullets": [
                        "A mandatory 5-minute guard band gap [t-5, t] eliminating interpolation artifacts.",
                        "Strict participant-disjoint cross-validation (50 folds) with training-only preprocessing.",
                        "Online residual personalization adapting global models using early patient days.",
                    ],
                },
            ],
        },
        # Slide 4: Healthcare Use Case
        {
            "title": "Healthcare Use Case & Clinical Impact",
            "subtitle": "Empowering Proactive Diabetes Management & Clinical Decision Support",
            "cards": [
                {
                    "title": "Clinical Value Chain",
                    "bullets": [
                        "Proactive Alerting: 30 to 60 minutes of advance lead time before hyper/hypoglycemia occurs.",
                        "Behavioral Intervention Window: Enables timely patient action (light exercise, hydration, meal pacing).",
                        "Decision Support: Provides endocrinologists with individual trajectory confidence bounds.",
                    ],
                },
                {
                    "title": "Target Clinical Population",
                    "bullets": [
                        "Type 2 Diabetes: Mitigates postprandial glycemic excursions and glycemic variability.",
                        "Prediabetes: Delivers biofeedback on dietary sensitivity to prevent progression.",
                        "Ambulatory Monitoring: Designed for free-living individuals with self-reported meals.",
                    ],
                },
            ],
        },
        # Slide 5: Why Glucose Forecasting Matters
        {
            "title": "Why Physiological Glucose Forecasting Matters",
            "subtitle": "Moving from Reactive Continuous Glucose Monitoring to Predictive Guidance",
            "cards": [
                {
                    "title": "The Global Burden of Type 2 Diabetes",
                    "bullets": [
                        "Over 537 million adults live with diabetes worldwide (IDF Diabetes Atlas).",
                        "Chronic glycemic variability drives microvascular (retinopathy, nephropathy) and macrovascular complications.",
                        "Current commercial CGMs are reactive: alarms trigger only after thresholds are breached.",
                    ],
                },
                {
                    "title": "The Promise of Digital Twins",
                    "bullets": [
                        "Simulates individual patient response dynamically based on recent telemetry and meals.",
                        "Bridges the gap between rigid clinical guidelines and personalized daily living.",
                        "Evaluates what-if timing scenarios to optimize metabolic control.",
                    ],
                },
            ],
        },
        # Slide 6: Dataset & Characterization
        {
            "title": "Dataset: PhysioNet CGMacros Cohort",
            "subtitle": "Open-Access Clinical Telemetry (Bent et al., Scientific Data 2025)",
            "cards": [
                {
                    "title": "Cohort Demographics & Composition",
                    "bullets": [
                        "45 ambulatory participants spanning the metabolic health continuum.",
                        "Normoglycemic Controls: 15 subjects | Prediabetes: 16 subjects | Type 2 Diabetes: 14 subjects.",
                        "Continuous interstitial glucose logged via Dexcom G6 at 1-minute to 5-minute sampling.",
                        "Demographics recorded: Age, Sex, Body Mass Index (BMI), and baseline HbA1c.",
                    ],
                },
                {
                    "title": "Data Ingestion & Integrity Standard",
                    "bullets": [
                        "Delta t = 60s contiguous run segmentation: zero heuristic interpolation across sensor drops.",
                        "Lattice grid alignment: m(t) = round((t - t0) / 60s), issuance restricted to m(t) mod 5 == 0.",
                        "123,599 strictly validated evaluation origins across the full cohort.",
                    ],
                },
            ],
        },
        # Slide 7: Solution Architecture
        {
            "title": "End-to-End System Architecture",
            "subtitle": "Modular Five-Layer Pipeline from Raw Telemetry to Interactive UI",
            "cards": [
                {
                    "title": "Data Pipeline & Feature Space",
                    "bullets": [
                        "Layer 1: Ingestion & Run Segmentation (Delta t = 60s, lattice grid alignment).",
                        "Layer 2: Guarded Feature Extraction (13 lags, 3 meal flags, 4 clinical covariates -> R^20 space).",
                        "Layer 3: Global Model Ladder (8 rungs evaluated under 50 participant-disjoint folds).",
                    ],
                },
                {
                    "title": "Adaptation & Delivery",
                    "bullets": [
                        "Layer 4: Residual Personalization (regularized Ridge on early 2, 4, 6 study days).",
                        "Layer 5: Statistical Verification & UI (bootstrap CIs across 45 subjects, Streamlit dashboard).",
                        "Decoupled Architecture: Zero raw data dependencies in production UI.",
                    ],
                },
            ],
        },
        # Slide 8: Leakage-Aware Methodology
        {
            "title": "Five Architectural Leakage Countermeasures",
            "subtitle": "Eliminating Temporal Bleed & Intra-Subject Memorization",
            "cards": [
                {
                    "title": "Temporal Safeguards",
                    "bullets": [
                        "1. 5-Minute Guard Band Gap: Mandatory zero-input buffer [t-5, t] eliminating interpolation bleed.",
                        "2. Causal Autoregressive Lags: Strictly bounded to [y(t-65) ... y(t-5)] (60-min window).",
                        "3. 120-Minute Purge Buffer: Mandatory blackout separating adaptation days from test evaluation.",
                    ],
                },
                {
                    "title": "Evaluation Safeguards",
                    "bullets": [
                        "4. Participant-Disjoint Stratification: 10 repeated 5-fold CV with 0% subject overlap.",
                        "5. Participant-Level Bootstrap: B=2,000 resamples of 45 independent participant units.",
                        "Guarantee: No evaluation participant telemetry or demographics ever observed during training.",
                    ],
                },
            ],
        },
        # Slide 9: Forecasting Model Ladder
        {
            "title": "The Stage 2 Global Forecasting Ladder",
            "subtitle": "Progressive 8-Rung Benchmark on Identical Origins (N=123,599)",
            "cards": [
                {
                    "title": "Benchmark Rungs (0 through 4b)",
                    "bullets": [
                        "Rung 0: Guarded Persistence baseline — y_base = y(t-5).",
                        "Rung 1: Damped Trend Extrapolation — velocity damped by tuned gamma.",
                        "Rung 2: Guarded Ridge Regression — 13 autoregressive history lags.",
                        "Rung 3: + Activity Ridge — 13 lags + heart rate & METs preceding 30 min.",
                        "Rung 4 & 4b: + Meal Context — meal timing flags with and without macronutrients.",
                    ],
                },
                {
                    "title": "Advanced Rungs (5 and 6)",
                    "bullets": [
                        "Rung 5: + Clinical Covariates — 13 lags + meal timing + Age, Sex, BMI, HbA1c (R^20 space).",
                        "Rung 6: Fixed GBDT — HistGradientBoostingRegressor on identical R^20 features.",
                        "Fairness: Strictly identical evaluation origins across all 50 disjoint folds.",
                    ],
                },
            ],
        },
        # Slide 10: Global Forecasting Results
        {
            "title": "Stage 2 Global Forecasting Results",
            "subtitle": "Rung 5 Ridge Achieves Best Population Performance & Parity with GBDT",
            "cards": [
                {
                    "title": "Headline Benchmark Metrics (Cohort Mean RMSE)",
                    "bullets": [
                        "Persistence (Rung 0): 21.55 mg/dL (+30m) | 29.32 mg/dL (+60m).",
                        "Autoregressive Core (Rung 2): 19.87 mg/dL (+30m) | 26.97 mg/dL (+60m) [+8.0% skill].",
                        "Selected Foundation (Rung 5): 18.85 mg/dL (+30m) | 25.45 mg/dL (+60m) [+11.85% skill].",
                        "Fixed GBDT (Rung 6): 19.15 mg/dL (+30m) | 25.64 mg/dL (+60m) [+11.2% skill].",
                    ],
                },
                {
                    "title": "Why Rung 5 Ridge Was Selected Over GBDT",
                    "bullets": [
                        "Statistical Parity: Paired Delta-RMSE between GBDT and Ridge crosses zero at both horizons.",
                        "GBDT did not demonstrate a statistically significant overall advantage over linear Ridge.",
                        "Ridge guarantees closed-form mathematical stability, millisecond training, and zero fold failures.",
                    ],
                },
            ],
        },
        # Slide 11: Personalization Methodology
        {
            "title": "Stage 3 Chronological Personalization Methodology",
            "subtitle": "Individual Adaptation via Regularized Residual Correction",
            "cards": [
                {
                    "title": "Experimental Design & Cutoff Guards",
                    "bullets": [
                        "Adaptation Windows: Evaluates first 2, 4, and 6 study days per participant.",
                        "Temporal Purge: Mandatory >= 120-min blackout period following adaptation cutoff.",
                        "Matched Baseline: Compared against matched global baseline on identical post-purge origins.",
                    ],
                },
                {
                    "title": "Residual Calibration Mechanism",
                    "bullets": [
                        "Global Foundation: Pre-trained Rung 5 Ridge forecaster.",
                        "Residual Target: r(t) = y(t+h) - y_hat_global(t+h).",
                        "Participant Ridge: Fits individual model on 16 dynamic features (13 lags + 3 meal timing).",
                        "Evaluation: 100% on unseen subsequent study days.",
                    ],
                },
            ],
        },
        # Slide 12: Personalization Results
        {
            "title": "Stage 3 Personalization Results",
            "subtitle": "Statistically Significant Error Reduction Under 6-Day Adaptation (p < 0.05)",
            "cards": [
                {
                    "title": "+60-Minute Horizon Trajectory",
                    "bullets": [
                        "2 Study Days: Delta-RMSE = -0.025 mg/dL (n.s., sparse calibration telemetry).",
                        "4 Study Days: Delta-RMSE = -1.146 mg/dL (p < 0.05, 95% CI strictly excludes zero).",
                        "6 Study Days: Delta-RMSE = -1.811 mg/dL [-2.43, -1.09] (8.0% relative error reduction).",
                        "Cohort Benefit: 40 out of 45 participants (88.9%) improve over global model.",
                    ],
                },
                {
                    "title": "Clinical Subgroup Stratification",
                    "bullets": [
                        "Normal Controls: -1.33 mg/dL error change (tight endogenous insulin buffering).",
                        "Prediabetes: -1.82 mg/dL error change (moderate glycemic excursions).",
                        "Type 2 Diabetes: -2.34 mg/dL error change (largest absolute therapeutic benefit).",
                    ],
                },
            ],
        },
        # Slide 13: Interactive Streamlit Demo
        {
            "title": "Interactive Research Dashboard Tour",
            "subtitle": "Light Dual-Tone Clinical Interface Built with Streamlit & Plotly",
            "cards": [
                {
                    "title": "Four Analytical Modules",
                    "bullets": [
                        "1. Project Overview: Executive cohort statistics, ML failure modes, and system architecture.",
                        "2. Global Forecasting Explorer: Interactive horizon toggle (+30m, +60m), 8-rung benchmark ladder with 95% CIs.",
                        "3. Personalization Lab: Dynamic adaptation window controls (2, 4, 6 days), dose-response plots, subgroup table.",
                        "4. Methodology & Guard Band: Guard-band schematic, protocol comparison, and responsible use guidelines.",
                    ],
                },
                {
                    "title": "Dashboard Engineering Strengths",
                    "bullets": [
                        "Mild green and white dual-tone clinical palette with zero emojis.",
                        "Runs entirely on verified aggregate metrics — zero raw data requirement.",
                        "Immediate local launch via 'streamlit run app.py' and pre-configured for Cloud deployment.",
                    ],
                },
            ],
        },
        # Slide 14: Technical Stack
        {
            "title": "Technical Architecture & Repository Hygiene",
            "subtitle": "Production-Grade Research Engineering Standards",
            "cards": [
                {
                    "title": "Core Technologies & Libraries",
                    "bullets": [
                        "Languages: Python 3.10, 3.11, 3.12 (native compatibility verified).",
                        "Machine Learning: Scikit-learn (Ridge, HistGradientBoosting, GroupKFold).",
                        "Data & Math: NumPy, Pandas, PyYAML.",
                        "Interactive UI: Streamlit, Plotly (interactive charts and responsive layouts).",
                    ],
                },
                {
                    "title": "Quality Gates & CI/CD",
                    "bullets": [
                        "135 automated unit and regression tests passing cleanly via pytest.",
                        "Strict linting and code formatting enforced by Ruff (0 violations).",
                        "Static type safety verified across all modules via Mypy (0 issues).",
                        "GitHub Actions CI matrix verifying every commit across 3 Python versions.",
                    ],
                },
            ],
        },
        # Slide 15: Limitations & Responsible AI
        {
            "title": "Limitations & Responsible AI Framework",
            "subtitle": "Scientific Rigor, Observational Boundaries & Clinical Disclaimers",
            "cards": [
                {
                    "title": "Methodological Scope & Limitations",
                    "bullets": [
                        "Observational Data: Observational cohort telemetry does not establish causal physiological effects.",
                        "No Automated Control: Digital twin benchmarks forecasting accuracy; it does not simulate closed-loop insulin delivery.",
                        "Sensor Hardware Drift: Does not model acute subcutaneous sensor displacement or pressure-induced sensor attenuation.",
                    ],
                },
                {
                    "title": "Responsible AI Commitments",
                    "bullets": [
                        "Not FDA-cleared: Research prototype strictly intended for benchmarking and education.",
                        "Not a diagnostic or treatment system; never substitute for professional medical care.",
                        "Privacy: Zero Protected Health Information (PHI) stored or displayed.",
                    ],
                },
            ],
        },
        # Slide 16: Conclusion & Impact
        {
            "title": "Conclusion & Strategic Impact",
            "subtitle": "Key Takeaways from the Glucose Digital Twin Benchmark",
            "cards": [
                {
                    "title": "Summary of Contributions",
                    "bullets": [
                        "1. Defensible Methodology: Established the 5-min guard band and temporal purge standard for CGM ML.",
                        "2. Benchmark Reference: Proven that Rung 5 Ridge achieves +11.8% skill with mathematical stability.",
                        "3. Personalization Proof: 6-day online adaptation delivers a statistically significant 8.0% error reduction (p < 0.05).",
                        "4. Clinical Benefit: Greatest error drop (-2.34 mg/dL) observed in Type 2 Diabetic individuals.",
                    ],
                },
                {
                    "title": "Future Horizons",
                    "bullets": [
                        "Integration with wearable fitness and meal photologging sensors.",
                        "Expansion to multi-day circadian and nocturnal hypoglycemia forecasting.",
                        "Federated on-device adaptation preserving patient privacy at the edge.",
                    ],
                },
            ],
        },
        # Slide 17: Links & Attribution
        {
            "title": "Repository, Demo & Submission Links",
            "subtitle": "All Artifacts Are Publicly Accessible and Reproducible",
            "cards": [
                {
                    "title": "Public Repository Resources",
                    "bullets": [
                        "GitHub Repository: https://github.com/DMounas/personalized-glucose-digital-twin",
                        "Architecture PDF & PPTX: docs/submission/architecture.pdf / architecture.pptx",
                        "Presentation PDF & PPTX: docs/submission/presentation.pdf / presentation.pptx",
                        "Video Demonstration Script: docs/submission/DEMO_SCRIPT.md",
                    ],
                },
                {
                    "title": "Open Source Attribution",
                    "bullets": [
                        "Software License: MIT License (Copyright 2026 Debangshu Mounas).",
                        "Dataset Source: PhysioNet CGMacros 1.0.0 (Bent et al., Scientific Data 2025).",
                        "Interactive Launch: streamlit run app.py (localhost:8501).",
                        "Thank you for reviewing the DMounas Lab Hackathon Submission!",
                    ],
                },
            ],
        },
    ]

    for s_idx, s_data in enumerate(slides_content):
        slide = prs.slides.add_slide(blank_layout)

        # Background
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_BG
        bg.line.color.rgb = COLOR_BORDER

        # Header Box
        hdr = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.6),
            Inches(0.4),
            Inches(12.133),
            Inches(1.05),
        )
        hdr.fill.solid()
        hdr.fill.fore_color.rgb = COLOR_CARD_BG
        hdr.line.color.rgb = COLOR_BORDER
        hdr.line.width = Pt(1.5)

        htf = hdr.text_frame
        htf.word_wrap = True
        htf.margin_left = Inches(0.25)
        htf.margin_top = Inches(0.12)

        hp0 = htf.paragraphs[0]
        hp0.text = f"{s_idx + 1:02d} | {s_data['title'].upper()}"
        hp0.font.bold = True
        hp0.font.size = Pt(17)
        hp0.font.color.rgb = COLOR_PRIMARY
        hp0.font.name = "Arial"

        hp1 = htf.add_paragraph()
        hp1.text = s_data["subtitle"]
        hp1.font.size = Pt(10.5)
        hp1.font.color.rgb = COLOR_TEXT_MUTED
        hp1.font.name = "Arial"

        # Content Cards (2 Columns)
        cards = s_data["cards"]
        card_w = Inches(5.95)
        card_h = Inches(5.2)
        top_pos = Inches(1.65)

        for c_idx, card in enumerate(cards):
            left_pos = Inches(0.6) + c_idx * (card_w + Inches(0.233))

            c_shape = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, top_pos, card_w, card_h
            )
            c_shape.fill.solid()
            c_shape.fill.fore_color.rgb = COLOR_CARD_BG
            c_shape.line.color.rgb = COLOR_BORDER
            c_shape.line.width = Pt(1.5)

            ctf = c_shape.text_frame
            ctf.word_wrap = True
            ctf.margin_left = Inches(0.3)
            ctf.margin_right = Inches(0.3)
            ctf.margin_top = Inches(0.3)

            cp0 = ctf.paragraphs[0]
            cp0.text = card["title"]
            cp0.font.bold = True
            cp0.font.size = Pt(14)
            cp0.font.color.rgb = COLOR_ACCENT
            cp0.font.name = "Arial"
            cp0.space_after = Pt(14)

            for b in card["bullets"]:
                bp = ctf.add_paragraph()
                bp.text = f"• {b}"
                bp.font.size = Pt(10.5)
                bp.font.color.rgb = COLOR_TEXT_MAIN
                bp.font.name = "Arial"
                bp.space_after = Pt(8)

    prs.save(str(output_path))


def create_presentation_pdf(output_path: Path) -> None:
    """Create polished 17-slide presentation in vector PDF."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    slide_title_style = ParagraphStyle(
        "SlideTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=HexColor(HEX_PRIMARY),
    )

    slide_sub_style = ParagraphStyle(
        "SlideSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=HexColor(HEX_MUTED),
    )

    card_title_style = ParagraphStyle(
        "CardTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=HexColor(HEX_ACCENT),
    )

    card_body_style = ParagraphStyle(
        "CardBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.5,
        textColor=HexColor(HEX_TEXT),
    )

    # Content definition matching 17 slides
    slides_data = [
        (
            "Personalized Glucose Digital Twin for Type 2 Diabetes",
            "Leak-Free Ambulatory Glucose Forecasting Framework & Participant-Specific Calibration Engine",
            "Hackathon Submission Details",
            (
                "• <b>Team:</b> DMounas Lab (Debangshu Mounas, Solo Developer & Researcher)<br/>"
                "• <b>Affiliation:</b> National Institute of Technology Silchar (NIT Silchar)<br/>"
                "• <b>Track:</b> Healthcare AI & Continuous Biomarker Intelligence<br/>"
                "• <b>Repository:</b> DMounas/personalized-glucose-digital-twin<br/>"
                "• <b>License:</b> MIT Open Source License"
            ),
            "Executive Summary",
            (
                "• Evaluated across 45 participants from PhysioNet CGMacros cohort.<br/>"
                "• Enforces strict 5-min history guard band against telemetry leakage.<br/>"
                "• <b>+11.85% population skill</b> over persistence at both 30m &amp; 60m horizons.<br/>"
                "• <b>6-day personalization:</b> -1.81 mg/dL (8.0%) error reduction (p &lt; 0.05, 40/45 improved).<br/>"
                "• Interactive Streamlit dashboard in dual-tone clinical palette."
            ),
        ),
        (
            "Team & Institutional Affiliation",
            "DMounas Lab — National Institute of Technology Silchar",
            "Debangshu Mounas (Solo)",
            (
                "• <b>Role:</b> Lead Machine Learning Researcher & Full-Stack System Architect.<br/>"
                "• <b>Affiliation:</b> National Institute of Technology Silchar (NIT Silchar).<br/>"
                "• <b>GitHub Profile:</b> @DMounas (https://github.com/DMounas).<br/>"
                "• <b>Focus:</b> Rigorous ML validation, leakage countermeasures, digital twins."
            ),
            "Core Values & Discipline",
            (
                "• <b>Research Integrity:</b> Preregistered protocols, zero data snooping.<br/>"
                "• <b>Open Source:</b> Permissive MIT license with clear PhysioNet attribution.<br/>"
                "• <b>Safety First:</b> Prominent non-clinical disclaimers and PHI privacy.<br/>"
                "• <b>Quality Gates:</b> 135 automated tests, Ruff, and multi-version CI."
            ),
        ),
        (
            "The Problem: Why Ambulatory Glucose ML Fails",
            "Three Structural Vulnerabilities in Published Glucose Forecasting Literature",
            "Literature Pitfalls",
            (
                "• <b>1. Telemetry Interpolation Bleed:</b> Sensors log every 5 min; resampling to 1 min leaks future packets backwards.<br/>"
                "• <b>2. Intra-Participant Contamination:</b> Random K-fold CV mixes readings from the same subject across train/test folds.<br/>"
                "• <b>3. High Inter-Subject Heterogeneity:</b> Population models fail to capture individual insulin sensitivity and hepatic output."
            ),
            "Digital Twin Solutions",
            (
                "• <b>Strict 5-Minute Guard Band:</b> Blackout buffer [t-5, t] eliminating interpolation bleed.<br/>"
                "• <b>Participant-Disjoint CV:</b> 50 folds with 0% intra-subject identity bleed.<br/>"
                "• <b>Online Personalization:</b> Adapts global models using early patient telemetry."
            ),
        ),
        (
            "Healthcare Use Case & Clinical Motivation",
            "Empowering Proactive Diabetes Management & Clinical Decision Support",
            "Clinical Value Chain",
            (
                "• <b>Proactive Lead Time:</b> 30 to 60 minutes advance warning before hyper/hypoglycemia occurs.<br/>"
                "• <b>Actionable Window:</b> Enables timely patient action (light exercise, hydration, meal adjustments).<br/>"
                "• <b>Clinician Support:</b> Quantifies individual trajectory confidence and residual variance."
            ),
            "Target Population",
            (
                "• <b>Type 2 Diabetes:</b> Mitigates postprandial excursions and glycemic variability.<br/>"
                "• <b>Prediabetes:</b> Delivers dietary biofeedback to prevent progression.<br/>"
                "• <b>Ambulatory Monitoring:</b> Tailored to free-living ambulatory individuals."
            ),
        ),
        (
            "Why Physiological Glucose Forecasting Matters",
            "Moving from Reactive Monitoring to Predictive Guidance",
            "Global Diabetes Burden",
            (
                "• Over 537 million adults live with diabetes worldwide (IDF Diabetes Atlas).<br/>"
                "• Glycemic variability drives severe microvascular and macrovascular complications.<br/>"
                "• Commercial CGMs are reactive: alerts trigger only after thresholds are crossed."
            ),
            "Digital Twin Impact",
            (
                "• Simulates individual patient glycemic dynamics based on recent telemetry and meals.<br/>"
                "• Bridges the gap between static guidelines and personalized daily reality.<br/>"
                "• Enables what-if timing evaluations to optimize metabolic control."
            ),
        ),
        (
            "Dataset: PhysioNet CGMacros Cohort",
            "Open-Access Clinical Telemetry (Bent et al., Scientific Data 2025)",
            "Cohort Composition",
            (
                "• <b>45 diverse subjects</b> across the metabolic health continuum.<br/>"
                "• <b>Subgroups:</b> Normal Controls (15), Prediabetes (16), Type 2 Diabetes (14).<br/>"
                "• Telemetry logged via Dexcom G6 continuous monitors.<br/>"
                "• Demographics: Age, Sex, BMI, and baseline HbA1c."
            ),
            "Data Quality & Integrity",
            (
                "• <b>Delta t = 60s rule:</b> Contiguous run segmentation with zero synthetic interpolation.<br/>"
                "• <b>Lattice Grid:</b> m(t) = round((t-t0)/60s), issuance on m(t) mod 5 == 0.<br/>"
                "• <b>123,599 valid origins</b> evaluated across the full cohort."
            ),
        ),
        (
            "End-to-End System Architecture",
            "Modular Five-Layer Pipeline from Raw Sensor Ingestion to User Interface",
            "Feature Engineering Space",
            (
                "• <b>Ingestion:</b> Run segmentation, lattice grid alignment (phi = 0).<br/>"
                "• <b>Guarded Features:</b> 13 autoregressive lags [y(t-65) ... y(t-5)].<br/>"
                "• <b>Multimodal Context:</b> 3 meal-timing flags + 4 clinical covariates (R^20 space)."
            ),
            "Modeling & Delivery",
            (
                "• <b>Global Ladder:</b> 8 rungs evaluated under 50 disjoint folds.<br/>"
                "• <b>Personalization:</b> Regularized Ridge residual calibration on early study days.<br/>"
                "• <b>Interactive UI:</b> Modular Streamlit dashboard with zero raw data dependencies."
            ),
        ),
        (
            "Five Architectural Leakage Countermeasures",
            "Eliminating Temporal Bleed & Intra-Subject Memorization",
            "Temporal Protections",
            (
                "• <b>1. 5-Min Guard Band Gap:</b> Mandatory zero-input buffer in [t-5, t].<br/>"
                "• <b>2. 13 Permitted Lags:</b> Strictly bounded to [y(t-65) ... y(t-5)].<br/>"
                "• <b>3. 120-Min Purge Buffer:</b> Mandatory blackout separating adaptation from test days."
            ),
            "Evaluation Protections",
            (
                "• <b>4. Participant-Disjoint CV:</b> 10 repeats x 5 folds with zero subject overlap.<br/>"
                "• <b>5. Participant Bootstrap:</b> B=2,000 resamples of 45 independent participant units.<br/>"
                "• <b>Guarantee:</b> Zero test subject telemetry or covariates seen during training."
            ),
        ),
        (
            "The Stage 2 Global Forecasting Ladder",
            "Progressive 8-Rung Benchmark on Identical Origins (N=123,599)",
            "Rungs 0 through 4b",
            (
                "• <b>Rung 0:</b> Guarded Persistence baseline (latest lag y(t-5)).<br/>"
                "• <b>Rung 1:</b> Damped Trend Extrapolation (velocity damped by gamma).<br/>"
                "• <b>Rung 2:</b> Guarded Ridge Regression (13 autoregressive lags).<br/>"
                "• <b>Rung 3 &amp; 4:</b> Activity &amp; Meal timing context."
            ),
            "Advanced Rungs 5 & 6",
            (
                "• <b>Rung 5:</b> Clinical Covariates Ridge (Age, Sex, BMI, HbA1c in R^20 space).<br/>"
                "• <b>Rung 6:</b> Fixed HistGradientBoostingRegressor on identical R^20 features.<br/>"
                "• Evaluated across strictly identical evaluation origins."
            ),
        ),
        (
            "Stage 2 Global Forecasting Results",
            "Rung 5 Ridge Achieves Best Population Performance & Parity with GBDT",
            "Headline Benchmark Metrics",
            (
                "• <b>Persistence (R0):</b> 21.55 mg/dL (+30m) | 29.32 mg/dL (+60m).<br/>"
                "• <b>Autoregressive Core (R2):</b> 19.87 mg/dL (+30m) | 26.97 mg/dL (+60m).<br/>"
                "• <b>Selected Foundation (R5):</b> <b>18.85 mg/dL</b> (+30m) | <b>25.45 mg/dL</b> (+60m).<br/>"
                "• <b>Population Skill:</b> <b>+11.82%</b> (+30m) | <b>+11.85%</b> (+60m) vs Persistence."
            ),
            "Ridge vs. GBDT Parity",
            (
                "• GBDT (Rung 6): 19.15 mg/dL (+30m) | 25.64 mg/dL (+60m).<br/>"
                "• Paired Delta-RMSE between GBDT and Ridge crosses zero at both horizons.<br/>"
                "• GBDT did not demonstrate a statistically significant gain over Ridge.<br/>"
                "• Ridge provides closed-form stability and instant training."
            ),
        ),
        (
            "Stage 3 Personalization Methodology",
            "Individual Adaptation via Regularized Residual Correction",
            "Experimental Design",
            (
                "• <b>Adaptation Windows:</b> Evaluates first 2, 4, and 6 study days.<br/>"
                "• <b>Purge Blackout:</b> Mandatory &gt;= 120-min buffer separating adaptation from test.<br/>"
                "• <b>Matched Baseline:</b> Evaluated on strictly identical post-purge origins."
            ),
            "Residual Calibration",
            (
                "• <b>Foundation:</b> Pre-trained Rung 5 Ridge global model.<br/>"
                "• <b>Residual Target:</b> r(t) = y(t+h) - y_hat_global(t+h).<br/>"
                "• <b>Model:</b> Ridge fitted on 16 dynamic features (13 lags + 3 meal timing).<br/>"
                "• <b>Evaluation:</b> 100% on unseen subsequent telemetry."
            ),
        ),
        (
            "Stage 3 Personalization Results",
            "Statistically Significant Error Reduction Under 6-Day Adaptation (p < 0.05)",
            "+60-Minute Horizon Impact",
            (
                "• <b>2 Study Days:</b> Delta-RMSE = -0.025 mg/dL (spans zero; sparse telemetry).<br/>"
                "• <b>4 Study Days:</b> Delta-RMSE = -1.146 mg/dL (p &lt; 0.05, strictly excludes zero).<br/>"
                "• <b>6 Study Days:</b> <b>-1.811 mg/dL</b> [-2.43, -1.09] (<b>8.0% relative reduction</b>).<br/>"
                "• <b>Cohort Benefit:</b> <b>40 out of 45 participants (88.9%) improve.</b>"
            ),
            "Subgroup Excursion Dynamics",
            (
                "• <b>Normal Controls:</b> -1.33 mg/dL error change.<br/>"
                "• <b>Prediabetes:</b> -1.82 mg/dL error change.<br/>"
                "• <b>Type 2 Diabetes:</b> <b>-2.34 mg/dL error change</b> (largest absolute therapeutic benefit)."
            ),
        ),
        (
            "Interactive Research Dashboard Tour",
            "Light Dual-Tone Clinical Interface Built with Streamlit & Plotly",
            "Four Dedicated Modules",
            (
                "• <b>1. Project Overview:</b> Cohort summary, ML failure modes, system architecture.<br/>"
                "• <b>2. Global Explorer:</b> Horizon toggle (+30m, +60m), 8-rung benchmark ladder with 95% CIs.<br/>"
                "• <b>3. Personalization Lab:</b> Window controls (2d, 4d, 6d), dose-response plots, subgroup table.<br/>"
                "• <b>4. Methodology:</b> Guard-band schematic, protocol guide, responsible use."
            ),
            "Design Discipline",
            (
                "• Mild green and white dual-tone clinical palette with <b>zero emojis</b>.<br/>"
                "• Powered by verified canonical aggregate metrics — zero raw data exposure.<br/>"
                "• Instant local launch: streamlit run app.py."
            ),
        ),
        (
            "Technical Architecture & Repository Hygiene",
            "Production-Grade Research Engineering Standards",
            "Core Technologies",
            (
                "• <b>Languages:</b> Python 3.10, 3.11, 3.12 (native multi-version verification).<br/>"
                "• <b>ML Core:</b> Scikit-learn (Ridge, HistGradientBoosting, GroupKFold).<br/>"
                "• <b>Data & Math:</b> NumPy, Pandas, PyYAML.<br/>"
                "• <b>UI & Visualization:</b> Streamlit, Plotly, Matplotlib."
            ),
            "Quality Gates & CI/CD",
            (
                "• <b>135 automated unit &amp; regression tests</b> passing cleanly (pytest).<br/>"
                "• Strict linting &amp; formatting enforced by Ruff (0 violations).<br/>"
                "• Complete static type safety verified via Mypy (0 issues).<br/>"
                "• GitHub Actions CI matrix testing every commit."
            ),
        ),
        (
            "Limitations & Responsible AI Framework",
            "Scientific Rigor, Observational Boundaries & Clinical Disclaimers",
            "Methodological Boundaries",
            (
                "• <b>Observational Data:</b> Observational telemetry does not establish causal physiological mechanisms.<br/>"
                "• <b>No Closed-Loop Control:</b> Benchmarks forecasting accuracy; does not titrate insulin.<br/>"
                "• <b>Hardware Drift:</b> Does not simulate acute sensor displacement or compression artifacts."
            ),
            "Responsible AI Standards",
            (
                "• <b>Not FDA-cleared:</b> Research prototype strictly intended for benchmarking and education.<br/>"
                "• Not a diagnostic or treatment system; never substitute for clinical advice.<br/>"
                "• <b>Zero PHI:</b> Complete privacy compliance without raw patient data exposure."
            ),
        ),
        (
            "Conclusion & Strategic Impact",
            "Key Takeaways from the Glucose Digital Twin Benchmark",
            "Summary of Contributions",
            (
                "• <b>1. Defensible Methodology:</b> Established the 5-min guard band and temporal purge standard.<br/>"
                "• <b>2. Benchmark Foundation:</b> Proven that Rung 5 Ridge achieves +11.8% skill with mathematical stability.<br/>"
                "• <b>3. Personalization Proof:</b> 6-day adaptation delivers a statistically significant 8.0% error drop (p &lt; 0.05).<br/>"
                "• <b>4. Clinical Equity:</b> Largest benefit (-2.34 mg/dL) achieved in Type 2 Diabetes cohort."
            ),
            "Future Horizons",
            (
                "• Wearable integration (continuous physical activity and meal photologging).<br/>"
                "• Nocturnal hypoglycemia risk prediction across multi-day circadian windows.<br/>"
                "• Federated on-device model adaptation preserving patient privacy at the edge."
            ),
        ),
        (
            "Repository, Demo & Submission Links",
            "All Artifacts Are Publicly Accessible and Fully Reproducible",
            "Public Submission Resources",
            (
                "• <b>GitHub Repository:</b> https://github.com/DMounas/personalized-glucose-digital-twin<br/>"
                "• <b>Architecture Diagram:</b> docs/submission/architecture.pdf | architecture.pptx<br/>"
                "• <b>Presentation Slide Deck:</b> docs/submission/presentation.pdf | presentation.pptx<br/>"
                "• <b>Demo Video Script:</b> docs/submission/DEMO_SCRIPT.md"
            ),
            "Open Source & Attribution",
            (
                "• <b>License:</b> MIT License (Copyright 2026 Debangshu Mounas).<br/>"
                "• <b>Dataset Attribution:</b> PhysioNet CGMacros 1.0.0 (Bent et al., Scientific Data 2025).<br/>"
                "• <b>Local Launch:</b> streamlit run app.py<br/>"
                "• Thank you for reviewing the DMounas Lab Hackathon Submission!"
            ),
        ),
    ]

    story: list[Any] = []

    for idx, (title, sub, c1_title, c1_body, c2_title, c2_body) in enumerate(slides_data):
        # Header Table
        hdr_data = [
            [Paragraph(f"SLIDE {idx + 1:02d} | {title.upper()}", slide_title_style)],
            [Paragraph(sub, slide_sub_style)],
        ]
        hdr_table = Table(hdr_data, colWidths=[720])
        hdr_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor(HEX_CARD)),
                    ("BOX", (0, 0), (-1, -1), 1.5, HexColor(HEX_BORDER)),
                    ("PADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(hdr_table)
        story.append(Spacer(1, 14))

        # Two Column Cards Table
        c1_content = [
            Paragraph(c1_title, card_title_style),
            Spacer(1, 8),
            Paragraph(c1_body, card_body_style),
        ]
        c2_content = [
            Paragraph(c2_title, card_title_style),
            Spacer(1, 8),
            Paragraph(c2_body, card_body_style),
        ]

        body_table = Table([[c1_content, c2_content]], colWidths=[353, 353])
        body_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor(HEX_CARD)),
                    ("BOX", (0, 0), (0, 0), 1.5, HexColor(HEX_BORDER)),
                    ("BOX", (1, 0), (1, 0), 1.5, HexColor(HEX_BORDER)),
                    ("PADDING", (0, 0), (-1, -1), 12),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(body_table)

        if idx < len(slides_data) - 1:
            story.append(PageBreak())

    doc.build(story)


def main() -> None:
    """Generate all submission assets."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating submission assets in:", OUTPUT_DIR)

    arch_pptx = OUTPUT_DIR / "architecture.pptx"
    arch_pdf = OUTPUT_DIR / "architecture.pdf"
    pres_pptx = OUTPUT_DIR / "presentation.pptx"
    pres_pdf = OUTPUT_DIR / "presentation.pdf"

    print("1. Creating architecture.pptx...")
    create_architecture_pptx(arch_pptx)
    print("   Created:", arch_pptx)

    print("2. Creating architecture.pdf...")
    create_architecture_pdf(arch_pdf)
    print("   Created:", arch_pdf)

    print("3. Creating presentation.pptx...")
    create_presentation_pptx(pres_pptx)
    print("   Created:", pres_pptx)

    print("4. Creating presentation.pdf...")
    create_presentation_pdf(pres_pdf)
    print("   Created:", pres_pdf)

    print("All submission assets generated successfully!")


if __name__ == "__main__":
    main()
