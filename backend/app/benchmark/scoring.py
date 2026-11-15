"""Calculate the provider-independent overall benchmark score."""

from collections.abc import Mapping
from math import isclose, isfinite


CORE_CRITERIA = (
    "translation_accuracy",
    "critical_information",
    "conversational_latency",
    "robustness",
    "reliability",
)


def calculate_overall_score(
    normalized_criterion_scores: Mapping[str, float],
    criterion_weights: Mapping[str, float],
) -> float:
    """
    calculate weighted overall score from normalized core criterion scores

    -all criterion scores must be between 0 and 100
    -all criterion weights must add up to 1.0
    """
    _validate_criterion_scores(normalized_criterion_scores)
    _validate_criterion_weights(criterion_weights)

    return sum(
        normalized_criterion_scores[criterion_name]
        * criterion_weights[criterion_name]
        for criterion_name in CORE_CRITERIA
    )


def _validate_criterion_scores(
    normalized_criterion_scores: Mapping[str, float],
) -> None:
    required_criteria = set(CORE_CRITERIA)
    provided_criteria = set(normalized_criterion_scores)

    missing_criteria = required_criteria - provided_criteria
    if missing_criteria:
        raise ValueError(
            f"Missing core criterion scores: {sorted(missing_criteria)}"
        )

    unexpected_criteria = provided_criteria - required_criteria
    if unexpected_criteria:
        raise ValueError(
            f"Unexpected criterion scores: {sorted(unexpected_criteria)}"
        )

    for criterion_name in CORE_CRITERIA:
        criterion_score = normalized_criterion_scores[criterion_name]

        if not isinstance(criterion_score, (int, float)) or isinstance(
            criterion_score, bool
        ):
            raise TypeError(
                f"Criterion score '{criterion_name}' must be a number."
            )

        if not isfinite(criterion_score):
            raise ValueError(
                f"Criterion score '{criterion_name}' must be finite."
            )

        if not 0 <= criterion_score <= 100:
            raise ValueError(
                f"Criterion score '{criterion_name}' must be between 0 and 100."
            )


def _validate_criterion_weights(
    criterion_weights: Mapping[str, float],
) -> None:
    required_criteria = set(CORE_CRITERIA)
    provided_criteria = set(criterion_weights)

    missing_criteria = required_criteria - provided_criteria
    if missing_criteria:
        raise ValueError(
            f"Missing criterion weights: {sorted(missing_criteria)}"
        )

    unexpected_criteria = provided_criteria - required_criteria
    if unexpected_criteria:
        raise ValueError(
            f"Unexpected criterion weights: {sorted(unexpected_criteria)}"
        )

    for criterion_name in CORE_CRITERIA:
        criterion_weight = criterion_weights[criterion_name]

        if not isinstance(criterion_weight, (int, float)) or isinstance(
            criterion_weight, bool
        ):
            raise TypeError(
                f"Criterion weight '{criterion_name}' must be a number."
            )

        if not isfinite(criterion_weight):
            raise ValueError(
                f"Criterion weight '{criterion_name}' must be finite."
            )

        if not 0 <= criterion_weight <= 1:
            raise ValueError(
                f"Criterion weight '{criterion_name}' must be between 0 and 1."
            )

    total_weight = sum(criterion_weights.values())

    if not isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(
            f"Criterion weights must add up to 1.0, but add up to {total_weight}."
        )