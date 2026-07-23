"""Dataset-level checks, including temporal leakage guards."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from votecastbench.schemas import candidate_ids, validate_question

QUESTION_KEYS = {
    "question_id",
    "forecast_as_of",
    "question",
    "election",
    "candidates",
    "ward_history",
    "information_policy",
}
ELECTION_KEYS = {
    "ballot_paper_id",
    "name",
    "date",
    "organisation",
    "ward",
    "post_id",
    "region",
    "voting_system",
    "seats",
    "candidate_list_locked",
    "official_candidate_list_source",
}
CANDIDATE_KEYS = {
    "candidate_id",
    "name",
    "party",
    "ballot_description",
    "candidacy_created",
    "profile",
    "prior_electoral_record",
}
PROFILE_KEYS = {
    "democracy_club_person_id",
    "statement_to_voters",
    "statement_last_updated",
    "public_links",
    "profile_last_updated",
}
PRIOR_RECORD_KEYS = {
    "election_date",
    "ballot_paper_id",
    "organisation",
    "post",
    "party",
    "elected",
    "votes",
    "vote_share_percentage",
    "turnout_percentage",
}
WARD_RECORD_KEYS = {
    "election_date",
    "ballot_paper_id",
    "candidates",
    "turnout_percentage",
}
WARD_CANDIDATE_KEYS = {"name", "party", "votes", "elected"}
INFORMATION_POLICY_KEYS = {"included", "excluded"}
LABEL_KEYS = {
    "question_id",
    "winner_candidate_id",
    "votes",
    "result_source",
    "resolved_on",
    "turnout_percentage",
}


def _date(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _require_exact_keys(value: dict[str, Any], allowed: set[str], context: str) -> None:
    unexpected = value.keys() - allowed
    if unexpected:
        raise ValueError(f"{context}: unexpected fields {sorted(unexpected)}")


def validate_dataset(
    questions: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    *,
    expected_count: int | None = None,
    require_profile_timestamps: bool = False,
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
        _require_exact_keys(question, QUESTION_KEYS, question_id)
        label = label_map[question_id]
        _require_exact_keys(label, LABEL_KEYS, f"{question_id}: label")
        forecast_at = _date(question["forecast_as_of"])
        election_at = _date(question["election"]["date"])
        if forecast_at >= election_at:
            raise ValueError(f"{question_id}: forecast is not before election")
        _require_exact_keys(question["election"], ELECTION_KEYS, f"{question_id}: election")
        if question["election"].get("candidate_list_locked") is not True:
            raise ValueError(f"{question_id}: candidate list was not locked")
        ballot_id = str(question["election"]["ballot_paper_id"])
        election_date = str(question["election"]["date"])
        suffix = f".{election_date}"
        if not ballot_id.startswith("local.") or not ballot_id.endswith(suffix):
            raise ValueError(f"{question_id}: incoherent target ballot ID")
        expected_question_id = (
            ballot_id.removeprefix("local.").removesuffix(suffix).replace(".", "_")
        )
        if question_id != expected_question_id:
            raise ValueError(f"{question_id}: question ID does not match target ballot")
        if _date(label["resolved_on"]) < election_at:
            raise ValueError(f"{question_id}: resolution predates election")
        ids = set(candidate_ids(question))
        votes = {str(key): int(value) for key, value in label["votes"].items()}
        if ids != votes.keys():
            raise ValueError(f"{question_id}: label candidate set differs")
        if any(value < 0 for value in votes.values()) or sum(votes.values()) <= 0:
            raise ValueError(f"{question_id}: invalid target vote totals")
        winner_id = str(label["winner_candidate_id"])
        if winner_id not in ids:
            raise ValueError(f"{question_id}: winner is not a candidate")
        maximum = max(votes.values())
        if votes[winner_id] != maximum or sum(value == maximum for value in votes.values()) != 1:
            raise ValueError(f"{question_id}: target result lacks a unique labelled winner")
        if not isinstance(label.get("result_source"), str) or not label["result_source"].strip():
            raise ValueError(f"{question_id}: target result source is missing")
        for forbidden in ("winner_candidate_id", "votes", "result_source", "resolved_on"):
            if forbidden in question:
                raise ValueError(f"{question_id}: top-level leakage field {forbidden}")
        for candidate in question["candidates"]:
            candidate_id = str(candidate.get("candidate_id"))
            context = f"{question_id}: candidate {candidate_id}"
            _require_exact_keys(candidate, CANDIDATE_KEYS, context)
            if _date(candidate["candidacy_created"]) > forecast_at:
                raise ValueError(f"{context}: candidacy was created after forecast")
            profile = candidate["profile"]
            _require_exact_keys(profile, PROFILE_KEYS, f"{context}: profile")
            if str(profile["democracy_club_person_id"]) != candidate_id:
                raise ValueError(f"{context}: profile person ID does not match candidate")
            statement = profile.get("statement_to_voters")
            statement_at = profile.get("statement_last_updated")
            if statement and not statement_at:
                raise ValueError(f"{context}: statement has no timestamp")
            if statement_at and _date(statement_at) > forecast_at:
                raise ValueError(f"{context}: post-forecast candidate statement")
            links = profile.get("public_links")
            profile_at = profile.get("profile_last_updated")
            if links is not None:
                if not isinstance(links, dict) or not all(
                    isinstance(key, str) and isinstance(value, str) for key, value in links.items()
                ):
                    raise ValueError(f"{context}: malformed public links")
                if require_profile_timestamps and not profile_at:
                    raise ValueError(f"{context}: public links have no profile timestamp")
                if profile_at and _date(profile_at) > forecast_at:
                    raise ValueError(f"{context}: post-forecast public links")
            for record in candidate["prior_electoral_record"]:
                _require_exact_keys(record, PRIOR_RECORD_KEYS, f"{context}: prior record")
                if _date(record["election_date"]) > forecast_at:
                    raise ValueError(f"{context}: post-forecast candidate record")
                if record["ballot_paper_id"] == ballot_id:
                    raise ValueError(f"{context}: target ballot appears in candidate history")
        for record in question["ward_history"]:
            _require_exact_keys(record, WARD_RECORD_KEYS, f"{question_id}: ward history")
            if _date(record["election_date"]) > forecast_at:
                raise ValueError(f"{question_id}: post-forecast ward result")
            if record["ballot_paper_id"] == ballot_id:
                raise ValueError(f"{question_id}: target ballot appears in ward history")
            for prior_candidate in record["candidates"]:
                _require_exact_keys(
                    prior_candidate,
                    WARD_CANDIDATE_KEYS,
                    f"{question_id}: ward-history candidate",
                )
        _require_exact_keys(
            question["information_policy"],
            INFORMATION_POLICY_KEYS,
            f"{question_id}: information policy",
        )
        organisations.add(question["election"]["organisation"])
        regions.add(question["election"]["region"])
        candidate_count += len(ids)

    return {
        "question_count": len(questions),
        "candidate_count": candidate_count,
        "organisation_count": len(organisations),
        "region_count": len(regions),
    }
