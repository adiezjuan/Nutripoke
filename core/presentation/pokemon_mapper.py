# pokemon_mapper.py

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


DOMAIN_LABELS = {
    "lipidos": "Lípidos",
    "glucosa": "Glucosa",
    "inflamacion": "Inflamación",
    "higado": "Hígado",
    "rinon": "Riñón",
    "hematologia": "Hematología",
    "nutricional": "Nutricional",
    "hormonal": "Hormonal",
    "oxidativo": "Estrés oxidativo",
}


ANALYTE_DOMAIN_MAP = {
    "apob_mg_dl": "lipidos",
    "ldl_mg_dl": "lipidos",
    "chol_total_mg_dl": "lipidos",
    "triglycerides_mg_dl": "lipidos",
    "hdl_mg_dl": "lipidos",

    "glucose_mg_dl": "glucosa",
    "hba1c_pct": "glucosa",
    "insulin_uui_ml": "glucosa",
    "homa_ir": "glucosa",

    "hscrp_mg_l": "inflamacion",
    "crp_mg_l": "inflamacion",
    "ferritin_ng_ml": "inflamacion",

    "alt_u_l": "higado",
    "ast_u_l": "higado",
    "ggt_u_l": "higado",

    "creatinine_mg_dl": "rinon",
    "egfr_ml_min": "rinon",
    "urea_mg_dl": "rinon",

    "hb_g_dl": "hematologia",
    "hematocrit_pct": "hematologia",
    "mcv_fl": "hematologia",
    "rdw_pct": "hematologia",

    "vitamin_d_ng_ml": "nutricional",
    "vit_b12_pg_ml": "nutricional",
    "folate_ng_ml": "nutricional",
    "albumin_g_dl": "nutricional",
    "bmi_kg_m2": "nutricional",

    "testosterone_ng_dl": "hormonal",
    "tsh_uui_ml": "hormonal",
    "free_t4_ng_dl": "hormonal",

    "uric_acid_mg_dl": "oxidativo",
}


DOMAIN_BASE_STATS = {
    "lipidos": "lipidos",
    "glucosa": "glucosa",
    "inflamacion": "inflamacion",
    "higado": "higado",
    "rinon": "rinon",
    "hematologia": "hematologia",
    "nutricional": "nutricion",
    "hormonal": "hormonal",
    "oxidativo": "estres_oxidativo",
}


DOMAIN_MOVES = {
    "lipidos": [
        "Golpe aterogénico",
        "Marea lipídica",
        "Escama de ApoB",
    ],
    "glucosa": [
        "Pulso glucémico",
        "Pico insulínico",
        "Carga glicada",
    ],
    "inflamacion": [
        "Niebla inflamatoria",
        "Llama silenciosa",
        "Eco de bajo grado",
    ],
    "higado": [
        "Carga hepática",
        "Pulso detox",
        "Sobrecarga enzimática",
    ],
    "rinon": [
        "Filtro cansado",
        "Presión osmótica",
        "Eco renal",
    ],
    "hematologia": [
        "Pulso eritroide",
        "Trama sanguínea",
        "Variación celular",
    ],
    "nutricional": [
        "Reserva esencial",
        "Campo anabólico",
        "Balance mineral",
    ],
    "hormonal": [
        "Señal endocrina",
        "Ritmo hormonal",
        "Eje inestable",
    ],
    "oxidativo": [
        "Chispa oxidativa",
        "Aura reactiva",
        "Estrés mitocondrial",
    ],
}


DOMAIN_NAME_PARTS = {
    "lipidos": ("Ather", "don"),
    "glucosa": ("Gluco", "zar"),
    "inflamacion": ("Pyro", "mist"),
    "higado": ("Hepa", "drake"),
    "rinon": ("Nefro", "shell"),
    "hematologia": ("Hemo", "fang"),
    "nutricional": ("Nutra", "morph"),
    "hormonal": ("Endo", "volt"),
    "oxidativo": ("Oxi", "flare"),
}


def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _title_label(key: str) -> str:
    return key.replace("_", " ").strip().title()


def _extract_variables_clave(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Busca variables_clave en distintas rutas posibles.
    """
    if isinstance(payload.get("variables_clave"), list):
        return payload["variables_clave"]

    nube = _safe_dict(payload.get("nube"))
    if isinstance(nube.get("variables_clave"), list):
        return nube["variables_clave"]

    analitos = _safe_dict(payload.get("analitos"))
    out = []
    for key, value in analitos.items():
        if isinstance(value, dict):
            item = {
                "key": key,
                "value": value.get("value"),
                "classification": value.get("classification"),
            }
            out.append(item)
    return out


def _extract_outputs(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    outputs = payload.get("outputs")
    if isinstance(outputs, list):
        return outputs
    return []


def _score_from_classification(classification: Optional[str]) -> float:
    c = str(classification or "").strip().lower()
    if c in {"high", "alto", "elevado", "up"}:
        return 1.0
    if c in {"low", "bajo", "down"}:
        return 0.7
    if c in {"borderline", "limite", "límite"}:
        return 0.5
    if c in {"normal", "ok", "in_range"}:
        return 0.0
    return 0.25


def _aggregate_domains(variables: List[Dict[str, Any]]) -> Tuple[Dict[str, float], List[str]]:
    domain_scores: Dict[str, float] = {}
    source_markers: List[str] = []

    for item in variables:
        key = str(item.get("key", "")).strip()
        classification = item.get("classification")
        value = item.get("value")
        domain = ANALYTE_DOMAIN_MAP.get(key)

        if not domain:
            continue

        score = _score_from_classification(classification)
        domain_scores[domain] = domain_scores.get(domain, 0.0) + score

        if classification and str(classification).lower() not in {"normal", "ok", "in_range"}:
            source_markers.append(f"{_title_label(key)}: {value} ({classification})")

    return domain_scores, source_markers


def _top_domains(domain_scores: Dict[str, float], top_k: int = 3) -> List[Tuple[str, float]]:
    ranked = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]


def _make_name(top_domains: List[Tuple[str, float]]) -> str:
    if not top_domains:
        return "Metamon"

    parts = []
    for domain, _ in top_domains[:2]:
        prefix, suffix = DOMAIN_NAME_PARTS.get(domain, ("Meta", "mon"))
        if not parts:
            parts.append(prefix)
        else:
            parts.append(suffix)

    name = "".join(parts)
    return f"{name} GX"


def _make_types(top_domains: List[Tuple[str, float]]) -> List[str]:
    out = []
    for domain, _ in top_domains[:2]:
        out.append(DOMAIN_LABELS.get(domain, _title_label(domain)))
    return out or ["Metabólico"]


def _make_rarity(total_score: float) -> str:
    if total_score >= 5.0:
        return "Legendario"
    if total_score >= 3.5:
        return "Épico"
    if total_score >= 2.0:
        return "Raro"
    return "Común"


def _make_threat_level(total_score: float) -> str:
    if total_score >= 5.0:
        return "Alto"
    if total_score >= 3.0:
        return "Medio-alto"
    if total_score >= 1.5:
        return "Medio"
    return "Bajo"


def _make_stats(domain_scores: Dict[str, float]) -> Dict[str, int]:
    stats: Dict[str, int] = {}

    for domain, label_key in DOMAIN_BASE_STATS.items():
        raw = domain_scores.get(domain, 0.0)
        value = int(min(100, round(raw * 28)))
        if value > 0:
            stats[label_key] = value

    if not stats:
        stats = {
            "equilibrio": 55,
            "adaptacion": 48,
        }

    return stats


def _make_moves(top_domains: List[Tuple[str, float]]) -> List[str]:
    moves: List[str] = []
    for domain, _ in top_domains[:2]:
        moves.extend(DOMAIN_MOVES.get(domain, [])[:2])

    seen = set()
    unique_moves = []
    for m in moves:
        if m not in seen:
            seen.add(m)
            unique_moves.append(m)

    return unique_moves[:4]


def _make_clinical_summary(top_domains: List[Tuple[str, float]], outputs: List[Dict[str, Any]]) -> str:
    if outputs:
        top_texts = []
        for out in outputs[:3]:
            txt = out.get("short_template") or out.get("display_label") or out.get("output_key")
            if txt:
                top_texts.append(str(txt).strip())
        if top_texts:
            return " / ".join(top_texts)

    if not top_domains:
        return "Perfil relativamente estable sin un dominio dominante claro."

    labels = [DOMAIN_LABELS.get(d, _title_label(d)) for d, _ in top_domains[:2]]
    if len(labels) == 1:
        return f"Predomina un patrón centrado en {labels[0].lower()}."
    return f"Predomina una combinación de {labels[0].lower()} y {labels[1].lower()}."


def _make_image_prompt(name: str, types_: List[str], rarity: str, threat_level: str, top_domains: List[Tuple[str, float]]) -> str:
    domain_flavor = ", ".join([DOMAIN_LABELS.get(d, d) for d, _ in top_domains[:3]])
    types_text = ", ".join(types_)
    return (
        f"Creature fusion monster, original design, cinematic trading-card illustration, "
        f"main character centered, highly detailed, polished digital art, "
        f"name {name}, elemental metabolic types: {types_text}, dominant physiological themes: {domain_flavor}, "
        f"rarity {rarity}, threat level {threat_level}, glowing aura, dynamic pose, clean background, "
        f"fantasy biotech style, premium card-art composition"
    )


def build_pokemon_card(
    payload: Dict[str, Any],
    image_path: Optional[str] = None,
    image_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convierte el resultado del motor a una tarjeta Pokémon compatible con render_pokemon_mode().

    payload puede contener por ejemplo:
    {
        "nube": {
            "variables_clave": [
                {"key": "apob_mg_dl", "classification": "high", "value": 108},
                ...
            ]
        },
        "outputs": [...]
    }
    """
    payload = _safe_dict(payload)

    variables = _extract_variables_clave(payload)
    outputs = _extract_outputs(payload)

    domain_scores, source_markers = _aggregate_domains(variables)
    top_domains = _top_domains(domain_scores, top_k=3)

    total_score = sum(domain_scores.values())
    name = _make_name(top_domains)
    types_ = _make_types(top_domains)
    rarity = _make_rarity(total_score)
    threat_level = _make_threat_level(total_score)
    stats = _make_stats(domain_scores)
    moves = _make_moves(top_domains)
    clinical_summary = _make_clinical_summary(top_domains, outputs)
    image_prompt = _make_image_prompt(name, types_, rarity, threat_level, top_domains)

    subtitle = "Avatar metabólico actual"

    return {
        "name": name,
        "image_path": image_path,
        "image_url": image_url,
        "types": types_,
        "rarity": rarity,
        "threat_level": threat_level,
        "subtitle": subtitle,
        "stats": stats,
        "moves": moves,
        "clinical_summary": clinical_summary,
        "source_markers": source_markers[:8],
        "image_prompt": image_prompt,
        "dominant_domains": [
            {
                "domain_key": domain,
                "domain_label": DOMAIN_LABELS.get(domain, _title_label(domain)),
                "score": round(score, 2),
            }
            for domain, score in top_domains
        ],
    }