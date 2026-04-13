PRIORITY_RULES = [
    {
        "type": "boost",
        "domain": "glucose_regulation",
        "priority": 10,
        "boost": 8,
        "reason": "Señal glucémica coherente por glucosa y HbA1c.",
        "conditions": [
            {"key": "glucose_mg_dl", "op": ">=", "value": 100},
            {"key": "hba1c_pct", "op": ">=", "value": 5.7},
        ],
    },
    {
        "type": "boost",
        "domain": "glucose_regulation",
        "priority": 20,
        "boost": 12,
        "reason": "Eje glucosa-insulina reforzado por HOMA-IR elevado.",
        "conditions": [
            {"key": "glucose_mg_dl", "op": ">=", "value": 100},
            {"any": [
                {"key": "insulin_uIU_ml", "op": ">=", "value": 15},
                {"key": "homa_ir", "op": ">=", "value": 2.5},
            ]},
        ],
    },
    {
        "type": "boost",
        "domain": "atherogenic_lipids",
        "priority": 10,
        "boost": 10,
        "reason": "Patrón lipídico aterogénico por TG altos y HDL bajo.",
        "conditions": [
            {"key": "triglycerides_mg_dl", "op": ">=", "value": 150},
            {"key": "hdl_mg_dl", "op": "<", "value": 40},
        ],
    },
    {
        "type": "override",
        "domain": "glucose_regulation",
        "priority": 100,
        "reason": "Patrón glucometabólico dominante claramente establecido.",
        "conditions": [
            {"key": "glucose_mg_dl", "op": ">=", "value": 110},
            {"key": "hba1c_pct", "op": ">=", "value": 5.9},
            {"any": [
                {"key": "insulin_uIU_ml", "op": ">=", "value": 18},
                {"key": "homa_ir", "op": ">=", "value": 4.0},
            ]},
        ],
    },
]