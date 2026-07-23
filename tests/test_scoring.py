import pytest

from votecastbench.scoring import aggregate_scores, score_forecast

QUESTION = {
    "question_id": "q1",
    "forecast_as_of": "2026-05-01T23:59:59+01:00",
    "question": "Who will win?",
    "election": {"seats": 1, "voting_system": "FPTP"},
    "candidates": [
        {"candidate_id": "a", "name": "A"},
        {"candidate_id": "b", "name": "B"},
        {"candidate_id": "c", "name": "C"},
    ],
}
LABEL = {
    "question_id": "q1",
    "winner_candidate_id": "b",
    "votes": {"a": 25, "b": 60, "c": 15},
    "turnout_percentage": 48.0,
}


def test_multiclass_brier_is_sum_over_candidates() -> None:
    forecast = {
        "winner_probabilities": [
            {"candidate_id": "a", "probability": 0.2},
            {"candidate_id": "b", "probability": 0.7},
            {"candidate_id": "c", "probability": 0.1},
        ],
        "rationale": "B is favoured.",
    }
    score = score_forecast(QUESTION, LABEL, forecast, "winner_only")
    assert score["brier_score"] == pytest.approx(0.14)
    assert score["top_choice_accuracy"] == 1.0


def test_joint_forecast_reports_macro_candidate_share_mae() -> None:
    forecast = {
        "winner_probabilities": [
            {"candidate_id": "a", "probability": 0.2},
            {"candidate_id": "b", "probability": 0.7},
            {"candidate_id": "c", "probability": 0.1},
        ],
        "vote_shares": [
            {"candidate_id": "a", "percentage": 20},
            {"candidate_id": "b", "percentage": 70},
            {"candidate_id": "c", "percentage": 10},
        ],
        "turnout_percentage": 50,
        "rationale": "B is favoured.",
    }
    score = score_forecast(QUESTION, LABEL, forecast, "joint")
    assert score["vote_share_mae"] == (5 + 10 + 5) / 3
    assert score["turnout_mae"] == 2


def test_small_rounding_error_is_normalised() -> None:
    forecast = {
        "winner_probabilities": [
            {"candidate_id": "a", "probability": 0.2},
            {"candidate_id": "b", "probability": 0.69},
            {"candidate_id": "c", "probability": 0.1},
        ],
        "rationale": "",
    }
    score = score_forecast(QUESTION, LABEL, forecast, "winner_only")
    assert 0 <= score["brier_score"] <= 2


def test_aggregate_is_question_macro_average() -> None:
    aggregate = aggregate_scores(
        [
            {"brier_score": 0.1, "top_choice_accuracy": 1},
            {"brier_score": 0.3, "top_choice_accuracy": 0},
        ]
    )
    assert aggregate["n"] == 2
    assert aggregate["mean_brier_score"] == 0.2
    assert aggregate["mean_top_choice_accuracy"] == 0.5
