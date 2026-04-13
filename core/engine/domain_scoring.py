"""Scoring por dominios y ranking base."""

from __future__ import annotations

from typing import Any
import math


CORE_ROLES = {"core", "anchor", "primary"}
SECONDARY_ROLES = {"derived", "support", "context"}


def is_nan(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def clamp(x: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(x)))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _coverage_factor(coverage: float) -> float:
    """Penaliza cobertura escasa sin hundir por completo dominios parciales."""
    if coverage <= 0:
        return 0.0
    if coverage >= 0.75:
        return 1.0
    return 0.55 + 0.60 * coverage


def _core_factor(core_coverage: float, used_count: int) -> float:
    """Premia convergencia en variables core y penaliza monocanal."""
    if used_count <= 0:
        return 0.0

    base = 0.72 + 0.28 * core_coverage
    if used_count == 1:
        base *= 0.82
    elif used_count == 2:
        base *= 0.93
    return min(base, 1.0)


def score_domain(
    domain_key: str,
    all_values: dict[str, Any],
    variable_scores: dict[str, dict[str, Any]],
    domain_master: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    config = domain_master[domain_key]
    active_vars = [v for v in config.get("variables", []) if v.get("weight", 0) > 0]

    weighted_sum = 0.0
    total_weight_used = 0.0
    used_items: list[dict[str, Any]] = []

    total_possible = sum(float(v.get("weight", 0.0)) for v in active_vars) if active_vars else 0.0
    core_possible = sum(
        float(v.get("weight", 0.0))
        for v in active_vars
        if str(v.get("role", "")).strip().lower() in CORE_ROLES
    )

    core_weight_used = 0.0
    abnormal_weight_used = 0.0

    for var in active_vars:
        key = var["key"]
        weight = float(var["weight"])
        role = str(var.get("role", "")).strip().lower()
        score_info = variable_scores.get(key, {"score": math.nan})
        score = score_info["score"]
        classification = score_info.get("classification", "missing")

        if is_nan(score):
            continue

        weighted_sum += score * weight
        total_weight_used += weight
        if role in CORE_ROLES:
            core_weight_used += weight
        if classification in {"high", "low", "critical_high", "critical_low"}:
            abnormal_weight_used += weight

        used_items.append(
            {
                "key": key,
                "score": score,
                "weight": weight,
                "role": role,
                "value": all_values.get(key, math.nan),
                "classification": classification,
            }
        )

    if total_weight_used == 0:
        domain_score = math.nan
        coverage = 0.0
        base_score = math.nan
        core_coverage = 0.0
        abnormal_share = 0.0
    else:
        base_score = weighted_sum / total_weight_used
        coverage = _safe_ratio(total_weight_used, total_possible)
        core_coverage = _safe_ratio(core_weight_used, core_possible) if core_possible > 0 else coverage
        abnormal_share = _safe_ratio(abnormal_weight_used, total_weight_used)

        domain_score = base_score
        domain_score *= _coverage_factor(coverage)
        domain_score *= _core_factor(core_coverage, len(used_items))
        domain_score *= 0.88 + 0.12 * abnormal_share

    return {
        "key": domain_key,
        "label": config.get("label", domain_key),
        "definition": config.get("definition", ""),
        "priority_override": config.get("priority_override", False),
        "score": clamp(domain_score) if not is_nan(domain_score) else math.nan,
        "base_score": clamp(base_score) if not is_nan(base_score) else math.nan,
        "coverage": coverage,
        "core_coverage": core_coverage,
        "abnormal_share": abnormal_share,
        "used_count": len(used_items),
        "used": used_items,
    }


def score_domains(
    all_values: dict[str, Any],
    variable_scores: dict[str, dict[str, Any]],
    domain_master: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        domain_key: score_domain(domain_key, all_values, variable_scores, domain_master)
        for domain_key in domain_master.keys()
    }
