DOMAIN_MASTER = {
    "glucose_regulation": {
        "label": "Regulación glucémica",
        "definition": "Homeostasis de glucosa, insulina y control glucémico.",
        "priority_override": False,
        "variables": [
            {"key": "glucose_mg_dl", "weight": 1.0, "role": "core"},
            {"key": "insulin_uIU_ml", "weight": 0.9, "role": "core"},
            {"key": "homa_ir", "weight": 0.9, "role": "derived"},
            {"key": "hba1c_pct", "weight": 1.0, "role": "core"},
        ],
    },
    "atherogenic_lipids": {
        "label": "Dislipidemia aterogénica",
        "definition": "Perfil lipídico aterogénico y riesgo metabólico asociado.",
        "priority_override": False,
        "variables": [
            {"key": "chol_total_mg_dl", "weight": 0.6, "role": "support"},
            {"key": "hdl_mg_dl", "weight": 0.9, "role": "core"},
            {"key": "triglycerides_mg_dl", "weight": 1.0, "role": "core"},
            {"key": "non_hdl_mg_dl", "weight": 0.8, "role": "derived"},
            {"key": "tg_hdl_ratio", "weight": 0.9, "role": "derived"},
        ],
    },
    "inflammatory_tone": {
        "label": "Tono inflamatorio",
        "definition": "Inflamación de bajo grado y señal inflamatoria sistémica.",
        "priority_override": False,
        "variables": [
            {"key": "hscrp_mg_l", "weight": 1.0, "role": "core"},
            {"key": "ferritin_ng_ml", "weight": 0.5, "role": "support"},
            {"key": "nlr", "weight": 0.7, "role": "derived"},
        ],
    },
    "hepatic_load": {
        "label": "Carga hepática",
        "definition": "Estrés hepatometabólico y señal de carga hepática.",
        "priority_override": False,
        "variables": [
            {"key": "alt_u_l", "weight": 1.0, "role": "core"},
            {"key": "ast_u_l", "weight": 0.8, "role": "support"},
            {"key": "ggt_u_l", "weight": 0.9, "role": "core"},
            {"key": "uric_acid_mg_dl", "weight": 0.4, "role": "support"},
        ],
    },
    "micronutrient_status": {
        "label": "Estado micronutricional",
        "definition": "Reserva o insuficiencia de micronutrientes clave.",
        "priority_override": False,
        "variables": [
            {"key": "vitamin_d_ng_ml", "weight": 1.0, "role": "core"},
            {"key": "ferritin_ng_ml", "weight": 0.6, "role": "support"},
        ],
    },
    "renal_uric_axis": {
        "label": "Eje renal-úrico",
        "definition": "Filtrado renal básico y tendencia hiperuricémica.",
        "priority_override": False,
        "variables": [
            {"key": "creatinine_mg_dl", "weight": 0.9, "role": "core"},
            {"key": "uric_acid_mg_dl", "weight": 1.0, "role": "core"},
        ],
    },
}