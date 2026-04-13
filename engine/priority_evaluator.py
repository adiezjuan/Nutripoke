"""Reglas de prioridad y ranking final de dominios."""

from __future__ import annotations

from typing import Any
import math


MIN_DOMAIN_SCORE = 5.0


def is_nan(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def clamp(x: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(x)))


def evaluate_simple_condition(cond: dict[str, Any], all_values: dict[str, Any]) -> bool:
    key = cond["key"]
    value = all_values.get(key, math.nan)
    if is_nan(value):
        return False

    op = cond["op"]
    target = cond["value"]

    if op == "<":
        return value < target
    if op == "<=":
        return value <= target
    if op == ">":
        return value > target
    if op == ">=":
        return value >= target
    if op == "==":
        return value == target
    return False


def evaluate_conditions(conditions: list[dict[str, Any]], all_values: dict[str, Any]) -> bool:
    if not conditions:
        return False
    results = []
    for cond in conditions:
        if "any" in cond:
            results.append(any(evaluate_simple_condition(c, all_values) for c in cond["any"]))
        else:
            results.append(evaluate_simple_condition(cond, all_values))
    return all(results)


def apply_priority_rules(
    domain_scores: dict[str, dict[str, Any]],
    all_values: dict[str, Any],
    priority_rules: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], str | None, str | None, list[str]]:
    applied = []
    for rule in priority_rules:
        if evaluate_conditions(rule.get("conditions", []), all_values):
            applied.append(rule)

    applied_sorted = sorted(
        applied,
        key=lambda r: (r.get("type") == "override", r.get("priority", 0), r.get("boost", 0)),
        reverse=True,
    )

    adjusted = {k: dict(v) for k, v in domain_scores.items()}
    reasons: list[str] = []

    for rule in applied_sorted:
        if rule.get("type") == "boost":
            domain = rule["domain"]
            if domain in adjusted and not is_nan(adjusted[domain]["score"]):
                adjusted[domain]["score"] = clamp(adjusted[domain]["score"] + rule.get("boost", 0))
                reasons.append(rule["reason"])

    override_rules = [r for r in applied_sorted if r.get("type") == "override"]
    forced_domain = None
    forced_reason = None
    if override_rules:
        strongest = max(override_rules, key=lambda r: r.get("priority", 0))
        forced_domain = strongest["domain"]
        forced_reason = strongest["reason"]

    return adjusted, forced_domain, forced_reason, reasons


def rank_domains(
    domain_scores: dict[str, dict[str, Any]],
    all_values: dict[str, Any],
    priority_rules: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None, str | None, list[str]]:
    adjusted_scores, forced_domain, forced_reason, boost_reasons = apply_priority_rules(
        domain_scores, all_values, priority_rules
    )

    valid = [
        d for d in adjusted_scores.values()
        if not is_nan(d["score"]) and float(d["score"]) >= MIN_DOMAIN_SCORE
    ]
    ranked = sorted(valid, key=lambda x: x["score"], reverse=True)

    if forced_domain is not None:
        forced = adjusted_scores.get(forced_domain)
        if forced is not None:
            forced_score = forced.get("score", math.nan)
            if not is_nan(forced_score) and float(forced_score) >= MIN_DOMAIN_SCORE:
                rest = [d for d in ranked if d["key"] != forced_domain]
                ranked = [forced] + rest

    return ranked, forced_domain, forced_reason, boost_reasons
