import math
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.catalog.lab_schema_v3 import SCHEMA_V3
from core.engine.case_pipeline import CasePipeline
from core.engine.default_dependencies import build_default_engine_dependencies
from core.engine.reference_scoring import get_reference_config, get_reference_ranges
from core.motor.dynamic_network import run_dynamic_projection
from core.presentation.case_assembler import assemble_case_view

from ui.components.input_panel import render_input_controls_main
from ui.components.case_header import render_case_header
from ui.components.canonical_card import render_canonical_card
from ui.components.motor_card import render_motor_card
# from ui.components.variable_alerts_card import render_variable_alerts_card

from core.presentation.pokemon_mapper import build_pokemon_card
from core.presentation.pokemon_image_generator import generate_pokemon_card_image
from ui.components.render_pokemon_mode import render_pokemon_mode

st.set_page_config(page_title="Nutri New", layout="wide")
st.title("Nutri New")
st.caption("Arquitectura limpia en construcción: una capa decide, las demás justifican.")


def get_default_input_value(key: str):
    static_defaults = {
        "age_years": "45",
        "sex": "M",
    }
    if key in static_defaults:
        return static_defaults[key]

    reference_ranges = get_reference_ranges()
    neutral_context = {"sex": "M", "age_years": 45}
    ref = get_reference_config(key, neutral_context, reference_ranges)
    if not ref:
        return ""

    target = ref.get("target_default")
    if target is None:
        return ""

    return str(target)


def get_demo_input_value(key: str):
    demo = {
        "age_years": "47",
        "sex": "M",

        "bmi_kg_m2": "27.4",
        "waist_cm": "98",

        "hscrp_mg_l": "2.6",
        "esr_mm_h": "14",
        "fibrinogen_mg_dl": "360",
        "wbc_x10_3_mm3": "6.8",
        "neut_abs_x10_3_mm3": "4.1",
        "lymph_abs_x10_3_mm3": "1.9",

        "glucose_mg_dl": "102",
        "hba1c_pct": "5.7",
        "insulin_uIU_ml": "11",

        "chol_total_mg_dl": "214",
        "ldl_mg_dl": "138",
        "hdl_mg_dl": "43",
        "triglycerides_mg_dl": "168",
        "apob_mg_dl": "108",

        "hb_g_dl": "14.2",
        "hct_pct": "42.3",
        "rbc_x10_6_mm3": "4.8",
        "mcv_fl": "89",
        "rdw_pct": "13.8",
        "ferritin_ng_ml": "126",
        "iron_ug_dl": "92",
        "transferrin_mg_dl": "284",
        "transferrin_sat_pct": "24",
        "tibc_ug_dl": "370",
        "vitb12_pg_ml": "410",
        "folate_ng_ml": "7.2",
        "platelets_x10_3_uL": "248",

        "alt_u_l": "34",
        "ast_u_l": "28",
        "ggt_u_l": "31",
        "alp_u_l": "79",
        "bilirubin_total_mg_dl": "0.8",
        "albumin_g_dl": "4.4",

        "creatinine_mg_dl": "0.98",
        "egfr_ml_min_1_73m2": "92",
        "uric_acid_mg_dl": "6.7",
        "urea_mg_dl": "34",

        "tsh_mIU_l": "2.1",
        "ft4_ng_dl": "1.1",
    }
    return demo.get(key)


def make_json_safe(obj):
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return [make_json_safe(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


def to_case_dict(case_result):
    if hasattr(case_result, "to_dict"):
        return case_result.to_dict()
    return case_result


def normalize_view_model(case_result, view_model):
    case_dict = to_case_dict(case_result)
    profile_state = case_dict.get("profile_state", {}) or {}
    ranked_domains = case_dict.get("ranked_domains", []) or []
    forced_domain = case_dict.get("forced_domain")
    forced_reason = case_dict.get("forced_reason")
    boost_reasons = case_dict.get("boost_reasons", []) or []

    if not isinstance(view_model, dict):
        view_model = {}

    if "headline" not in view_model:
        if profile_state.get("all_normal"):
            view_model["headline"] = "Sin alteraciones relevantes"
        elif ranked_domains:
            view_model["headline"] = ranked_domains[0].get("label", "Sin definir")
        else:
            view_model["headline"] = "Sin definir"

    if "summary" not in view_model:
        if profile_state.get("all_normal"):
            view_model["summary"] = (
                "Todas las variables medidas están dentro de rango. "
                "No aparece una señal fisiopatológica dominante."
            )
        elif ranked_domains:
            top = ranked_domains[0]
            view_model["summary"] = (
                f"El caso apunta de forma preliminar a {top.get('label', 'un dominio dominante')}, "
                f"con score {float(top.get('score', 0.0)):.1f}."
            )
        else:
            view_model["summary"] = "Todavía no hay suficiente información para una lectura robusta."

    if "next_step" not in view_model:
        if profile_state.get("all_normal"):
            view_model["next_step"] = "Mantener el control evolutivo y repetir analítica según contexto clínico."
        else:
            view_model["next_step"] = "Completar más analitos clave y seguir poblando la capa canónica."

    view_model["confidence_label"] = case_dict.get(
        "confidence_label",
        view_model.get("confidence_label", "—"),
    )
    view_model["measured_count"] = profile_state.get(
        "measured_count",
        view_model.get("measured_count", 0),
    )
    view_model["abnormal_count"] = profile_state.get(
        "abnormal_count",
        view_model.get("abnormal_count", 0),
    )
    view_model["top_domains"] = ranked_domains[:3]
    view_model["forced_domain_label"] = (
        forced_domain.get("label") if isinstance(forced_domain, dict) else forced_domain
    )
    view_model["forced_reason"] = forced_reason
    view_model["boost_reasons"] = boost_reasons

    return view_model


# -----------------------------
# Inputs
# -----------------------------
input_state = render_input_controls_main(
    schema=SCHEMA_V3,
    get_default_value_fn=get_default_input_value,
    get_demo_value_fn=get_demo_input_value,
)
modo_lectura = st.radio(
    "Modo de lectura",
    ["Clásico", "Pokémon"],
    horizontal=True,
)
pokemon_mode = modo_lectura == "Pokémon"
values = dict(input_state["values"])
values["alcohol"] = input_state["alcohol"]
values["sleep"] = input_state["sleep"]
values["meds"] = input_state["meds"]


# -----------------------------
# Engine
# -----------------------------
pipeline = CasePipeline(build_default_engine_dependencies())
case_result = pipeline.run(values)
motor_result = run_dynamic_projection(case_result.all_values, case_result.variable_scores)

profile_state = case_result.profile_state or {}
if profile_state.get("all_normal"):
    motor_result["mechanisms"] = []
    motor_result["top_mechanisms"] = []
    motor_result["active_mechanisms"] = []
    motor_result["activation_map"] = {}
    motor_result["outputs"] = []
    motor_result["outputs_by_block"] = {}
    motor_result["outputs_by_type"] = {}
    motor_result["top_outputs"] = []
    motor_result["all_normal"] = True


# -----------------------------
# View model
# -----------------------------
try:
    raw_view_model = assemble_case_view(case_result, motor_result)
    view_model = normalize_view_model(case_result, raw_view_model)
except Exception as exc:
    st.warning(
        "El ensamblador todavía está verde. "
        f"Se usa una vista de respaldo. Detalle: {exc}"
    )
    view_model = normalize_view_model(case_result, {})


# -----------------------------
# Main UI
# -----------------------------
# -----------------------------
# Main UI
# -----------------------------
st.markdown("---")
render_case_header(view_model)

if pokemon_mode:
    try:
        variable_scores = getattr(case_result, "variable_scores", {}) or {}

        payload = {
            "nube": {
                "variables_clave": [
                    {
                        "key": key,
                        "value": info.get("value"),
                        "classification": info.get("classification"),
                    }
                    for key, info in variable_scores.items()
                    if isinstance(info, dict)
                ]
            },
            "outputs": motor_result.get("outputs", []) or [],
        }

        pokemon_card = build_pokemon_card(payload)

        image_path = generate_pokemon_card_image(
            pokemon_card,
            output_path=str(PROJECT_ROOT / "outputs" / "pokemon_final.png"),
        )
        pokemon_card["image_path"] = image_path

        render_pokemon_mode(
            pokemon_card,
            section_title="Modo Pokémon",
            show_debug=False,
        )

    except Exception as exc:
        st.warning(
            "El modo Pokémon todavía está verde. "
            f"Se usa la vista clásica como respaldo. Detalle: {exc}"
        )
        render_canonical_card(view_model)
        render_motor_card(motor_result)
else:
    render_canonical_card(view_model)
    render_motor_card(motor_result)
# -----------------------------
# Debug / traceability
# -----------------------------
show_debug = st.toggle("Mostrar trazabilidad técnica", value=False)
if show_debug:
    st.markdown("## Trazabilidad técnica")

    case_dict = to_case_dict(case_result)
    profile_state = case_dict.get("profile_state", {}) or {}
    variable_scores = case_dict.get("variable_scores", {}) or {}

    abnormal_rows = []
    for key, info in variable_scores.items():
        classification = info.get("classification", "missing")
        if classification in {"high", "low", "critical_high", "critical_low"}:
            abnormal_rows.append(
                {
                    "Variable": key,
                    "Estado": classification,
                    "Valor": info.get("value"),
                    "Score": info.get("score"),
                    "Nota": info.get("note", ""),
                }
            )

    with st.expander("Resumen técnico", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Medidas", profile_state.get("measured_count", 0))
        c2.metric("Fuera de rango", profile_state.get("abnormal_count", 0))
        c3.metric("Confianza", case_dict.get("confidence_label", "—"))
        c4.metric("Mecanismos activos", len(motor_result.get("active_mechanisms", []) or []))

    with st.expander("Variables fuera de rango", expanded=True):
        if abnormal_rows:
            st.dataframe(abnormal_rows, use_container_width=True, hide_index=True)
        else:
            st.success("No hay variables fuera de rango.")

    with st.expander("Mecanismos detectados", expanded=False):
        mech_rows = []
        for item in motor_result.get("mechanisms", []) or []:
            mech_rows.append(
                {
                    "Mecanismo": item.get("label", item.get("mechanism_id", "")),
                    "Activación": item.get("activation", 0),
                    "Estado": item.get("status", ""),
                    "Sistema": item.get("system", ""),
                }
            )
        if mech_rows:
            st.dataframe(mech_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Sin mecanismos detectables.")

    with st.expander("Evidencia del mecanismo principal", expanded=False):
        top_mechs = motor_result.get("top_mechanisms", []) or []
        if top_mechs:
            evidence = top_mechs[0].get("evidence", []) or []
            rows = []
            for ev in evidence:
                rows.append(
                    {
                        "Fuente": ev.get("source", ""),
                        "Tipo": ev.get("source_type", ""),
                        "Clasificación": ev.get("classification", ""),
                        "Impacto": ev.get("signal", ""),
                        "Regla": ev.get("rule_id", ""),
                    }
                )
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("Sin evidencia trazable.")
        else:
            st.info("Sin mecanismo principal.")

    with st.expander("JSON completo de desarrollo", expanded=False):
        st.caption("Solo para depuración profunda.")
        st.json(
            {
                "view_model": make_json_safe(view_model),
                "case_result": make_json_safe(case_dict),
                "motor_result": make_json_safe(motor_result),
            }
        )