from typing import Any, Dict, List
from pathlib import Path
from functools import lru_cache
import unicodedata

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NETWORK_DIR = PROJECT_ROOT / "data" / "network"
SPECIES_RULES_PATH = NETWORK_DIR / "pokemon_species_rules.csv"
FORM_RULES_PATH = NETWORK_DIR / "pokemon_form_rules.csv"


DOMAIN_COLOR_MAP = {
    "metabolico": "🟠",
    "metabolica": "🟠",
    "glucemico": "🟠",
    "glucemica": "🟠",
    "lipidos": "🟡",
    "lipidico": "🟡",
    "inflamacion": "🔴",
    "inflamatorio": "🔴",
    "hepatico": "🟤",
    "hepatica": "🟤",
    "renal": "🔵",
    "kidney": "🔵",
    "hematologia": "🟣",
    "hematologico": "🟣",
    "nutricional": "🟢",
    "endocrino": "🩵",
    "thyroid": "🩵",
    "hormonal": "🩵",
}


def _safe_list(value):
    return value if isinstance(value, list) else []


def _norm_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def _split_pipe(value: Any) -> List[str]:
    text = str(value).strip() if value is not None else ""
    if not text or text.lower() == "nan":
        return []
    return [_norm_text(x) for x in text.split("|") if str(x).strip()]


def _get_color(system: str) -> str:
    key = _norm_text(system)
    if not key:
        return "⚪"
    for domain_key, emoji in DOMAIN_COLOR_MAP.items():
        if domain_key in key or key in domain_key:
            return emoji
    return "⚪"


def _coherence_to_label(item: Dict[str, Any]) -> str:
    coherence = item.get("coherence")
    if isinstance(coherence, dict):
        passed = coherence.get("passed_checks", 0)
        total = coherence.get("total_checks", 0)
        if total <= 0:
            return "media"
        ratio = passed / total
        if ratio >= 0.75:
            return "alta"
        if ratio >= 0.4:
            return "media"
        return "baja"
    return "media"


def _infer_flavor(item: Dict[str, Any]) -> str:
    label = _norm_text(item.get("label", ""))
    system = _norm_text(item.get("system", ""))

    if "inflam" in label or "inflam" in system:
        return "reactivo"
    if "gluc" in label or "insulin" in label:
        return "cronico-metabolico"
    if "metabol" in system:
        return "cronico-metabolico"
    if "lip" in label or "aterog" in label:
        return "aterogenico"
    if "hep" in label or "hep" in system or "liver" in system:
        return "metabolico-hepatico"
    if "renal" in label or "renal" in system or "kidney" in system:
        return "filtrado-renal"
    if "anem" in label or "hema" in label or "hemat" in system:
        return "hematologico"
    return "mixto"


def _infer_fusion_group(item: Dict[str, Any]) -> str:
    label = _norm_text(item.get("label", ""))
    system = _norm_text(item.get("system", ""))

    if any(x in label for x in ["insulin", "aterog", "cardiomet", "metabol", "glucid", "gluc", "visceral"]):
        return "cardiometabolico"
    if "inflam" in label or "inflam" in system:
        return "inflamatorio"
    if "hep" in label or "hep" in system or "liver" in system:
        return "hepatico_metabolico"
    if "renal" in label or "renal" in system or "kidney" in system:
        return "renal"
    if "anem" in label or "hema" in label or "hemat" in system:
        return "hematologico"
    if "thyroid" in system or "tiro" in label or "hormonal" in system:
        return "endocrino"
    return "mixto"


@lru_cache(maxsize=1)
def _load_species_rules() -> pd.DataFrame:
    if not SPECIES_RULES_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(SPECIES_RULES_PATH)
    if "is_enabled" in df.columns:
        df = df[df["is_enabled"].fillna(0).astype(int) == 1].copy()
    if "priority" in df.columns:
        df["priority"] = pd.to_numeric(df["priority"], errors="coerce").fillna(0)
        df = df.sort_values("priority", ascending=False)
    return df


@lru_cache(maxsize=1)
def _load_form_rules() -> pd.DataFrame:
    if not FORM_RULES_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(FORM_RULES_PATH)
    if "is_enabled" in df.columns:
        df = df[df["is_enabled"].fillna(0).astype(int) == 1].copy()
    if "priority" in df.columns:
        df["priority"] = pd.to_numeric(df["priority"], errors="coerce").fillna(0)
        df = df.sort_values("priority", ascending=False)
    return df


def _build_circulos(motor_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    mechanisms = _safe_list(motor_result.get("mechanisms"))
    top_mechs = _safe_list(motor_result.get("top_mechanisms"))
    source_mechanisms = mechanisms if mechanisms else top_mechs

    circulos = []
    for item in source_mechanisms:
        score = float(item.get("activation", 0) or 0)
        if score < 10:
            continue

        evidence = _safe_list(item.get("evidence"))
        drivers = []
        for ev in evidence[:4]:
            source = ev.get("source")
            if source:
                drivers.append(source)

        circulos.append(
            {
                "id": item.get("mechanism_id", ""),
                "label": item.get("label", item.get("mechanism_id", "")),
                "score": round(score, 1),
                "color": _get_color(item.get("system", "")),
                "dominio": item.get("system", ""),
                "sabor": _infer_flavor(item),
                "coherencia": _coherence_to_label(item),
                "drivers": drivers,
                "fusion_group": _infer_fusion_group(item),
            }
        )

    circulos.sort(key=lambda x: x["score"], reverse=True)
    return circulos


def _build_personajes(motor_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    top_mechs = _safe_list(motor_result.get("top_mechanisms"))
    if not top_mechs:
        top_mechs = _safe_list(motor_result.get("mechanisms"))

    personajes = []
    for item in top_mechs:
        score = float(item.get("activation", 0) or 0)
        coherence = _coherence_to_label(item)
        if score < 25:
            continue

        personajes.append(
            {
                "id": item.get("mechanism_id", ""),
                "label": item.get("label", item.get("mechanism_id", "")),
                "label_norm": _norm_text(item.get("label", item.get("mechanism_id", ""))),
                "score": round(score, 1),
                "color": _get_color(item.get("system", "")),
                "dominio": item.get("system", ""),
                "sabor": _infer_flavor(item),
                "coherencia": coherence,
                "fusion_group": _infer_fusion_group(item),
                "mensaje": (
                    f"{item.get('label', item.get('mechanism_id', 'Mecanismo'))} "
                    f"aparece consolidado con activación {round(score, 1)} y coherencia {coherence}."
                ),
            }
        )

    personajes.sort(key=lambda x: x["score"], reverse=True)
    return personajes[:4]


def _domain_bucket_from_variable(key: str) -> str:
    k = _norm_text(key)

    if k in {"glucose_mg_dl", "hba1c_pct", "insulin_uiu_ml"}:
        return "glucemico"
    if k in {"triglycerides_mg_dl", "hdl_mg_dl", "ldl_mg_dl", "chol_total_mg_dl", "apob_mg_dl", "lpa_nmol_l"}:
        return "lipidico"
    if k in {"bmi_kg_m2", "waist_cm"}:
        return "visceral"
    if k in {"hscrp_mg_l", "esr_mm_h", "fibrinogen_mg_dl", "wbc_x10_3_mm3", "neut_abs_x10_3_mm3", "lymph_abs_x10_3_mm3"}:
        return "inflamatorio"
    if k in {"alt_u_l", "ast_u_l", "ggt_u_l", "alp_u_l", "bilirubin_total_mg_dl", "albumin_g_dl"}:
        return "hepatico"
    if k in {"creatinine_mg_dl", "egfr_ml_min_1_73m2", "urea_mg_dl", "uacr_mg_g"}:
        return "renal"
    if k in {"hb_g_dl", "hct_pct", "rbc_x10_6_mm3", "mcv_fl", "rdw_pct", "ferritin_ng_ml", "iron_ug_dl", "transferrin_mg_dl", "transferrin_sat_pct", "tibc_ug_dl", "platelets_x10_3_ul"}:
        return "hematologico"
    if k in {"tsh_miu_l", "ft4_ng_dl"}:
        return "endocrino"
    return "mixto"


def _build_cloud_signature(case_result) -> Dict[str, float]:
    variable_scores = getattr(case_result, "variable_scores", {}) or {}
    signature = {
        "glucemico": 0.0,
        "lipidico": 0.0,
        "visceral": 0.0,
        "inflamatorio": 0.0,
        "hepatico": 0.0,
        "renal": 0.0,
        "hematologico": 0.0,
        "endocrino": 0.0,
        "mixto": 0.0,
    }

    altered_count = 0
    for key, info in variable_scores.items():
        cls = _norm_text(info.get("classification", ""))
        if cls not in {"high", "low", "critical_high", "critical_low"}:
            continue

        altered_count += 1
        bucket = _domain_bucket_from_variable(key)
        weight = 1.0
        if cls in {"critical_high", "critical_low"}:
            weight = 1.5
        signature[bucket] += weight

    if altered_count == 0:
        return signature

    max_value = max(signature.values()) if signature else 0.0
    if max_value > 0:
        for k in list(signature.keys()):
            signature[k] = round(signature[k] / max_value, 3)

    return signature


def _dominant_cloud_domains(cloud_signature: Dict[str, float]) -> List[str]:
    ranked = sorted(cloud_signature.items(), key=lambda x: x[1], reverse=True)
    return [k for k, v in ranked if v >= 0.35][:3]


def _row_matches_species_rule(row: pd.Series, personajes: List[Dict[str, Any]], group_scores: Dict[str, float]) -> bool:
    fusion_group = _norm_text(row.get("fusion_group", ""))
    if fusion_group and group_scores.get(fusion_group, 0.0) <= 0:
        return False

    min_personajes = int(pd.to_numeric(row.get("min_personajes", 1), errors="coerce") or 1)
    if len(personajes) < min_personajes:
        return False

    labels_norm = {p.get("label_norm", _norm_text(p.get("label", ""))) for p in personajes}

    req_any = _split_pipe(row.get("requires_labels_any", ""))
    req_all = _split_pipe(row.get("requires_labels_all", ""))

    if req_any and not any(x in labels_norm for x in req_any):
        return False

    if req_all and not all(x in labels_norm for x in req_all):
        return False

    return True


def _fuse_characters(personajes: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not personajes:
        return {
            "species": "fenotipo_indefinido",
            "label": "Fenotipo no definido",
            "group": "mixto",
            "componentes": [],
        }

    group_scores: Dict[str, float] = {}
    for p in personajes:
        g = _norm_text(p.get("fusion_group", "mixto"))
        group_scores[g] = group_scores.get(g, 0.0) + float(p.get("score", 0) or 0)

    species_rules = _load_species_rules()
    if not species_rules.empty:
        for _, row in species_rules.iterrows():
            if _row_matches_species_rule(row, personajes, group_scores):
                return {
                    "species": row.get("species_id", "fenotipo_mixto"),
                    "label": row.get("species_label", "Fenotipo mixto"),
                    "group": _norm_text(row.get("fusion_group", "mixto")),
                    "componentes": [p["label"] for p in personajes[:3]],
                    "rule_id": row.get("rule_id", ""),
                }

    top_group = max(group_scores.items(), key=lambda x: x[1])[0]
    fallback_map = {
        "cardiometabolico": ("fenotipo_cardiometabolico", "Fenotipo cardiometabólico"),
        "inflamatorio": ("fenotipo_inflamatorio", "Fenotipo inflamatorio"),
        "hepatico_metabolico": ("fenotipo_hepatico_metabolico", "Fenotipo hepático-metabólico"),
        "renal": ("fenotipo_renal", "Fenotipo renal"),
        "hematologico": ("fenotipo_hematologico", "Fenotipo hematológico"),
        "endocrino": ("fenotipo_endocrino", "Fenotipo endocrino"),
    }
    species_id, label = fallback_map.get(top_group, ("fenotipo_mixto", "Fenotipo mixto"))
    return {
        "species": species_id,
        "label": label,
        "group": top_group,
        "componentes": [p["label"] for p in personajes[:3]],
    }


def _derive_form_from_cloud(base_fusion: Dict[str, Any], cloud_signature: Dict[str, float]) -> Dict[str, str]:
    doms = _dominant_cloud_domains(cloud_signature)
    primary = doms[0] if doms else "mixto"
    secondary = doms[1] if len(doms) > 1 else ""

    form_rules = _load_form_rules()
    species_id = base_fusion.get("species", "fenotipo_mixto")

    if not form_rules.empty:
        subset = form_rules[form_rules["species_id"].astype(str) == species_id]
        if not subset.empty:
            for _, row in subset.iterrows():
                row_primary = _norm_text(row.get("primary_cloud_domain", ""))
                row_secondary = _norm_text(row.get("secondary_cloud_domain", ""))

                if row_primary and row_primary != primary:
                    continue
                if row_secondary and row_secondary != secondary:
                    continue

                return {
                    "form": row.get("form_id", "basal"),
                    "form_label": row.get("form_label", "basal"),
                    "tone": row.get("tone", "mixto"),
                    "temperament": row.get("temperament", "estable"),
                    "primary_cloud_domain": primary,
                    "secondary_cloud_domain": secondary,
                    "rule_id": row.get("rule_id", ""),
                }

    return {
        "form": "basal",
        "form_label": "basal",
        "tone": "mixto",
        "temperament": "estable",
        "primary_cloud_domain": primary,
        "secondary_cloud_domain": secondary,
    }


def _build_pokemon_final(
    assembled_case: Dict[str, Any],
    personajes: List[Dict[str, Any]],
    circulos: List[Dict[str, Any]],
    cloud_signature: Dict[str, float],
) -> Dict[str, Any]:
    next_step = assembled_case.get("next_step", "")

    dominante = (
        personajes[0]["label"]
        if personajes
        else (circulos[0]["label"] if circulos else "Sin patrón dominante")
    )

    fusion = _fuse_characters(personajes)
    form_data = _derive_form_from_cloud(fusion, cloud_signature)

    species_label = fusion["label"]
    form = form_data["form"]
    form_label = form_data.get("form_label", form)
    tone = form_data["tone"]
    temperament = form_data["temperament"]
    componentes = fusion["componentes"]

    label_final = species_label
    if form and form != "basal":
        label_final = f"{species_label} · forma {form_label}"

    if dominante != "Sin patrón dominante":
        mensaje_final = (
            f"Predomina {dominante.lower()}, integrado como {species_label.lower()} "
            f"con forma {form_label} y tono {tone}."
        )
    else:
        mensaje_final = "Todavía no hay un fenotipo integrado dominante."

    return {
        "label": label_final,
        "species": species_label,
        "species_id": fusion.get("species", ""),
        "form": form,
        "form_label": form_label,
        "tone": tone,
        "temperament": temperament,
        "dominante": dominante,
        "componentes": componentes,
        "cloud_signature": cloud_signature,
        "species_rule_id": fusion.get("rule_id", ""),
        "form_rule_id": form_data.get("rule_id", ""),
        "mensaje": mensaje_final,
        "next_step": next_step,
    }


def build_pokemon_view(case_result, motor_result, assembled_case) -> Dict[str, Any]:
    assembled_case = assembled_case if isinstance(assembled_case, dict) else {}

    circulos = _build_circulos(motor_result or {})
    personajes = _build_personajes(motor_result or {})
    cloud_signature = _build_cloud_signature(case_result)

    variable_scores = getattr(case_result, "variable_scores", {}) or {}
    variables_clave = []
    for key, info in variable_scores.items():
        cls = info.get("classification")
        if cls in {"high", "low", "critical_high", "critical_low"}:
            variables_clave.append(
                {
                    "key": key,
                    "classification": cls,
                    "value": info.get("value"),
                }
            )

    nube = {
        "variables_clave": variables_clave[:8],
        "num_variables_alteradas": len(variables_clave),
        "signature": cloud_signature,
        "dominant_domains": _dominant_cloud_domains(cloud_signature),
    }

    pokemon_final = _build_pokemon_final(
        assembled_case=assembled_case,
        personajes=personajes,
        circulos=circulos,
        cloud_signature=cloud_signature,
    )

    return {
        "nube": nube,
        "circulos": circulos,
        "personajes": personajes,
        "pokemon_final": pokemon_final,
    }