import pytest

from votecastbench.baselines import last_ward_party_share_forecast, uniform_forecast

QUESTION = {
    "candidates": [
        {"candidate_id": "lab", "party": "Labour Party"},
        {"candidate_id": "con", "party": "Conservative and Unionist Party"},
        {"candidate_id": "new", "party": "Reform UK"},
    ],
    "ward_history": [
        {
            "election_date": "2024-05-02",
            "candidates": [
                {"party": "Labour and Co-operative Party", "votes": 600},
                {"party": "Conservative and Unionist Party", "votes": 400},
            ],
        }
    ],
}


def test_uniform_baseline_sums_to_one() -> None:
    forecast = uniform_forecast(QUESTION)
    assert sum(row["probability"] for row in forecast["winner_probabilities"]) == 1


def test_last_party_share_maps_labour_coop_and_smooths_new_party() -> None:
    forecast = last_ward_party_share_forecast(QUESTION)
    probabilities = {
        row["candidate_id"]: row["probability"] for row in forecast["winner_probabilities"]
    }
    assert sum(probabilities.values()) == pytest.approx(1)
    assert probabilities["lab"] > probabilities["con"] > probabilities["new"] > 0


def test_last_party_share_uses_uniform_fallback_without_history() -> None:
    question = {
        "candidates": [{"candidate_id": "a"}, {"candidate_id": "b"}],
        "ward_history": [],
    }

    result = last_ward_party_share_forecast(question)

    assert result["winner_probabilities"] == uniform_forecast(question)["winner_probabilities"]
    assert "uniform fallback" in result["rationale"]
