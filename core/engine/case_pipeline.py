"""Orquestador base del caso.

Este módulo concentra la base analítica del sistema:
- entrada de datos
- derivados
- scoring por referencia
- scoring por dominio
- prioridad/ranking
- flags
- confianza

No renderiza UI.
No contiene narrativa final.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable
import math


def _make_json_safe(obj):
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


@dataclass
class EngineContext:
    values: dict[str, Any] = field(default_factory=dict)
    derived: dict[str, Any] = field(default_factory=dict)
    all_values: dict[str, Any] = field(default_factory=dict)
    variable_scores: dict[str, Any] = field(default_factory=dict)
    domain_scores: dict[str, Any] = field(default_factory=dict)
    ranked_domains: list[dict[str, Any]] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    confidence_label: str = "Baja"
    confidence_value: float = 0.0
    forced_domain: str | None = None
    forced_reason: str | None = None
    boost_reasons: list[str] = field(default_factory=list)
    profile_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _make_json_safe(asdict(self))


@dataclass
class EngineDependencies:
    compute_derived: Callable[[dict[str, Any]], dict[str, Any]]
    merge_values: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
    score_all_variables: Callable[[dict[str, Any]], dict[str, Any]]
    score_domains: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
    rank_domains: Callable[[dict[str, Any], dict[str, Any]], tuple[list[dict[str, Any]], Any, Any, Any]]
    build_flags: Callable[[dict[str, Any]], list[str]]
    confidence_level: Callable[[dict[str, Any]], tuple[str, float]]
    summarize_profile_state: Callable[[dict[str, Any]], dict[str, Any]] | None = None


class CasePipeline:
  #  \"\"\"Pipeline base del caso.\"\"\"

    def __init__(self, deps: EngineDependencies) -> None:
        self.deps = deps

    def run(self, values: dict[str, Any]) -> EngineContext:
        derived = self.deps.compute_derived(values)
        all_values = self.deps.merge_values(values, derived)
        variable_scores = self.deps.score_all_variables(all_values)
        domain_scores = self.deps.score_domains(all_values, variable_scores)
        ranked_domains, forced_domain, forced_reason, boost_reasons = self.deps.rank_domains(
            domain_scores, all_values
        )
        flags = self.deps.build_flags(all_values)
        confidence_label, confidence_value = self.deps.confidence_level(domain_scores)
        profile_state = (
            self.deps.summarize_profile_state(variable_scores)
            if self.deps.summarize_profile_state is not None
            else {}
        )

        return EngineContext(
            values=values,
            derived=derived,
            all_values=all_values,
            variable_scores=variable_scores,
            domain_scores=domain_scores,
            ranked_domains=ranked_domains,
            flags=flags,
            confidence_label=confidence_label,
            confidence_value=confidence_value,
            forced_domain=forced_domain,
            forced_reason=forced_reason,
            boost_reasons=list(boost_reasons or []),
            profile_state=profile_state,
        )