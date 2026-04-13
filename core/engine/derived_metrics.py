"""Cálculo de métricas derivadas del caso."""

from __future__ import annotations

from typing import Any
import math


def is_nan(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def compute_derived(values: dict[str, Any]) -> dict[str, float]:
    """Calcula derivados básicos independientes de la UI.

    Mantiene la lógica mínima heredada del proyecto actual.
    """
    tg = values.get("triglycerides_mg_dl", math.nan)
    hdl = values.get("hdl_mg_dl", math.nan)
    chol = values.get("chol_total_mg_dl", math.nan)
    glu = values.get("glucose_mg_dl", math.nan)
    ins = values.get("insulin_uIU_ml", math.nan)
    neut = values.get("neut_abs_x10_3_mm3", math.nan)
    lymph = values.get("lymph_abs_x10_3_mm3", math.nan)

    tg_hdl_ratio = math.nan
    if not is_nan(tg) and not is_nan(hdl) and hdl > 0:
        tg_hdl_ratio = tg / hdl

    non_hdl_mg_dl = math.nan
    if not is_nan(chol) and not is_nan(hdl):
        non_hdl_mg_dl = chol - hdl

    homa_ir = math.nan
    if not is_nan(glu) and not is_nan(ins):
        homa_ir = (glu * ins) / 405.0

    nlr = math.nan
    if not is_nan(neut) and not is_nan(lymph) and lymph > 0:
        nlr = neut / lymph

    return {
        "tg_hdl_ratio": tg_hdl_ratio,
        "non_hdl_mg_dl": non_hdl_mg_dl,
        "homa_ir": homa_ir,
        "nlr": nlr,
    }


def merge_values(values: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
    merged = dict(values)
    merged.update(derived)
    return merged
