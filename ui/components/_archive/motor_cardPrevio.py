import streamlit as st


def _status_label(status: str) -> str:
    mapping = {
        "active": "Activo",
        "weak": "Débil",
        "inactive": "Inactivo",
    }
    return mapping.get(str(status or "").lower(), status or "—")


def _activation_bucket(value: float) -> str:
    if value >= 70:
        return "Alta"
    if value >= 35:
        return "Media"
    if value > 0:
        return "Baja"
    return "Nula"


def _build_headline(top_mechanisms: list[dict]) -> tuple[str, str]:
    if not top_mechanisms:
        return (
            "Sin lectura mecanística útil todavía",
            "El motor no encuentra señal fisiológica suficiente con los datos actuales.",
        )

    primary = top_mechanisms[0]
    primary_label = primary.get("label", primary.get("mechanism_id", "—"))
    primary_activation = float(primary.get("activation", 0.0))
    primary_bucket = _activation_bucket(primary_activation)

    secondary_text = ""
    if len(top_mechanisms) > 1:
        secondary = top_mechanisms[1]
        secondary_label = secondary.get("label", secondary.get("mechanism_id", "—"))
        secondary_activation = float(secondary.get("activation", 0.0))
        if secondary_activation > 0:
            secondary_text = f" El segundo eje es {secondary_label} ({secondary_activation:.1f}/100)."

    headline = f"Predomina {primary_label}"
    body = (
        f"El motor sugiere que el eje fisiológico dominante es **{primary_label}**, "
        f"con una activación **{primary_bucket.lower()}** ({primary_activation:.1f}/100)."
        f"{secondary_text}"
    )
    return headline, body


def _build_driver_lines(evidence: list[dict]) -> list[str]:
    lines = []
    for ev in evidence[:4]:
        source = ev.get("source", "—")
        classification = ev.get("classification", "")
        signal = ev.get("signal", 0)

        if classification:
            lines.append(f"{source} · {classification} · impacto {float(signal):.1f}")
        else:
            lines.append(f"{source} · impacto {float(signal):.1f}")

    return lines


def _render_output_group(title: str, items: list[dict]):
    with st.container(border=True):
        st.markdown(f"### {title}")
        if not items:
            st.write("Sin salidas disparadas.")
            return

        for item in items:
            label = item.get("display_label", item.get("output_key", "—"))
            mech = item.get("mechanism_label", item.get("mechanism_id", "—"))
            activation = float(item.get("mechanism_activation", 0.0))
            short_text = item.get("short_text", "")
            long_text = item.get("long_text", "")
            followup = item.get("followup", "")

            st.markdown(f"**{label}**")
            st.write(short_text)
            if long_text:
                st.caption(long_text)
            st.caption(f"Fuente: {mech} · activación {activation:.1f}/100")
            if followup:
                st.write(f"Seguimiento: {followup}")


def render_motor_card(motor_result: dict):
    st.markdown("## Explicación fisiológica")

    top_mechanisms = motor_result.get("top_mechanisms", []) or []
    active_mechanisms = motor_result.get("active_mechanisms", []) or []
    unknown_rules = motor_result.get("unknown_rules", []) or []
    outputs_by_block = motor_result.get("outputs_by_block", {}) or {}
    top_outputs = motor_result.get("top_outputs", []) or []

    headline, summary = _build_headline(top_mechanisms)

    top_left, top_right = st.columns([1.6, 1.0], gap="large")

    with top_left:
        with st.container(border=True):
            st.markdown(f"### {headline}")
            st.write(summary)

            if top_mechanisms:
                primary = top_mechanisms[0]
                definition = primary.get("definition", "")
                if definition:
                    st.caption(definition)

    with top_right:
        with st.container(border=True):
            st.markdown("### Resumen del motor")
            st.write(f"**Mecanismos activos:** {len(active_mechanisms)}")
            st.write(f"**Mecanismos detectados:** {len(top_mechanisms)}")
            st.write(f"**Salidas disparadas:** {len(motor_result.get('outputs', []) or [])}")
            st.write(f"**Reglas no resueltas:** {len(unknown_rules)}")

    if top_outputs:
        col_a, col_b = st.columns(2, gap="large")
        with col_a:
            _render_output_group("Resumen ejecutivo", outputs_by_block.get("executive_summary", []))
        with col_b:
            _render_output_group("Interpretación clínica", outputs_by_block.get("clinical_interpretation", []))

        col_c, col_d = st.columns(2, gap="large")
        with col_c:
            _render_output_group("Acciones / seguimiento", outputs_by_block.get("followup", []) + outputs_by_block.get("nutrition_actions", []))
        with col_d:
            _render_output_group("Guardrails y prioridad", outputs_by_block.get("guardrails", []) + outputs_by_block.get("priority_signals", []))

    if top_mechanisms:
        c1, c2 = st.columns(2, gap="large")

        with c1:
            with st.container(border=True):
                st.markdown("### Ejes dominantes")
                for item in top_mechanisms[:3]:
                    label = item.get("label", item.get("mechanism_id", "—"))
                    activation = float(item.get("activation", 0.0))
                    status = _status_label(item.get("status", "—"))
                    system = item.get("system", "")

                    st.markdown(f"**{label}**")
                    st.write(f"Activación: {activation:.1f}/100 · Estado: {status}")
                    if system:
                        st.caption(system)

        with c2:
            with st.container(border=True):
                st.markdown("### Drivers principales")
                primary_evidence = top_mechanisms[0].get("evidence", []) or []
                driver_lines = _build_driver_lines(primary_evidence)

                if driver_lines:
                    for line in driver_lines:
                        st.write(f"- {line}")
                else:
                    st.write("Sin drivers trazables todavía.")

    if top_outputs:
        with st.expander("Ver salidas completas del motor", expanded=False):
            rows = []
            for item in motor_result.get("outputs", []) or []:
                rows.append(
                    {
                        "Bloque UI": item.get("ui_block", ""),
                        "Etiqueta": item.get("display_label", ""),
                        "Tipo": item.get("output_type", ""),
                        "Mecanismo": item.get("mechanism_label", ""),
                        "Activación": item.get("mechanism_activation", ""),
                        "Texto corto": item.get("short_text", ""),
                        "Seguimiento": item.get("followup", ""),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)

    if top_mechanisms:
        with st.expander("Ver evidencia técnica del motor", expanded=False):
            for item in top_mechanisms[:5]:
                label = item.get("label", item.get("mechanism_id", "—"))
                st.markdown(f"### {label}")

                evidence = item.get("evidence", []) or []
                if not evidence:
                    st.write("- Sin evidencia trazable")
                    continue

                rows = []
                for ev in evidence[:12]:
                    rows.append(
                        {
                            "Fuente": ev.get("source", ""),
                            "Tipo": ev.get("source_type", ""),
                            "Estado analito": ev.get("classification", ""),
                            "Impacto": ev.get("signal", ""),
                            "Regla": ev.get("rule_id", ""),
                        }
                    )

                st.dataframe(rows, use_container_width=True, hide_index=True)

    if unknown_rules:
        with st.expander("Reglas del motor no resueltas", expanded=False):
            st.dataframe(unknown_rules, use_container_width=True, hide_index=True)
