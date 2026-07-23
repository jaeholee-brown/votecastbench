#!/usr/bin/env python3
"""Render the fresh-500 model panel and uncertainty into one durable table."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from votecastbench.io import read_json, read_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--uncertainty",
        type=Path,
        default=Path("results/fresh-500/uncertainty.json"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("results/fresh-500/manifest.json"),
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("data/expansion/questions-500.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/fresh-500/RESULTS.md"),
    )
    return parser.parse_args()


def interval(value: float, bounds: list[float], *, percentage: bool = False) -> str:
    scale = 100 if percentage else 1
    digits = 1 if percentage else 4
    return (
        f"{value * scale:.{digits}f} "
        f"[{bounds[0] * scale:.{digits}f}, {bounds[1] * scale:.{digits}f}]"
    )


def model_cost(row: dict[str, Any], manifest: dict[str, Any]) -> str:
    model = row["model"]
    if model.startswith("baseline/"):
        return "$0.000"
    return f"${manifest['models'][model]['estimated_cost_usd']:.3f}"


def main() -> None:
    args = parse_args()
    uncertainty = read_json(args.uncertainty)
    manifest = read_json(args.manifest)
    questions = read_jsonl(args.questions)
    no_ward_history = sum(not row["ward_history"] for row in questions)
    lines = [
        "# Fresh 500-question results",
        "",
        (
            "Primary metric: multiclass Brier score (lower is better). Accuracy is the "
            "fractional top-choice accuracy used by the scorer (higher is better). "
            "Brackets are paired 95% organisation-cluster bootstrap intervals."
        ),
        "",
        "| Rank | Forecaster | Brier [95% CI] | Accuracy % [95% CI] "
        "| Vote-share MAE | Fresh API cost |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for rank, row in enumerate(uncertainty["forecasters"], start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    row["model"],
                    interval(row["mean_brier_score"], row["brier_95_interval"]),
                    interval(
                        row["mean_top_choice_accuracy"],
                        row["top_choice_accuracy_95_interval"],
                        percentage=True,
                    ),
                    "N/A",
                    model_cost(row, manifest),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            (
                f"Fresh model-panel estimated cost: "
                f"${manifest['panel_estimated_cost_usd']:.6f}. "
                f"All-in cumulative estimated cost including prior work: "
                f"${manifest['cumulative_estimated_cost_usd']:.6f}."
            ),
            "",
            (
                "Vote-share MAE is N/A because the protected run requested only winner "
                "probabilities; winner probabilities are not reinterpreted as vote shares. "
                "Rationale length had no prompt-level limit."
            ),
            "",
            (
                f"The last-ward baseline uses a documented uniform fallback for the "
                f"{no_ward_history}/500 packets with no supplied same-ward history."
            ),
            "",
            (
                "Intervals resample 95 councils and capture question/organisation sampling "
                "uncertainty, not model sampling variance; every model-question cell has one "
                "successful forecast."
            ),
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
