from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
NORMALIZED_DIR = DATA_DIR / "normalized"
DERIVED_DIR = DATA_DIR / "derived"

REFERENCE_JSON = DERIVED_DIR / "reference_ranges.json"
NORMALIZED_CSV = NORMALIZED_DIR / "analitos_master_normalized.csv"


def _to_none(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    return value


def _to_float_or_none(value: Any) -> float | None:
    value = _to_none(value)
    if value is None:
        return None
    return float(value)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False

    text = str(value).strip().lower()
    return text in {"1", "true", "si", "sí", "yes", "y"}


def _csv_to_reference_ranges(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for param, group in df.groupby("Parametro_backend", sort=True):
        first = group.iloc[0]

        base: dict[str, Any] = {
            "key": param,
            "label": _to_none(first.get("Parametro_mostrar")) or param,
            "unit": _to_none(first.get("Unidad")) or "",
            "unit_normalized": _to_none(first.get("Unidad_normalizada")) or "",
            "threshold_type": _to_none(first.get("Tipo_umbral")) or "reference",
            "threshold_basis": _to_none(first.get("Base_umbral")) or "",
            "uses_fasting": _to_bool(first.get("Usa_ayuno")),
            "priority": _to_none(first.get("Prioridad_clinica")) or "",
            "main_domain": _to_none(first.get("Dominio_principal")) or "",
            "is_driver": _to_bool(first.get("Es_driver")),
            "is_guardrail": _to_bool(first.get("Es_guardrail")),
            "high_category": _to_none(first.get("Categoria_alto")) or "",
            "low_category": _to_none(first.get("Categoria_bajo")) or "",
            "high_causes": _to_none(first.get("Causas_alto")) or "",
            "low_causes": _to_none(first.get("Causas_bajo")) or "",
            "note": _to_none(first.get("Nota")) or "",
            "applicability_comment": _to_none(first.get("Comentario_aplicabilidad")) or "",
        }

        sexes = set(str(x).strip().lower() for x in group["Sexo"].tolist())

        if sexes == {"m", "f"}:
            base["sex_specific"] = {}

            for _, row in group.iterrows():
                sex_key = str(row["Sexo"]).strip().upper()
                base["sex_specific"][sex_key] = {
                    "reference_low": _to_float_or_none(row.get("Valor_min")),
                    "reference_high": _to_float_or_none(row.get("Valor_max")),
                    "age_min": _to_float_or_none(row.get("Edad_min")),
                    "age_max": _to_float_or_none(row.get("Edad_max")),
                    "source": _to_none(row.get("Fuente_intervalo")) or "",
                    "source_year": _to_float_or_none(row.get("Año_fuente")),
                    "interval_type": _to_none(row.get("Tipo_intervalo")) or "",
                }
        else:
            row = group.iloc[0]
            base["reference_low"] = _to_float_or_none(row.get("Valor_min"))
            base["reference_high"] = _to_float_or_none(row.get("Valor_max"))
            base["age_min"] = _to_float_or_none(row.get("Edad_min"))
            base["age_max"] = _to_float_or_none(row.get("Edad_max"))
            base["source"] = _to_none(row.get("Fuente_intervalo")) or ""
            base["source_year"] = _to_float_or_none(row.get("Año_fuente"))
            base["interval_type"] = _to_none(row.get("Tipo_intervalo")) or ""

        result[param] = base

    return result


def load_reference_ranges() -> dict[str, dict[str, Any]]:
    """
    Prioridad de carga:
    1) data/derived/reference_ranges.json
    2) data/normalized/analitos_master_normalized.csv
    """
    if REFERENCE_JSON.exists():
        with open(REFERENCE_JSON, "r", encoding="utf-8") as f:
            return json.load(f)

    if NORMALIZED_CSV.exists():
        df = pd.read_csv(NORMALIZED_CSV)
        return _csv_to_reference_ranges(df)

    raise FileNotFoundError(
        "No se encontró ninguna fuente de referencias. "
        f"Busca en {REFERENCE_JSON} o {NORMALIZED_CSV}"
    )


def load_reference_master_normalized() -> pd.DataFrame:
    if not NORMALIZED_CSV.exists():
        raise FileNotFoundError(f"No existe {NORMALIZED_CSV}")
    return pd.read_csv(NORMALIZED_CSV)
