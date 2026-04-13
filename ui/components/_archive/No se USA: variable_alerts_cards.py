import streamlit as st


def _classification_label(classification: str) -> str:
    mapping = {
        "high": "↑ Alto",
        "critical_high": "↑ Muy alto",
        "low": "↓ Bajo",
        "critical_low": "↓ Muy bajo",
        "normal": "✓ Normal",
        "missing": "—",
    }
    return mapping.get(classification, classification or "—")


def _classification_tone(classification: str) -> str:
    if classification in {"critical_high", "critical_low"}:
        return "danger"
    if classification in {"high", "low"}:
        return "warn"
    if classification == "normal":
        return "good"
    return "neutral"


def _render_badge(text: str, tone: str):
    tones = {
        "neutral": {"bg": "#f3f4f6", "fg": "#374151"},
        "good": {"bg": "#e8f5e9", "fg": "#166534"},
        "warn": {"bg": "#fff7ed", "fg": "#9a3412"},
        "danger": {"bg": "#fef2f2", "fg": "#991b1b"},
    }
    t = tones[tone]
    st.markdown(
        f"""
        <span style="
            display:inline-block;
            padding:0.2rem 0.55rem;
            border-radius:999px;
            background:{t['bg']};
            color:{t['fg']};
            font-weight:600;
            font-size:0.85rem;
        ">{text}</span>
        """,
        unsafe_allow_html=True,
    )


def render_variable_alerts_card(case_result):
    case_dict = case_result.to_dict() if hasattr(case_result, "to_dict") else case_result
    variable_scores = case_dict.get("variable_scores", {}) or {}

    altered = []
    for key, info in variable_scores.items():
        classification = info.get("classification", "missing")
        if classification not in {"high", "critical_high", "low", "critical_low"}:
            continue

        ref = info.get("reference") or {}
        altered.append(
            {
                "key": key,
                "label": ref.get("label", key),
                "value": info.get("value"),
                "classification": classification,
                "category": (
                    ref.get("categoria_alto", "")
                    if classification in {"high", "critical_high"}
                    else ref.get("categoria_bajo", "")
                ),
                "range_text": _format_reference_range(ref),
                "note": info.get("note", "") or ref.get("notes", ""),
            }
        )

    st.markdown("## Variables alteradas")

    if not altered:
        st.success("No se detectan variables fuera de rango con los datos disponibles.")
        return

    cols = st.columns(2, gap="large")
    for idx, item in enumerate(altered):
        with cols[idx % 2]:
            with st.container(border=True):
                top_left, top_right = st.columns([1.7, 0.9])

                with top_left:
                    st.markdown(f"### {item['label']}")
                    if item["category"]:
                        st.caption(item["category"])

                with top_right:
                    _render_badge(
                        _classification_label(item["classification"]),
                        _classification_tone(item["classification"]),
                    )

                st.write(f"**Valor:** {item['value']}")
                st.write(f"**Rango:** {item['range_text']}")

                if item["note"]:
                    st.caption(item["note"])


def _format_reference_range(ref_cfg: dict) -> str:
    ref_low = ref_cfg.get("reference_low")
    ref_high = ref_cfg.get("reference_high")

    if ref_low is not None and ref_high is not None:
        return f"{ref_low}–{ref_high}"
    if ref_low is not None:
        return f">= {ref_low}"
    if ref_high is not None:
        return f"<= {ref_high}"
    return "—"