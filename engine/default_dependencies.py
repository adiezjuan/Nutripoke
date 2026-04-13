from core.engine.case_pipeline import EngineDependencies
from core.engine.derived_metrics import compute_derived, merge_values
from core.engine.reference_scoring import score_all_variables, get_reference_ranges
from core.engine.domain_scoring import score_domains
from core.engine.priority_evaluator import rank_domains
from core.engine.flags_confidence import (
    build_flags,
    confidence_level,
    summarize_profile_state,
)

from core.catalog.domain_master import DOMAIN_MASTER
from core.catalog.priority_rules import PRIORITY_RULES


def build_default_engine_dependencies() -> EngineDependencies:
    return EngineDependencies(
        compute_derived=compute_derived,
        merge_values=merge_values,
        score_all_variables=score_all_variables,
        score_domains=lambda all_values, variable_scores: score_domains(
            all_values,
            variable_scores,
            DOMAIN_MASTER,
        ),
        rank_domains=lambda domain_scores, all_values: rank_domains(
            domain_scores,
            all_values,
            PRIORITY_RULES,
        ),
        build_flags=lambda all_values: build_flags(
            all_values,
            get_reference_ranges(),
        ),
        confidence_level=confidence_level,
        summarize_profile_state=summarize_profile_state,
    )