#!/usr/bin/env python3
"""Rebuild paired-bootstrap uncertainty estimates for the score panel."""

from __future__ import annotations

import argparse
from pathlib import Path

from votecastbench.io import write_json
from votecastbench.uncertainty import bootstrap_report, load_brier_matrix


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scores",
        type=Path,
        action="append",
        default=[
            Path("results/panel/scores.json"),
            Path("results/baselines/scores.json"),
        ],
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
    model_ids, question_ids, matrix = load_brier_matrix(args.scores)
    report = bootstrap_report(
        model_ids,
        question_ids,
        matrix,
        replicates=args.replicates,
        seed=args.seed,
    )
    write_json(args.output, report)


if __name__ == "__main__":
    main()
