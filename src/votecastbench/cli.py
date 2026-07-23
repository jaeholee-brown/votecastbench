"""Command-line interface for running and scoring VoteCastBench."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from votecastbench.env import load_env_file
from votecastbench.io import read_json, read_jsonl, write_json
from votecastbench.runner import run_benchmark
from votecastbench.schemas import OutputFormat
from votecastbench.scoring import score_runs
from votecastbench.validation import validate_dataset


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="votecastbench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--questions", type=Path, default=Path("data/questions.jsonl"))
    validate.add_argument("--labels", type=Path, default=Path("data/labels.jsonl"))

    run = subparsers.add_parser("run")
    run.add_argument("--questions", type=Path, default=Path("data/questions.jsonl"))
    run.add_argument("--models", type=Path, default=Path("configs/models.json"))
    run.add_argument("--env-file", type=Path)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument(
        "--formats",
        nargs="+",
        choices=["winner_only", "joint"],
        default=["winner_only"],
    )
    run.add_argument("--model", action="append", dest="model_ids")
    run.add_argument("--limit", type=int)
    run.add_argument("--concurrency", type=int, default=32)
    run.add_argument("--attempts", type=int, default=3)

    score = subparsers.add_parser("score")
    score.add_argument("--questions", type=Path, default=Path("data/questions.jsonl"))
    score.add_argument("--labels", type=Path, default=Path("data/labels.jsonl"))
    score.add_argument("--predictions", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    return parser


def _load_specs(path: Path, model_ids: list[str] | None) -> list[dict[str, Any]]:
    specs = read_json(path)
    if model_ids:
        specs = [spec for spec in specs if spec["id"] in model_ids]
        missing = set(model_ids) - {spec["id"] for spec in specs}
        if missing:
            raise ValueError(f"unknown model IDs: {sorted(missing)}")
    return specs


def main() -> None:
    args = _parser().parse_args()
    if args.command == "validate":
        summary = validate_dataset(
            read_jsonl(args.questions),
            read_jsonl(args.labels),
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return
    if args.command == "run":
        if args.env_file:
            load_env_file(args.env_file)
        questions = read_jsonl(args.questions)
        if args.limit:
            questions = questions[: args.limit]
        specs = _load_specs(args.models, args.model_ids)
        asyncio.run(
            run_benchmark(
                questions,
                specs,
                list[OutputFormat](args.formats),
                args.output,
                concurrency=args.concurrency,
                attempts=args.attempts,
            )
        )
        return
    if args.command == "score":
        predictions = [row for row in read_jsonl(args.predictions) if row.get("status") == "ok"]
        report = score_runs(
            read_jsonl(args.questions),
            read_jsonl(args.labels),
            predictions,
        )
        write_json(args.output, report)
        print(json.dumps(report["groups"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
