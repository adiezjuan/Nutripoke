"""Ensambla la salida final para UI."""

from __future__ import annotations

from typing import Any


MIN_DOMAIN_SCORE = 5.0


def _mechanism_summary_line(item: dict) -> str:
    label = item.get("label", item.get("mechanism_id", "señal mecanística"))
    activation = float(item.get("activation", 0.0) or 0.0)
    solidity = item.get("solidity", "")
    extras = []
    if activation > 0:
        extras.append(f"{activation:.1f}/100")
    if solidity:
        extras.append(f"solidez {solidity.lower()}")
    suffix = f" ({', '.join(extras)})" if extras else ""
    return f"{label}{suffix}"


def assemble_case_view(engine_context: Any, motor_result: dict | None = None) -> dict:
    profile_state = getattr(engine_context, "profile_state", {}) or {}
    ranked_domains = getattr(engine_context, "ranked_domains", []) or []
    forced_domain = getattr(engine_context, "forced_domain", None)
    forced_reason = getattr(engine_context, "forced_reason", None)
    boost_reasons = getattr(engine_context, "boost_reasons", []) or []
    confidence_label = getattr(engine_context, "confidence_label", "—")

    motor_result = motor_result or {}
    top_mechanisms = motor_result.get("top_mechanisms", []) or []
    top_outputs = motor_result.get("top_outputs", []) or []

    headline = "Sin definir"
    summary = "Todavía no hay suficiente información para una lectura robusta."
    next_step = "Completar más analitos clave y seguir poblando la capa canónica."

    all_normal = profile_state.get("all_normal", False)

    if all_normal:
        headline = "Sin alteraciones relevantes"
        summary = "Todas las variables medidas están dentro de rango. No aparece un dominio dominante ni un mecanismo robusto."
        next_step = "Mantener seguimiento evolutivo."
    elif top_mechanisms:
        primary = top_mechanisms[0]
        headline = primary.get("label", primary.get("mechanism_id", "Sin definir"))
        summary = (
            f"Predomina {_mechanism_summary_line(primary)}. "
            f"La lectura integra la capa canónica con la red mecanística para priorizar convergencia y no solo intensidad."
        )
        if len(top_mechanisms) > 1:
            summary += f" Se asocia además a {_mechanism_summary_line(top_mechanisms[1])}."
        if top_outputs:
            summary += f" La salida prioritaria es: {top_outputs[0].get('short_text', top_outputs[0].get('display_label', 'sin definir'))}"
        next_step = top_outputs[0].get("followup") or "Confirmar drivers principales, completar cobertura y revisar evolución clínica."
    elif ranked_domains and float(ranked_domains[0].get("score", 0.0)) >= MIN_DOMAIN_SCORE:
        top = ranked_domains[0]
        headline = top.get("label", "Sin definir")
        summary = (
            f"El caso apunta de forma preliminar a {top.get('label', 'un dominio dominante')}, "
            f"con score ajustado {float(top.get('score', 0.0)):.1f} "
            f"y cobertura {100.0 * float(top.get('coverage', 0.0) or 0.0):.0f}%."
        )

    return {
        "headline": headline,
        "summary": summary,
        "next_step": next_step,
        "confidence_label": confidence_label,
        "measured_count": profile_state.get("measured_count", 0),
        "abnormal_count": profile_state.get("abnormal_count", 0),
        "top_domains": ranked_domains[:3],
        "top_mechanisms": top_mechanisms[:3],
        "top_outputs": top_outputs[:3],
        "forced_domain_label": forced_domain.get("label") if isinstance(forced_domain, dict) else forced_domain,
        "forced_reason": forced_reason,
        "boost_reasons": boost_reasons,
    }
