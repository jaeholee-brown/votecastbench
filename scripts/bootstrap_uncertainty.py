#!/usr/bin/env python3
"""Rebuild paired-bootstrap uncertainty estimates for the score panel."""

from __future__ import annotations

import argparse
from pathlib import Path

from votecastbench.io import write_json
from votecastbench.uncertainty import (
    bootstrap_report,
    load_brier_matrix,
    load_metric_matrix,
    load_organisation_ids,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scores",
        type=Path,
        action="append",
        default=None,
    )
    parser.add_argument(
        "--questions",
        type=Path,
        help=(
            "Question JSONL used to resample by election.organisation. "
            "If omitted, resample individual questions."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/panel/uncertainty.json"),
    )
    parser.add_argument("--replicates", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20260723)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    score_paths = args.scores or [
        Path("results/panel/scores.json"),
        Path("results/baselines/scores.json"),
    ]
    model_ids, question_ids, matrix = load_brier_matrix(score_paths)
    accuracy_model_ids, accuracy_question_ids, accuracy_matrix = load_metric_matrix(
        score_paths,
        "top_choice_accuracy",
    )
    if (accuracy_model_ids, accuracy_question_ids) != (model_ids, question_ids):
        raise ValueError("accuracy scores do not align with Brier scores")
    organisation_ids = (
        load_organisation_ids(args.questions, question_ids) if args.questions else None
    )
    report = bootstrap_report(
        model_ids,
        question_ids,
        matrix,
        replicates=args.replicates,
        seed=args.seed,
        organisation_ids=organisation_ids,
        accuracy_matrix=accuracy_matrix,
    )
    write_json(args.output, report)


if __name__ == "__main__":
    main()
