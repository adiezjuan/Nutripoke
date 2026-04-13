from __future__ import annotations

from typing import Any
import math
import re
from statistics import median

import pandas as pd

from core.motor.network_loader import (
    load_mechanism_coherence_catalog,
    load_mechanism_coherence_rules,
    load_mechanism_output_rules,
    load_mechanisms_catalog,
    load_output_catalog,
    split_rules_by_source_type,
)


MAX_OUTPUTS_TOTAL = 12
MAX_OUTPUTS_PER_BLOCK = 3
TOP_OUTPUTS_LIMIT = 6


def clamp(x: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(x)))


def is_nan(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def is_abnormal(classification: str) -> bool:
    return classification in {"high", "low", "critical_high", "critical_low"}


def _text_or_fallback(*values: Any, fallback: str = "") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return fallback


def _saturating_curve(total_signal: float, scale: float) -> float:
    if total_signal <= 0:
        return 0.0
    scale = max(scale, 1.0)
    return 100.0 * (1.0 - math.exp(-float(total_signal) / scale))


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    if math.isnan(parsed):
        return None
    return parsed


def _parse_csvish_list(value: str) -> list[str]:
    if not value:
        return []
    cleaned = re.sub(r"\s*\|\s*nota_clinica=.*$", "", value).strip()
    parts = [item.strip() for item in cleaned.split(",")]
    return [item for item in parts if item and item.lower() != "nan"]


def _parse_rule_notes(notes: Any) -> dict[str, Any]:
    text = _text_or_fallback(notes)
    if not text:
        return {}

    meta: dict[str, Any] = {"_raw": text}
    raw_parts = [part.strip() for part in text.split("|") if part.strip()]
    free_text: list[str] = []

    numeric_keys = {"threshold_mecanismo", "min_hits", "min_groups", "display_threshold", "crit_bajo", "crit_alto"}
    list_keys = {"confirmatorios", "competidores"}

    for part in raw_parts:
        if "=" not in part:
            if not part.startswith("["):
                free_text.append(part)
            continue
        key, value = part.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key in numeric_keys:
            parsed = _as_float(value)
            if parsed is not None:
                meta[key] = parsed
        elif key in list_keys:
            meta[key] = _parse_csvish_list(value)
        else:
            meta[key] = value

    if free_text:
        meta["free_text"] = " | ".join(free_text)
    return meta


def _qualitative_multiplier(rule: dict[str, Any]) -> float:
    evidence_mult = {"alta": 1.0, "media": 0.96, "baja": 0.9}.get(str(rule.get("evidence_tier", "")).strip().lower(), 0.95)
    specificity_mult = {"alta": 1.0, "media": 0.97, "baja": 0.92}.get(str(rule.get("especificidad", "")).strip().lower(), 0.95)
    strength_mult = {"alta": 1.0, "media": 0.97, "baja": 0.93}.get(str(rule.get("fuerza", "")).strip().lower(), 0.96)
    role_mult = {"primary_driver": 1.0, "supporting_driver": 0.98, "contextual_support": 0.9}.get(str(rule.get("role", "")).strip().lower(), 0.95)
    return evidence_mult * specificity_mult * strength_mult * role_mult


def matches_activation_mode(classification: str, activation_mode: str) -> bool:
    mode = str(activation_mode or "").strip().lower()

    if mode == "high":
        return classification in {"high", "critical_high"}
    if mode == "low":
        return classification in {"low", "critical_low"}
    if mode == "outside_range":
        return classification in {"high", "low", "critical_high", "critical_low"}
    if mode == "any_abnormal":
        return is_abnormal(classification)

    return False


def resolve_rule_signal(rule: dict[str, Any], source_score: float, classification: str) -> float:
    if not matches_activation_mode(classification, rule.get("activation_mode", "")):
        return 0.0

    severity_mode = str(rule.get("severity_mode", "direct_score")).strip().lower()
    weight = float(rule.get("weight", 1.0))

    if severity_mode == "binary":
        base = 100.0
    else:
        base = 0.0 if is_nan(source_score) else float(source_score)

    signal = base * weight * _qualitative_multiplier(rule)
    return clamp(signal)


def resolve_mechanism_to_mechanism_signal(rule: dict[str, Any], source_activation: float) -> float:
    severity_mode = str(rule.get("severity_mode", "direct_score")).strip().lower()
    weight = float(rule.get("weight", 1.0))

    if source_activation <= 0:
        return 0.0

    if severity_mode == "binary":
        base = 100.0
    else:
        base = source_activation

    signal = base * weight * _qualitative_multiplier(rule)
    return clamp(signal)


def _extract_rule_runtime_config(evidence_rows: list[dict[str, Any]]) -> dict[str, Any]:
    variable_rows = [ev for ev in evidence_rows if ev.get("source_type") == "variable"]
    primary_rows = [ev for ev in variable_rows if ev.get("is_primary", False)] or variable_rows

    def pick_numeric(key: str, default: float | int | None, mode: str = "median") -> float | int | None:
        values = [ev.get("parsed_meta", {}).get(key) for ev in primary_rows]
        values = [_as_float(v) for v in values if _as_float(v) is not None]
        if not values:
            values = [ev.get("parsed_meta", {}).get(key) for ev in variable_rows]
            values = [_as_float(v) for v in values if _as_float(v) is not None]
        if not values:
            return default
        if mode == "max":
            return max(values)
        return float(median(values))

    confirmatorios: set[str] = set()
    competidores: set[str] = set()
    for ev in variable_rows:
        meta = ev.get("parsed_meta", {}) or {}
        confirmatorios.update(meta.get("confirmatorios", []) or [])
        competidores.update(meta.get("competidores", []) or [])

    return {
        "threshold_mecanismo": pick_numeric("threshold_mecanismo", None, mode="median"),
        "min_hits": pick_numeric("min_hits", None, mode="max"),
        "min_groups": pick_numeric("min_groups", None, mode="max"),
        "display_threshold": pick_numeric("display_threshold", None, mode="max"),
        "confirmatorios": sorted(confirmatorios),
        "competidores": sorted(competidores),
    }


def _contextual_adjustment(
    rule: dict[str, Any],
    signal: float,
    classification: str,
    variable_scores: dict[str, dict[str, Any]],
    all_values: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    if signal <= 0:
        return 0.0, {"context_multiplier": 0.0, "confirmatory_hits": 0, "competitor_hits": 0, "fasting_penalty": False}

    meta = rule.get("parsed_meta", {}) or {}
    confirmatory_vars = [k for k in meta.get("confirmatorios", []) if k in variable_scores]
    competitor_vars = [k for k in meta.get("competidores", []) if k in variable_scores]

    confirmatory_hits = sum(1 for key in confirmatory_vars if is_abnormal(str(variable_scores.get(key, {}).get("classification", ""))))
    competitor_hits = sum(1 for key in competitor_vars if is_abnormal(str(variable_scores.get(key, {}).get("classification", ""))))

    multiplier = 1.0
    gate = str(rule.get("context_gate", "")).strip().lower()
    is_critical = classification in {"critical_high", "critical_low"}

    if gate == "confirmatory_bundle" and confirmatory_vars:
        if confirmatory_hits == 0:
            multiplier *= 0.82 if is_critical else 0.58
        elif confirmatory_hits == 1:
            multiplier *= 0.86
        else:
            multiplier *= 1.0

    if competitor_hits:
        multiplier *= max(0.55, 1.0 - 0.17 * competitor_hits)

    fasting_penalty = False
    if bool(rule.get("requires_fasting", False)):
        fasting_hours = _as_float(all_values.get("fasting_hours"))
        if fasting_hours is not None and fasting_hours < 8:
            multiplier *= 0.72 if is_critical else 0.62
            fasting_penalty = True

    adjusted = clamp(signal * multiplier)
    return adjusted, {
        "context_multiplier": round(multiplier, 3),
        "confirmatory_hits": confirmatory_hits,
        "competitor_hits": competitor_hits,
        "fasting_penalty": fasting_penalty,
        "confirmatory_vars": confirmatory_vars,
        "competitor_vars": competitor_vars,
    }


def _compute_mechanism_strength(
    evidence_rows: list[dict[str, Any]],
    coherence_info: dict[str, Any],
) -> dict[str, float]:
    variable_rows = [ev for ev in evidence_rows if ev.get("source_type") == "variable"]
    mechanism_rows = [ev for ev in evidence_rows if ev.get("source_type") == "mechanism"]

    total_variable_signal = sum(float(ev.get("signal", 0.0) or 0.0) for ev in variable_rows)
    total_mechanism_signal = sum(float(ev.get("signal", 0.0) or 0.0) for ev in mechanism_rows)

    group_signals: dict[str, float] = {}
    for ev in variable_rows:
        group = str(ev.get("combo_group", "")).strip() or f"var::{ev.get('source', '')}"
        group_signals[group] = max(group_signals.get(group, 0.0), float(ev.get("signal", 0.0) or 0.0))

    grouped_total_signal = sum(group_signals.values()) if group_signals else total_variable_signal
    evidence_strength = _saturating_curve(grouped_total_signal, scale=115.0)
    support_strength = _saturating_curve(total_mechanism_signal, scale=180.0)

    hit_count = int(coherence_info.get("hit_count", 0) or 0)
    group_count = int(coherence_info.get("group_count", 0) or 0)
    primary_hits = int(coherence_info.get("primary_hits", 0) or 0)
    confirmatory_hits = int(coherence_info.get("confirmatory_hits", 0) or 0)
    competitor_hits = int(coherence_info.get("competitor_hits", 0) or 0)

    diversity_factor = min(1.0, 0.66 + 0.11 * min(group_count, 3) + 0.05 * min(hit_count, 4))
    primary_factor = 1.0 if primary_hits > 0 else 0.88
    confirmatory_factor = min(1.06, 0.96 + 0.05 * min(confirmatory_hits, 2))
    competitor_factor = max(0.72, 1.0 - 0.08 * competitor_hits)

    if hit_count <= 1:
        diversity_factor *= 0.76
    elif hit_count == 2:
        diversity_factor *= 0.9

    coherence_factor = 1.0 if coherence_info.get("passes", False) else 0.68
    raw_score = evidence_strength * diversity_factor * primary_factor * confirmatory_factor * competitor_factor * coherence_factor
    final_score = clamp(raw_score + support_strength * 0.22 + float(coherence_info.get("coherence_bonus", 0.0) or 0.0))

    confidence = clamp(
        (diversity_factor * 48.0)
        + (10.0 * min(primary_hits, 2))
        + (8.0 * min(confirmatory_hits, 2))
        + (36.0 if coherence_info.get("passes", False) else 14.0)
        - (6.0 * min(competitor_hits, 2))
    )
    return {
        "raw_score": clamp(raw_score),
        "final_score": final_score,
        "evidence_strength": clamp(evidence_strength),
        "support_strength": clamp(support_strength),
        "diversity_factor": round(diversity_factor, 3),
        "primary_factor": round(primary_factor, 3),
        "confirmatory_factor": round(confirmatory_factor, 3),
        "competitor_factor": round(competitor_factor, 3),
        "coherence_factor": round(coherence_factor, 3),
        "confidence": confidence,
    }


def _dedupe_and_limit_outputs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_key: dict[str, dict[str, Any]] = {}
    for item in rows:
        key = str(item.get("output_key", "")).strip()
        current = best_by_key.get(key)
        if current is None:
            best_by_key[key] = item
            continue
        candidate_rank = (item.get("priority", 99), -float(item.get("mechanism_activation", 0.0) or 0.0))
        current_rank = (current.get("priority", 99), -float(current.get("mechanism_activation", 0.0) or 0.0))
        if candidate_rank < current_rank:
            best_by_key[key] = item

    ordered = sorted(
        best_by_key.values(),
        key=lambda item: (item["priority"], -item["mechanism_activation"], item["display_label"]),
    )

    final_rows: list[dict[str, Any]] = []
    block_counts: dict[str, int] = {}
    for item in ordered:
        block = str(item.get("ui_block", "misc")).strip() or "misc"
        if block_counts.get(block, 0) >= MAX_OUTPUTS_PER_BLOCK:
            continue
        final_rows.append(item)
        block_counts[block] = block_counts.get(block, 0) + 1
        if len(final_rows) >= MAX_OUTPUTS_TOTAL:
            break
    return final_rows


def build_outputs_from_mechanisms(
    ranking: list[dict[str, Any]],
    active_mechanisms: list[dict[str, Any]],
) -> dict[str, Any]:
    links_df = load_mechanism_output_rules()
    outputs_df = load_output_catalog()

    if links_df.empty or outputs_df.empty:
        return {"outputs": [], "by_block": {}, "by_type": {}, "top_outputs": []}

    active_map = {str(item["mechanism_id"]).strip(): item for item in active_mechanisms}
    if not active_map:
        return {"outputs": [], "by_block": {}, "by_type": {}, "top_outputs": []}

    rows: list[dict[str, Any]] = []

    for _, row in links_df.iterrows():
        link = row.to_dict()
        mechanism_id = str(link.get("mechanism_id", "")).strip()
        if mechanism_id not in active_map:
            continue

        mechanism = active_map[mechanism_id]
        activation = float(mechanism.get("activation", 0.0))
        min_activation = link.get("min_activation", math.nan)
        max_activation = link.get("max_activation", math.nan)

        if not pd.isna(min_activation) and activation < float(min_activation):
            continue
        if not pd.isna(max_activation) and activation > float(max_activation):
            continue

        output_key = str(link.get("output_key", "")).strip()
        catalog_hit = outputs_df[outputs_df["output_key"] == output_key]
        output_meta = catalog_hit.iloc[0].to_dict() if not catalog_hit.empty else {}

        priority = link.get("priority", math.nan)
        if pd.isna(priority):
            priority = output_meta.get("default_priority", math.nan)
        try:
            priority_value = int(priority)
        except Exception:
            priority_value = 99

        short_text = _text_or_fallback(
            link.get("message_short"),
            output_meta.get("short_template"),
            fallback=mechanism.get("label", output_key),
        )
        long_text = _text_or_fallback(
            link.get("message_long"),
            output_meta.get("long_template"),
            mechanism.get("definition", ""),
        )
        followup = _text_or_fallback(
            link.get("followup_hint"),
            output_meta.get("followup_template"),
        )
        ui_block = _text_or_fallback(output_meta.get("ui_block"), fallback="misc")
        output_type = _text_or_fallback(link.get("output_type"), output_meta.get("output_type"), fallback="message")
        display_label = _text_or_fallback(output_meta.get("display_label"), fallback=output_key)

        rows.append(
            {
                "output_key": output_key,
                "output_type": output_type,
                "display_label": display_label,
                "display_group": _text_or_fallback(output_meta.get("display_group")),
                "ui_block": ui_block,
                "severity_style": _text_or_fallback(output_meta.get("severity_style"), fallback="info"),
                "priority": priority_value,
                "mechanism_id": mechanism_id,
                "mechanism_label": mechanism.get("label", mechanism_id),
                "mechanism_activation": activation,
                "mechanism_kind": mechanism.get("kind", ""),
                "short_text": short_text,
                "long_text": long_text,
                "followup": followup,
                "target_variable": _text_or_fallback(link.get("target_variable"), output_meta.get("default_target_variable")),
                "target_direction": _text_or_fallback(link.get("target_direction"), output_meta.get("default_target_direction")),
                "guardrail_key": _text_or_fallback(link.get("guardrail_key"), output_meta.get("guardrail_key")),
                "source_link_id": str(link.get("link_id", "")).strip(),
            }
        )

    rows = _dedupe_and_limit_outputs(rows)

    by_block: dict[str, list[dict[str, Any]]] = {}
    by_type: dict[str, list[dict[str, Any]]] = {}
    for item in rows:
        by_block.setdefault(item["ui_block"], []).append(item)
        by_type.setdefault(item["output_type"], []).append(item)

    return {"outputs": rows, "by_block": by_block, "by_type": by_type, "top_outputs": rows[:TOP_OUTPUTS_LIMIT]}


def build_coherence_maps() -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    mech_df = load_mechanism_coherence_catalog()
    rules_df = load_mechanism_coherence_rules()

    mech_map: dict[str, dict[str, Any]] = {}
    if not mech_df.empty:
        for _, row in mech_df.iterrows():
            data = row.to_dict()
            mech_map[str(data.get("mechanism_id", "")).strip()] = data

    rules_map: dict[str, list[dict[str, Any]]] = {}
    if not rules_df.empty:
        for _, row in rules_df.iterrows():
            data = row.to_dict()
            mech_id = str(data.get("mechanism_id", "")).strip()
            rules_map.setdefault(mech_id, []).append(data)

    return mech_map, rules_map


def evaluate_coherence(
    mechanism_id: str,
    evidence_rows: list[dict[str, Any]],
    mechanism_meta: dict[str, Any],
    coherence_meta: dict[str, Any] | None,
    coherence_rules: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    meta = dict(mechanism_meta or {})
    coh = dict(coherence_meta or {})
    runtime_cfg = _extract_rule_runtime_config(evidence_rows)

    default_threshold = runtime_cfg.get("threshold_mecanismo")
    if default_threshold is None:
        default_threshold = meta.get("activation_threshold", 30.0)

    min_hits = int((runtime_cfg.get("min_hits") if runtime_cfg.get("min_hits") is not None else (coh.get("min_hits") if not pd.isna(coh.get("min_hits", pd.NA)) else meta.get("min_hits", 1))) or 1)
    min_groups = int((runtime_cfg.get("min_groups") if runtime_cfg.get("min_groups") is not None else (coh.get("min_groups") if not pd.isna(coh.get("min_groups", pd.NA)) else meta.get("min_groups", 1))) or 1)
    min_primary_hits = int((coh.get("min_primary_hits") if not pd.isna(coh.get("min_primary_hits", pd.NA)) else meta.get("min_primary_hits", 0)) or 0)
    coherence_bonus = float((coh.get("coherence_bonus") if not pd.isna(coh.get("coherence_bonus", pd.NA)) else meta.get("coherence_bonus", 0.0)) or 0.0)
    display_threshold = float((runtime_cfg.get("display_threshold") if runtime_cfg.get("display_threshold") is not None else (coh.get("display_threshold") if not pd.isna(coh.get("display_threshold", pd.NA)) else meta.get("display_threshold", default_threshold))) or default_threshold)
    requires_primary_driver = bool(coh.get("requires_primary_driver", meta.get("requires_primary_driver", False)))

    variable_rows = [ev for ev in evidence_rows if ev.get("source_type") == "variable"]
    by_source = {str(ev.get("source", "")).strip(): ev for ev in variable_rows}

    hit_count = len(by_source)
    primary_hits = sum(1 for ev in variable_rows if bool(ev.get("is_primary", False)))
    groups_seen = {
        str(ev.get("combo_group", "")).strip() or f"var::{ev.get('source', '')}"
        for ev in variable_rows
        if str(ev.get("source", "")).strip()
    }
    matched_variables = sorted(by_source.keys())
    rationale_lines: list[str] = []

    rules = coherence_rules or []
    if rules:
        for rule in rules:
            source_key = str(rule.get("variable_key", "")).strip()
            if source_key not in by_source:
                continue
            rationale = str(rule.get("clinical_rationale", "")).strip()
            if rationale:
                rationale_lines.append(rationale)

    confirmatory_hits = sum(int(ev.get("context", {}).get("confirmatory_hits", 0) or 0) for ev in variable_rows)
    competitor_hits = sum(int(ev.get("context", {}).get("competitor_hits", 0) or 0) for ev in variable_rows)

    has_primary_driver = primary_hits >= max(min_primary_hits, 1) if requires_primary_driver else primary_hits >= min_primary_hits
    enough_hits = hit_count >= min_hits
    enough_groups = len(groups_seen) >= min_groups
    passes = enough_hits and enough_groups and (has_primary_driver or not requires_primary_driver)

    unmet = []
    if not enough_hits:
        unmet.append(f"requiere al menos {min_hits} señales")
    if not enough_groups:
        unmet.append(f"requiere al menos {min_groups} grupos fisiológicos")
    if requires_primary_driver and not has_primary_driver:
        unmet.append("requiere driver principal")

    return {
        "passes": passes,
        "hit_count": hit_count,
        "group_count": len(groups_seen),
        "primary_hits": primary_hits,
        "confirmatory_hits": confirmatory_hits,
        "competitor_hits": competitor_hits,
        "groups_seen": sorted(groups_seen),
        "matched_variables": matched_variables,
        "has_primary_driver": has_primary_driver,
        "coherence_bonus": coherence_bonus if passes else 0.0,
        "display_threshold": display_threshold,
        "activation_threshold": float(default_threshold),
        "unmet_requirements": unmet,
        "clinical_rationale": rationale_lines[:5],
        "runtime_config": runtime_cfg,
    }


def run_dynamic_projection(
    all_values: dict[str, Any],
    variable_scores: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    variable_keys = set(all_values.keys()) | set(variable_scores.keys())
    variable_rules_df, mechanism_rules_df, unknown_rules_df = split_rules_by_source_type(variable_keys)
    mechanisms_df = load_mechanisms_catalog()
    coherence_mech_map, coherence_rules_map = build_coherence_maps()

    mechanisms_meta = {str(row["mechanism_id"]).strip(): row.to_dict() for _, row in mechanisms_df.iterrows()}

    evidence: dict[str, list[dict[str, Any]]] = {mechanism_id: [] for mechanism_id in mechanisms_meta.keys()}

    # 1) Analito -> mecanismo
    for _, row in variable_rules_df.iterrows():
        rule = row.to_dict()
        rule["parsed_meta"] = _parse_rule_notes(rule.get("notes", ""))
        source_key = str(rule["variable_key"]).strip()
        target_mechanism = str(rule["mechanism_id"]).strip()

        if target_mechanism not in evidence:
            continue

        variable_info = variable_scores.get(source_key, {})
        classification = variable_info.get("classification", "missing")
        source_score = variable_info.get("score", math.nan)

        raw_signal = resolve_rule_signal(rule, source_score, classification)
        if raw_signal <= 0:
            continue

        signal, context_info = _contextual_adjustment(rule, raw_signal, classification, variable_scores, all_values)
        if signal <= 0:
            continue

        evidence[target_mechanism].append(
            {
                "source_type": "variable",
                "source": source_key,
                "classification": classification,
                "source_score": source_score,
                "signal": signal,
                "signal_raw": raw_signal,
                "rule_id": rule.get("rule_id", ""),
                "notes": rule.get("notes", ""),
                "role": rule.get("role", ""),
                "combo_group": rule.get("combo_group", ""),
                "is_primary": bool(rule.get("is_primary", False)),
                "evidence_tier": rule.get("evidence_tier", ""),
                "clinical_rationale": rule.get("clinical_rationale", ""),
                "parsed_meta": rule.get("parsed_meta", {}),
                "context": context_info,
            }
        )

    precomputed: dict[str, dict[str, Any]] = {}
    for mechanism_id, rows in evidence.items():
        meta = mechanisms_meta.get(mechanism_id, {})
        coherence_info = evaluate_coherence(
            mechanism_id=mechanism_id,
            evidence_rows=rows,
            mechanism_meta=meta,
            coherence_meta=coherence_mech_map.get(mechanism_id),
            coherence_rules=coherence_rules_map.get(mechanism_id),
        )
        precomputed[mechanism_id] = {
            "coherence": coherence_info,
            "strength": _compute_mechanism_strength(rows, coherence_info),
        }

    # 2) Mecanismo -> mecanismo usando score preliminar ya suavizado
    for _, row in mechanism_rules_df.iterrows():
        rule = row.to_dict()
        source_mechanism = str(rule["variable_key"]).strip()
        target_mechanism = str(rule["mechanism_id"]).strip()

        if source_mechanism not in evidence or target_mechanism not in evidence:
            continue

        source_activation = float(precomputed.get(source_mechanism, {}).get("strength", {}).get("final_score", 0.0) or 0.0)
        signal = resolve_mechanism_to_mechanism_signal(rule, source_activation)
        if signal <= 0:
            continue

        evidence[target_mechanism].append(
            {
                "source_type": "mechanism",
                "source": source_mechanism,
                "source_activation": source_activation,
                "signal": signal,
                "rule_id": rule.get("rule_id", ""),
                "notes": rule.get("notes", ""),
            }
        )

    ranking = []
    activation_map: dict[str, float] = {}
    for mechanism_id, rows in evidence.items():
        meta = mechanisms_meta.get(mechanism_id, {})

        coherence_info = evaluate_coherence(
            mechanism_id=mechanism_id,
            evidence_rows=rows,
            mechanism_meta=meta,
            coherence_meta=coherence_mech_map.get(mechanism_id),
            coherence_rules=coherence_rules_map.get(mechanism_id),
        )
        strength = _compute_mechanism_strength(rows, coherence_info)

        threshold_value = float(coherence_info.get("activation_threshold", meta.get("activation_threshold", 30.0)) or 30.0)
        adjusted_activation = float(strength["final_score"])
        display_threshold = float(coherence_info.get("display_threshold", threshold_value))
        activation_map[mechanism_id] = adjusted_activation

        if coherence_info.get("passes", False) and adjusted_activation >= max(threshold_value, display_threshold):
            status = "active"
        elif adjusted_activation >= max(15.0, threshold_value * 0.45):
            status = "weak"
        else:
            status = "inactive"

        confidence_value = float(strength.get("confidence", 0.0) or 0.0)
        if confidence_value >= 75:
            solidity = "Alta"
        elif confidence_value >= 50:
            solidity = "Media"
        elif confidence_value > 0:
            solidity = "Baja"
        else:
            solidity = "Nula"

        ranking.append(
            {
                "mechanism_id": mechanism_id,
                "label": meta.get("label", mechanism_id),
                "definition": meta.get("definition", ""),
                "system": meta.get("system", ""),
                "kind": meta.get("kind", ""),
                "priority_base": meta.get("priority_base", ""),
                "activation_threshold": threshold_value,
                "display_threshold": display_threshold,
                "activation_raw": round(float(strength["raw_score"]), 2),
                "activation": round(adjusted_activation, 2),
                "evidence_strength": round(float(strength["evidence_strength"]), 2),
                "support_strength": round(float(strength["support_strength"]), 2),
                "confidence": round(confidence_value, 2),
                "solidity": solidity,
                "status": status,
                "evidence": rows,
                "coherence": coherence_info,
                "clinical_notes": _text_or_fallback(
                    coherence_mech_map.get(mechanism_id, {}).get("clinical_notes", ""),
                    meta.get("clinical_notes", ""),
                ),
            }
        )

    ranking.sort(key=lambda x: (x["status"] != "active", -x["activation"], -x["confidence"]))

    top_mechanisms = [m for m in ranking if m["status"] != "inactive"][:5]
    active_mechanisms = [m for m in ranking if m["status"] == "active"]

    unknown_rules = []
    if not unknown_rules_df.empty:
        for _, row in unknown_rules_df.iterrows():
            unknown_rules.append(
                {
                    "rule_id": row.get("rule_id", ""),
                    "variable_key": row.get("variable_key", ""),
                    "mechanism_id": row.get("mechanism_id", ""),
                }
            )

    outputs_payload = build_outputs_from_mechanisms(ranking, active_mechanisms)

    return {
        "mechanisms": ranking,
        "top_mechanisms": top_mechanisms,
        "active_mechanisms": active_mechanisms,
        "activation_map": activation_map,
        "unknown_rules": unknown_rules,
        "all_normal": all(info.get("classification") in {"normal", "missing"} for info in variable_scores.values()),
        "outputs": outputs_payload["outputs"],
        "outputs_by_block": outputs_payload["by_block"],
        "outputs_by_type": outputs_payload["by_type"],
        "top_outputs": outputs_payload["top_outputs"],
    }
