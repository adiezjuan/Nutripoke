import streamlit as st


def render_case_header(view_model: dict):
    st.markdown("## Resumen del caso")

    headline = view_model.get("headline", "Sin definir")
    confidence_label = view_model.get("confidence_label", "—")
    measured_count = view_model.get("measured_count", 0)
    abnormal_count = view_model.get("abnormal_count", 0)
    forced_domain = view_model.get("forced_domain_label")
    boost_reasons = view_model.get("boost_reasons", []) or []

    c1, c2, c3, c4 = st.columns([1.8, 1, 1, 1])

    with c1:
        st.info(f"**Patrón principal**\n\n{headline}")

    with c2:
        st.metric("Confianza", confidence_label)

    with c3:
        st.metric("Variables medidas", str(measured_count))

    with c4:
        st.metric("Fuera de rango", str(abnormal_count))

    meta = []
    if forced_domain:
        meta.append(f"**Dominio forzado:** {forced_domain}")
    if boost_reasons:
        meta.append("**Boosts activos:** " + " · ".join(boost_reasons[:3]))

    if meta:
        st.caption(" | ".join(meta))
