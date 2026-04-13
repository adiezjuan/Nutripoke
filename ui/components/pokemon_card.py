import streamlit as st


COLOR_BG = {
    "🟠": "#FFF4E5",
    "🟡": "#FFFBEA",
    "🔴": "#FDECEC",
    "🟤": "#F6EEE8",
    "🔵": "#EAF2FF",
    "🟣": "#F3E8FF",
    "🟢": "#ECFDF3",
    "🩵": "#EAF8FF",
    "⚪": "#F5F5F5",
}


def _pill(text: str) -> str:
    return (
        f"<span style='display:inline-block;padding:0.2rem 0.55rem;"
        f"border-radius:999px;background:#f2f4f7;font-size:0.82rem;"
        f"margin-right:0.35rem;margin-bottom:0.25rem;'>{text}</span>"
    )


def _score_badge(score: float) -> str:
    if score >= 70:
        return "🔥 alto"
    if score >= 45:
        return "⚡ medio"
    return "🫧 bajo"


def _render_pills(items):
    if not items:
        st.caption("—")
        return
    html = "".join(_pill(str(x)) for x in items if x)
    st.markdown(html, unsafe_allow_html=True)


def _render_circle_card(item):
    color = item.get("color", "⚪")
    bg = COLOR_BG.get(color, "#F5F5F5")
    label = item.get("label", "Sin nombre")
    score = float(item.get("score", 0) or 0)
    coherencia = item.get("coherencia", "media")
    sabor = item.get("sabor", "mixto")
    dominio = item.get("dominio", "—")
    drivers = item.get("drivers", []) or []

    st.markdown(
        f"""
        <div style="
            background:{bg};
            border:1px solid rgba(0,0,0,0.06);
            border-radius:18px;
            padding:16px 18px;
            margin-bottom:10px;
        ">
            <div style="font-size:1.05rem;font-weight:700;">
                {color} {label}
            </div>
            <div style="margin-top:6px;font-size:0.92rem;opacity:0.9;">
                {_score_badge(score)} · valor {score:.1f} · coherencia {coherencia} · sabor {sabor}
            </div>
            <div style="margin-top:4px;font-size:0.9rem;opacity:0.85;">
                Dominio: {dominio}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if drivers:
        st.caption("Drivers")
        _render_pills(drivers)


def _render_character_card(item):
    color = item.get("color", "⚪")
    bg = COLOR_BG.get(color, "#F5F5F5")
    label = item.get("label", "Sin nombre")
    score = float(item.get("score", 0) or 0)
    coherencia = item.get("coherencia", "media")
    sabor = item.get("sabor", "mixto")
    mensaje = item.get("mensaje", "")

    st.markdown(
        f"""
        <div style="
            background:{bg};
            border-left:6px solid rgba(0,0,0,0.18);
            border-radius:18px;
            padding:16px 18px;
            margin-bottom:10px;
        ">
            <div style="font-size:1.08rem;font-weight:800;">
                {color} {label}
            </div>
            <div style="margin-top:6px;font-size:0.92rem;opacity:0.9;">
                {_score_badge(score)} · score {score:.1f} · coherencia {coherencia} · sabor {sabor}
            </div>
            <div style="margin-top:10px;font-size:0.94rem;line-height:1.45;">
                {mensaje}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pokemon_card(pokemon_view, assembled_case=None, motor_result=None):
    pokemon_view = pokemon_view or {}
    nube = pokemon_view.get("nube", {}) or {}
    circulos = pokemon_view.get("circulos", []) or []
    personajes = pokemon_view.get("personajes", []) or []
    pokemon_final = pokemon_view.get("pokemon_final", {}) or {}

    st.subheader("Modo Pokémon")

    # NUBE
    with st.container(border=True):
        st.markdown("### ☁️ Nube")
        st.caption(
            f"Variables alteradas detectadas: {nube.get('num_variables_alteradas', 0)}"
        )

        variables = nube.get("variables_clave", []) or []
        if variables:
            cols = st.columns(min(4, max(1, len(variables[:4]))))
            for i, item in enumerate(variables[:4]):
                with cols[i % len(cols)]:
                    st.metric(
                        item.get("key", ""),
                        item.get("value", "—"),
                        item.get("classification", ""),
                    )

            if len(variables) > 4:
                st.caption("Más señales en la nube")
                _render_pills([v.get("key", "") for v in variables[4:]])
        else:
            st.write("Sin señales alteradas relevantes.")

    # CIRCULOS
    with st.container(border=True):
        st.markdown("### 🫧 Círculos")
        st.caption("Mecanismos posibles que empiezan a tomar forma.")
        if circulos:
            for item in circulos[:6]:
                _render_circle_card(item)
        else:
            st.write("No hay círculos activos suficientes.")

    # PERSONAJES
    with st.container(border=True):
        st.markdown("### 👤 Personajes")
        st.caption("Mecanismos ya consolidados con identidad clínica.")
        if personajes:
            for item in personajes:
                _render_character_card(item)
        else:
            st.write("Todavía no hay personajes consolidados.")

        # POKEMON FINAL
    with st.container(border=True):
        st.markdown("### ⚡ Pokémon final")

        label = pokemon_final.get("label", "Sin fenotipo final")
        species = pokemon_final.get("species", "")
        form = pokemon_final.get("form", "")
        form_label = pokemon_final.get("form_label", form)
        tone = pokemon_final.get("tone", "")
        temperament = pokemon_final.get("temperament", "")
        dominante = pokemon_final.get("dominante", "")
        componentes = pokemon_final.get("componentes", []) or []
        mensaje = pokemon_final.get("mensaje", "")
        next_step = pokemon_final.get("next_step", "")
        cloud_signature = pokemon_final.get("cloud_signature", {}) or {}
        species_rule_id = pokemon_final.get("species_rule_id", "")
        form_rule_id = pokemon_final.get("form_rule_id", "")

        st.markdown(
            f"""
            <div style="
                background:linear-gradient(135deg, #eef6ff 0%, #f8fbff 100%);
                border:1px solid rgba(0,0,0,0.06);
                border-radius:22px;
                padding:18px 20px;
                margin-bottom:12px;
            ">
                <div style="font-size:1.2rem;font-weight:800;">{label}</div>
                <div style="margin-top:8px;font-size:0.95rem;">
                    <b>Especie:</b> {species or "—"}
                </div>
                <div style="margin-top:4px;font-size:0.95rem;">
                    <b>Forma:</b> {form_label or "—"}
                </div>
                <div style="margin-top:4px;font-size:0.95rem;">
                    <b>Tono:</b> {tone or "—"}
                </div>
                <div style="margin-top:4px;font-size:0.95rem;">
                    <b>Temperamento:</b> {temperament or "—"}
                </div>
                <div style="margin-top:4px;font-size:0.95rem;">
                    <b>Predominio:</b> {dominante or "—"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if componentes:
            st.caption("Fusión de personajes")
            _render_pills(componentes)

        if cloud_signature:
            st.caption("Firma de nube")
            ranked = sorted(cloud_signature.items(), key=lambda x: x[1], reverse=True)
            top_cloud = [f"{k}: {v:.2f}" for k, v in ranked[:4] if v > 0]
            _render_pills(top_cloud)

        meta = []
        if species_rule_id:
            meta.append(f"species_rule: {species_rule_id}")
        if form_rule_id:
            meta.append(f"form_rule: {form_rule_id}")
        if meta:
            st.caption("Reglas aplicadas")
            _render_pills(meta)

        if mensaje:
            st.info(mensaje)

        if next_step:
            st.caption("Siguiente paso")
            st.write(next_step)