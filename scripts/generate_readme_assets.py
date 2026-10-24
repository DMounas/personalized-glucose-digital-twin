"""Generate visual assets for README.md and documentation.

Reads aggregate benchmark metrics directly from:
- docs/reports/stage2_baseline_metrics.json
- docs/reports/stage3_personalization_metrics.json

Outputs:
- assets/global_benchmark.png
- assets/personalization_dashboard.png
- assets/hero_banner.svg
- assets/system_architecture.svg
- assets/guard_band_timeline.svg
- assets/pipeline_workflow.svg
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def set_dark_theme() -> None:
    """Configure matplotlib with a modern, high-contrast dark theme."""
    plt.style.use("dark_background")
    plt.rcParams.update(
        {
            "figure.facecolor": "#0B1120",
            "axes.facecolor": "#0F172A",
            "axes.edgecolor": "#334155",
            "axes.labelcolor": "#F8FAFC",
            "axes.grid": True,
            "grid.color": "#1E293B",
            "grid.linestyle": "--",
            "grid.alpha": 0.6,
            "text.color": "#F8FAFC",
            "xtick.color": "#94A3B8",
            "ytick.color": "#94A3B8",
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "Inter", "Arial", "DejaVu Sans"],
        }
    )


def validate_metrics(stage2_data: dict, stage3_data: dict) -> None:
    """Validate that canonical metrics adhere to protocol invariants and expected values.

    Fails clearly if required fields are missing, out of range, or violate statistical properties.
    """
    # 1. Stage 2 presence
    if "horizons" not in stage2_data:
        raise ValueError("Stage 2 metrics missing 'horizons' key")
    for h in ["h30", "h60"]:
        if h not in stage2_data["horizons"]:
            raise ValueError(f"Stage 2 metrics missing horizon '{h}'")
        h_data = stage2_data["horizons"][h]
        for r in [
            "rung0_guarded_persistence",
            "rung1_damped_trend",
            "rung2_ridge_regression",
            "rung3_activity_ridge",
            "rung4_meal_ridge",
            "rung4_nomacros_ablation",
            "rung5_baseline_covariates",
            "rung6_hist_gradient_boosting",
        ]:
            if r not in h_data or "summary" not in h_data[r]:
                raise ValueError(f"Stage 2 horizon '{h}' missing rung '{r}' summary")

    # 2. Key invariant Stage 2 checks
    r0_30 = stage2_data["horizons"]["h30"]["rung0_guarded_persistence"]["summary"]["headline_rmse"][
        "mean"
    ]
    r0_60 = stage2_data["horizons"]["h60"]["rung0_guarded_persistence"]["summary"]["headline_rmse"][
        "mean"
    ]
    r2_30 = stage2_data["horizons"]["h30"]["rung2_ridge_regression"]["summary"]["headline_rmse"][
        "mean"
    ]
    r2_60 = stage2_data["horizons"]["h60"]["rung2_ridge_regression"]["summary"]["headline_rmse"][
        "mean"
    ]
    r5_30 = stage2_data["horizons"]["h30"]["rung5_baseline_covariates"]["summary"]["headline_rmse"][
        "mean"
    ]
    r5_60 = stage2_data["horizons"]["h60"]["rung5_baseline_covariates"]["summary"]["headline_rmse"][
        "mean"
    ]
    r6_30 = stage2_data["horizons"]["h30"]["rung6_hist_gradient_boosting"]["summary"][
        "headline_rmse"
    ]["mean"]
    r6_60 = stage2_data["horizons"]["h60"]["rung6_hist_gradient_boosting"]["summary"][
        "headline_rmse"
    ]["mean"]

    expected_checks = [
        ("Rung 0 Persistence h30", r0_30, 21.554),
        ("Rung 0 Persistence h60", r0_60, 29.321),
        ("Rung 2 Ridge h30", r2_30, 19.866),
        ("Rung 2 Ridge h60", r2_60, 26.966),
        ("Rung 5 Covariates h30", r5_30, 18.853),
        ("Rung 5 Covariates h60", r5_60, 25.452),
        ("Rung 6 HistGradientBoosting h30", r6_30, 19.146),
        ("Rung 6 HistGradientBoosting h60", r6_60, 25.642),
    ]
    for name, actual, exp in expected_checks:
        if abs(actual - exp) > 0.05:
            raise ValueError(
                f"Validation failure for {name}: actual={actual:.4f}, expected={exp:.4f}"
            )

    # 3. Stage 3 presence & invariants
    if "horizons" not in stage3_data:
        raise ValueError("Stage 3 metrics missing 'horizons' key")
    for h in ["h30", "h60"]:
        if h not in stage3_data["horizons"] or "windows" not in stage3_data["horizons"][h]:
            raise ValueError(f"Stage 3 metrics missing windows for horizon '{h}'")
        windows = stage3_data["horizons"][h]["windows"]
        for w in ["window_2d", "window_4d", "window_6d"]:
            if w not in windows or "summary" not in windows[w]:
                raise ValueError(f"Stage 3 horizon '{h}' missing window '{w}' summary")

    # 4. Significance assertions:
    # All three +30m windows must cross zero (not statistically significant)
    for w in ["window_2d", "window_4d", "window_6d"]:
        ci = stage3_data["horizons"]["h30"]["windows"][w]["summary"]["paired_difference"][
            "ci_95_mean_delta_rmse"
        ]
        if not (ci[0] < 0 < ci[1]):
            raise ValueError(
                f"Stage 3 +30m {w} CI [{ci[0]}, {ci[1]}] does not cross zero as required"
            )

    # +60m 4d and 6d must strictly exclude zero (statistically significant benefit)
    for w in ["window_4d", "window_6d"]:
        ci = stage3_data["horizons"]["h60"]["windows"][w]["summary"]["paired_difference"][
            "ci_95_mean_delta_rmse"
        ]
        if ci[1] >= 0:
            raise ValueError(
                f"Stage 3 +60m {w} CI [{ci[0]}, {ci[1]}] does not strictly exclude zero as required"
            )

    print("Canonical metrics validation passed successfully.")


def generate_global_benchmark_chart(stage2_data: dict, output_path: Path) -> None:
    """Generate high-resolution comparison chart of Stage 2 model ladder."""
    models = [
        ("Rung 0: Persistence", "rung0_guarded_persistence", "#94A3B8"),
        ("Rung 1: Trend Extrap.", "rung1_damped_trend", "#64748B"),
        ("Rung 2: Guarded Ridge", "rung2_ridge_regression", "#38BDF8"),
        ("Rung 3: +Activity", "rung3_activity_ridge", "#0284C7"),
        ("Rung 4: +Meals (Full)", "rung4_meal_ridge", "#818CF8"),
        ("Rung 4b: +Meals (Timing)", "rung4_nomacros_ablation", "#6366F1"),
        ("Rung 5: +Covariates", "rung5_baseline_covariates", "#10B981"),
        ("Rung 6: Fixed GBDT", "rung6_hist_gradient_boosting", "#F59E0B"),
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.5), dpi=300)

    for ax, h_key, h_title in [
        (ax1, "h30", "+30-Minute Forecast Horizon"),
        (ax2, "h60", "+60-Minute Forecast Horizon"),
    ]:
        h_data = stage2_data["horizons"][h_key]
        names = [m[0] for m in models]
        rmses = [h_data[m[1]]["summary"]["headline_rmse"]["mean"] for m in models]
        ci_low = [h_data[m[1]]["summary"]["headline_rmse"]["ci_95_mean"][0] for m in models]
        ci_high = [h_data[m[1]]["summary"]["headline_rmse"]["ci_95_mean"][1] for m in models]
        colors = [m[2] for m in models]

        y_pos = np.arange(len(models))
        x_err = [
            np.array(rmses) - np.array(ci_low),
            np.array(ci_high) - np.array(rmses),
        ]

        bars = ax.barh(
            y_pos,
            rmses,
            xerr=x_err,
            color=colors,
            height=0.62,
            alpha=0.9,
            capsize=4,
            error_kw={"ecolor": "#F1F5F9", "elinewidth": 1.2},
        )
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontweight="medium")
        ax.invert_yaxis()
        ax.set_xlabel(
            "Cohort Mean RMSE (mg/dL) [Lower is Better]", fontweight="semibold", labelpad=8
        )
        ax.set_title(h_title, fontweight="bold", fontsize=13, pad=12, color="#38BDF8")

        # Persistence baseline vertical reference
        p_rmse = rmses[0]
        ax.axvline(
            p_rmse,
            color="#EF4444",
            linestyle=":",
            linewidth=1.5,
            alpha=0.8,
            label="Persistence Ref",
        )

        # Value annotations
        for i, bar in enumerate(bars):
            val = rmses[i]
            sk = h_data[models[i][1]]["summary"]["headline_skill"]["mean"] * 100
            txt = f"{val:.2f}" if i == 0 else f"{val:.2f} ({sk:+.1f}%)"
            # Place label slightly to the right of the bar point estimate
            ax.text(
                val + 0.35,
                bar.get_y() + bar.get_height() / 2,
                txt,
                va="center",
                ha="left",
                fontsize=9.5,
                fontweight="semibold",
                color="#F8FAFC",
            )

        x_min = 16 if h_key == "h30" else 22
        x_max = 24.5 if h_key == "h30" else 35.0
        ax.set_xlim(x_min, x_max)

    fig.suptitle(
        "Stage 2 Global Model Ladder Benchmark (CGMacros Cohort, N=45 Participants, 50 Folds)",
        fontsize=15,
        fontweight="bold",
        y=0.98,
        color="#F8FAFC",
    )
    plt.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated {output_path}")


def generate_personalization_dashboard(stage3_data: dict, output_path: Path) -> None:
    """Generate high-resolution personalization performance and uncertainty dashboard."""
    windows = ["window_2d", "window_4d", "window_6d"]
    win_labels = ["2 Study Days", "4 Study Days", "6 Study Days"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10.5), dpi=300)

    # 1. Horizon +30m RMSE Comparison
    x = np.arange(len(windows))
    width = 0.32
    g_30 = [
        stage3_data["horizons"]["h30"]["windows"][w]["summary"]["matched_global"]["mean_rmse"]
        for w in windows
    ]
    p_30 = [
        stage3_data["horizons"]["h30"]["windows"][w]["summary"]["personalized"]["mean_rmse"]
        for w in windows
    ]

    ax1.bar(x - width / 2, g_30, width, label="Matched Global Ridge", color="#64748B", alpha=0.9)
    b_p30 = ax1.bar(
        x + width / 2, p_30, width, label="Personalized (Adapted)", color="#38BDF8", alpha=0.95
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels(win_labels, fontweight="semibold")
    ax1.set_ylabel("Mean RMSE (mg/dL)", fontweight="semibold")
    ax1.set_ylim(14, 20.5)
    ax1.set_title(
        "+30-Minute Horizon: Matched Evaluation", fontweight="bold", fontsize=12, color="#38BDF8"
    )
    ax1.legend(loc="upper right", framealpha=0.4)
    for b in b_p30:
        ax1.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 0.15,
            f"{b.get_height():.2f}",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
        )

    # 2. Horizon +60m RMSE Comparison
    g_60 = [
        stage3_data["horizons"]["h60"]["windows"][w]["summary"]["matched_global"]["mean_rmse"]
        for w in windows
    ]
    p_60 = [
        stage3_data["horizons"]["h60"]["windows"][w]["summary"]["personalized"]["mean_rmse"]
        for w in windows
    ]

    ax2.bar(x - width / 2, g_60, width, label="Matched Global Ridge", color="#64748B", alpha=0.9)
    b_p60 = ax2.bar(
        x + width / 2, p_60, width, label="Personalized (Adapted)", color="#10B981", alpha=0.95
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels(win_labels, fontweight="semibold")
    ax2.set_ylabel("Mean RMSE (mg/dL)", fontweight="semibold")
    ax2.set_ylim(20, 27.5)
    ax2.set_title(
        "+60-Minute Horizon: Matched Evaluation", fontweight="bold", fontsize=12, color="#10B981"
    )
    ax2.legend(loc="upper right", framealpha=0.4)
    for b in b_p60:
        ax2.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 0.15,
            f"{b.get_height():.2f}",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
        )

    # 3. Paired Delta RMSE with 95% Bootstrap CIs
    d_30 = [
        stage3_data["horizons"]["h30"]["windows"][w]["summary"]["paired_difference"][
            "mean_delta_rmse"
        ]
        for w in windows
    ]
    ci_30_low = [
        stage3_data["horizons"]["h30"]["windows"][w]["summary"]["paired_difference"][
            "ci_95_mean_delta_rmse"
        ][0]
        for w in windows
    ]
    ci_30_high = [
        stage3_data["horizons"]["h30"]["windows"][w]["summary"]["paired_difference"][
            "ci_95_mean_delta_rmse"
        ][1]
        for w in windows
    ]
    err_30 = [np.array(d_30) - np.array(ci_30_low), np.array(ci_30_high) - np.array(d_30)]

    d_60 = [
        stage3_data["horizons"]["h60"]["windows"][w]["summary"]["paired_difference"][
            "mean_delta_rmse"
        ]
        for w in windows
    ]
    ci_60_low = [
        stage3_data["horizons"]["h60"]["windows"][w]["summary"]["paired_difference"][
            "ci_95_mean_delta_rmse"
        ][0]
        for w in windows
    ]
    ci_60_high = [
        stage3_data["horizons"]["h60"]["windows"][w]["summary"]["paired_difference"][
            "ci_95_mean_delta_rmse"
        ][1]
        for w in windows
    ]
    err_60 = [np.array(d_60) - np.array(ci_60_low), np.array(ci_60_high) - np.array(d_60)]

    ax3.axhline(
        0,
        color="#EF4444",
        linestyle="--",
        linewidth=1.5,
        alpha=0.8,
        label="Zero Effect (No Change)",
    )
    ax3.errorbar(
        x - 0.08,
        d_30,
        yerr=err_30,
        fmt="o-",
        color="#38BDF8",
        linewidth=2,
        markersize=8,
        capsize=5,
        label="+30m Delta RMSE (95% CI, spans 0)",
    )
    ax3.errorbar(
        x + 0.08,
        d_60,
        yerr=err_60,
        fmt="s-",
        color="#10B981",
        linewidth=2,
        markersize=8,
        capsize=5,
        label="+60m Delta RMSE (95% CI)",
    )
    ax3.set_xticks(x)
    ax3.set_xticklabels(win_labels, fontweight="semibold")
    ax3.set_ylabel("Paired RMSE Change (mg/dL)", fontweight="semibold")
    ax3.set_title(
        "Paired RMSE Change & 95% Bootstrap CIs (Negative = Improvement)",
        fontweight="bold",
        fontsize=12,
    )
    ax3.legend(loc="upper right", framealpha=0.5)
    ax3.set_ylim(-3.0, 2.2)

    # Informative callout about significance
    ax3.text(
        0.04,
        0.18,
        "• +30m: All CIs cross zero (not statistically significant)\n• +60m: 4-day & 6-day CIs strictly exclude zero (p < 0.05)",
        transform=ax3.transAxes,
        fontsize=9,
        va="bottom",
        ha="left",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#1E293B", edgecolor="#334155", alpha=0.85),
        color="#F8FAFC",
    )

    # 4. Proportion of Participants Improved
    imp_30 = [
        stage3_data["horizons"]["h30"]["windows"][w]["summary"]["paired_difference"][
            "fraction_improved"
        ]
        * 100
        for w in windows
    ]
    imp_60 = [
        stage3_data["horizons"]["h60"]["windows"][w]["summary"]["paired_difference"][
            "fraction_improved"
        ]
        * 100
        for w in windows
    ]

    ax4.plot(
        win_labels,
        imp_30,
        marker="o",
        color="#38BDF8",
        linewidth=2.5,
        markersize=8,
        label="+30m Improved %",
    )
    ax4.plot(
        win_labels,
        imp_60,
        marker="s",
        color="#10B981",
        linewidth=2.5,
        markersize=8,
        label="+60m Improved %",
    )
    ax4.axhline(50, color="#94A3B8", linestyle=":", alpha=0.7, label="50% Chance")
    ax4.set_ylabel("% of Participants Improved", fontweight="semibold")
    ax4.set_title(
        "Participant Improvement Rate across Adaptation Windows", fontweight="bold", fontsize=12
    )
    ax4.set_ylim(45, 100)
    ax4.legend(loc="lower right", framealpha=0.4)

    for i, txt in enumerate(imp_30):
        n_p = stage3_data["horizons"]["h30"]["windows"][windows[i]]["summary"]["paired_difference"][
            "n_improved"
        ]
        ax4.annotate(
            f"{txt:.1f}% ({n_p}/45)",
            (win_labels[i], txt + 2.5),
            ha="center",
            fontsize=9.5,
            fontweight="bold",
            color="#38BDF8",
        )
    for i, txt in enumerate(imp_60):
        n_p = stage3_data["horizons"]["h60"]["windows"][windows[i]]["summary"]["paired_difference"][
            "n_improved"
        ]
        ax4.annotate(
            f"{txt:.1f}% ({n_p}/45)",
            (win_labels[i], txt - 4.5),
            ha="center",
            fontsize=9.5,
            fontweight="bold",
            color="#10B981",
        )

    fig.suptitle(
        "Stage 3 Personalization: Adaptation Window Dose-Response Dynamics",
        fontsize=15,
        fontweight="bold",
        y=0.98,
        color="#F8FAFC",
    )
    plt.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated {output_path}")


def generate_hero_banner_svg(output_path: Path, stage2_data: dict, stage3_data: dict) -> None:
    """Create hero SVG banner with data-driven metric callouts."""
    s2_skill = (
        stage2_data["horizons"]["h60"]["rung5_baseline_covariates"]["summary"]["headline_skill"][
            "mean"
        ]
        * 100
    )
    s3_delta = stage3_data["horizons"]["h60"]["windows"]["window_6d"]["summary"][
        "paired_difference"
    ]["mean_delta_rmse"]
    s3_pct = stage3_data["horizons"]["h60"]["windows"]["window_6d"]["summary"]["paired_difference"][
        "mean_pct_reduction"
    ]

    skill_str = f"{s2_skill:+.2f}% vs Pers"
    delta_str = f"{s3_delta:.2f} mg/dL ({s3_pct:.1f}%)"

    svg_code = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#070D1A"/>
      <stop offset="50%" stop-color="#0F172A"/>
      <stop offset="100%" stop-color="#091E3A"/>
    </linearGradient>
    <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#06B6D4" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#38BDF8" stop-opacity="1"/>
    </linearGradient>
    <linearGradient id="forecastGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38BDF8" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#10B981" stop-opacity="0.9"/>
    </linearGradient>
    <linearGradient id="accentGlow" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#38BDF8" stop-opacity="0.0"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1200" height="360" rx="16" fill="url(#bgGrad)"/>

  <!-- Subtle Grid Pattern -->
  <g stroke="#1E293B" stroke-width="1" stroke-opacity="0.6">
    <line x1="80" y1="80" x2="1120" y2="80"/>
    <line x1="80" y1="140" x2="1120" y2="140"/>
    <line x1="80" y1="200" x2="1120" y2="200"/>
    <line x1="80" y1="260" x2="1120" y2="260"/>
    <line x1="300" y1="40" x2="300" y2="320"/>
    <line x1="600" y1="40" x2="600" y2="320"/>
    <line x1="850" y1="40" x2="850" y2="320"/>
    <line x1="1020" y1="40" x2="1020" y2="320"/>
  </g>

  <!-- Forecast Region Shading -->
  <rect x="850" y="50" width="270" height="260" rx="8" fill="#10B981" fill-opacity="0.06" stroke="#10B981" stroke-opacity="0.3" stroke-dasharray="4,4"/>
  <text x="865" y="75" fill="#10B981" font-family="Segoe UI, Inter, sans-serif" font-size="12" font-weight="700" letter-spacing="1">FORECAST ZONE (+30m / +60m)</text>

  <!-- Shaded Area Under Glucose Curve -->
  <path d="M 120 220 Q 220 160 340 190 T 520 140 T 700 170 T 850 130 T 980 110 T 1100 135 L 1100 290 L 120 290 Z" fill="url(#accentGlow)"/>

  <!-- Historical Glucose Trace (Cyan) -->
  <path d="M 120 220 Q 220 160 340 190 T 520 140 T 700 170 T 850 130" fill="none" stroke="url(#cyanGrad)" stroke-width="3.5" filter="url(#glow)"/>

  <!-- Forecast Glucose Trace (Emerald Green - Dashed) -->
  <path d="M 850 130 T 980 110 T 1100 135" fill="none" stroke="url(#forecastGrad)" stroke-width="3.5" stroke-dasharray="6,4" filter="url(#glow)"/>

  <!-- Issuance Origin Marker -->
  <circle cx="850" cy="130" r="7" fill="#38BDF8" stroke="#0F172A" stroke-width="3"/>
  <circle cx="980" cy="110" r="6" fill="#10B981" stroke="#0F172A" stroke-width="2.5"/>
  <circle cx="1100" cy="135" r="6" fill="#10B981" stroke="#0F172A" stroke-width="2.5"/>

  <!-- Origin Callouts -->
  <text x="850" y="105" fill="#38BDF8" font-family="Segoe UI, Inter, sans-serif" font-size="12" font-weight="700" text-anchor="middle">t (Issuance)</text>
  <text x="980" y="85" fill="#10B981" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700" text-anchor="middle">t + 30m</text>
  <text x="1100" y="110" fill="#10B981" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700" text-anchor="middle">t + 60m</text>

  <!-- Title & Subtitle Badge -->
  <g transform="translate(80, 75)">
    <rect x="0" y="0" width="165" height="26" rx="13" fill="#38BDF8" fill-opacity="0.15" stroke="#38BDF8" stroke-opacity="0.4"/>
    <text x="82" y="17" fill="#38BDF8" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800" text-anchor="middle" letter-spacing="1.5">RESEARCH REPOSITORY</text>

    <text x="0" y="65" fill="#F8FAFC" font-family="Segoe UI, Inter, sans-serif" font-size="34" font-weight="900" letter-spacing="-0.5">GLUCOSE DIGITAL TWIN</text>
    <text x="0" y="98" fill="#94A3B8" font-family="Segoe UI, Inter, sans-serif" font-size="16" font-weight="500">Guarded Physiological Forecasting &amp; Residual Personalization</text>

    <!-- Key Stats Ribbon -->
    <g transform="translate(0, 135)">
      <rect x="0" y="0" width="130" height="52" rx="8" fill="#1E293B" fill-opacity="0.8" stroke="#334155"/>
      <text x="15" y="22" fill="#94A3B8" font-family="Segoe UI, Inter, sans-serif" font-size="10" font-weight="600">COHORT</text>
      <text x="15" y="42" fill="#F8FAFC" font-family="Segoe UI, Inter, sans-serif" font-size="16" font-weight="800">45 Subjects</text>

      <rect x="145" y="0" width="150" height="52" rx="8" fill="#1E293B" fill-opacity="0.8" stroke="#334155"/>
      <text x="160" y="22" fill="#94A3B8" font-family="Segoe UI, Inter, sans-serif" font-size="10" font-weight="600">GLOBAL SKILL (+60m)</text>
      <text x="160" y="42" fill="#38BDF8" font-family="Segoe UI, Inter, sans-serif" font-size="16" font-weight="800">{skill_str}</text>

      <rect x="310" y="0" width="170" height="52" rx="8" fill="#1E293B" fill-opacity="0.8" stroke="#334155"/>
      <text x="325" y="22" fill="#94A3B8" font-family="Segoe UI, Inter, sans-serif" font-size="10" font-weight="600">6-DAY ADAPTATION (+60m)</text>
      <text x="325" y="42" fill="#10B981" font-family="Segoe UI, Inter, sans-serif" font-size="16" font-weight="800">{delta_str}</text>
    </g>
  </g>
</svg>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_code)
    print(f"Generated {output_path}")


def generate_guard_band_timeline_svg(output_path: Path) -> None:
    """Create temporal guard-band schematic SVG in mild green light theme."""
    svg_code = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 320" width="100%" height="100%">
  <!-- Canvas Background -->
  <rect width="1000" height="320" rx="12" fill="#FFFFFF" stroke="#D6E8DC" stroke-width="1.5"/>

  <!-- Titles -->
  <text x="50" y="42" fill="#0F291E" font-family="Segoe UI, Inter, sans-serif" font-size="18" font-weight="800">Temporal Guard-Band Architecture (Stage 2 v1.0.0)</text>
  <text x="50" y="65" fill="#475569" font-family="Segoe UI, Inter, sans-serif" font-size="12">Prevents interpolation leakage and boundary bleed across 1-minute to 5-minute sampling intervals</text>

  <!-- Timeline axis -->
  <line x1="80" y1="180" x2="920" y2="180" stroke="#CBD5E1" stroke-width="3"/>

  <!-- Permitted History Zone: t-65 to t-5 -->
  <rect x="100" y="110" width="370" height="140" rx="8" fill="#F0FDF4" stroke="#86EFAC" stroke-width="1.5"/>
  <text x="285" y="135" fill="#166534" font-family="Segoe UI, Inter, sans-serif" font-size="12" font-weight="700" text-anchor="middle">PERMITTED GLUCOSE HISTORY</text>
  <text x="285" y="155" fill="#475569" font-family="Segoe UI, Inter, sans-serif" font-size="11" text-anchor="middle">13 Lags: [y(t-65), y(t-60), ..., y(t-5)]</text>

  <!-- Guard-Band Gap: t-5 to t -->
  <rect x="470" y="110" width="80" height="140" rx="8" fill="#FEF2F2" stroke="#EF4444" stroke-width="1.5" stroke-dasharray="4,4"/>
  <text x="510" y="135" fill="#DC2626" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800" text-anchor="middle">GUARD</text>
  <text x="510" y="152" fill="#DC2626" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800" text-anchor="middle">BAND</text>
  <text x="510" y="170" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10" text-anchor="middle">5-min</text>
  <text x="510" y="240" fill="#DC2626" font-family="Segoe UI, Inter, sans-serif" font-size="9.5" text-anchor="middle" font-weight="600">ZERO INPUT</text>

  <!-- Issuance Marker t -->
  <line x1="550" y1="90" x2="550" y2="270" stroke="#166534" stroke-width="2.5" stroke-dasharray="2,2"/>
  <circle cx="550" cy="180" r="7" fill="#166534" stroke="#FFFFFF" stroke-width="2"/>
  <text x="550" y="80" fill="#0F291E" font-family="Segoe UI, Inter, sans-serif" font-size="13" font-weight="800" text-anchor="middle">Forecast Issuance (t)</text>

  <!-- Forecast Targets: t+30 and t+60 -->
  <rect x="570" y="110" width="350" height="140" rx="8" fill="#F0FDF4" stroke="#15803D" stroke-width="1.5"/>
  <text x="745" y="135" fill="#15803D" font-family="Segoe UI, Inter, sans-serif" font-size="12" font-weight="700" text-anchor="middle">FORECAST HORIZONS</text>

  <circle cx="730" cy="180" r="6" fill="#15803D"/>
  <text x="730" y="210" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700" text-anchor="middle">y(t + 30m)</text>
  <text x="730" y="228" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10" text-anchor="middle">+35m from y(t-5)</text>

  <circle cx="890" cy="180" r="6" fill="#15803D"/>
  <text x="890" y="210" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700" text-anchor="middle">y(t + 60m)</text>
  <text x="890" y="228" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10" text-anchor="middle">+65m from y(t-5)</text>

  <!-- Labeled Time Ticks -->
  <text x="100" y="200" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10" text-anchor="middle">t - 65m</text>
  <text x="470" y="200" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10" text-anchor="middle">t - 5m</text>
  <text x="550" y="200" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="10" font-weight="700" text-anchor="middle">t (0m)</text>
</svg>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_code)
    print(f"Generated {output_path}")


def generate_system_architecture_svg(
    output_path: Path, stage2_data: dict, stage3_data: dict
) -> None:
    """Create system architecture diagram SVG in mild green light theme with dynamic metrics."""
    s2_skill = (
        stage2_data["horizons"]["h60"]["rung5_baseline_covariates"]["summary"]["headline_skill"][
            "mean"
        ]
        * 100
    )
    s3_delta = stage3_data["horizons"]["h60"]["windows"]["window_6d"]["summary"][
        "paired_difference"
    ]["mean_delta_rmse"]
    s3_pct = stage3_data["horizons"]["h60"]["windows"]["window_6d"]["summary"]["paired_difference"][
        "mean_pct_reduction"
    ]

    callout_s2 = f"Rung 5 Ridge ({s2_skill:+.1f}% Skill)"
    callout_s3 = f"6-Day: {s3_delta:.2f} mg/dL ({s3_pct:.1f}%)"

    svg_code = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 420" width="100%" height="100%">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#16A34A"/>
    </marker>
  </defs>

  <!-- Canvas Background -->
  <rect width="1100" height="420" rx="14" fill="#FFFFFF" stroke="#D6E8DC" stroke-width="1.5"/>

  <!-- Titles -->
  <text x="50" y="40" fill="#0F291E" font-family="Segoe UI, Inter, sans-serif" font-size="18" font-weight="800">System Architecture &amp; Data Pipeline</text>
  <text x="50" y="62" fill="#475569" font-family="Segoe UI, Inter, sans-serif" font-size="12">End-to-end reproducible pipeline from raw continuous glucose monitoring to participant-disjoint personalized evaluation</text>

  <!-- Stage Blocks -->
  <!-- Block 1: Ingestion & Run Segmentation -->
  <g transform="translate(50, 90)">
    <rect width="180" height="290" rx="10" fill="#F8FBF9" stroke="#D6E8DC" stroke-width="1.5"/>
    <rect width="180" height="34" rx="10" fill="#E8F5E9"/>
    <text x="90" y="22" fill="#166534" font-family="Segoe UI, Inter, sans-serif" font-size="12" font-weight="800" text-anchor="middle">1. DATA INGESTION</text>

    <text x="15" y="60" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">CGMacros Cohort</text>
    <text x="15" y="78" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">45 participants</text>
    <text x="15" y="93" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">Normal / Prediab / T2D</text>

    <line x1="15" y1="110" x2="165" y2="110" stroke="#E2E8F0"/>

    <text x="15" y="130" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">Contiguous Runs</text>
    <text x="15" y="148" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">Delta = 60s validation</text>
    <text x="15" y="163" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">Zero gap interpolation</text>

    <line x1="15" y1="180" x2="165" y2="180" stroke="#E2E8F0"/>

    <text x="15" y="200" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">Lattice Grid (phi=0)</text>
    <text x="15" y="218" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">m(t) = round((t-t0)/60s)</text>
    <text x="15" y="233" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">m(t) mod 5 == 0</text>
  </g>

  <!-- Arrow 1 -> 2 -->
  <path d="M 235 235 L 265 235" stroke="#16A34A" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Block 2: Feature Matrix Construction -->
  <g transform="translate(270, 90)">
    <rect width="210" height="290" rx="10" fill="#F8FBF9" stroke="#D6E8DC" stroke-width="1.5"/>
    <rect width="210" height="34" rx="10" fill="#E8F5E9"/>
    <text x="105" y="22" fill="#166534" font-family="Segoe UI, Inter, sans-serif" font-size="12" font-weight="800" text-anchor="middle">2. GUARDED FEATURES</text>

    <text x="15" y="60" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">Glucose History (13)</text>
    <text x="15" y="78" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">y(t-5) through y(t-65)</text>

    <line x1="15" y1="95" x2="195" y2="95" stroke="#E2E8F0"/>

    <text x="15" y="115" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">Meal Context (3)</text>
    <text x="15" y="133" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">Time since last meal</text>
    <text x="15" y="148" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">Meal in 60m / No recent meal</text>

    <line x1="15" y1="165" x2="195" y2="165" stroke="#E2E8F0"/>

    <text x="15" y="185" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">Static Covariates (4)</text>
    <text x="15" y="203" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">Age, Gender, BMI, HbA1c</text>

    <line x1="15" y1="220" x2="195" y2="220" stroke="#E2E8F0"/>

    <text x="15" y="240" fill="#16A34A" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800">Total Predictor Matrix</text>
    <text x="15" y="258" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">R^20 Feature Vector</text>
  </g>

  <!-- Arrow 2 -> 3 -->
  <path d="M 485 235 L 515 235" stroke="#16A34A" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Block 3: Global Model Ladder & Participant Disjoint CV -->
  <g transform="translate(520, 90)">
    <rect width="240" height="290" rx="10" fill="#F8FBF9" stroke="#D6E8DC" stroke-width="1.5"/>
    <rect width="240" height="34" rx="10" fill="#E8F5E9"/>
    <text x="120" y="22" fill="#166534" font-family="Segoe UI, Inter, sans-serif" font-size="12" font-weight="800" text-anchor="middle">3. GLOBAL BENCHMARK</text>

    <text x="15" y="60" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">Participant-Disjoint CV</text>
    <text x="15" y="78" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">10 repeats x 5 folds (K=45)</text>
    <text x="15" y="93" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">Zero leakage between subjects</text>

    <line x1="15" y1="110" x2="225" y2="110" stroke="#E2E8F0"/>

    <text x="15" y="130" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">Model Ladder (Rungs 0-6)</text>
    <text x="15" y="148" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">R0: Persistence (y_base)</text>
    <text x="15" y="163" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">R1: Damped Trend</text>
    <text x="15" y="178" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">R2-R5: Ridge + Activity/Meals/Cov</text>
    <text x="15" y="193" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">R6: Fixed GBDT</text>

    <line x1="15" y1="210" x2="225" y2="210" stroke="#E2E8F0"/>

    <text x="15" y="230" fill="#16A34A" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800">Best Population Model</text>
    <text x="15" y="248" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">{callout_s2}</text>
  </g>

  <!-- Arrow 3 -> 4 -->
  <path d="M 765 235 L 795 235" stroke="#16A34A" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Block 4: Stage 3 Personalization Layer -->
  <g transform="translate(800, 90)">
    <rect width="250" height="290" rx="10" fill="#F0FDF4" stroke="#15803D" stroke-width="1.8"/>
    <rect width="250" height="34" rx="10" fill="#DCFCE7"/>
    <text x="125" y="22" fill="#166534" font-family="Segoe UI, Inter, sans-serif" font-size="12" font-weight="800" text-anchor="middle">4. PERSONALIZATION</text>

    <text x="15" y="60" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">Residual Correction</text>
    <text x="15" y="78" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">r(t) = y(t+h) - y_hat_global(t+h)</text>
    <text x="15" y="93" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">16 dynamic features (Lags+Meals)</text>

    <line x1="15" y1="110" x2="235" y2="110" stroke="#BBF7D0"/>

    <text x="15" y="130" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">Adaptation Windows</text>
    <text x="15" y="148" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">2, 4, and 6 Study Days</text>
    <text x="15" y="163" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">&gt;= 120m temporal purge buffer</text>

    <line x1="15" y1="180" x2="235" y2="180" stroke="#BBF7D0"/>

    <text x="15" y="200" fill="#14532D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="700">Bootstrap Evaluation</text>
    <text x="15" y="218" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">45 independent participant unit</text>
    <text x="15" y="233" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10">B=2,000 paired bootstrap</text>

    <line x1="15" y1="245" x2="235" y2="245" stroke="#BBF7D0"/>
    <text x="15" y="265" fill="#15803D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800">{callout_s3}</text>
  </g>
</svg>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_code)
    print(f"Generated {output_path}")


def generate_pipeline_workflow_svg(output_path: Path) -> None:
    """Create linear pipeline flow SVG banner in mild green light theme."""
    svg_code = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 120" width="100%" height="100%">
  <rect width="1000" height="120" rx="10" fill="#F8FBF9" stroke="#D6E8DC" stroke-width="1.5"/>

  <!-- Steps -->
  <g transform="translate(30, 25)">
    <rect width="130" height="70" rx="8" fill="#FFFFFF" stroke="#86EFAC"/>
    <text x="65" y="32" fill="#166534" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800" text-anchor="middle">CGMacros</text>
    <text x="65" y="52" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10" text-anchor="middle">45 Subjects (T2D)</text>
  </g>

  <path d="M 170 60 L 195 60" stroke="#16A34A" stroke-width="2"/>

  <g transform="translate(205, 25)">
    <rect width="135" height="70" rx="8" fill="#FFFFFF" stroke="#86EFAC"/>
    <text x="67" y="32" fill="#166534" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800" text-anchor="middle">Guarded Lags</text>
    <text x="67" y="52" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10" text-anchor="middle">13 Lags + Guard Band</text>
  </g>

  <path d="M 350 60 L 375 60" stroke="#16A34A" stroke-width="2"/>

  <g transform="translate(385, 25)">
    <rect width="145" height="70" rx="8" fill="#FFFFFF" stroke="#86EFAC"/>
    <text x="72" y="32" fill="#166534" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800" text-anchor="middle">Model Ladder</text>
    <text x="72" y="52" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10" text-anchor="middle">Rungs 0 through 6</text>
  </g>

  <path d="M 540 60 L 565 60" stroke="#16A34A" stroke-width="2"/>

  <g transform="translate(575, 25)">
    <rect width="150" height="70" rx="8" fill="#F0FDF4" stroke="#15803D"/>
    <text x="75" y="32" fill="#15803D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800" text-anchor="middle">Personalization</text>
    <text x="75" y="52" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10" text-anchor="middle">2, 4, 6 Study Days</text>
  </g>

  <path d="M 735 60 L 760 60" stroke="#15803D" stroke-width="2"/>

  <g transform="translate(770, 25)">
    <rect width="190" height="70" rx="8" fill="#F0FDF4" stroke="#15803D"/>
    <text x="95" y="32" fill="#15803D" font-family="Segoe UI, Inter, sans-serif" font-size="11" font-weight="800" text-anchor="middle">Participant Bootstrap</text>
    <text x="95" y="52" fill="#64748B" font-family="Segoe UI, Inter, sans-serif" font-size="10" text-anchor="middle">B=2,000 Independent CIs</text>
  </g>
</svg>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_code)
    print(f"Generated {output_path}")


def main() -> None:
    set_dark_theme()
    repo_root = Path(__file__).resolve().parent.parent
    assets_dir = repo_root / "assets"
    docs_reports = repo_root / "docs" / "reports"

    stage2_metrics_file = docs_reports / "stage2_baseline_metrics.json"
    stage3_metrics_file = docs_reports / "stage3_personalization_metrics.json"

    if not stage2_metrics_file.exists():
        raise FileNotFoundError(f"Missing Stage 2 metrics: {stage2_metrics_file}")
    if not stage3_metrics_file.exists():
        raise FileNotFoundError(f"Missing Stage 3 metrics: {stage3_metrics_file}")

    with open(stage2_metrics_file, encoding="utf-8") as f:
        stage2_data = json.load(f)
    with open(stage3_metrics_file, encoding="utf-8") as f:
        stage3_data = json.load(f)

    # 1. Automated validation check
    validate_metrics(stage2_data, stage3_data)

    print("Generating README visual assets...")
    generate_hero_banner_svg(assets_dir / "hero_banner.svg", stage2_data, stage3_data)
    generate_guard_band_timeline_svg(assets_dir / "guard_band_timeline.svg")
    generate_system_architecture_svg(
        assets_dir / "system_architecture.svg", stage2_data, stage3_data
    )
    generate_pipeline_workflow_svg(assets_dir / "pipeline_workflow.svg")
    generate_global_benchmark_chart(stage2_data, assets_dir / "global_benchmark.png")
    generate_personalization_dashboard(stage3_data, assets_dir / "personalization_dashboard.png")

    print("All README visual assets generated and verified successfully!")


if __name__ == "__main__":
    main()
