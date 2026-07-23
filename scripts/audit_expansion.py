#!/usr/bin/env python3
"""Reproduce the automated launch gate for the fresh 500-question expansion."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from votecastbench.io import read_json, read_jsonl, write_json
from votecastbench.prompting import SYSTEM_PROMPT, build_user_prompt
from votecastbench.runner import prompt_hash
from votecastbench.validation import validate_dataset

HISTORICAL_DATES = [
    "2021-05-06",
    "2022-05-05",
    "2023-05-04",
    "2024-05-02",
    "2025-05-01",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("data/expansion/questions-500.jsonl"),
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=Path("data/expansion/labels-500.jsonl"),
    )
    parser.add_argument(
        "--manual-audit",
        type=Path,
        default=Path("data/expansion/manual-audit.json"),
    )
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/expansion/audit-report.json"),
    )
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def historical_source_gate(
    questions: list[dict[str, Any]],
    cache_dir: Path,
) -> dict[str, int]:
    rows = [
        row
        for date in HISTORICAL_DATES
        for row in read_csv(cache_dir / f"local-{date}.csv")
    ]
    by_ballot: dict[str, list[dict[str, str]]] = {}
    by_person_ballot: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        by_ballot.setdefault(row["ballot_paper_id"], []).append(row)
        by_person_ballot[(row["person_id"], row["ballot_paper_id"])] = row

    ward_records = 0
    candidate_records = 0
    for question in questions:
        for record in question["ward_history"]:
            ballot_id = record["ballot_paper_id"]
            source_rows = by_ballot.get(ballot_id, [])
            expected = sorted(
                (
                    row["person_name"],
                    row["party_name"],
                    int(row["votes_cast"]),
                    row["elected"] == "t",
                )
                for row in source_rows
            )
            actual = sorted(
                (
                    row["name"],
                    row["party"],
                    int(row["votes"]),
                    bool(row["elected"]),
                )
                for row in record["candidates"]
            )
            if actual != expected:
                raise ValueError(f"ward history differs from raw export: {ballot_id}")
            ward_records += 1
        for candidate in question["candidates"]:
            for record in candidate["prior_electoral_record"]:
                key = (str(candidate["candidate_id"]), record["ballot_paper_id"])
                source = by_person_ballot.get(key)
                if source is None:
                    raise ValueError(f"candidate history absent from raw export: {key}")
                expected = (
                    source["election_date"],
                    source["organisation_name"],
                    source["post_label"],
                    source["party_name"],
                    source["elected"] == "t",
                    int(source["votes_cast"]),
                )
                actual = (
                    record["election_date"],
                    record["organisation"],
                    record["post"],
                    record["party"],
                    bool(record["elected"]),
                    int(record["votes"]),
                )
                if actual != expected:
                    raise ValueError(f"candidate history differs from raw export: {key}")
                candidate_records += 1
    return {
        "ward_history_records_checked": ward_records,
        "candidate_history_records_checked": candidate_records,
    }


def api_lineage_gate(questions: list[dict[str, Any]], cache_dir: Path) -> int:
    lineage = read_json("data/expansion/api-lineage.json")
    for question in questions:
        ballot_id = question["election"]["ballot_paper_id"]
        relative_url = f"ballots/{ballot_id}/"
        filename = f"{hashlib.sha256(relative_url.encode()).hexdigest()}.json"
        source = cache_dir / "api" / filename
        if file_sha256(source) != lineage[ballot_id]:
            raise ValueError(f"API cache hash mismatch: {ballot_id}")
    return len(lineage)


def prompt_gate(
    questions: list[dict[str, Any]],
    labels: list[dict[str, Any]],
) -> dict[str, Any]:
    labels_by_id = {row["question_id"]: row for row in labels}
    sizes = []
    hashes = set()
    for question in questions:
        label = labels_by_id[question["question_id"]]
        prompt = build_user_prompt(question, "winner_only")
        for forbidden_key in ('"winner_candidate_id"', '"result_source"', '"resolved_on"'):
            if forbidden_key in prompt:
                raise ValueError(
                    f"{question['question_id']}: target-only key appears in rendered prompt"
                )
        if label["result_source"] in prompt:
            raise ValueError(
                f"{question['question_id']}: target result URL appears in rendered prompt"
            )
        sizes.append(len(SYSTEM_PROMPT) + len(prompt))
        hashes.add(prompt_hash(SYSTEM_PROMPT, prompt))
    return {
        "rendered_prompts_checked": len(questions),
        "unique_prompt_hashes": len(hashes),
        "minimum_prompt_characters": min(sizes),
        "maximum_prompt_characters": max(sizes),
        "rationale_length_restriction_present": False,
        "provider_web_tools_attached": False,
    }


def main() -> None:
    args = parse_args()
    questions = read_jsonl(args.questions)
    labels = read_jsonl(args.labels)
    old_ballots = {
        row["election"]["ballot_paper_id"] for row in read_jsonl("data/questions.jsonl")
    }
    new_ballots = {row["election"]["ballot_paper_id"] for row in questions}
    overlap = sorted(old_ballots & new_ballots)
    if overlap:
        raise ValueError(f"fresh expansion overlaps the original 20: {overlap}")

    summary = validate_dataset(
        questions,
        labels,
        expected_count=500,
        require_profile_timestamps=True,
    )
    history = historical_source_gate(questions, args.cache_dir)
    api_record_count = api_lineage_gate(questions, args.cache_dir)
    prompts = prompt_gate(questions, labels)
    manual = read_json(args.manual_audit)
    unacceptable = [
        row
        for row in manual["cases"]
        if row["status"] not in {"pass", "pass_with_minor_notes"}
    ]
    if unacceptable:
        raise ValueError(f"manual audit has unacceptable cases: {unacceptable}")

    report = {
        "status": "pass",
        "launch_gate_passed": True,
        "selection_is_fresh": True,
        "overlap_with_original_20": 0,
        "resolution_date_policy": (
            "resolved_on records the target poll/event date. It is not a result-page "
            "publication timestamp; some formal declarations are dated the following day."
        ),
        "dataset_summary": summary,
        "automated_checks": {
            "strict_dataset_validation": "pass",
            "api_lineage": "pass",
            "historical_export_reconciliation": "pass",
            "rendered_prompt_leakage_scan": "pass",
            "cached_api_records_checked": api_record_count,
            **history,
            **prompts,
        },
        "manual_audit": manual,
        "artifact_sha256": {
            "questions": file_sha256(args.questions),
            "labels": file_sha256(args.labels),
            "selection": file_sha256(Path("data/expansion/selection.json")),
            "api_lineage": file_sha256(Path("data/expansion/api-lineage.json")),
        },
    }
    write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
