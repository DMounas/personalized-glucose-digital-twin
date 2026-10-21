"""Structured data loader and validators for the Glucose Digital Twin Dashboard.

Loads and parses canonical aggregate benchmark metrics directly from:
- docs/reports/stage2_baseline_metrics.json
- docs/reports/stage3_personalization_metrics.json

Guarantees data privacy:
- Extracts strictly cohort-level and subgroup summaries.
- Never reads or exposes raw participant traces, individual IDs, or prediction arrays.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Default repository paths
DEFAULT_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_STAGE2_PATH = DEFAULT_REPO_ROOT / "docs" / "reports" / "stage2_baseline_metrics.json"
DEFAULT_STAGE3_PATH = DEFAULT_REPO_ROOT / "docs" / "reports" / "stage3_personalization_metrics.json"


@dataclass(frozen=True)
class GlobalRungMetric:
    """Cohort summary for one model rung in the Stage 2 ladder."""

    rung_key: str
    rung_label: str
    model_name: str
    feature_description: str
    mean_rmse: float
    ci_95_rmse: tuple[float, float]
    mean_mae: float
    ci_95_mae: tuple[float, float]
    mean_skill_pct: float
    ci_95_skill_pct: tuple[float, float]
    fraction_improved: float
    n_improved: int
    total_participants: int
    color: str
    subgroups: dict[str, dict[str, float]]


@dataclass(frozen=True)
class PersonalizationWindowMetric:
    """Cohort summary for one adaptation window in Stage 3."""

    window_key: str
    window_label: str
    horizon_key: str
    horizon_label: str
    matched_global_rmse: float
    personalized_rmse: float
    mean_delta_rmse: float
    ci_95_delta_rmse: tuple[float, float]
    mean_pct_reduction: float
    fraction_improved: float
    n_improved: int
    total_participants: int
    is_statistically_significant: bool
    subgroups: dict[str, dict[str, float]]


# Model metadata mapping for the 8 rungs
RUNG_METADATA = [
    {
        "key": "rung0_guarded_persistence",
        "label": "Rung 0",
        "name": "Guarded Persistence",
        "features": "Latest observed glucose lag y(t-5)",
        "color": "#94A3B8",
    },
    {
        "key": "rung1_damped_trend",
        "label": "Rung 1",
        "name": "Damped Trend",
        "features": "2 lags + inner-CV tuned damping parameter",
        "color": "#64748B",
    },
    {
        "key": "rung2_ridge_regression",
        "label": "Rung 2",
        "name": "Guarded Ridge",
        "features": "13 autoregressive lags: [y(t-65) ... y(t-5)]",
        "color": "#86EFAC",
    },
    {
        "key": "rung3_activity_ridge",
        "label": "Rung 3",
        "name": "+ Activity Ridge",
        "features": "13 lags + Heart Rate & METs (preceding 30m)",
        "color": "#4ADE80",
    },
    {
        "key": "rung4_meal_ridge",
        "label": "Rung 4",
        "name": "+ Meal Context (Full)",
        "features": "13 lags + meal timing & macronutrients",
        "color": "#22C55E",
    },
    {
        "key": "rung4_nomacros_ablation",
        "label": "Rung 4b",
        "name": "+ Meal Timing Only",
        "features": "13 lags + time-since-meal & meal flags (no macros)",
        "color": "#16A34A",
    },
    {
        "key": "rung5_baseline_covariates",
        "label": "Rung 5",
        "name": "+ Clinical Covariates",
        "features": "13 lags + meal timing + Age, Sex, BMI, HbA1c",
        "color": "#15803D",
    },
    {
        "key": "rung6_hist_gradient_boosting",
        "label": "Rung 6",
        "name": "Fixed GBDT (Nonlinear)",
        "features": "Same multimodal 20 features with HistGradientBoosting",
        "color": "#475569",
    },
]

WINDOW_METADATA = [
    {"key": "window_2d", "label": "2 Study Days", "days": 2},
    {"key": "window_4d", "label": "4 Study Days", "days": 4},
    {"key": "window_6d", "label": "6 Study Days", "days": 6},
]


class DashboardDataLoader:
    """Thread-safe, privacy-preserving loader for aggregate research metrics."""

    def __init__(
        self,
        stage2_path: Path | str | None = None,
        stage3_path: Path | str | None = None,
    ) -> None:
        self.stage2_path = Path(stage2_path) if stage2_path else DEFAULT_STAGE2_PATH
        self.stage3_path = Path(stage3_path) if stage3_path else DEFAULT_STAGE3_PATH

        self._s2_raw: dict[str, Any] | None = None
        self._s3_raw: dict[str, Any] | None = None

    def _ensure_loaded(self) -> None:
        if self._s2_raw is None:
            if not self.stage2_path.exists():
                raise FileNotFoundError(f"Canonical Stage 2 report not found: {self.stage2_path}")
            with open(self.stage2_path, encoding="utf-8") as f:
                self._s2_raw = json.load(f)

        if self._s3_raw is None:
            if not self.stage3_path.exists():
                raise FileNotFoundError(f"Canonical Stage 3 report not found: {self.stage3_path}")
            with open(self.stage3_path, encoding="utf-8") as f:
                self._s3_raw = json.load(f)

    def get_global_ladder(self, horizon: str = "h30") -> list[GlobalRungMetric]:
        """Load all 8 model rungs for the given horizon ('h30' or 'h60')."""
        self._ensure_loaded()
        assert self._s2_raw is not None
        h_key = "h30" if "30" in horizon else "h60"
        h_data = self._s2_raw["horizons"][h_key]

        results = []
        for meta in RUNG_METADATA:
            k = meta["key"]
            if k not in h_data:
                continue
            summary = h_data[k]["summary"]
            rmse_info = summary["headline_rmse"]
            mae_info = summary["headline_mae"]
            skill_info = summary["headline_skill"]

            subgroups_data: dict[str, dict[str, float]] = {}
            if "subgroups" in summary:
                for grp, grp_info in summary["subgroups"].items():
                    subgroups_data[grp] = {
                        "n_participants": grp_info.get("n_participants", 0),
                        "mean_rmse": grp_info.get("mean_rmse", 0.0),
                        "median_rmse": grp_info.get("median_rmse", 0.0),
                        "mean_skill": grp_info.get("mean_skill", 0.0) * 100,
                        "fraction_improved": grp_info.get("fraction_improved", 0.0) * 100,
                    }

            metric = GlobalRungMetric(
                rung_key=k,
                rung_label=meta["label"],
                model_name=meta["name"],
                feature_description=meta["features"],
                mean_rmse=float(rmse_info["mean"]),
                ci_95_rmse=(float(rmse_info["ci_95_mean"][0]), float(rmse_info["ci_95_mean"][1])),
                mean_mae=float(mae_info["mean"]),
                ci_95_mae=(float(mae_info["ci_95_mean"][0]), float(mae_info["ci_95_mean"][1])),
                mean_skill_pct=float(skill_info["mean"]) * 100.0,
                ci_95_skill_pct=(
                    float(skill_info["ci_95_mean"][0]) * 100.0,
                    float(skill_info["ci_95_mean"][1]) * 100.0,
                ),
                fraction_improved=float(skill_info.get("fraction_improved", 0.0)),
                n_improved=int(skill_info.get("n_participants_improved", 0)),
                total_participants=int(summary.get("cohort_participants", 45)),
                color=meta["color"],
                subgroups=subgroups_data,
            )
            results.append(metric)

        return results

    def get_personalization_metric(
        self, horizon: str = "h60", window: str = "window_6d"
    ) -> PersonalizationWindowMetric:
        """Load single personalization window metric."""
        self._ensure_loaded()
        assert self._s3_raw is not None
        h_key = "h30" if "30" in horizon else "h60"
        h_label = "+30 min" if h_key == "h30" else "+60 min"

        w_key = window if window.startswith("window_") else f"window_{window}"
        win_dict = next((w for w in WINDOW_METADATA if w["key"] == w_key), WINDOW_METADATA[2])

        w_data = self._s3_raw["horizons"][h_key]["windows"][w_key]
        summary = w_data["summary"]
        diff = summary["paired_difference"]
        ci_delta = (
            float(diff["ci_95_mean_delta_rmse"][0]),
            float(diff["ci_95_mean_delta_rmse"][1]),
        )

        # Statistical significance: 95% bootstrap CI must strictly exclude 0 (upper CI < 0)
        is_significant = ci_delta[1] < 0.0

        subgroups_data: dict[str, dict[str, float]] = {}
        if "subgroups" in summary:
            for grp, grp_info in summary["subgroups"].items():
                subgroups_data[grp] = {
                    "n_participants": grp_info.get("n_participants", 0),
                    "mean_rmse_global": grp_info.get("mean_rmse_global", 0.0),
                    "mean_rmse_pers": grp_info.get("mean_rmse_pers", 0.0),
                    "mean_delta_rmse": grp_info.get("mean_delta_rmse", 0.0),
                    "mean_pct_reduction": grp_info.get("mean_pct_reduction", 0.0),
                    "fraction_improved": grp_info.get("fraction_improved", 0.0) * 100,
                    "n_improved": grp_info.get("n_improved", 0),
                }

        return PersonalizationWindowMetric(
            window_key=w_key,
            window_label=str(win_dict["label"]),
            horizon_key=h_key,
            horizon_label=h_label,
            matched_global_rmse=float(summary["matched_global"]["mean_rmse"]),
            personalized_rmse=float(summary["personalized"]["mean_rmse"]),
            mean_delta_rmse=float(diff["mean_delta_rmse"]),
            ci_95_delta_rmse=ci_delta,
            mean_pct_reduction=float(diff["mean_pct_reduction"]),
            fraction_improved=float(diff["fraction_improved"]),
            n_improved=int(diff["n_improved"]),
            total_participants=int(summary.get("cohort_participants", 45)),
            is_statistically_significant=is_significant,
            subgroups=subgroups_data,
        )

    def get_personalization_trajectory(
        self, horizon: str = "h60"
    ) -> list[PersonalizationWindowMetric]:
        """Load all three adaptation windows (2d, 4d, 6d) for dose-response curve."""
        return [
            self.get_personalization_metric(horizon=horizon, window=str(w["key"]))
            for w in WINDOW_METADATA
        ]
