import numpy as np
import streamlit as st


def parse_float_or_nan(raw: str) -> float:
    raw = (raw or "").strip().replace(",", ".")
    if raw == "":
        return np.nan
    try:
        return float(raw)
    except ValueError:
        return np.nan


def group_by_level(schema):
    groups = {"essential": [], "precision": [], "advanced": []}
    for item in schema:
        lvl = item.get("level", "advanced")
        groups.setdefault(lvl, []).append(item)
    return groups


def load_default_input_state(schema, get_default_value_fn):
    for item in schema:
        key = item["key"]
        default_value = get_default_value_fn(key)
        if default_value is not None:
            st.session_state[f"inp_{key}"] = default_value


def reset_input_state(schema, get_default_value_fn):
    for item in schema:
        st.session_state.pop(f"inp_{item['key']}", None)
    load_default_input_state(schema, get_default_value_fn)


def load_demo_input_state(schema, get_demo_value_fn):
    for item in schema:
        key = item["key"]
        demo_value = get_demo_value_fn(key)
        if demo_value is not None:
            st.session_state[f"inp_{key}"] = demo_value


def _render_field(item, get_default_value_fn):
    key = item["key"]
    label = item["label"]
    unit = item.get("unit", "")
    input_type = item.get("input_type", "number")

    if input_type == "select":
        options = item.get("options", [])
        option_labels = item.get("option_labels", {})
        shown = [option_labels.get(opt, opt) for opt in options]

        current_value = st.session_state.get(f"inp_{key}")
        if current_value in options:
            default_index = options.index(current_value)
        else:
            default_value = "M" if "M" in options else options[0]
            default_index = options.index(default_value)

        selected = st.selectbox(
            label,
            shown,
            index=default_index,
            key=f"inp_{key}",
        )
        reverse = {option_labels.get(opt, opt): opt for opt in options}
        return reverse[selected]

    default_value = st.session_state.get(f"inp_{key}", get_default_value_fn(key))
    raw = st.text_input(
        f"{label} ({unit})" if unit else label,
        value=str(default_value) if default_value is not None else "",
        key=f"inp_{key}",
        placeholder="vacío = desconocido",
    )
    return parse_float_or_nan(raw)


def render_input_controls_main(schema, get_default_value_fn, get_demo_value_fn):
    st.markdown("## Entrada de datos")

    c1, c2, c3, c4, c5, c6 = st.columns([1.2, 1, 1, 1.1, 0.8, 0.8])

    with c1:
        unit_mode = st.radio("Unidades", ["mg/dL", "mmol/L"], horizontal=True)

    with c2:
        alcohol = st.selectbox("Alcohol", ["No", "Ocasional", "Frecuente"], index=1)

    with c3:
        sleep = st.selectbox("Sueño", ["Bueno", "Irregular", "Malo"], index=0)

    with c4:
        meds = st.checkbox("Medicación crónica", value=False)

    with c5:
        reset_clicked = st.button("Reset", use_container_width=True)

    with c6:
        demo_clicked = st.button("Demo", use_container_width=True)

    if reset_clicked:
        reset_input_state(schema, get_default_value_fn)
        st.rerun()

    if demo_clicked:
        load_demo_input_state(schema, get_demo_value_fn)
        st.rerun()

    st.caption("Introduce los datos clínicos en la ventana principal. Reset carga un perfil neutro; Demo carga un caso alterado.")
    st.markdown("---")

    levels = group_by_level(schema)
    tabs = st.tabs(["Essential", "Precision", "Advanced"])

    values = {}

    def render_level(tab, items, cols=3):
        with tab:
            cols_list = st.columns(cols)
            for idx, item in enumerate(items):
                with cols_list[idx % cols]:
                    values[item["key"]] = _render_field(item, get_default_value_fn)

    render_level(tabs[0], levels["essential"])
    render_level(tabs[1], levels["precision"])
    render_level(tabs[2], levels["advanced"])

    return {
        "values": values,
        "unit_mode": unit_mode,
        "alcohol": alcohol,
        "sleep": sleep,
        "meds": meds,
    }
