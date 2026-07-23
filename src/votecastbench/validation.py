"""Dataset-level checks, including temporal leakage guards."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from votecastbench.schemas import candidate_ids, validate_question


def _date(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def validate_dataset(
    questions: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    *,
    expected_count: int | None = None,
) -> dict[str, Any]:
    if expected_count is not None and len(questions) != expected_count:
        raise ValueError(f"expected {expected_count} questions, found {len(questions)}")
    question_map = {row["question_id"]: row for row in questions}
    label_map = {row["question_id"]: row for row in labels}
    if len(question_map) != len(questions):
        raise ValueError("duplicate question_id in questions")
    if len(label_map) != len(labels):
        raise ValueError("duplicate question_id in labels")
    if question_map.keys() != label_map.keys():
        raise ValueError("question and label ID sets differ")

    organisations: set[str] = set()
    regions: set[str] = set()
    candidate_count = 0
    for question_id, question in question_map.items():
        validate_question(question)
        label = label_map[question_id]
        forecast_at = _date(question["forecast_as_of"])
        election_at = _date(question["election"]["date"])
        if forecast_at >= election_at:
            raise ValueError(f"{question_id}: forecast is not before election")
        if _date(label["resolved_on"]) < election_at:
            raise ValueError(f"{question_id}: resolution predates election")
        ids = set(candidate_ids(question))
        votes = {str(key): int(value) for key, value in label["votes"].items()}
        if ids != votes.keys():
            raise ValueError(f"{question_id}: label candidate set differs")
        winner_id = str(label["winner_candidate_id"])
        if winner_id not in ids:
            raise ValueError(f"{question_id}: winner is not a candidate")
        if votes[winner_id] != max(votes.values()):
            raise ValueError(f"{question_id}: labelled winner does not have the most votes")
        for forbidden in ("winner_candidate_id", "votes", "result_source", "resolved_on"):
            if forbidden in question:
                raise ValueError(f"{question_id}: top-level leakage field {forbidden}")
        for candidate in question["candidates"]:
            if "votes" in candidate or "elected" in candidate:
                raise ValueError(f"{question_id}: current candidate result leaked")
            for record in candidate["prior_electoral_record"]:
                if _date(record["election_date"]) >= election_at:
                    raise ValueError(f"{question_id}: non-prior candidate record")
            statement_at = candidate["profile"].get("statement_last_updated")
            if statement_at and _date(statement_at) > forecast_at:
                raise ValueError(f"{question_id}: post-forecast candidate statement")
        for record in question["ward_history"]:
            if _date(record["election_date"]) >= election_at:
                raise ValueError(f"{question_id}: non-prior ward result")
        organisations.add(question["election"]["organisation"])
        regions.add(question["election"]["region"])
        candidate_count += len(ids)

    return {
        "question_count": len(questions),
        "candidate_count": candidate_count,
        "organisation_count": len(organisations),
        "region_count": len(regions),
    }
