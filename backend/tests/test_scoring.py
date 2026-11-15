import pytest

from app.benchmark.scoring import calculate_overall_score


WORKING_CRITERION_WEIGHTS = {
    "translation_accuracy": 0.30,
    "critical_information": 0.20,
    "conversational_latency": 0.20,
    "robustness": 0.15,
    "reliability": 0.15,
}


def test_overall_score_uses_configured_core_weights() -> None:
    criterion_scores = {
        "translation_accuracy": 85.0,
        "critical_information": 90.0,
        "conversational_latency": 75.0,
        "robustness": 80.0,
        "reliability": 95.0,
    }

    overall_score = calculate_overall_score(
        normalized_criterion_scores=criterion_scores,
        criterion_weights=WORKING_CRITERION_WEIGHTS,
    )

    assert overall_score == pytest.approx(84.75)


def test_overall_score_is_100_when_all_criteria_are_100() -> None:
    criterion_scores = {
        "translation_accuracy": 100.0,
        "critical_information": 100.0,
        "conversational_latency": 100.0,
        "robustness": 100.0,
        "reliability": 100.0,
    }

    overall_score = calculate_overall_score(
        normalized_criterion_scores=criterion_scores,
        criterion_weights=WORKING_CRITERION_WEIGHTS,
    )

    assert overall_score == pytest.approx(100.0)


def test_overall_score_is_0_when_all_criteria_are_0() -> None:
    criterion_scores = {
        "translation_accuracy": 0.0,
        "critical_information": 0.0,
        "conversational_latency": 0.0,
        "robustness": 0.0,
        "reliability": 0.0,
    }

    overall_score = calculate_overall_score(
        normalized_criterion_scores=criterion_scores,
        criterion_weights=WORKING_CRITERION_WEIGHTS,
    )

    assert overall_score == pytest.approx(0.0)


def test_scoring_rejects_weights_that_do_not_add_up_to_one() -> None:
    invalid_weights = {
        "translation_accuracy": 0.30,
        "critical_information": 0.20,
        "conversational_latency": 0.20,
        "robustness": 0.15,
        "reliability": 0.10,
    }

    criterion_scores = {
        "translation_accuracy": 85.0,
        "critical_information": 90.0,
        "conversational_latency": 75.0,
        "robustness": 80.0,
        "reliability": 95.0,
    }

    with pytest.raises(ValueError, match="must add up to 1.0"):
        calculate_overall_score(
            normalized_criterion_scores=criterion_scores,
            criterion_weights=invalid_weights,
        )


def test_scoring_rejects_missing_core_criterion() -> None:
    criterion_scores_without_robustness = {
        "translation_accuracy": 85.0,
        "critical_information": 90.0,
        "conversational_latency": 75.0,
        "reliability": 95.0,
    }

    with pytest.raises(ValueError, match="Missing core criterion scores"):
        calculate_overall_score(
            normalized_criterion_scores=criterion_scores_without_robustness,
            criterion_weights=WORKING_CRITERION_WEIGHTS,
        )


def test_scoring_rejects_criterion_score_above_100() -> None:
    criterion_scores = {
        "translation_accuracy": 101.0,
        "critical_information": 90.0,
        "conversational_latency": 75.0,
        "robustness": 80.0,
        "reliability": 95.0,
    }

    with pytest.raises(ValueError, match="must be between 0 and 100"):
        calculate_overall_score(
            normalized_criterion_scores=criterion_scores,
            criterion_weights=WORKING_CRITERION_WEIGHTS,
        )


def test_scoring_rejects_criterion_score_below_0() -> None:
    criterion_scores = {
        "translation_accuracy": 85.0,
        "critical_information": 90.0,
        "conversational_latency": -1.0,
        "robustness": 80.0,
        "reliability": 95.0,
    }

    with pytest.raises(ValueError, match="must be between 0 and 100"):
        calculate_overall_score(
            normalized_criterion_scores=criterion_scores,
            criterion_weights=WORKING_CRITERION_WEIGHTS,
        )


def test_overall_score_keeps_full_precision_until_output() -> None:
    criterion_scores = {
        "translation_accuracy": 83.333,
        "critical_information": 91.111,
        "conversational_latency": 78.456,
        "robustness": 88.888,
        "reliability": 97.777,
    }

    overall_score = calculate_overall_score(
        normalized_criterion_scores=criterion_scores,
        criterion_weights=WORKING_CRITERION_WEIGHTS,
    )

    assert overall_score == pytest.approx(86.91305)