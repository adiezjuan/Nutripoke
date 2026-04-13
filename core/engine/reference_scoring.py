"""Scoring por variable frente a tablas de referencia."""

from __future__ import annotations

from typing import Any
import math
from functools import lru_cache

from core.catalog.reference_loader import load_reference_ranges


def is_nan(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def clamp(x: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(x)))


@lru_cache(maxsize=1)

def to_float_or_nan(value: Any) -> float:
    if value is None:
        return math.nan
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if text == "":
            return math.nan
        try:
            return float(text)
        except ValueError:
            return math.nan
    return math.nan

def get_reference_ranges() -> dict[str, dict[str, Any]]:
    return load_reference_ranges()


def infer_direction(ref_cfg: dict[str, Any]) -> str:
    """
    Traduce la nueva estructura de referencia a una lógica de scoring compatible.

    Reglas:
    - si hay min y max -> outside_range_worse
    - si solo hay min -> lower_worse
    - si solo hay max -> higher_worse
    """
    if ref_cfg.get("direction"):
        return ref_cfg["direction"]

    ref_low = ref_cfg.get("reference_low")
    ref_high = ref_cfg.get("reference_high")

    if ref_low is not None and ref_high is not None:
        return "outside_range_worse"
    if ref_low is not None:
        return "lower_worse"
    if ref_high is not None:
        return "higher_worse"
    return "outside_range_worse"


def infer_target_default(ref_cfg: dict[str, Any]) -> float | None:
    if ref_cfg.get("target_default") is not None:
        return ref_cfg["target_default"]

    ref_low = ref_cfg.get("reference_low")
    ref_high = ref_cfg.get("reference_high")

    if ref_low is not None and ref_high is not None:
        return (ref_low + ref_high) / 2.0
    if ref_low is not None:
        return ref_low
    if ref_high is not None:
        return ref_high
    return None


def enrich_reference_config(ref_cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Añade campos derivados para compatibilizar el scoring con la tabla nueva.
    """
    cfg = dict(ref_cfg)

    ref_low = cfg.get("reference_low")
    ref_high = cfg.get("reference_high")

    cfg["direction"] = infer_direction(cfg)
    cfg["target_default"] = infer_target_default(cfg)

    if cfg["direction"] == "outside_range_worse":
        cfg.setdefault("low_flag", ref_low)
        cfg.setdefault("high_flag", ref_high)

        if ref_low is not None and ref_high is not None:
            width = max(ref_high - ref_low, 1e-9)
            cfg.setdefault("critical_low", ref_low - 0.5 * width)
            cfg.setdefault("critical_high", ref_high + 0.5 * width)

    elif cfg["direction"] == "lower_worse":
        cfg.setdefault("low_flag", ref_low)
        if ref_low is not None:
            cfg.setdefault("critical_low", ref_low * 0.7 if ref_low != 0 else ref_low - 1.0)

    elif cfg["direction"] == "higher_worse":
        cfg.setdefault("high_flag", ref_high)
        if ref_high is not None:
            cfg.setdefault("critical_high", ref_high * 1.5 if ref_high != 0 else ref_high + 1.0)

    # compatibilidad de nombres con tu UI anterior
    cfg.setdefault("notes", cfg.get("note", ""))
    cfg.setdefault("categoria_alto", cfg.get("high_category", ""))
    cfg.setdefault("categoria_bajo", cfg.get("low_category", ""))

    return cfg


def get_reference_config(
    key: str,
    all_values: dict[str, Any],
    reference_ranges: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    reference_ranges = reference_ranges or get_reference_ranges()

    cfg = reference_ranges.get(key)
    if cfg is None:
        return None

    sex = str(all_values.get("sex", "M")).upper()

    if "sex_specific" in cfg:
        sex_cfg = cfg["sex_specific"].get(sex, cfg["sex_specific"].get("M", {}))
        merged = {k: v for k, v in cfg.items() if k != "sex_specific"}
        merged.update(sex_cfg)
        return enrich_reference_config(merged)

    return enrich_reference_config(cfg)


def classify_against_reference(value: float, ref_cfg: dict[str, Any] | None) -> str:
    if ref_cfg is None or is_nan(value):
        return "missing"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "missing"
    direction = ref_cfg.get("direction")
    low_flag = ref_cfg.get("low_flag")
    high_flag = ref_cfg.get("high_flag")
    critical_low = ref_cfg.get("critical_low")
    critical_high = ref_cfg.get("critical_high")

    if direction == "higher_worse":
        if critical_high is not None and value >= critical_high:
            return "critical_high"
        if high_flag is not None and value >= high_flag:
            return "high"
        if critical_low is not None and value <= critical_low:
            return "critical_low"
        if low_flag is not None and value < low_flag:
            return "low"
        return "normal"

    if direction == "lower_worse":
        if critical_low is not None and value <= critical_low:
            return "critical_low"
        if low_flag is not None and value < low_flag:
            return "low"
        if critical_high is not None and value >= critical_high:
            return "critical_high"
        if high_flag is not None and value > high_flag:
            return "high"
        return "normal"

    if direction == "outside_range_worse":
        if critical_low is not None and value <= critical_low:
            return "critical_low"
        if critical_high is not None and value >= critical_high:
            return "critical_high"
        if low_flag is not None and value < low_flag:
            return "low"
        if high_flag is not None and value > high_flag:
            return "high"
        return "normal"

    return "normal"


def score_from_reference(value: float, ref_cfg: dict[str, Any] | None) -> float:
    if ref_cfg is None or is_nan(value):
        return math.nan
    try:
        value = float(value)
    except (TypeError, ValueError):
        return math.nan
    direction = ref_cfg.get("direction")
    target = ref_cfg.get("target_default")
    low_flag = ref_cfg.get("low_flag")
    high_flag = ref_cfg.get("high_flag")
    critical_low = ref_cfg.get("critical_low")
    critical_high = ref_cfg.get("critical_high")
    ref_low = ref_cfg.get("reference_low")
    ref_high = ref_cfg.get("reference_high")

    if direction == "higher_worse":
        if high_flag is None:
            return 0.0
        if target is None:
            target = high_flag
        if value <= target:
            return 0.0
        if critical_high is None:
            critical_high = high_flag * 1.5
        if value >= critical_high:
            return 100.0
        return clamp(100.0 * (value - target) / max(critical_high - target, 1e-9))

    if direction == "lower_worse":
        if low_flag is None:
            return 0.0
        if target is None:
            target = low_flag
        if value >= target:
            return 0.0
        if critical_low is None:
            critical_low = low_flag * 0.7 if low_flag != 0 else low_flag - 1.0
        if value <= critical_low:
            return 100.0
        return clamp(100.0 * (target - value) / max(target - critical_low, 1e-9))

    if direction == "outside_range_worse":
        if ref_low is None or ref_high is None:
            return math.nan

        if ref_low <= value <= ref_high:
            return 0.0

        if value < ref_low:
            floor = critical_low if critical_low is not None else ref_low - (ref_high - ref_low) * 0.5
            if value <= floor:
                return 100.0
            return clamp(100.0 * (ref_low - value) / max(ref_low - floor, 1e-9))

        ceil = critical_high if critical_high is not None else ref_high + (ref_high - ref_low) * 0.5
        if value >= ceil:
            return 100.0
        return clamp(100.0 * (value - ref_high) / max(ceil - ref_high, 1e-9))

    return math.nan


def score_variable(
    key: str,
    value: Any,
    all_values: dict[str, Any],
    reference_ranges: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    numeric_value = to_float_or_nan(value)

    if is_nan(numeric_value):
        return {
            "score": math.nan,
            "value": value,
            "classification": "missing",
            "reference": None,
            "note": "sin dato numérico",
        }

    ref_cfg = get_reference_config(key, all_values, reference_ranges)
    if ref_cfg is None:
        return {
            "score": math.nan,
            "value": value,
            "classification": "missing",
            "reference": None,
            "note": "sin referencia",
        }

    classification = classify_against_reference(numeric_value, ref_cfg)
    score = score_from_reference(numeric_value, ref_cfg)

    return {
        "score": clamp(score) if not is_nan(score) else math.nan,
        "value": numeric_value,
        "classification": classification,
        "reference": ref_cfg,
        "note": ref_cfg.get("notes", ""),
        "categoria_alto": ref_cfg.get("categoria_alto", ""),
        "categoria_bajo": ref_cfg.get("categoria_bajo", ""),
    }
def score_all_variables(
    all_values: dict[str, Any],
    reference_ranges: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    reference_ranges = reference_ranges or get_reference_ranges()

    scored = {}
    for key, cfg in reference_ranges.items():
        has_numeric_reference = (
            cfg.get("reference_low") is not None
            or cfg.get("reference_high") is not None
            or cfg.get("low_flag") is not None
            or cfg.get("high_flag") is not None
            or cfg.get("critical_low") is not None
            or cfg.get("critical_high") is not None
            or cfg.get("direction") is not None
            or "sex_specific" in cfg
        )
        if not has_numeric_reference:
            continue

        scored[key] = score_variable(
            key,
            all_values.get(key, math.nan),
            all_values,
            reference_ranges,
        )

    return scored