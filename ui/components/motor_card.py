import streamlit as st


SEVERITY_TO_CONTAINER = {
    "danger": st.error,
    "warning": st.warning,
    "info": st.info,
    "success": st.success,
}


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
    if value >= 45:
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
    solidity = str(primary.get("solidity", "")).lower()

    headline = f"Predomina {primary_label}"
    body = (
        f"El motor sitúa **{primary_label}** como eje dominante, con activación **{primary_bucket.lower()}** "
        f"({primary_activation:.1f}/100) y solidez **{solidity or 'sin definir'}**."
    )

    if len(top_mechanisms) > 1:
        secondary = top_mechanisms[1]
        secondary_label = secondary.get("label", secondary.get("mechanism_id", "—"))
        secondary_activation = float(secondary.get("activation", 0.0))
        if secondary_activation > 0:
            body += f" El patrón asociado más relevante es **{secondary_label}** ({secondary_activation:.1f}/100)."
    return headline, body


def _driver_label(ev: dict) -> str:
    source = ev.get("source", "—")
    classification = ev.get("classification", "")
    signal = float(ev.get("signal", 0.0) or 0.0)
    if classification:
        return f"{source} · {classification} · impacto {signal:.1f}"
    return f"{source} · impacto {signal:.1f}"


def _build_driver_lines(evidence: list[dict]) -> list[str]:
    variable_rows = [ev for ev in evidence if ev.get("source_type") == "variable"]
    variable_rows.sort(key=lambda ev: float(ev.get("signal", 0.0) or 0.0), reverse=True)
    return [_driver_label(ev) for ev in variable_rows[:5]]


def _build_associated_patterns(top_mechanisms: list[dict]) -> list[str]:
    rows = []
    for item in top_mechanisms[1:3]:
        label = item.get("label", item.get("mechanism_id", "—"))
        activation = float(item.get("activation", 0.0) or 0.0)
        solidity = item.get("solidity", "")
        rows.append(f"{label} · {activation:.1f}/100 · solidez {str(solidity).lower()}")
    return rows


def _render_output_item(item: dict):
    label = item.get("display_label", item.get("output_key", "—"))
    short_text = item.get("short_text", "")
    long_text = item.get("long_text", "")
    followup = item.get("followup", "")
    mech = item.get("mechanism_label", item.get("mechanism_id", "—"))
    activation = float(item.get("mechanism_activation", 0.0) or 0.0)

    st.markdown(f"**{label}**")
    if short_text:
        st.write(short_text)
    if long_text:
        st.caption(long_text)
    st.caption(f"Fuente: {mech} · activación {activation:.1f}/100")
    if followup:
        st.write(f"Siguiente paso: {followup}")


def _render_priority_outputs(top_outputs: list[dict]):
    with st.container(border=True):
        st.markdown("### Qué significa")
        if not top_outputs:
            st.write("Sin salidas priorizadas todavía.")
            return
        for item in top_outputs[:3]:
            _render_output_item(item)


def _render_next_steps(top_outputs: list[dict]):
    with st.container(border=True):
        st.markdown("### Qué haría ahora")
        if not top_outputs:
            st.write("Completar más variables clave y repetir la lectura al ampliar cobertura.")
            return
        for item in top_outputs[:3]:
            followup = item.get("followup", "")
            if followup:
                st.write(f"- {followup}")


def _render_coherence_summary(item: dict):
    coherence = item.get("coherence", {}) or {}
    passes = bool(coherence.get("passes", False))
    hit_count = int(coherence.get("hit_count", 0) or 0)
    group_count = int(coherence.get("group_count", 0) or 0)
    primary_hits = int(coherence.get("primary_hits", 0) or 0)
    has_primary = bool(coherence.get("has_primary_driver", False))
    groups_seen = coherence.get("groups_seen", []) or []
    unmet = coherence.get("unmet_requirements", []) or []
    rationale = coherence.get("clinical_rationale", []) or []

    if passes:
        st.success("Coherencia robusta para presentarlo como mecanismo principal.")
    else:
        st.warning("Lectura parcial: la señal existe, pero la convergencia fisiológica aún es limitada.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Señales", str(hit_count))
    c2.metric("Grupos", str(group_count))
    c3.metric("Drivers core", str(primary_hits))
    c4.metric("Driver principal", "Sí" if has_primary else "No")

    if groups_seen:
        st.caption("Convergencia por grupos: " + " · ".join(groups_seen))
    if rationale:
        st.caption("Racional clínico: " + " · ".join(rationale[:3]))
    if unmet:
        st.caption("Pendiente para ganar solidez: " + " · ".join(unmet))


def render_motor_card(motor_result: dict):
    st.markdown("## Explicación fisiológica")

    top_mechanisms = motor_result.get("top_mechanisms", []) or []
    active_mechanisms = motor_result.get("active_mechanisms", []) or []
    unknown_rules = motor_result.get("unknown_rules", []) or []
    all_outputs = motor_result.get("outputs", []) or []
    top_outputs = motor_result.get("top_outputs", []) or []

    headline, summary = _build_headline(top_mechanisms)

    top_left, top_right = st.columns([1.8, 1.0], gap="large")

    with top_left:
        with st.container(border=True):
            st.markdown(f"### {headline}")
            st.write(summary)
            if top_mechanisms:
                primary = top_mechanisms[0]
                definition = primary.get("definition", "")
                if definition:
                    st.caption(definition)
                clinical_notes = primary.get("clinical_notes", "")
                if clinical_notes:
                    st.caption(clinical_notes)

    with top_right:
        with st.container(border=True):
            st.markdown("### Resumen del motor")
            st.write(f"**Mecanismos activos:** {len(active_mechanisms)}")
            st.write(f"**Lecturas visibles:** {len(top_mechanisms)}")
            st.write(f"**Salidas priorizadas:** {len(all_outputs)}")
            st.write(f"**Reglas no resueltas:** {len(unknown_rules)}")

    if top_mechanisms:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            with st.container(border=True):
                st.markdown("### Por qué predomina")
                driver_lines = _build_driver_lines(top_mechanisms[0].get("evidence", []) or [])
                if driver_lines:
                    for line in driver_lines:
                        st.write(f"- {line}")
                else:
                    st.write("Sin drivers trazables todavía.")

        with c2:
            with st.container(border=True):
                st.markdown("### Qué compite con esto")
                rows = _build_associated_patterns(top_mechanisms)
                if rows:
                    for line in rows:
                        st.write(f"- {line}")
                else:
                    st.write("No aparecen patrones asociados de peso.")

    if top_mechanisms:
        c3, c4 = st.columns(2, gap="large")
        with c3:
            with st.container(border=True):
                st.markdown("### Nivel de solidez")
                primary = top_mechanisms[0]
                st.write(f"**Solidez global:** {primary.get('solidity', '—')}")
                st.write(f"**Activación final:** {float(primary.get('activation', 0.0) or 0.0):.1f}/100")
                st.write(f"**Evidencia directa:** {float(primary.get('evidence_strength', 0.0) or 0.0):.1f}/100")
                st.write(f"**Arrastre de red:** {float(primary.get('support_strength', 0.0) or 0.0):.1f}/100")
        with c4:
            _render_priority_outputs(top_outputs)

    if top_mechanisms:
        with st.container(border=True):
            st.markdown("### Coherencia del mecanismo principal")
            _render_coherence_summary(top_mechanisms[0])

    if top_outputs:
        _render_next_steps(top_outputs)

    if all_outputs:
        with st.expander("Ver salidas completas del motor", expanded=False):
            rows = []
            for item in all_outputs:
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
        with st.expander("Ver ranking completo de mecanismos", expanded=False):
            rows = []
            for item in motor_result.get("mechanisms", []) or []:
                coherence = item.get("coherence", {}) or {}
                rows.append(
                    {
                        "Mecanismo": item.get("label", item.get("mechanism_id", "")),
                        "Estado": _status_label(item.get("status", "")),
                        "Activación": item.get("activation", ""),
                        "Base": item.get("activation_raw", ""),
                        "Solidez": item.get("solidity", ""),
                        "Coherente": coherence.get("passes", False),
                        "Señales": coherence.get("hit_count", 0),
                        "Grupos": coherence.get("group_count", 0),
                        "Drivers core": coherence.get("primary_hits", 0),
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
                            "Rol": ev.get("role", ""),
                            "Grupo": ev.get("combo_group", ""),
                            "Primary": ev.get("is_primary", False),
                        }
                    )
                st.dataframe(rows, use_container_width=True, hide_index=True)

    if unknown_rules:
        with st.expander("Reglas del motor no resueltas", expanded=False):
            st.dataframe(unknown_rules, use_container_width=True, hide_index=True)
