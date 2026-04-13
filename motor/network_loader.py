from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NETWORK_DIR = PROJECT_ROOT / "data" / "network"

RULES_CSV = NETWORK_DIR / "reglas_variable_a_mecanismo.csv"
MECHANISMS_CSV = NETWORK_DIR / "mecanismos_catalogo.csv"
MECHANISM_OUTPUT_RULES_CSV = NETWORK_DIR / "reglas_mecanismo_a_salidas.csv"
OUTPUT_CATALOG_CSV = NETWORK_DIR / "output_catalogo.csv"

COHERENCE_MECHANISMS_CSV = NETWORK_DIR / "mecanismos_coherencia_catalogo.csv"
COHERENCE_RULES_CSV = NETWORK_DIR / "reglas_coherencia_mecanismo.csv"


TRUE_VALUES = {"1", "true", "yes", "y", "si", "sí"}


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in TRUE_VALUES


def _ensure_text(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).str.strip()
    return df


def _ensure_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_mechanisms_catalog() -> pd.DataFrame:
    if not MECHANISMS_CSV.exists():
        raise FileNotFoundError(f"No existe {MECHANISMS_CSV}")

    df = pd.read_csv(MECHANISMS_CSV).fillna("")
    if "mechanism_id" not in df.columns:
        raise ValueError("mecanismos_catalogo.csv debe incluir la columna 'mechanism_id'")

    if "is_enabled" in df.columns:
        df["is_enabled"] = df["is_enabled"].apply(_to_bool)
        df = df[df["is_enabled"]].copy()

    df = _ensure_text(
        df,
        [
            "mechanism_id",
            "label",
            "definition",
            "system",
            "kind",
            "priority_base",
            "narrative_short",
            "narrative_long",
            "clinical_notes",
        ],
    )
    df = _ensure_numeric(df, ["activation_threshold", "display_threshold", "coherence_bonus", "min_hits", "min_groups", "min_primary_hits"])

    if "requires_primary_driver" not in df.columns:
        df["requires_primary_driver"] = False
    df["requires_primary_driver"] = df["requires_primary_driver"].apply(_to_bool)

    return df


def load_rules_master() -> pd.DataFrame:
    if not RULES_CSV.exists():
        raise FileNotFoundError(f"No existe {RULES_CSV}")

    df = pd.read_csv(RULES_CSV).fillna("")

    required = {"rule_id", "variable_key", "mechanism_id"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"reglas_variable_a_mecanismo.csv necesita columnas: {sorted(missing)}")

    if "is_enabled" in df.columns:
        df["is_enabled"] = df["is_enabled"].apply(_to_bool)
        df = df[df["is_enabled"]].copy()

    df = _ensure_text(
        df,
        [
            "rule_id",
            "variable_key",
            "mechanism_id",
            "activation_mode",
            "direction",
            "severity_mode",
            "sex_scope",
            "notes",
            "context_gate",
            "role",
            "effect_direction",
            "combo_group",
            "evidence_tier",
            "clinical_rationale",
            "fuerza",
            "especificidad",
        ],
    )

    if "weight" not in df.columns:
        df["weight"] = 1.0
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(1.0)

    if "requires_fasting" not in df.columns:
        df["requires_fasting"] = False
    df["requires_fasting"] = df["requires_fasting"].apply(_to_bool)

    if "is_primary" not in df.columns:
        df["is_primary"] = False
    df["is_primary"] = df["is_primary"].apply(_to_bool)

    return df


def load_mechanism_output_rules() -> pd.DataFrame:
    if not MECHANISM_OUTPUT_RULES_CSV.exists():
        return pd.DataFrame()

    df = pd.read_csv(MECHANISM_OUTPUT_RULES_CSV).fillna("")

    required = {"link_id", "mechanism_id", "output_key"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"reglas_mecanismo_a_salidas.csv necesita columnas: {sorted(missing)}")

    if "is_enabled" in df.columns:
        df["is_enabled"] = df["is_enabled"].apply(_to_bool)
        df = df[df["is_enabled"]].copy()

    df = _ensure_text(
        df,
        [
            "link_id",
            "mechanism_id",
            "output_key",
            "output_type",
            "strength_mode",
            "condition_context",
            "message_short",
            "message_long",
            "target_variable",
            "target_direction",
            "followup_hint",
            "guardrail_key",
            "notes",
        ],
    )
    df = _ensure_numeric(df, ["priority", "min_activation", "max_activation"])

    return df


def load_output_catalog() -> pd.DataFrame:
    if not OUTPUT_CATALOG_CSV.exists():
        return pd.DataFrame()

    df = pd.read_csv(OUTPUT_CATALOG_CSV).fillna("")

    required = {"output_key", "display_label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"output_catalogo.csv necesita columnas: {sorted(missing)}")

    if "is_enabled" in df.columns:
        df["is_enabled"] = df["is_enabled"].apply(_to_bool)
        df = df[df["is_enabled"]].copy()

    df = _ensure_text(
        df,
        [
            "output_key",
            "output_type",
            "display_label",
            "display_group",
            "default_target_variable",
            "default_target_direction",
            "ui_block",
            "guardrail_key",
            "short_template",
            "long_template",
            "followup_template",
            "severity_style",
            "notes",
        ],
    )
    df = _ensure_numeric(df, ["default_priority"])

    if "is_reusable" not in df.columns:
        df["is_reusable"] = False
    df["is_reusable"] = df["is_reusable"].apply(_to_bool)

    return df


def load_mechanism_coherence_catalog() -> pd.DataFrame:
    if not COHERENCE_MECHANISMS_CSV.exists():
        return pd.DataFrame()

    df = pd.read_csv(COHERENCE_MECHANISMS_CSV).fillna("")
    if "mechanism_id" not in df.columns:
        raise ValueError("mecanismos_coherencia_catalogo.csv debe incluir 'mechanism_id'")

    if "is_enabled" in df.columns:
        df["is_enabled"] = df["is_enabled"].apply(_to_bool)
        df = df[df["is_enabled"]].copy()

    df = _ensure_text(df, ["mechanism_id", "clinical_notes"])
    df = _ensure_numeric(df, ["min_hits", "min_groups", "min_primary_hits", "coherence_bonus", "display_threshold"])

    if "requires_primary_driver" not in df.columns:
        df["requires_primary_driver"] = False
    df["requires_primary_driver"] = df["requires_primary_driver"].apply(_to_bool)

    return df


def load_mechanism_coherence_rules() -> pd.DataFrame:
    if not COHERENCE_RULES_CSV.exists():
        return pd.DataFrame()

    df = pd.read_csv(COHERENCE_RULES_CSV).fillna("")
    required = {"mechanism_id", "variable_key"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"reglas_coherencia_mecanismo.csv necesita columnas: {sorted(missing)}")

    if "is_enabled" in df.columns:
        df["is_enabled"] = df["is_enabled"].apply(_to_bool)
        df = df[df["is_enabled"]].copy()

    df = _ensure_text(df, ["mechanism_id", "variable_key", "role", "combo_group", "evidence_tier", "clinical_rationale"])
    if "is_primary" not in df.columns:
        df["is_primary"] = False
    df["is_primary"] = df["is_primary"].apply(_to_bool)

    if "weight" not in df.columns:
        df["weight"] = 1.0
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(1.0)

    return df


def split_rules_by_source_type(variable_keys: set[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rules_df = load_rules_master()
    mech_df = load_mechanisms_catalog()

    mechanism_ids = set(mech_df["mechanism_id"].astype(str).str.strip())

    def classify_source(value: str) -> str:
        value = str(value).strip()
        if value in variable_keys:
            return "variable"
        if value in mechanism_ids:
            return "mechanism"
        return "unknown"

    rules_df["source_type"] = rules_df["variable_key"].astype(str).apply(classify_source)

    variable_rules = rules_df[rules_df["source_type"] == "variable"].copy()
    mechanism_rules = rules_df[rules_df["source_type"] == "mechanism"].copy()
    unknown_rules = rules_df[rules_df["source_type"] == "unknown"].copy()

    return variable_rules, mechanism_rules, unknown_rules
