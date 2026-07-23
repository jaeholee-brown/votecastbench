from copy import deepcopy
from pathlib import Path

import pytest

from votecastbench.io import read_jsonl
from votecastbench.validation import validate_dataset

ROOT = Path(__file__).parents[1]
QUESTION = read_jsonl(ROOT / "data" / "questions.jsonl")[0]
LABEL = read_jsonl(ROOT / "data" / "labels.jsonl")[0]


def assert_rejected(mutator) -> None:
    question = deepcopy(QUESTION)
    mutator(question)
    with pytest.raises(ValueError):
        validate_dataset([question], [LABEL])


def test_rejects_unlocked_candidate_list() -> None:
    assert_rejected(lambda question: question["election"].update(candidate_list_locked=False))


def test_rejects_post_forecast_candidacy() -> None:
    assert_rejected(
        lambda question: question["candidates"][0].update(
            candidacy_created="2026-05-06T12:00:00+01:00"
        )
    )


def test_rejects_untimestamped_statement() -> None:
    def mutate(question):
        question["candidates"][0]["profile"]["statement_to_voters"] = "Vote for me."
        question["candidates"][0]["profile"].pop("statement_last_updated", None)

    assert_rejected(mutate)


def test_rejects_post_forecast_history() -> None:
    assert_rejected(lambda question: question["ward_history"][0].update(election_date="2026-05-05"))


def test_rejects_unknown_nested_candidate_field() -> None:
    assert_rejected(lambda question: question["candidates"][0].update(outcome="winner"))


def test_strict_lineage_rejects_untimestamped_public_links() -> None:
    question = deepcopy(QUESTION)
    question["candidates"][0]["profile"]["public_links"] = {"result": "https://example.test/result"}
    with pytest.raises(ValueError):
        validate_dataset(
            [question],
            [LABEL],
            require_profile_timestamps=True,
        )


def test_rejects_negative_votes_and_tied_winner() -> None:
    question = deepcopy(QUESTION)
    label = deepcopy(LABEL)
    label["votes"][next(iter(label["votes"]))] = -1
    with pytest.raises(ValueError):
        validate_dataset([question], [label])

    label = deepcopy(LABEL)
    label["votes"] = {candidate_id: 10 for candidate_id in label["votes"]}
    with pytest.raises(ValueError):
        validate_dataset([question], [label])


def test_rejects_incoherent_or_historical_target_ballot() -> None:
    assert_rejected(
        lambda question: question["election"].update(ballot_paper_id="local.fake.2026-05-07")
    )
    assert_rejected(
        lambda question: question["ward_history"][0].update(
            ballot_paper_id=question["election"]["ballot_paper_id"]
        )
    )
