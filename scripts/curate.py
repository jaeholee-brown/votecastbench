#!/usr/bin/env python3
"""Rebuild the 20-question VoteCastBench v1 dataset.

The script downloads Democracy Club CSV exports and API records, then separates
forecast-time fields from outcome labels. API responses are cached locally
under the ignored cache directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from votecastbench.io import write_json, write_jsonl
from votecastbench.schemas import validate_question

BASE_URL = "https://candidates.democracyclub.org.uk"
EXPORT_URL = f"{BASE_URL}/data/export_csv/"
API_URL = f"{BASE_URL}/api/next"
FORECAST_AS_OF = "2026-05-01T23:59:59+01:00"
ELECTION_DATE = "2026-05-07"
HISTORICAL_DATES = [
    "2021-05-06",
    "2022-05-05",
    "2023-05-04",
    "2024-05-02",
    "2025-05-01",
]
SELECTED_BALLOTS = [
    "local.adur.buckingham.2026-05-07",
    "local.cherwell.deddington.2026-05-07",
    "local.exeter.mincinglake-whipton.2026-05-07",
    "local.norwich.bowthorpe.2026-05-07",
    "local.welwyn-hatfield.peartree.2026-05-07",
    "local.rugby.new-bilton.2026-05-07",
    "local.chorley.chorley-east.2026-05-07",
    "local.cambridge.west-chesterton.2026-05-07",
    "local.hartlepool.throston.2026-05-07",
    "local.leeds.killingbeck-seacroft.2026-05-07",
    "local.basingstoke-and-deane.winklebury-manydown.2026-05-07",
    "local.plymouth.sutton-and-mount-gould.2026-05-07",
    "local.sheffield.crookes-crosspool.2026-05-07",
    "local.salford.eccles.2026-05-07",
    "local.city-of-lincoln.moorland.2026-05-07",
    "local.portsmouth.fratton.2026-05-07",
    "local.pendle.brierfield-east-clover-hill.2026-05-07",
    "local.winchester.central-meon-valley.2026-05-07",
    "local.watford.holywell.2026-05-07",
    "local.colchester.prettygate.2026-05-07",
]
PUBLIC_LINK_FIELDS = {
    "homepage_url": "homepage",
    "party_ppc_page_url": "party_profile",
    "wikipedia_url": "wikipedia",
    "facebook_page_url": "facebook",
    "twitter_username": "twitter",
    "instagram_url": "instagram",
    "linkedin_url": "linkedin",
    "blue_sky_url": "bluesky",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache"))
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def export_params(election_date: str) -> list[tuple[str, str]]:
    return [
        ("election_date", election_date),
        ("election_id", "^local.*"),
        ("format", "csv"),
        ("field_group", "results"),
        ("field_group", "person"),
        ("field_group", "candidacy"),
        ("field_group", "election"),
        ("results", "True"),
    ]


def download_export(client: httpx.Client, cache_dir: Path, election_date: str) -> Path:
    target = cache_dir / f"local-{election_date}.csv"
    if not target.exists():
        response = client.get(EXPORT_URL, params=export_params(election_date))
        response.raise_for_status()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
    return target


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def cached_api_get(client: httpx.Client, cache_dir: Path, relative_url: str) -> dict[str, Any]:
    cache_key = hashlib.sha256(relative_url.encode()).hexdigest()
    target = cache_dir / "api" / f"{cache_key}.json"
    if target.exists():
        with target.open(encoding="utf-8") as handle:
            return json.load(handle)
    url = f"{API_URL}/{relative_url.lstrip('/')}"
    for attempt in range(7):
        response = client.get(url)
        if response.status_code != 429 and response.status_code < 500:
            break
        if attempt == 6:
            response.raise_for_status()
        retry_after = response.headers.get("retry-after")
        delay = float(retry_after) if retry_after else min(1.5 * 2**attempt, 15)
        time.sleep(delay)
    response.raise_for_status()
    value = response.json()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value


def is_at_or_before_forecast(timestamp: str | None) -> bool:
    if not timestamp:
        return False
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    forecast = datetime.fromisoformat(FORECAST_AS_OF)
    return parsed <= forecast


def candidate_history(
    person_id: str,
    historical_by_person: dict[str, list[dict[str, str]]],
    historical_by_ballot: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for row in historical_by_person.get(person_id, []):
        if not row.get("votes_cast", "").isdigit():
            continue
        ballot_rows = historical_by_ballot[row["ballot_paper_id"]]
        if any(not value.get("votes_cast", "").isdigit() for value in ballot_rows):
            continue
        votes = int(row["votes_cast"])
        total_valid_votes = sum(int(value["votes_cast"]) for value in ballot_rows)
        record: dict[str, Any] = {
            "election_date": row["election_date"],
            "ballot_paper_id": row["ballot_paper_id"],
            "organisation": row["organisation_name"],
            "post": row["post_label"],
            "party": row["party_name"],
            "elected": row["elected"] == "t",
            "votes": votes,
        }
        if total_valid_votes:
            record["vote_share_percentage"] = round(votes * 100 / total_valid_votes, 2)
        if row.get("turnout_percentage"):
            record["turnout_percentage"] = float(row["turnout_percentage"])
        history.append(record)
    return sorted(history, key=lambda value: (value["election_date"], value["ballot_paper_id"]))


def public_profile(row: dict[str, str]) -> dict[str, Any]:
    profile: dict[str, Any] = {"democracy_club_person_id": int(row["person_id"])}
    statement_updated = row.get("statement_last_updated")
    if is_at_or_before_forecast(statement_updated) and row.get("statement_to_voters"):
        profile["statement_to_voters"] = row["statement_to_voters"]
        profile["statement_last_updated"] = statement_updated
    if is_at_or_before_forecast(row.get("person_last_updated")):
        links = {
            label: row[field].strip().strip('"')
            for field, label in PUBLIC_LINK_FIELDS.items()
            if row.get(field)
        }
        if links:
            profile["public_links"] = links
    return profile


def ward_history(
    historical_rows: list[dict[str, str]],
    post_id: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in historical_rows:
        if row.get("post_id") == post_id:
            grouped[row["ballot_paper_id"]].append(row)
    history = []
    for ballot_id, rows in sorted(grouped.items()):
        if any(not row.get("votes_cast", "").isdigit() for row in rows):
            continue
        candidates = [
            {
                "name": row["person_name"],
                "party": row["party_name"],
                "votes": int(row["votes_cast"]),
                "elected": row["elected"] == "t",
            }
            for row in sorted(rows, key=lambda value: int(value["votes_cast"]), reverse=True)
        ]
        item: dict[str, Any] = {
            "election_date": rows[0]["election_date"],
            "ballot_paper_id": ballot_id,
            "candidates": candidates,
        }
        if rows[0].get("turnout_percentage"):
            item["turnout_percentage"] = float(rows[0]["turnout_percentage"])
        history.append(item)
    return history


def clean_question_id(ballot_id: str) -> str:
    return ballot_id.removeprefix("local.").removesuffix(".2026-05-07").replace(".", "_")


def build_dataset(
    client: httpx.Client,
    cache_dir: Path,
    current_rows: list[dict[str, str]],
    historical_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    current_by_ballot: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in current_rows:
        current_by_ballot[row["ballot_paper_id"]].append(row)
    historical_by_person: dict[str, list[dict[str, str]]] = defaultdict(list)
    historical_by_ballot: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in historical_rows:
        historical_by_person[row["person_id"]].append(row)
        historical_by_ballot[row["ballot_paper_id"]].append(row)
    questions = []
    labels = []
    for ballot_id in SELECTED_BALLOTS:
        rows = current_by_ballot[ballot_id]
        if not rows:
            raise ValueError(f"selected ballot not found: {ballot_id}")
        ballot = cached_api_get(
            client,
            cache_dir,
            f"ballots/{quote(ballot_id, safe='.:_-')}/",
        )
        if ballot["voting_system"] != "FPTP" or int(ballot["winner_count"]) != 1:
            raise ValueError(f"not a single-winner FPTP ballot: {ballot_id}")
        if not ballot["candidates_locked"]:
            raise ValueError(f"candidate list was not locked: {ballot_id}")
        ballot_candidacies = {int(value["person"]["id"]): value for value in ballot["candidacies"]}
        candidates = []
        for row in sorted(rows, key=lambda value: int(value["person_id"])):
            person_id = int(row["person_id"])
            candidacy = ballot_candidacies[person_id]
            if not is_at_or_before_forecast(candidacy["created"]):
                raise ValueError(f"candidate was not known at cutoff: {person_id}")
            candidate = {
                "candidate_id": str(person_id),
                "name": row["person_name"],
                "party": row["party_name"],
                "ballot_description": row["party_description_text"] or None,
                "candidacy_created": candidacy["created"],
                "profile": public_profile(row),
                "prior_electoral_record": candidate_history(
                    row["person_id"],
                    historical_by_person,
                    historical_by_ballot,
                ),
            }
            candidates.append(candidate)
        question_id = clean_question_id(ballot_id)
        question = {
            "question_id": question_id,
            "forecast_as_of": FORECAST_AS_OF,
            "question": (
                f"Who will win the {rows[0]['post_label']} ward in the "
                f"{ballot['election']['name']} on {ELECTION_DATE}?"
            ),
            "election": {
                "ballot_paper_id": ballot_id,
                "name": ballot["election"]["name"],
                "date": ELECTION_DATE,
                "organisation": rows[0]["organisation_name"],
                "ward": rows[0]["post_label"],
                "post_id": rows[0]["post_id"],
                "region": rows[0]["nuts1"].strip('"'),
                "voting_system": "FPTP",
                "seats": 1,
                "candidate_list_locked": True,
                "official_candidate_list_source": (ballot.get("sopn") or {}).get("source_url"),
            },
            "ward_history": ward_history(historical_rows, rows[0]["post_id"]),
            "candidates": candidates,
            "information_policy": {
                "included": [
                    "official candidate list known by forecast_as_of",
                    "Democracy Club candidate statements timestamped by forecast_as_of",
                    "public profile links when the profile was last updated by forecast_as_of",
                    "candidate and same-post regular May local-election results, 2021–2025",
                ],
                "excluded": [
                    "2026 result fields",
                    "post-forecast candidate statements and profile edits",
                    "photos, gender, birth date, and inferred protected characteristics",
                    "web access or information not written in this packet",
                ],
            },
        }
        validate_question(question)
        winners = [row for row in rows if row["elected"] == "t"]
        if len(winners) != 1 or any(not row["votes_cast"].isdigit() for row in rows):
            raise ValueError(f"incomplete or non-unique result: {ballot_id}")
        label: dict[str, Any] = {
            "question_id": question_id,
            "winner_candidate_id": winners[0]["person_id"],
            "votes": {row["person_id"]: int(row["votes_cast"]) for row in rows},
            "result_source": rows[0]["results_source"],
            "resolved_on": ELECTION_DATE,
        }
        if rows[0].get("turnout_percentage"):
            label["turnout_percentage"] = float(rows[0]["turnout_percentage"])
        else:
            label["turnout_percentage"] = None
        questions.append(question)
        labels.append(label)
    return questions, labels


def main() -> None:
    args = parse_args()
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        export_paths = {
            date: download_export(client, args.cache_dir, date)
            for date in [*HISTORICAL_DATES, ELECTION_DATE]
        }
        current_rows = read_csv(export_paths[ELECTION_DATE])
        historical_rows = [row for date in HISTORICAL_DATES for row in read_csv(export_paths[date])]
        questions, labels = build_dataset(
            client,
            args.cache_dir,
            current_rows,
            historical_rows,
        )
    write_jsonl(args.output_dir / "questions.jsonl", questions)
    write_jsonl(args.output_dir / "labels.jsonl", labels)
    manifest = {
        "dataset": "VoteCastBench UK Local v1",
        "version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "question_count": len(questions),
        "forecast_as_of": FORECAST_AS_OF,
        "resolution_date": ELECTION_DATE,
        "selection": {
            "design": "hand-selected stratified sample",
            "criteria": [
                "resolved after 2026-02-16",
                "single-seat first-past-the-post",
                "three to six candidates",
                "complete candidate vote totals and a unique winner",
                "usable exact-post history and/or candidate electoral history",
                "variation in geography, winner party, and competitiveness",
            ],
            "ballot_paper_ids": SELECTED_BALLOTS,
        },
        "sources": [
            {
                "election_date": date,
                "url": EXPORT_URL,
                "query": export_params(date),
                "sha256": sha256(path),
            }
            for date, path in export_paths.items()
        ],
        "api_base_url": API_URL,
        "license_note": (
            "Candidate data is derived from Democracy Club. Check upstream field-level "
            "licensing and the linked source records before redistribution beyond this benchmark."
        ),
    }
    write_json(args.output_dir / "manifest.json", manifest)
    print(f"Wrote {len(questions)} questions and {len(labels)} labels to {args.output_dir}")


if __name__ == "__main__":
    main()
