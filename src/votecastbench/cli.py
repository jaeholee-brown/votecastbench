"""Command-line interface for running and scoring VoteCastBench."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from votecastbench.baselines import baseline_predictions
from votecastbench.env import load_env_file
from votecastbench.io import read_json, read_jsonl, write_json, write_jsonl
from votecastbench.panel import build_panel_manifest, pool_records
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

    baseline = subparsers.add_parser("baseline")
    baseline.add_argument("--questions", type=Path, default=Path("data/questions.jsonl"))
    baseline.add_argument("--output", type=Path, required=True)

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

    pool = subparsers.add_parser("pool")
    pool.add_argument("--questions", type=Path, default=Path("data/questions.jsonl"))
    pool.add_argument("--models", type=Path, default=Path("configs/models.json"))
    pool.add_argument("--input", action="append", type=Path, required=True, dest="inputs")
    pool.add_argument("--output", type=Path, required=True)

    panel = subparsers.add_parser("panel-report")
    panel.add_argument("--questions", type=Path, default=Path("data/questions.jsonl"))
    panel.add_argument("--models", type=Path, default=Path("configs/models.json"))
    panel.add_argument("--predictions", type=Path, required=True)
    panel.add_argument("--output", type=Path, required=True)
    panel.add_argument("--format", choices=["winner_only", "joint"], default="winner_only")
    panel.add_argument("--additional-historical-cost-usd", type=float, default=0.0)
    panel.add_argument(
        "--additional-cost",
        action="append",
        default=[],
        metavar="LABEL=USD",
    )
    panel.add_argument("--budget-reference-usd", type=float, default=50.0)
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
    if args.command == "baseline":
        write_jsonl(args.output, baseline_predictions(read_jsonl(args.questions)))
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
        return
    if args.command == "pool":
        questions = read_jsonl(args.questions)
        specs = read_json(args.models)
        rows = pool_records(
            [read_jsonl(path) for path in args.inputs],
            questions,
            specs,
        )
        write_jsonl(args.output, rows)
        print(f"pooled {len(rows)} observations into {args.output}")
        return
    if args.command == "panel-report":
        additional_costs = {}
        for item in args.additional_cost:
            label, separator, amount = item.partition("=")
            if not separator or not label:
                raise ValueError("--additional-cost must be LABEL=USD")
            additional_costs[label] = float(amount)
        manifest = build_panel_manifest(
            read_jsonl(args.questions),
            read_json(args.models),
            read_jsonl(args.predictions),
            output_format=args.format,
            additional_historical_cost_usd=args.additional_historical_cost_usd,
            additional_costs_usd=additional_costs,
            budget_reference_usd=args.budget_reference_usd,
        )
        write_json(args.output, manifest)
        print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
