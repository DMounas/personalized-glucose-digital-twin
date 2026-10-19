"""Aggregate-only profiler for CGMacros meal encoding, timeseries coverage, and baseline cohorts.

Never opens photograph files as images. Never outputs individual participant traces or raw rows.
Produces privacy-preserving cohort-level distributions and data quality summaries.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def normalize_meal_type(val: Any) -> str:
    """Normalize raw meal type string to standard lowercase category."""
    if val is None or pd.isna(val):
        return "none"
    s = str(val).strip().lower()
    if "breakfast" in s:
        return "breakfast"
    elif "lunch" in s:
        return "lunch"
    elif "dinner" in s:
        return "dinner"
    elif "snack" in s:
        return "snack"
    return s


def compute_numeric_summary(values: list[float] | np.ndarray | pd.Series) -> dict[str, float]:
    """Compute aggregate descriptive statistics for numeric series."""
    arr = np.array(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return {
            "count": 0,
            "mean": 0.0,
            "std": 0.0,
            "median": 0.0,
            "q25": 0.0,
            "q75": 0.0,
            "min": 0.0,
            "max": 0.0,
        }
    return {
        "count": int(len(arr)),
        "mean": round(float(np.mean(arr)), 2),
        "std": round(float(np.std(arr)), 2),
        "median": round(float(np.median(arr)), 2),
        "q25": round(float(np.percentile(arr, 25)), 2),
        "q75": round(float(np.percentile(arr, 75)), 2),
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
    }


def profile_meals(dfs: list[pd.DataFrame]) -> dict[str, Any]:
    """Profile meal-field encoding and nutrition distributions across participants.

    Aggregate statistics only.
    """
    total_timeseries_rows = sum(len(df) for df in dfs)
    all_meal_rows = 0
    meal_type_counts: dict[str, int] = {}
    macro_data: dict[str, list[float]] = {
        "meal_calories": [],
        "meal_carbs": [],
        "meal_protein": [],
        "meal_fat": [],
        "meal_fiber": [],
        "sugar": [],
        "amount_consumed": [],
    }
    meals_with_image_path = 0

    # Impulse pattern check: count how many meal rows are immediately followed by another meal row
    consecutive_meal_rows = 0

    for df in dfs:
        if "meal_type" not in df.columns:
            continue
        meal_mask = df["meal_type"].notnull() & (df["meal_type"].astype(str).str.strip() != "")
        meal_df = df[meal_mask]
        all_meal_rows += len(meal_df)

        # Check consecutive impulse rows
        is_consec = meal_mask & meal_mask.shift(1).fillna(False)
        consecutive_meal_rows += int(is_consec.sum())

        for mt in meal_df["meal_type"]:
            norm_mt = normalize_meal_type(mt)
            meal_type_counts[norm_mt] = meal_type_counts.get(norm_mt, 0) + 1

        for col in macro_data.keys():
            if col in meal_df.columns:
                valid_vals = meal_df[col].dropna().astype(float).tolist()
                macro_data[col].extend(valid_vals)

        if "image_path" in meal_df.columns:
            has_img = meal_df["image_path"].notnull() & (
                meal_df["image_path"].astype(str).str.strip() != ""
            )
            meals_with_image_path += int(has_img.sum())

    macro_summaries = {col: compute_numeric_summary(vals) for col, vals in macro_data.items()}

    sparsity_pct = (
        (all_meal_rows / total_timeseries_rows * 100.0) if total_timeseries_rows > 0 else 0.0
    )
    img_pct = (meals_with_image_path / all_meal_rows * 100.0) if all_meal_rows > 0 else 0.0

    return {
        "total_meal_events": all_meal_rows,
        "total_timeseries_rows": total_timeseries_rows,
        "row_sparsity_pct": round(sparsity_pct, 4),
        "encoding_pattern": "Single-row impulse at meal start"
        if consecutive_meal_rows == 0
        else "Mixed impulse/interval",
        "consecutive_meal_rows_count": consecutive_meal_rows,
        "meal_types_distribution": meal_type_counts,
        "meals_with_photo_path_count": meals_with_image_path,
        "meals_with_photo_path_pct": round(img_pct, 2),
        "macro_distributions": macro_summaries,
    }


def profile_timeseries_coverage(dfs: list[pd.DataFrame]) -> dict[str, Any]:
    """Profile duration, row counts, and sensor availability across participants.

    Aggregate statistics only.
    """
    cohort_size = len(dfs)
    if cohort_size == 0:
        return {"cohort_size": 0}

    row_counts = [len(df) for df in dfs]
    durations_days: list[float] = []
    libre_cov: list[float] = []
    dexcom_cov: list[float] = []
    dual_cgm_cov: list[float] = []
    hr_cov: list[float] = []

    # Activity column prevalence
    has_calories_act = sum(1 for df in dfs if "calories_activity" in df.columns)
    has_mets = sum(1 for df in dfs if "mets" in df.columns)
    has_intensity = sum(1 for df in dfs if "intensity" in df.columns)
    has_steps = sum(1 for df in dfs if "steps" in df.columns)

    for df in dfs:
        n = len(df)
        if "relative_time_seconds" in df.columns and n > 0:
            dur_days = (
                float(df["relative_time_seconds"].max() - df["relative_time_seconds"].min())
                / 86400.0
            )
            durations_days.append(dur_days)
        elif "timestamp" in df.columns and n > 0:
            ts = pd.to_datetime(df["timestamp"], errors="coerce").dropna()
            if len(ts) > 1:
                dur_days = float((ts.max() - ts.min()).total_seconds()) / 86400.0
                durations_days.append(dur_days)

        if n > 0:
            lib = (df["libre_gl"].notnull().sum() / n * 100.0) if "libre_gl" in df.columns else 0.0
            dex = (
                (df["dexcom_gl"].notnull().sum() / n * 100.0) if "dexcom_gl" in df.columns else 0.0
            )
            dual = (
                ((df["libre_gl"].notnull() & df["dexcom_gl"].notnull()).sum() / n * 100.0)
                if ("libre_gl" in df.columns and "dexcom_gl" in df.columns)
                else 0.0
            )
            hr = (
                (df["heart_rate"].notnull().sum() / n * 100.0)
                if "heart_rate" in df.columns
                else 0.0
            )

            libre_cov.append(lib)
            dexcom_cov.append(dex)
            dual_cgm_cov.append(dual)
            hr_cov.append(hr)

    return {
        "cohort_size": cohort_size,
        "total_rows_sum": sum(row_counts),
        "rows_per_participant": compute_numeric_summary(row_counts),
        "duration_days": compute_numeric_summary(durations_days),
        "sensor_coverage_pct": {
            "libre_gl": compute_numeric_summary(libre_cov),
            "dexcom_gl": compute_numeric_summary(dexcom_cov),
            "dual_cgm_both": compute_numeric_summary(dual_cgm_cov),
            "heart_rate": compute_numeric_summary(hr_cov),
        },
        "sensor_missingness_pct": {
            "libre_gl_mean_missing": round(100.0 - float(np.mean(libre_cov)), 2),
            "dexcom_gl_mean_missing": round(100.0 - float(np.mean(dexcom_cov)), 2),
            "dual_cgm_mean_overlap": round(float(np.mean(dual_cgm_cov)), 2),
            "heart_rate_mean_missing": round(100.0 - float(np.mean(hr_cov)), 2),
        },
        "activity_column_prevalence": {
            "calories_activity_participants": has_calories_act,
            "mets_participants": has_mets,
            "intensity_participants": has_intensity,
            "steps_participants": has_steps,
        },
    }


def profile_baseline(bio_df: pd.DataFrame) -> dict[str, Any]:
    """Profile baseline cohort demographics, clinical labs, and sentinel values.

    Aggregate statistics only.
    """
    total = len(bio_df)
    hba1c_col = "hba1c_percent" if "hba1c_percent" in bio_df.columns else "A1c PDL (Lab)"

    # Metabolic status categorization
    categories = {"healthy": 0, "pre_diabetes": 0, "type_2_diabetes": 0, "unknown": 0}
    if hba1c_col in bio_df.columns:
        for val in bio_df[hba1c_col]:
            if pd.isna(val):
                categories["unknown"] += 1
            elif val < 5.7:
                categories["healthy"] += 1
            elif val <= 6.4:
                categories["pre_diabetes"] += 1
            else:
                categories["type_2_diabetes"] += 1

    # Demographics
    demographics = {}
    for col in [
        "age_years",
        "bmi",
        "weight_lbs",
        "height_inches",
        hba1c_col,
        "fasting_glucose_mg_dl",
        "fasting_insulin_mcu_ml",
    ]:
        if col in bio_df.columns:
            demographics[col] = compute_numeric_summary(bio_df[col].dropna())

    # Sentinel detection in clinical labs
    sentinels = {
        "ldl_800_error_count": int((bio_df["ldl_calculated_mg_dl"] == 800).sum())
        if "ldl_calculated_mg_dl" in bio_df.columns
        else 0,
        "vldl_400_error_count": int((bio_df["vldl_calculated_mg_dl"] == 400).sum())
        if "vldl_calculated_mg_dl" in bio_df.columns
        else 0,
        "cho_hdl_ratio_400_error_count": int((bio_df["cholesterol_hdl_ratio"] == 400).sum())
        if "cholesterol_hdl_ratio" in bio_df.columns
        else 0,
    }

    return {
        "total_participants": total,
        "metabolic_status_counts": categories,
        "metabolic_status_proportions": {
            k: round(v / total * 100.0, 1) if total > 0 else 0.0 for k, v in categories.items()
        },
        "demographics_and_labs": demographics,
        "sentinel_counts": sentinels,
    }
