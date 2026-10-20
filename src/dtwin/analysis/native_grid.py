"""Native-grid inference and synthetic validation engine (R2 corrected).

Scientific rationale:
CGMacros is documented as uniform 1-minute series linearly interpolated from
5-minute (Dexcom) and 15-minute (Libre) measurements.
This module distinguishes between 5-min and 15-min nested lattices using
run-bounded second-difference bend curvature, intermediate 5-minute bend analysis,
linear reconstruction residuals, and phase stability.

Time semantics (T1-T7):
- Explicit elapsed-time coordinates t_min mod P per run.
- Zero cross-gap second differences (eliminates boundary false bends).
- Native lattice selection based on elapsed minutes from run/series reference t0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from dtwin.analysis.benchmark_generator import (
    generate_blind_benchmark_trace,
    simulate_physiological_glucose,
)


@dataclass
class NativeGridInferenceResult:
    """Outcome of native grid inference on a continuous time series."""

    period_inferred: int | None
    phase_inferred: int | None
    confidence: str  # HIGH_CONFIDENCE, MEDIUM_CONFIDENCE, AMBIGUOUS, NO_RELIABLE_LATTICE
    is_native_inferred: bool
    reconstruction_residual_mean: float
    reconstruction_residual_max: float
    total_bends_detected: int
    informative_bends_fraction: float
    lattice_hit_rate: float
    intermediate_5min_bends_count: int
    intermediate_bend_distinction_ratio: float
    phase_stability_score: float
    candidate_gap_fill_segments: int


def wilson_score_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion."""
    if total == 0:
        return (0.0, 0.0)
    z = 1.959963984540054 if abs(confidence - 0.95) < 1e-4 else 2.5758293035489004
    p_hat = successes / total
    denom = 1.0 + (z**2) / total
    center = (p_hat + (z**2) / (2 * total)) / denom
    margin = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / total) + ((z**2) / (4 * total**2)))
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    if successes == 0:
        lower = 0.0
    if successes == total:
        upper = 1.0
    return (float(lower), float(upper))


def generate_synthetic_trace(
    scenario: str,
    length_points: int = 1440,
    noise_std: float = 0.2,
    integer_rounding: bool = True,
    seed: int | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Generate seeded synthetic glucose-like time series for backward compatibility.

    Calls underlying physiological generator for realistic traces.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(length_points)
    true_glucose = simulate_physiological_glucose(length_points=length_points, seed=seed)

    meta: dict[str, Any] = {"scenario": scenario, "length": length_points}

    if scenario == "continuous_one_minute_negative_control":
        trace = true_glucose + rng.normal(0, noise_std, length_points)
        if integer_rounding:
            trace = np.round(trace)
        meta["true_period"] = 1
        meta["true_phase"] = 0
        return trace, meta

    if scenario in (
        "five_minute_native",
        "five_minute_with_amplitude_noise_and_drops",
        "five_minute_with_jitter_and_drops",
    ):
        period = 5
        phase = int(rng.integers(0, period))
        sample_indices = np.arange(phase, length_points, period)

        if scenario in (
            "five_minute_with_amplitude_noise_and_drops",
            "five_minute_with_jitter_and_drops",
        ):
            keep_mask = rng.uniform(0, 1, len(sample_indices)) > 0.05
            if not keep_mask[0]:
                keep_mask[0] = True
            if not keep_mask[-1]:
                keep_mask[-1] = True
            sample_indices = sample_indices[keep_mask]  # type: ignore[assignment]

        sample_vals = true_glucose[sample_indices] + rng.normal(0, noise_std, len(sample_indices))
        if integer_rounding:
            sample_vals = np.round(sample_vals)

        interp_trace = np.interp(t, sample_indices, sample_vals)
        meta["true_period"] = 5
        meta["true_phase"] = phase
        return interp_trace, meta

    if scenario in ("fifteen_minute_native", "fifteen_minute_with_flat_stretches"):
        period = 15
        phase = int(rng.integers(0, period))
        sample_indices = np.arange(phase, length_points, period)

        sample_vals = true_glucose[sample_indices] + rng.normal(0, noise_std, len(sample_indices))
        if scenario == "fifteen_minute_with_flat_stretches":
            flat_mask = sample_indices < 300
            if np.any(flat_mask):
                sample_vals[flat_mask] = sample_vals[flat_mask][0]

        if integer_rounding:
            sample_vals = np.round(sample_vals)

        interp_trace = np.interp(t, sample_indices, sample_vals)
        meta["true_period"] = 15
        meta["true_phase"] = phase
        return interp_trace, meta

    msg = f"Unknown synthetic scenario: {scenario}"
    raise ValueError(msg)


def infer_native_grid_series(
    values: np.ndarray | pd.Series,
    config: dict[str, Any] | None = None,
    timestamps: np.ndarray | pd.Series | None = None,
) -> NativeGridInferenceResult:
    """Infer candidate native grid (5-min or 15-min) from a 1-minute time series.

    Combines:
    1. Second difference (bend) locations evaluated strictly within contiguous runs (no boundary false bends).
    2. Linear reconstruction residual under candidate lattices evaluated per run.
    3. Nested lattice intermediate bend differentiation.
    4. Phase stability across 1-day windows.
    """
    cfg = config.get("native_grid", {}) if config else {}
    bend_thresh = cfg.get("second_difference_bend_threshold", 0.15)
    max_res_thresh = cfg.get("max_reconstruction_residual_mg_dl", 0.35)
    min_bends_required = cfg.get("min_informative_bends_count", 20)
    gap_fill_thresh = cfg.get("gap_fill_candidate_threshold_minutes", 30)

    # Convert inputs to uniform arrays
    if isinstance(values, pd.Series):
        vals = values.to_numpy(dtype=float)
    else:
        vals = np.asarray(values, dtype=float)

    n_raw = len(vals)
    if n_raw == 0:
        return _empty_result()

    # Determine runs and elapsed-minute coordinates
    if timestamps is not None:
        if isinstance(timestamps, pd.Series):
            ts_series = pd.to_datetime(timestamps)
        else:
            ts_series = pd.Series(pd.to_datetime(timestamps))

        # Valid rows: non-null value and valid timestamp
        valid_mask = (~np.isnan(vals)) & (~ts_series.isna())
        valid_indices = np.where(valid_mask)[0]
        if len(valid_indices) < 120:
            return _empty_result()

        t0 = ts_series.iloc[valid_indices[0]]
        # Compute elapsed minutes from t0
        elapsed_all = np.full(n_raw, -1, dtype=int)
        elapsed_valid = np.round(
            (ts_series.iloc[valid_indices] - t0).dt.total_seconds() / 60.0
        ).astype(int)
        elapsed_all[valid_indices] = elapsed_valid.to_numpy()

        # Identify contiguous runs: valid mask AND step == 60 seconds
        runs: list[tuple[int, int]] = []
        cur_start = 0
        for i in range(1, len(valid_indices)):
            prev_idx = valid_indices[i - 1]
            curr_idx = valid_indices[i]
            # Check step: row indices contiguous OR timestamp step == 60s
            dt_s = (ts_series.iloc[curr_idx] - ts_series.iloc[prev_idx]).total_seconds()
            if abs(dt_s - 60.0) > 1.0:
                runs.append((valid_indices[cur_start], valid_indices[i - 1]))
                cur_start = i
        runs.append((valid_indices[cur_start], valid_indices[-1]))
    else:
        # Timestamps not provided: assume consecutive integer minutes 0..n-1
        valid_mask = ~np.isnan(vals)
        valid_indices = np.where(valid_mask)[0]
        if len(valid_indices) < 120:
            return _empty_result()

        elapsed_all = np.arange(n_raw, dtype=int)
        # Identify runs of contiguous valid indices
        runs = []
        cur_start = 0
        for i in range(1, len(valid_indices)):
            if valid_indices[i] != valid_indices[i - 1] + 1:
                runs.append((valid_indices[cur_start], valid_indices[i - 1]))
                cur_start = i
        runs.append((valid_indices[cur_start], valid_indices[-1]))

    # Collect bends strictly WITHIN contiguous runs (eliminates gap boundary bends)
    bend_elapsed_minutes: list[int] = []
    total_valid_eval_points = 0
    candidate_gap_fill_segments = 0

    for r_start, r_end in runs:
        r_len = r_end - r_start + 1
        if r_len < 3:
            continue
        r_vals = vals[r_start : r_end + 1]
        r_elapsed = elapsed_all[r_start : r_end + 1]
        total_valid_eval_points += r_len - 2

        # Second differences within this run
        d2 = np.abs(r_vals[2:] - 2.0 * r_vals[1:-1] + r_vals[:-2])
        is_bend = d2 > bend_thresh
        bend_sub_idx = np.where(is_bend)[0] + 1  # interior points
        for b_idx in bend_sub_idx:
            bend_elapsed_minutes.append(int(r_elapsed[b_idx]))

        # Check collinear / flat stretches within run
        is_collinear = ~is_bend
        cur_collinear_run = 0
        for flag in is_collinear:
            if flag:
                cur_collinear_run += 1
            else:
                if cur_collinear_run >= gap_fill_thresh:
                    candidate_gap_fill_segments += 1
                cur_collinear_run = 0
        if cur_collinear_run >= gap_fill_thresh:
            candidate_gap_fill_segments += 1

    total_bends = len(bend_elapsed_minutes)
    informative_fraction = total_bends / max(1, total_valid_eval_points)
    bends_arr = np.array(bend_elapsed_minutes, dtype=int)

    # Evaluate candidate period 5
    best_5_phase = 0
    best_5_hits = -1
    for phi in range(5):
        hits = int(np.sum((bends_arr % 5) == phi)) if total_bends > 0 else 0
        if hits > best_5_hits:
            best_5_hits = hits
            best_5_phase = phi
    hit_rate_5 = best_5_hits / max(1, total_bends)

    # Evaluate candidate period 15
    best_15_phase = 0
    best_15_hits = -1
    for phi in range(15):
        hits = int(np.sum((bends_arr % 15) == phi)) if total_bends > 0 else 0
        if hits > best_15_hits:
            best_15_hits = hits
            best_15_phase = phi
    hit_rate_15 = best_15_hits / max(1, total_bends)

    # Compute reconstruction residuals per run for candidate 5-min and 15-min lattices
    res_5_vals: list[np.ndarray] = []
    res_15_vals: list[np.ndarray] = []

    for r_start, r_end in runs:
        r_vals = vals[r_start : r_end + 1]
        r_elapsed = elapsed_all[r_start : r_end + 1]

        # 5-min reconstruction
        mask_5 = (r_elapsed % 5) == best_5_phase
        if np.sum(mask_5) >= 2:
            native_pos_5 = np.where(mask_5)[0]
            start_p, end_p = native_pos_5[0], native_pos_5[-1]
            sub_t = r_elapsed[start_p : end_p + 1]
            sub_v = r_vals[start_p : end_p + 1]
            recon_5 = np.interp(sub_t, r_elapsed[native_pos_5], r_vals[native_pos_5])
            res_5_vals.append(np.abs(sub_v - recon_5))

        # 15-min reconstruction
        mask_15 = (r_elapsed % 15) == best_15_phase
        if np.sum(mask_15) >= 2:
            native_pos_15 = np.where(mask_15)[0]
            start_p, end_p = native_pos_15[0], native_pos_15[-1]
            sub_t = r_elapsed[start_p : end_p + 1]
            sub_v = r_vals[start_p : end_p + 1]
            recon_15 = np.interp(sub_t, r_elapsed[native_pos_15], r_vals[native_pos_15])
            res_15_vals.append(np.abs(sub_v - recon_15))

    if res_5_vals:
        all_res_5 = np.concatenate(res_5_vals)
        res_5_mean = float(np.mean(all_res_5))
        res_5_max = float(np.max(all_res_5))
    else:
        res_5_mean, res_5_max = 999.0, 999.0

    if res_15_vals:
        all_res_15 = np.concatenate(res_15_vals)
        res_15_mean = float(np.mean(all_res_15))
        res_15_max = float(np.max(all_res_15))
    else:
        res_15_mean, res_15_max = 999.0, 999.0

    # Intermediate 5-minute bend analysis
    intermediate_phases = [(best_15_phase + 5) % 15, (best_15_phase + 10) % 15]
    if total_bends > 0:
        intermediate_bends = int(
            np.sum(
                (bends_arr % 15 == intermediate_phases[0])
                | (bends_arr % 15 == intermediate_phases[1])
            )
        )
    else:
        intermediate_bends = 0
    ratio_intermediate = (best_15_hits + 1.0) / (intermediate_bends + 1.0)

    # Phase stability across 1440-minute blocks of elapsed time
    max_elapsed = int(np.max(elapsed_all)) if len(elapsed_all) > 0 else 0
    n_blocks = max_elapsed // 1440
    if n_blocks > 1 and total_bends > 0:
        phase_5_matches = 0
        blocks_evaluated = 0
        for b in range(n_blocks):
            sub_bends = bends_arr[(bends_arr >= b * 1440) & (bends_arr < (b + 1) * 1440)]
            if len(sub_bends) > 10:
                sub_phase = int(np.argmax([np.sum((sub_bends % 5) == p) for p in range(5)]))
                if sub_phase == best_5_phase:
                    phase_5_matches += 1
                blocks_evaluated += 1
        stability_5 = phase_5_matches / max(1, blocks_evaluated)
    else:
        stability_5 = 1.0

    # Negative control / no reliable lattice checks
    if (
        total_bends < min_bends_required
        or (hit_rate_5 < 0.60 and hit_rate_15 < 0.60)
        or min(res_5_mean, res_15_mean) > max_res_thresh * 2
    ):
        return NativeGridInferenceResult(
            period_inferred=None,
            phase_inferred=None,
            confidence="NO_RELIABLE_LATTICE",
            is_native_inferred=False,
            reconstruction_residual_mean=min(res_5_mean, res_15_mean),
            reconstruction_residual_max=min(res_5_max, res_15_max),
            total_bends_detected=total_bends,
            informative_bends_fraction=informative_fraction,
            lattice_hit_rate=max(hit_rate_5, hit_rate_15),
            intermediate_5min_bends_count=intermediate_bends,
            intermediate_bend_distinction_ratio=ratio_intermediate,
            phase_stability_score=stability_5,
            candidate_gap_fill_segments=candidate_gap_fill_segments,
        )

    # Disentangle 15-min vs 5-min
    if res_15_mean <= max_res_thresh and intermediate_bends < max(5, 0.05 * total_bends):
        conf = (
            "HIGH_CONFIDENCE"
            if res_15_mean <= 0.25 and hit_rate_15 >= 0.85
            else "MEDIUM_CONFIDENCE"
        )
        return NativeGridInferenceResult(
            period_inferred=15,
            phase_inferred=best_15_phase,
            confidence=conf,
            is_native_inferred=True,
            reconstruction_residual_mean=res_15_mean,
            reconstruction_residual_max=res_15_max,
            total_bends_detected=total_bends,
            informative_bends_fraction=informative_fraction,
            lattice_hit_rate=hit_rate_15,
            intermediate_5min_bends_count=intermediate_bends,
            intermediate_bend_distinction_ratio=ratio_intermediate,
            phase_stability_score=stability_5,
            candidate_gap_fill_segments=candidate_gap_fill_segments,
        )

    if res_5_mean <= max_res_thresh and hit_rate_5 >= 0.80:
        conf = (
            "HIGH_CONFIDENCE"
            if res_5_mean <= 0.25 and hit_rate_5 >= 0.90 and stability_5 >= 0.80
            else "MEDIUM_CONFIDENCE"
        )
        return NativeGridInferenceResult(
            period_inferred=5,
            phase_inferred=best_5_phase,
            confidence=conf,
            is_native_inferred=True,
            reconstruction_residual_mean=res_5_mean,
            reconstruction_residual_max=res_5_max,
            total_bends_detected=total_bends,
            informative_bends_fraction=informative_fraction,
            lattice_hit_rate=hit_rate_5,
            intermediate_5min_bends_count=intermediate_bends,
            intermediate_bend_distinction_ratio=ratio_intermediate,
            phase_stability_score=stability_5,
            candidate_gap_fill_segments=candidate_gap_fill_segments,
        )

    return NativeGridInferenceResult(
        period_inferred=None,
        phase_inferred=None,
        confidence="AMBIGUOUS",
        is_native_inferred=False,
        reconstruction_residual_mean=min(res_5_mean, res_15_mean),
        reconstruction_residual_max=min(res_5_max, res_15_max),
        total_bends_detected=total_bends,
        informative_bends_fraction=informative_fraction,
        lattice_hit_rate=max(hit_rate_5, hit_rate_15),
        intermediate_5min_bends_count=intermediate_bends,
        intermediate_bend_distinction_ratio=ratio_intermediate,
        phase_stability_score=stability_5,
        candidate_gap_fill_segments=candidate_gap_fill_segments,
    )


def _empty_result() -> NativeGridInferenceResult:
    return NativeGridInferenceResult(
        period_inferred=None,
        phase_inferred=None,
        confidence="NO_RELIABLE_LATTICE",
        is_native_inferred=False,
        reconstruction_residual_mean=float("nan"),
        reconstruction_residual_max=float("nan"),
        total_bends_detected=0,
        informative_bends_fraction=0.0,
        lattice_hit_rate=0.0,
        intermediate_5min_bends_count=0,
        intermediate_bend_distinction_ratio=0.0,
        phase_stability_score=0.0,
        candidate_gap_fill_segments=0,
    )


def run_synthetic_validation(
    config_path: Path | str,
    samples_per_scenario: int = 500,
    seed: int = 42,
) -> dict[str, Any]:
    """Execute synthetic validation of the native-grid inference engine (5 core scenarios)."""
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    cfg_scenarios = config.get("synthetic_validation", {}).get("scenarios") if config else None
    if cfg_scenarios:
        scenarios = list(cfg_scenarios)
    else:
        scenarios = [
            "five_minute_native",
            "fifteen_minute_native",
            "continuous_one_minute_negative_control",
            "five_minute_with_amplitude_noise_and_drops",
            "fifteen_minute_with_flat_stretches",
        ]

    results_by_scenario: dict[str, Any] = {}
    confusion_matrix: dict[str, dict[str, int]] = {
        sc: {"inferred_5": 0, "inferred_15": 0, "no_lattice_or_ambiguous": 0} for sc in scenarios
    }

    for sc in scenarios:
        inferred_5 = 0
        inferred_15 = 0
        unresolved = 0
        conf_counts: dict[str, int] = {}

        for i in range(samples_per_scenario):
            trace, _ = generate_synthetic_trace(
                scenario=sc,
                length_points=1440,
                noise_std=0.2,
                integer_rounding=True,
                seed=seed + i,
            )
            res = infer_native_grid_series(trace, config)
            conf_counts[res.confidence] = conf_counts.get(res.confidence, 0) + 1

            if res.period_inferred == 5:
                inferred_5 += 1
                confusion_matrix[sc]["inferred_5"] += 1
            elif res.period_inferred == 15:
                inferred_15 += 1
                confusion_matrix[sc]["inferred_15"] += 1
            else:
                unresolved += 1
                confusion_matrix[sc]["no_lattice_or_ambiguous"] += 1

        total = samples_per_scenario
        if sc in (
            "five_minute_native",
            "five_minute_with_amplitude_noise_and_drops",
            "five_minute_with_jitter_and_drops",
        ):
            success_count = inferred_5
            metric_name = "sensitivity_5min"
        elif sc in ("fifteen_minute_native", "fifteen_minute_with_flat_stretches"):
            success_count = inferred_15
            metric_name = "sensitivity_15min"
        else:
            success_count = unresolved
            metric_name = "specificity_negative_control"

        rate = success_count / total
        ci_low, ci_high = wilson_score_interval(success_count, total)

        results_by_scenario[sc] = {
            "samples": total,
            "inferred_5_count": inferred_5,
            "inferred_15_count": inferred_15,
            "unresolved_count": unresolved,
            "primary_metric": metric_name,
            "rate": round(rate, 4),
            "wilson_ci_95": [round(ci_low, 4), round(ci_high, 4)],
            "confidence_distribution": conf_counts,
        }

    crit = config.get("synthetic_validation", {}).get("acceptance_criteria", {})
    min_sens_5 = crit.get("min_sensitivity_5min", 0.90)
    min_sens_15 = crit.get("min_sensitivity_15min", 0.90)
    max_fp_neg = crit.get("max_false_lattice_rate_negative_control", 0.05)

    sens_5_clean = results_by_scenario["five_minute_native"]["rate"]
    sens_15_clean = results_by_scenario["fifteen_minute_native"]["rate"]
    fp_neg = 1.0 - results_by_scenario["continuous_one_minute_negative_control"]["rate"]

    passed_criteria = (
        sens_5_clean >= min_sens_5 and sens_15_clean >= min_sens_15 and fp_neg <= max_fp_neg
    )

    return {
        "status": "PASSED" if passed_criteria else "FAILED",
        "scenarios_evaluated": len(scenarios),
        "total_test_series": len(scenarios) * samples_per_scenario,
        "results_by_scenario": results_by_scenario,
        "confusion_matrix": confusion_matrix,
        "acceptance_criteria_checks": {
            "sensitivity_5min": {
                "observed": sens_5_clean,
                "target": min_sens_5,
                "passed": bool(sens_5_clean >= min_sens_5),
            },
            "sensitivity_15min": {
                "observed": sens_15_clean,
                "target": min_sens_15,
                "passed": bool(sens_15_clean >= min_sens_15),
            },
            "false_positive_rate_negative_control": {
                "observed": round(fp_neg, 4),
                "target": max_fp_neg,
                "passed": bool(fp_neg <= max_fp_neg),
            },
        },
    }


def run_blind_benchmark_validation(
    config_path: Path | str,
    samples_per_scenario: int = 100,
    seed: int = 42,
) -> dict[str, Any]:
    """Execute detector-blind synthetic validation across 15 independent scenarios (C5)."""
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    scenarios = [
        "true_5min_linear",
        "true_15min_linear",
        "true_5min_rounded",
        "true_15min_rounded",
        "native_timestamp_jitter_5min",
        "native_timestamp_jitter_15min",
        "dropped_native_bridged_5min",
        "dropped_native_bridged_15min",
        "dropped_native_nan_5min",
        "absent_timestamp_gaps_15min",
        "collinear_flat_periods",
        "low_dynamic_range",
        "alternative_resampling_cubic_pchip",
        "alternative_resampling_nearest",
        "physiological_simulator_continuous",
    ]

    results_by_scenario: dict[str, Any] = {}
    for sc in scenarios:
        inferred_5 = 0
        inferred_15 = 0
        unresolved = 0
        for i in range(samples_per_scenario):
            trace, meta = generate_blind_benchmark_trace(sc, length_points=1440, seed=seed + i)
            res = infer_native_grid_series(trace, config)
            if res.period_inferred == 5:
                inferred_5 += 1
            elif res.period_inferred == 15:
                inferred_15 += 1
            else:
                unresolved += 1

        # Ground truth evaluation based on scenario metadata
        total = samples_per_scenario
        if meta.get("is_lattice", False):
            expected_period = meta.get("true_period")
            if expected_period == 5:
                success = inferred_5
            elif expected_period == 15:
                success = inferred_15
            else:
                success = unresolved
        else:
            success = unresolved

        ci_low, ci_high = wilson_score_interval(success, total)
        results_by_scenario[sc] = {
            "samples": total,
            "inferred_5": inferred_5,
            "inferred_15": inferred_15,
            "unresolved": unresolved,
            "success_rate": round(success / total, 4),
            "wilson_ci_95": [round(ci_low, 4), round(ci_high, 4)],
        }

    return {
        "benchmark_name": "detector_blind_15_scenario_suite",
        "scenarios_evaluated": len(scenarios),
        "samples_per_scenario": samples_per_scenario,
        "results": results_by_scenario,
    }
