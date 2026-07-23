"""Deterministic reference forecasts."""

from __future__ import annotations

from typing import Any


def party_family(party: str) -> str:
    aliases = {
        "Labour and Co-operative Party": "Labour Party",
        "Liberal Democrats": "Liberal Democrats",
        "Conservative and Unionist Party": "Conservative and Unionist Party",
    }
    return aliases.get(party, party)


def uniform_forecast(question: dict[str, Any]) -> dict[str, Any]:
    probability = 1 / len(question["candidates"])
    return {
        "winner_probabilities": [
            {
                "candidate_id": candidate["candidate_id"],
                "probability": probability,
            }
            for candidate in question["candidates"]
        ],
        "rationale": "Uniform reference forecast.",
    }


def last_ward_party_share_forecast(question: dict[str, Any]) -> dict[str, Any]:
    """Carry forward exact-party votes from the latest same-post contest.

    Each current candidate receives additive smoothing equal to one percent of
    the previous valid-vote total. Labour and Labour & Co-operative labels are
    treated as one party family. No candidate identity information is used.
    """
    latest = max(question["ward_history"], key=lambda row: row["election_date"])
    prior_votes: dict[str, int] = {}
    for candidate in latest["candidates"]:
        family = party_family(candidate["party"])
        prior_votes[family] = prior_votes.get(family, 0) + int(candidate["votes"])
    total_prior_votes = sum(prior_votes.values())
    smoothing = max(total_prior_votes * 0.01, 1)
    raw = {
        candidate["candidate_id"]: prior_votes.get(party_family(candidate["party"]), 0) + smoothing
        for candidate in question["candidates"]
    }
    total = sum(raw.values())
    return {
        "winner_probabilities": [
            {
                "candidate_id": candidate["candidate_id"],
                "probability": raw[candidate["candidate_id"]] / total,
            }
            for candidate in question["candidates"]
        ],
        "rationale": (
            "Deterministic reference: latest same-ward party votes with 1% additive smoothing."
        ),
    }


def baseline_predictions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    predictions = []
    methods = [
        ("baseline/uniform", uniform_forecast),
        ("baseline/last-ward-party-share", last_ward_party_share_forecast),
    ]
    for model, method in methods:
        for question in questions:
            predictions.append(
                {
                    "question_id": question["question_id"],
                    "model": model,
                    "provider": "deterministic",
                    "requested_model": model,
                    "resolved_model": model,
                    "output_format": "winner_only",
                    "forecast": method(question),
                    "status": "ok",
                }
            )
    return predictions
