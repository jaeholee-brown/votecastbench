#!/usr/bin/env python3
"""Curate the resolved non-7-May 2026 temporal extension.

The extension keeps the fresh-500 task shape unchanged: English and Welsh
single-winner local FPTP contests, three to six candidates, a six-day forecast
horizon, and candidate/exact-post history drawn only from regular May
elections in 2021-2025.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from datetime import time as datetime_time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

import curate as legacy  # noqa: E402
import curate_expansion as expansion  # noqa: E402

from votecastbench.io import read_json, write_json, write_jsonl  # noqa: E402
from votecastbench.prompting import SYSTEM_PROMPT, build_user_prompt  # noqa: E402
from votecastbench.runner import prompt_hash  # noqa: E402
from votecastbench.validation import validate_dataset  # noqa: E402

EXPECTED_COUNT = 89
FORECAST_LEAD_DAYS = 6
SELECTION_SEED = "votecastbench-uk-local-non-may-89-v1"
DATES = [
    "2026-02-19",
    "2026-02-26",
    "2026-03-05",
    "2026-03-12",
    "2026-03-17",
    "2026-03-26",
    "2026-04-02",
    "2026-04-09",
    "2026-04-16",
    "2026-04-22",
    "2026-04-23",
    "2026-04-30",
    "2026-05-21",
    "2026-05-28",
    "2026-06-04",
    "2026-06-11",
    "2026-06-18",
    "2026-06-25",
    "2026-07-02",
    "2026-07-07",
    "2026-07-09",
    "2026-07-16",
]
LONDON = ZoneInfo("Europe/London")
RESULT_OVERRIDES: dict[str, dict[str, Any]] = {
    # Democracy Club's export linked to an authentication redirect and recorded
    # Riches at 515. Braintree's official declaration records 517.
    "local.braintree.coggeshall.by.2026-03-05": {
        "result_source": (
            "https://www.braintree.gov.uk/directory-record/1064716/"
            "coggeshall-ward-by-election-results---march-2026"
        ),
        "votes": {"30705": 517},
    },
    # The export duplicated the same URL.
    "local.kent.cliftonville.by.2026-04-09": {
        "result_source": (
            "https://democracy.kent.gov.uk:9071/"
            "mgElectionAreaResults.aspx?ID=779&RPID=309191594"
        ),
    },
    # The export concatenated a town-council page and the official declaration.
    "local.northumberland.cramlington-south-west.by.2026-04-16": {
        "result_source": (
            "https://www.northumberland.gov.uk/NorthumberlandCountyCouncil/media/"
            "Councillors-and-Democracy/Electoral%20Services/"
            "Declaration%20of%20Result%20of%20Poll%20-%20"
            "Cramlington%20South%20West.pdf"
        ),
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/non-may-89"))
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def forecast_as_of(election_date: str) -> str:
    target = date.fromisoformat(election_date) - timedelta(days=FORECAST_LEAD_DAYS)
    value = datetime.combine(target, datetime_time(23, 59, 59), tzinfo=LONDON)
    return value.isoformat()


def at_or_before(timestamp: str | None, cutoff: str) -> bool:
    if not timestamp:
        return False
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    boundary = datetime.fromisoformat(cutoff)
    return parsed <= boundary


def public_profile(row: dict[str, str], cutoff: str) -> dict[str, Any]:
    profile: dict[str, Any] = {"democracy_club_person_id": int(row["person_id"])}
    statement_updated = row.get("statement_last_updated")
    if at_or_before(statement_updated, cutoff) and row.get("statement_to_voters"):
        profile["statement_to_voters"] = row["statement_to_voters"]
        profile["statement_last_updated"] = statement_updated
    profile_updated = row.get("person_last_updated")
    if at_or_before(profile_updated, cutoff):
        links = {
            label: row[field].strip().strip('"')
            for field, label in legacy.PUBLIC_LINK_FIELDS.items()
            if row.get(field)
        }
        if links:
            profile["public_links"] = links
            profile["profile_last_updated"] = profile_updated
    return profile


def cached_date_ballots(
    client: httpx.Client,
    cache_dir: Path,
    election_date: str,
) -> list[dict[str, Any]]:
    target = cache_dir / "non-may-ballot-pages" / f"{election_date}.json"
    if target.exists():
        return read_json(target)
    response = None
    for attempt in range(10):
        response = client.get(
            f"{legacy.API_URL}/ballots/",
            params={"election_date": election_date, "page_size": 100},
        )
        if response.status_code < 400:
            break
        if response.status_code not in {403, 429} and response.status_code < 500:
            response.raise_for_status()
        retry_after = response.headers.get("retry-after")
        delay = float(retry_after) + 1 if retry_after else min(2**attempt, 30)
        time.sleep(delay)
    assert response is not None
    response.raise_for_status()
    page = response.json()
    records = list(page["results"])
    next_url = page.get("next")
    while next_url:
        response = client.get(next_url.replace("http://", "https://"))
        response.raise_for_status()
        page = response.json()
        records.extend(page["results"])
        next_url = page.get("next")
    write_json(target, records)
    return records


def question_id(ballot_id: str, election_date: str) -> str:
    return ballot_id.removeprefix("local.").removesuffix(f".{election_date}").replace(".", "_")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(
        follow_redirects=True,
        timeout=120,
        headers={"User-Agent": "VoteCastBench-curation/1.0"},
    ) as client:
        export_paths = {
            election_date: legacy.download_export(client, args.cache_dir, election_date)
            for election_date in [*legacy.HISTORICAL_DATES, *DATES]
        }
        historical_people, historical_posts, historical_rows = expansion.history_availability(
            args.cache_dir
        )
        historical_by_person: dict[str, list[dict[str, str]]] = defaultdict(list)
        historical_by_ballot: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in historical_rows:
            historical_by_person[row["person_id"]].append(row)
            historical_by_ballot[row["ballot_paper_id"]].append(row)

        current_by_ballot: dict[str, list[dict[str, str]]] = {}
        api_by_ballot: dict[str, dict[str, Any]] = {}
        exclusion_counts: Counter[str] = Counter()
        for election_date in DATES:
            current_rows = read_csv(export_paths[election_date])
            eligible, exclusions = expansion.preliminary_eligible(
                current_rows,
                historical_people,
                historical_posts,
            )
            exclusion_counts.update(exclusions)
            current_by_ballot.update(eligible)
            for ballot in cached_date_ballots(client, args.cache_dir, election_date):
                ballot_id = str(ballot["ballot_paper_id"])
                if ballot_id in eligible:
                    api_by_ballot[ballot_id] = ballot

    selected: list[str] = []
    api_exclusions: Counter[str] = Counter()
    for ballot_id, rows in sorted(current_by_ballot.items()):
        ballot = api_by_ballot.get(ballot_id)
        if ballot is None:
            api_exclusions["missing_api_record"] += 1
            continue
        election_date = rows[0]["election_date"]
        cutoff = forecast_as_of(election_date)
        candidacies = {str(value["person"]["id"]): value for value in ballot.get("candidacies", [])}
        checks = {
            "not_fptp": ballot.get("voting_system") != "FPTP",
            "not_one_winner": int(ballot.get("winner_count", 0)) != 1,
            "candidate_set_mismatch": set(candidacies) != {str(row["person_id"]) for row in rows},
            "candidate_source_missing": not (
                (ballot.get("sopn") or {}).get("source_url")
                or (ballot.get("sopn") or {}).get("uploaded_file")
            ),
            "post_cutoff_candidacy": any(
                not at_or_before(value.get("created"), cutoff) for value in candidacies.values()
            ),
        }
        failed = [name for name, failure in checks.items() if failure]
        if failed:
            api_exclusions.update(failed)
            continue
        selected.append(ballot_id)
    if len(selected) != EXPECTED_COUNT:
        raise ValueError(
            f"expected {EXPECTED_COUNT} selected ballots, found {len(selected)}; "
            f"API exclusions={dict(api_exclusions)}"
        )

    questions: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    api_lineage: dict[str, str] = {}
    for ballot_id in selected:
        rows = current_by_ballot[ballot_id]
        ballot = api_by_ballot[ballot_id]
        election_date = rows[0]["election_date"]
        cutoff = forecast_as_of(election_date)
        candidacies = {str(value["person"]["id"]): value for value in ballot["candidacies"]}
        candidates = []
        for row in sorted(rows, key=lambda value: int(value["person_id"])):
            person_id = str(row["person_id"])
            candidacy = candidacies[person_id]
            candidates.append(
                {
                    "candidate_id": person_id,
                    "name": row["person_name"],
                    "party": row["party_name"],
                    "ballot_description": row["party_description_text"] or None,
                    "candidacy_created": candidacy["created"],
                    "profile": public_profile(row, cutoff),
                    "prior_electoral_record": legacy.candidate_history(
                        person_id,
                        historical_by_person,
                        historical_by_ballot,
                    ),
                }
            )
        sopn = ballot.get("sopn") or {}
        source = sopn.get("source_url") or sopn.get("uploaded_file")
        if source == rows[0]["results_source"] and sopn.get("uploaded_file"):
            source = sopn["uploaded_file"]
        identifier = question_id(ballot_id, election_date)
        question = {
            "question_id": identifier,
            "forecast_as_of": cutoff,
            "question": (
                f"Who will win the {rows[0]['post_label']} ward in the "
                f"{ballot['election']['name']} on {election_date}?"
            ),
            "election": {
                "ballot_paper_id": ballot_id,
                "name": ballot["election"]["name"],
                "date": election_date,
                "organisation": rows[0]["organisation_name"],
                "ward": rows[0]["post_label"],
                "post_id": rows[0]["post_id"],
                "region": rows[0]["nuts1"].strip('"'),
                "voting_system": "FPTP",
                "seats": 1,
                "candidate_list_locked": True,
                "official_candidate_list_source": source,
            },
            "ward_history": legacy.ward_history(historical_rows, rows[0]["post_id"]),
            "candidates": candidates,
            "information_policy": {
                "included": [
                    "official candidate list known by forecast_as_of",
                    "Democracy Club candidate statements timestamped by forecast_as_of",
                    "public profile links when the profile was last updated by forecast_as_of",
                    "candidate and same-post regular May local-election results, 2021–2025",
                ],
                "excluded": [
                    "target result fields",
                    "post-forecast candidate statements and profile edits",
                    "structured 2026 election result tables and target labels",
                    "photos, gender, birth date, and inferred protected characteristics",
                    "web access or information not written in this packet",
                ],
            },
        }
        winners = [row for row in rows if row["elected"] == "t"]
        label: dict[str, Any] = {
            "question_id": identifier,
            "winner_candidate_id": winners[0]["person_id"],
            "votes": {row["person_id"]: int(row["votes_cast"]) for row in rows},
            "result_source": rows[0]["results_source"],
            "resolved_on": election_date,
            "turnout_percentage": (
                float(rows[0]["turnout_percentage"]) if rows[0].get("turnout_percentage") else None
            ),
        }
        override = RESULT_OVERRIDES.get(ballot_id, {})
        label["result_source"] = override.get("result_source", label["result_source"])
        label["votes"].update(override.get("votes", {}))
        prompt = build_user_prompt(question, "winner_only")
        for forbidden_key in ('"winner_candidate_id"', '"result_source"', '"resolved_on"'):
            if forbidden_key in prompt:
                raise ValueError(f"{identifier}: target-only key appears in prompt")
        if json.dumps(label["result_source"]) in prompt:
            raise ValueError(f"{identifier}: result source appears in prompt")
        questions.append(question)
        labels.append(label)

        relative_url = f"ballots/{ballot_id}/"
        target = (
            args.cache_dir / "api" / f"{hashlib.sha256(relative_url.encode()).hexdigest()}.json"
        )
        write_json(target, ballot)
        api_lineage[ballot_id] = file_sha256(target)

    summary = validate_dataset(
        questions,
        labels,
        expected_count=EXPECTED_COUNT,
        require_profile_timestamps=True,
    )
    questions_path = args.output_dir / "questions.jsonl"
    labels_path = args.output_dir / "labels.jsonl"
    write_jsonl(questions_path, questions)
    write_jsonl(labels_path, labels)
    write_json(args.output_dir / "api-lineage.json", api_lineage)
    write_json(
        args.output_dir / "selection.json",
        {
            "dataset_revision": "VoteCastBench UK Local non-May temporal extension v1",
            "selection_seed": SELECTION_SEED,
            "selection_uses_outcome_identity_party_margin_or_turnout": False,
            "selection_design": (
                "Enumerate every covered non-7-May local contest from 2026-02-19 "
                "through 2026-07-16 and retain all cases passing the benchmark's "
                "existing structural, source, history, and API-time gates."
            ),
            "forecast_lead_days": FORECAST_LEAD_DAYS,
            "election_dates": DATES,
            "eligibility": [
                "target date after 2026-02-16 and not 2026-05-07",
                "three to six candidates",
                "one locked, non-cancelled FPTP seat",
                "complete non-tied uniquely resolvable result and result source",
                "usable 2021–2025 candidate or exact-post history",
                "every candidacy created by its six-day forecast cutoff",
                "official or archived official candidate-list source",
            ],
            "question_count": len(selected),
            "ballot_paper_ids": selected,
            "candidate_count_distribution": dict(
                sorted(Counter(len(current_by_ballot[value]) for value in selected).items())
            ),
            "date_distribution": dict(
                sorted(
                    Counter(
                        current_by_ballot[value][0]["election_date"] for value in selected
                    ).items()
                )
            ),
            "csv_exclusion_counts_nonexclusive": dict(sorted(exclusion_counts.items())),
            "api_exclusion_counts_nonexclusive": dict(sorted(api_exclusions.items())),
            "source_csv_sha256": {
                election_date: file_sha256(export_paths[election_date])
                for election_date in [*legacy.HISTORICAL_DATES, *DATES]
            },
        },
    )
    write_json(
        args.output_dir / "audit-report.json",
        {
            "status": "pass",
            "launch_gate_passed": True,
            "dataset_summary": summary,
            "rendered_prompts_checked": len(questions),
            "unique_prompt_hashes": len(
                {
                    prompt_hash(
                        SYSTEM_PROMPT,
                        build_user_prompt(question, "winner_only"),
                    )
                    for question in questions
                }
            ),
            "provider_web_tools_attached": False,
            "rationale_length_restriction_present": False,
            "forecast_lead_days": FORECAST_LEAD_DAYS,
            "questions_sha256": file_sha256(questions_path),
            "labels_sha256": file_sha256(labels_path),
            "api_lineage_sha256": file_sha256(args.output_dir / "api-lineage.json"),
            "generated_at": datetime.now(UTC).isoformat(),
        },
    )
    print(f"Curated and validated {len(questions)} non-May questions: {summary}")


if __name__ == "__main__":
    main()
