# ui/components/render_pokemon_mode.py

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import streamlit as st


def _safe_get(d: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def _normalize_stats(stats: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convierte un dict de stats a una lista homogénea:
    {
        "lipidos": 88,
        "glucosa": 61
    }
    =>
    [
        {"label": "Lipidos", "value": 88},
        {"label": "Glucosa", "value": 61}
    ]
    """
    if not stats:
        return []

    normalized = []
    for key, value in stats.items():
        try:
            num = float(value)
        except Exception:
            continue

        label = str(key).replace("_", " ").strip().title()
        normalized.append({"label": label, "value": max(0.0, min(100.0, num))})

    return normalized


def _render_type_badges(types_: Iterable[str]) -> None:
    types_list = [str(t).strip() for t in types_ if str(t).strip()]
    if not types_list:
        return

    badges_html = ""
    for t in types_list:
        badges_html += f"""
        <span style="
            display:inline-block;
            padding:0.35rem 0.7rem;
            margin:0 0.35rem 0.35rem 0;
            border-radius:999px;
            background:#eef2ff;
            color:#1e3a8a;
            font-size:0.85rem;
            font-weight:600;
            border:1px solid #c7d2fe;
        ">{t}</span>
        """

    st.markdown(badges_html, unsafe_allow_html=True)


def _render_stat_bar(label: str, value: float) -> None:
    st.markdown(
        f"""
        <div style="margin-bottom:0.65rem;">
            <div style="display:flex; justify-content:space-between; margin-bottom:0.18rem;">
                <span style="font-weight:600; font-size:0.95rem;">{label}</span>
                <span style="font-size:0.9rem;">{value:.0f}</span>
            </div>
            <div style="
                width:100%;
                height:12px;
                background:#e5e7eb;
                border-radius:999px;
                overflow:hidden;
            ">
                <div style="
                    width:{max(0, min(100, value))}%;
                    height:12px;
                    background:linear-gradient(90deg, #60a5fa 0%, #f59e0b 60%, #ef4444 100%);
                    border-radius:999px;
                "></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_moves(title: str, items: Iterable[str]) -> None:
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return

    st.markdown(f"### {title}")
    for item in items:
        st.markdown(f"- {item}")


def render_pokemon_mode(
    pokemon_card: Dict[str, Any],
    *,
    section_title: str = "Modo Pokémon",
    show_debug: bool = False,
) -> None:
    """
    Render principal del modo Pokémon.

    Estructura esperada de pokemon_card:
    {
        "name": "Atherodon GX",
        "image_path": "outputs/pokemon.png",   # o image_url
        "image_url": None,
        "types": ["Lípidos", "Inflamación"],
        "rarity": "Épico",
        "threat_level": "Medio-alto",
        "subtitle": "Avatar metabólico actual",
        "stats": {
            "lipidos": 88,
            "glucosa": 61,
            "inflamacion": 74,
            "estres_oxidativo": 52
        },
        "moves": [
            "Golpe aterogénico",
            "Niebla inflamatoria"
        ],
        "clinical_summary": "Predomina un patrón aterogénico con componente inflamatorio de bajo grado.",
        "source_markers": [
            "ApoB alta",
            "LDL alto",
            "Triglicéridos altos",
            "hsCRP elevada"
        ]
    }
    """
    name = _safe_get(pokemon_card, "name", "Pokémon metabólico")
    subtitle = _safe_get(pokemon_card, "subtitle", "")
    types_ = _safe_get(pokemon_card, "types", [])
    rarity = _safe_get(pokemon_card, "rarity", "")
    threat_level = _safe_get(pokemon_card, "threat_level", "")
    stats = _normalize_stats(_safe_get(pokemon_card, "stats", {}))
    moves = _safe_get(pokemon_card, "moves", [])
    clinical_summary = _safe_get(pokemon_card, "clinical_summary", "")
    source_markers = _safe_get(pokemon_card, "source_markers", [])

    image_path = _safe_get(pokemon_card, "image_path")
    image_url = _safe_get(pokemon_card, "image_url")

    st.markdown(f"## {section_title}")

    # Caja principal
    st.markdown(
        """
        <div style="
            padding:1.1rem 1.1rem 1.25rem 1.1rem;
            border-radius:22px;
            border:1px solid #e5e7eb;
            background:linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            box-shadow:0 8px 24px rgba(0,0,0,0.05);
            margin-bottom:1rem;
        ">
        """,
        unsafe_allow_html=True,
    )

    # Imagen principal, grande
    if image_path:
        st.image(image_path, use_container_width=True)
    elif image_url:
        st.image(image_url, use_container_width=True)
    else:
        st.info("No hay imagen generada para este Pokémon.")

    # Identidad
    st.markdown(f"## {name}")

    meta_parts = []
    if subtitle:
        meta_parts.append(subtitle)
    if rarity:
        meta_parts.append(f"Rareza: {rarity}")
    if threat_level:
        meta_parts.append(f"Nivel: {threat_level}")

    if meta_parts:
        st.markdown(" • ".join(meta_parts))

    _render_type_badges(types_)

    # Stats
    if stats:
        st.markdown("### Stats")
        for item in stats:
            _render_stat_bar(item["label"], item["value"])

    # Habilidades / ataques
    _render_moves("Habilidades", moves)

    # Interpretación clínica
    if clinical_summary:
        with st.expander("Interpretación clínica", expanded=True):
            st.write(clinical_summary)

    # Analitos o marcadores que originan la forma
    if source_markers:
        with st.expander("Marcadores que originan esta forma", expanded=False):
            for marker in source_markers:
                st.markdown(f"- {marker}")

    if show_debug:
        with st.expander("Debug Pokémon", expanded=False):
            st.json(pokemon_card)

    st.markdown("</div>", unsafe_allow_html=True)