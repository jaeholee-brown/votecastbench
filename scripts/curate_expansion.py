#!/usr/bin/env python3
"""Curate the outcome-blind 500-question expansion as one evaluation set."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import curate as legacy
import httpx

from votecastbench.io import read_json, read_jsonl, write_json, write_jsonl
from votecastbench.validation import validate_dataset

SEED = "votecastbench-uk-local-500-v1"
TARGET_TOTAL = 500
TARGET_BY_ELECTIONS = 5
TARGET_REGULAR = TARGET_TOTAL - TARGET_BY_ELECTIONS
AUDIT_SAMPLE_SIZE = 5
HISTORICAL_DATES = ["2021-05-06", "2022-05-05", "2023-05-04", "2024-05-02", "2025-05-01"]
LEGACY_PUBLIC_PROFILE = legacy.public_profile
SOURCE_URL_CORRECTIONS = {
    (
        "https://www.tamworth.gov.uk/sites/default/files/councillors_docs/"
        "03-Statement-of-Persons-Nominated-(All-Wards).docx"
    ): (
        "https://www.tamworth.gov.uk/sites/default/files/councillors_docs/"
        "03-Statement-of-Persons-Nominated-(All%20Wards).docx"
    )
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["select", "fetch-ballots", "curate", "audit-sample"],
    )
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/expansion"))
    parser.add_argument("--page-size", type=int, default=100)
    return parser.parse_args()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def history_availability(
    cache_dir: Path,
) -> tuple[set[str], set[str], list[dict[str, str]]]:
    historical = [
        row for date in HISTORICAL_DATES for row in read_csv(cache_dir / f"local-{date}.csv")
    ]
    by_ballot: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in historical:
        by_ballot[row["ballot_paper_id"]].append(row)
    complete_ballots = {
        ballot_id
        for ballot_id, rows in by_ballot.items()
        if all(row.get("votes_cast", "").isdigit() for row in rows)
    }
    people = {
        row["person_id"]
        for ballot_id, rows in by_ballot.items()
        if ballot_id in complete_ballots
        for row in rows
    }
    posts = {
        row["post_id"]
        for ballot_id, rows in by_ballot.items()
        if ballot_id in complete_ballots
        for row in rows
    }
    return people, posts, historical


def preliminary_eligible(
    current_rows: list[dict[str, str]],
    historical_people: set[str],
    historical_posts: set[str],
) -> tuple[dict[str, list[dict[str, str]]], Counter[str]]:
    by_ballot: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in current_rows:
        by_ballot[row["ballot_paper_id"]].append(row)
    eligible = {}
    exclusions: Counter[str] = Counter()
    for ballot_id, rows in by_ballot.items():
        votes = (
            [int(row["votes_cast"]) for row in rows]
            if all(row.get("votes_cast", "").isdigit() for row in rows)
            else []
        )
        checks = {
            "candidate_count_outside_3_to_6": not 3 <= len(rows) <= 6,
            "not_single_seat": {row.get("seats_contested") for row in rows} != {"1"},
            "candidate_list_not_locked": not all(
                row.get("candidates_locked") == "t" for row in rows
            ),
            "cancelled": any(row.get("cancelled_poll") == "t" for row in rows),
            "incomplete_votes": not votes,
            "not_one_elected": sum(row.get("elected") == "t" for row in rows) != 1,
            "no_unique_maximum": bool(votes) and sum(value == max(votes) for value in votes) != 1,
            "missing_result_source": not rows[0].get("results_source"),
            "no_usable_history": rows[0].get("post_id") not in historical_posts
            and not any(row["person_id"] in historical_people for row in rows),
        }
        failed = [name for name, failure in checks.items() if failure]
        if failed:
            exclusions.update(failed)
        else:
            eligible[ballot_id] = rows
    return eligible, exclusions


def select_ballots(
    eligible: dict[str, list[dict[str, str]]],
    existing_ids: set[str],
) -> tuple[list[str], list[str]]:
    by_elections = [
        ballot_id
        for ballot_id, rows in eligible.items()
        if any(row.get("by_election") == "t" for row in rows)
    ]
    selected_by = sorted(
        set(by_elections) - existing_ids,
        key=lambda ballot_id: digest(f"{SEED}|{ballot_id}"),
    )[:TARGET_BY_ELECTIONS]

    regular_by_org: dict[str, list[str]] = defaultdict(list)
    for ballot_id, rows in eligible.items():
        if ballot_id not in by_elections and ballot_id not in existing_ids:
            regular_by_org[rows[0]["organisation_name"]].append(ballot_id)
    base_slots = sum(min(len(ballots), 5) for ballots in regular_by_org.values())
    sixth_slots = TARGET_REGULAR - base_slots
    sixth_slot_orgs = set(
        sorted(
            (organisation for organisation, ballots in regular_by_org.items() if len(ballots) >= 6),
            key=lambda organisation: digest(f"{SEED}|{organisation}"),
        )[:sixth_slots]
    )
    selected_regular = []
    for organisation, ballots in sorted(regular_by_org.items()):
        quota = min(len(ballots), 5) + int(organisation in sixth_slot_orgs)
        remaining = sorted(
            ballots,
            key=lambda ballot_id: digest(f"{SEED}|{ballot_id}"),
        )
        selected_regular.extend(remaining[:quota])
    if len(selected_regular) != TARGET_REGULAR:
        raise ValueError(f"selected {len(selected_regular)} regular ballots, expected 495")
    selected_all = [*selected_regular, *selected_by]
    if len(selected_all) != TARGET_TOTAL or len(set(selected_all)) != TARGET_TOTAL:
        raise ValueError("selection is not exactly 500 unique ballots")
    selected_new = sorted(selected_all, key=lambda ballot_id: digest(f"{SEED}|{ballot_id}"))
    if len(selected_new) != TARGET_TOTAL:
        raise ValueError(f"selected {len(selected_new)} fresh ballots, expected 500")
    return selected_all, selected_new


def selection_command(cache_dir: Path, output_dir: Path) -> None:
    current_path = cache_dir / "local-2026-05-07.csv"
    current_rows = read_csv(current_path)
    historical_people, historical_posts, _ = history_availability(cache_dir)
    eligible, exclusions = preliminary_eligible(
        current_rows,
        historical_people,
        historical_posts,
    )
    existing_ids = set(read_json("data/manifest.json")["selection"]["ballot_paper_ids"])
    selected_all, selected_new = select_ballots(eligible, existing_ids)
    selected_rows = [eligible[ballot_id][0] for ballot_id in selected_all]
    manifest = {
        "dataset_revision": "VoteCastBench UK Local expansion v1",
        "selection_seed": SEED,
        "selection_uses_outcome_identity_party_margin_or_turnout": False,
        "selection_design": (
            "Exclude all 20 legacy questions; choose five by-elections by seeded hash; "
            "allocate 495 regular contests with five per authority plus seeded sixth "
            "slots, then use seeded ballot hashes within authority."
        ),
        "eligibility": [
            "election date 2026-05-07",
            "three to six candidates",
            "one seat and a locked, non-cancelled candidate list",
            "complete non-tied uniquely resolvable result",
            "nonempty result source",
            "usable 2021-2025 candidate or exact-post history",
            "API gate: FPTP, one winner, and every candidacy created by forecast cutoff",
        ],
        "source_csv_sha256": {
            date: file_sha256(cache_dir / f"local-{date}.csv")
            for date in [*HISTORICAL_DATES, "2026-05-07"]
        },
        "source_ballot_count": len(
            {row["ballot_paper_id"] for row in current_rows if row.get("ballot_paper_id")}
        ),
        "preliminary_eligible_count": len(eligible),
        "exclusion_counts_nonexclusive": dict(sorted(exclusions.items())),
        "excluded_legacy_question_count": len(existing_ids),
        "new_question_count": len(selected_new),
        "total_question_count": len(selected_all),
        "selected_by_election_count": sum(
            any(row.get("by_election") == "t" for row in eligible[ballot_id])
            for ballot_id in selected_all
        ),
        "selected_organisation_count": len({row["organisation_name"] for row in selected_rows}),
        "selected_region_count": len({row["nuts1"].strip('"') for row in selected_rows}),
        "selected_candidate_count_distribution": dict(
            sorted(Counter(len(eligible[ballot_id]) for ballot_id in selected_all).items())
        ),
        "selected_all_ballot_ids": selected_all,
        "selected_new_ballot_ids": selected_new,
    }
    write_json(output_dir / "selection.json", manifest)
    print(
        f"Selected {len(selected_new)} new questions across "
        f"{manifest['selected_organisation_count']} organisations"
    )


async def fetch_page(
    client: httpx.AsyncClient,
    cache_dir: Path,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    target = cache_dir / "ballot-pages" / f"page-{page:03d}.json"
    if target.exists():
        return read_json(target)
    url = "https://candidates.democracyclub.org.uk/api/next/ballots/"
    for attempt in range(8):
        response = await client.get(
            url,
            params={
                "election_date": "2026-05-07",
                "page_size": page_size,
                "page": page,
            },
        )
        if response.status_code < 400:
            value = response.json()
            write_json(target, value)
            return value
        if response.status_code not in {403, 429} and response.status_code < 500:
            response.raise_for_status()
        retry_after = response.headers.get("retry-after")
        delay = float(retry_after) if retry_after else min(2**attempt, 30)
        await asyncio.sleep(delay)
    response.raise_for_status()
    raise AssertionError("unreachable")


async def fetch_ballots_command(cache_dir: Path, output_dir: Path, page_size: int) -> None:
    selection = read_json(output_dir / "selection.json")
    selected = set(selection["selected_new_ballot_ids"])
    limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
    async with httpx.AsyncClient(
        timeout=120,
        follow_redirects=True,
        limits=limits,
    ) as client:
        first = await fetch_page(client, cache_dir, 1, page_size)
        page_count = (int(first["count"]) + page_size - 1) // page_size
        pages = [first]
        for page in range(2, page_count + 1):
            pages.append(await fetch_page(client, cache_dir, page, page_size))
            await asyncio.sleep(0.35)
    records = {
        record["ballot_paper_id"]: record
        for page in pages
        for record in page["results"]
        if record["ballot_paper_id"] in selected
    }
    missing = selected - records.keys()
    if missing:
        raise ValueError(f"selected ballots missing from API pages: {sorted(missing)}")
    api_hashes = {}
    for ballot_id, record in records.items():
        relative_url = f"ballots/{ballot_id}/"
        target = cache_dir / "api" / f"{hashlib.sha256(relative_url.encode()).hexdigest()}.json"
        write_json(target, record)
        api_hashes[ballot_id] = file_sha256(target)
    write_json(output_dir / "api-lineage.json", api_hashes)
    print(f"Cached API records for {len(records)} selected ballots from {len(pages)} pages")


def expansion_public_profile(row: dict[str, str]) -> dict[str, Any]:
    profile = LEGACY_PUBLIC_PROFILE(row)
    if profile.get("public_links"):
        profile["profile_last_updated"] = row["person_last_updated"]
    return profile


def correct_known_source_urls(questions: list[dict[str, Any]]) -> None:
    """Apply verified URL-only corrections without changing substantive packet data."""
    for question in questions:
        election = question["election"]
        source = election["official_candidate_list_source"]
        election["official_candidate_list_source"] = SOURCE_URL_CORRECTIONS.get(source, source)


def curate_command(cache_dir: Path, output_dir: Path) -> None:
    selection = read_json(output_dir / "selection.json")
    selected = selection["selected_new_ballot_ids"]
    current_rows = read_csv(cache_dir / "local-2026-05-07.csv")
    _, _, historical_rows = history_availability(cache_dir)
    legacy.SELECTED_BALLOTS = selected
    legacy.public_profile = expansion_public_profile
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        questions, labels = legacy.build_dataset(
            client,
            cache_dir,
            current_rows,
            historical_rows,
        )
    correct_known_source_urls(questions)
    summary = validate_dataset(
        questions,
        labels,
        expected_count=TARGET_TOTAL,
        require_profile_timestamps=True,
    )
    write_jsonl(output_dir / "questions-500.jsonl", questions)
    write_jsonl(output_dir / "labels-500.jsonl", labels)
    write_json(
        output_dir / "curation-summary.json",
        {
            "selection_seed": SEED,
            "generated_at_unix": time.time(),
            "summary": summary,
            "ballot_paper_ids": selected,
            "questions_sha256": file_sha256(output_dir / "questions-500.jsonl"),
            "labels_sha256": file_sha256(output_dir / "labels-500.jsonl"),
        },
    )
    print(f"Curated and strictly validated one 500-question set: {summary}")


def information_size(question: dict[str, Any]) -> tuple[int, int, int]:
    statement_length = sum(
        len(candidate["profile"].get("statement_to_voters", ""))
        for candidate in question["candidates"]
    )
    history_count = len(question["ward_history"]) + sum(
        len(candidate["prior_electoral_record"]) for candidate in question["candidates"]
    )
    link_count = sum(
        len(candidate["profile"].get("public_links", {})) for candidate in question["candidates"]
    )
    return statement_length, history_count, link_count


def audit_sample_command(output_dir: Path) -> None:
    questions = read_jsonl(output_dir / "questions-500.jsonl")
    remaining = {question["question_id"]: question for question in questions}
    chosen: list[tuple[str, str]] = []

    def choose(reason: str, key) -> None:
        question = max(remaining.values(), key=key)
        chosen.append((reason, question["question_id"]))
        del remaining[question["question_id"]]

    choose(
        "greatest total candidate-statement length", lambda question: information_size(question)[0]
    )
    choose(
        "most candidate-plus-ward history records", lambda question: information_size(question)[1]
    )
    choose(
        "greatest candidate count, then public-link count and serialized size",
        lambda question: (
            len(question["candidates"]),
            information_size(question)[2],
            len(json.dumps(question, ensure_ascii=False)),
        ),
    )
    question = min(
        remaining.values(),
        key=lambda value: (
            sum(information_size(value)),
            digest(f"{SEED}|audit-min|{value['question_id']}"),
        ),
    )
    chosen.append(("least supplied candidate and history information", question["question_id"]))
    del remaining[question["question_id"]]
    question = min(
        remaining.values(),
        key=lambda value: digest(f"{SEED}|audit-default|{value['question_id']}"),
    )
    chosen.append(
        ("lowest deterministic audit hash among remaining packets", question["question_id"])
    )
    question_map = {question["question_id"]: question for question in questions}
    write_json(
        output_dir / "audit-sample.json",
        {
            "selection_seed": SEED,
            "sample_size": AUDIT_SAMPLE_SIZE,
            "cases": [
                {
                    "reason": reason,
                    "question_id": question_id,
                    "ballot_paper_id": question_map[question_id]["election"]["ballot_paper_id"],
                }
                for reason, question_id in chosen
            ],
        },
    )
    print("Selected audit cases:")
    for reason, question_id in chosen:
        print(f"- {question_id}: {reason}")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.command == "select":
        selection_command(args.cache_dir, args.output_dir)
    elif args.command == "fetch-ballots":
        asyncio.run(fetch_ballots_command(args.cache_dir, args.output_dir, args.page_size))
    elif args.command == "curate":
        curate_command(args.cache_dir, args.output_dir)
    elif args.command == "audit-sample":
        audit_sample_command(args.output_dir)


if __name__ == "__main__":
    main()
