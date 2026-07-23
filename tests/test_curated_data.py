from pathlib import Path

from votecastbench.io import read_jsonl
from votecastbench.validation import validate_dataset

ROOT = Path(__file__).parents[1]


def test_curated_dataset_is_complete_and_temporally_valid() -> None:
    questions = read_jsonl(ROOT / "data" / "questions.jsonl")
    labels = read_jsonl(ROOT / "data" / "labels.jsonl")
    summary = validate_dataset(questions, labels, expected_count=20)
    assert summary["organisation_count"] == 20
    assert summary["region_count"] == 8
    assert summary["candidate_count"] >= 90


def test_every_resolution_is_post_february_2026() -> None:
    labels = read_jsonl(ROOT / "data" / "labels.jsonl")
    assert all(label["resolved_on"] > "2026-02-28" for label in labels)
