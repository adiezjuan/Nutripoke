import streamlit as st


def render_canonical_card(view_model: dict):
    st.markdown("## Lectura ejecutiva")

    headline = view_model.get("headline", "Sin lectura disponible")
    summary = view_model.get("summary", "Todavía no hay una narrativa consolidada.")
    next_step = view_model.get("next_step", "Completar más datos para mejorar la resolución del caso.")
    confidence_label = view_model.get("confidence_label", "—")
    top_domains = view_model.get("top_domains", []) or []

    left, right = st.columns([1.6, 1.0], gap="large")

    with left:
        with st.container(border=True):
            st.markdown(f"### {headline}")
            st.write(summary)
            st.write(f"**Siguiente paso:** {next_step}")

    with right:
        with st.container(border=True):
            st.markdown("### Estado")
            st.write(f"**Confianza:** {confidence_label}")

            if top_domains:
                st.write("**Dominios dominantes**")
                for item in top_domains[:3]:
                    label = item.get("label", "—")
                    score = item.get("score", 0.0)
                    st.write(f"- {label}: {score:.1f}")
            else:
                st.write("Sin dominios dominantes todavía.")
