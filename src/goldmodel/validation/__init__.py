"""Validatielaag: toetst of een bufferregel doet wat hij belooft.

Gescheiden van ``simulate.py`` omdat validatie een andere vraag beantwoordt
dan simulatie. Een simulatie produceert getallen; deze laag stelt vast of die
getallen kloppen — en of de toets waarmee je dat vaststelt genoeg kracht heeft
om iets te kunnen afwijzen.
"""

from goldmodel.validation.coverage import (
    CoverageResult,
    christoffersen_independence_test,
    compare_buffer_rules,
    ewma_buffer,
    fixed_buffer,
    kupiec_pof_test,
    max_excursion_buffer,
    rolling_percentile_buffer,
    evaluate_coverage,
)

__all__ = [
    "CoverageResult",
    "christoffersen_independence_test",
    "compare_buffer_rules",
    "ewma_buffer",
    "fixed_buffer",
    "kupiec_pof_test",
    "max_excursion_buffer",
    "rolling_percentile_buffer",
    "evaluate_coverage",
]
