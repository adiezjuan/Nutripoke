"""Flags críticos, confianza y resumen del estado del perfil."""

from __future__ import annotations

from typing import Any
import math

from core.engine.reference_scoring import classify_against_reference, get_reference_config


def is_nan(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def build_flags(
    all_values: dict[str, Any],
    reference_ranges: dict[str, dict[str, Any]],
) -> list[str]:
    flags: list[str] = []
    for key in reference_ranges.keys():
        value = all_values.get(key, math.nan)
        if is_nan(value):
            continue
        ref = get_reference_config(key, all_values, reference_ranges)
        classification = classify_against_reference(value, ref)
        label = ref.get("label", key) if ref else key
        if classification == "critical_low":
            flags.append(f"{label}: valor críticamente bajo.")
        elif classification == "critical_high":
            flags.append(f"{label}: valor críticamente alto.")
    return flags


def confidence_level(domain_scores: dict[str, dict[str, Any]]) -> tuple[str, float]:
    coverages = [d["coverage"] for d in domain_scores.values() if not is_nan(d["score"])]
    if not coverages:
        return "Baja", 0.0
    mean_cov = float(sum(coverages) / len(coverages))
    if mean_cov >= 0.80:
        return "Alta", mean_cov
    if mean_cov >= 0.50:
        return "Media", mean_cov
    return "Baja", mean_cov


def summarize_profile_state(variable_scores: dict[str, dict[str, Any]]) -> dict[str, Any]:
    measured = 0
    abnormal: list[str] = []
    for key, info in variable_scores.items():
        classification = info.get("classification", "missing")
        if classification == "missing":
            continue
        measured += 1
        if classification in ("high", "critical_high", "low", "critical_low"):
            abnormal.append(key)
    return {
        "measured_count": measured,
        "abnormal_count": len(abnormal),
        "abnormal_keys": abnormal,
        "all_normal": measured > 0 and len(abnormal) == 0,
    }
