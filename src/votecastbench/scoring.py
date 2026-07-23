"""Metric definitions for VoteCastBench."""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from votecastbench.schemas import OutputFormat, candidate_ids, validate_forecast


def score_forecast(
    question: dict[str, Any],
    label: dict[str, Any],
    forecast: dict[str, Any],
    output_format: OutputFormat,
) -> dict[str, Any]:
    clean = validate_forecast(forecast, question, output_format)
    ids = candidate_ids(question)
    winner_id = str(label["winner_candidate_id"])
    probabilities = clean["winner_probabilities"]
    brier = sum(
        (probabilities[candidate_id] - float(candidate_id == winner_id)) ** 2
        for candidate_id in ids
    )
    top_probability = max(probabilities.values())
    top_ids = {
        candidate_id
        for candidate_id, probability in probabilities.items()
        if abs(probability - top_probability) < 1e-12
    }
    result: dict[str, Any] = {
        "question_id": question["question_id"],
        "brier_score": brier,
        "top_choice_accuracy": float(winner_id in top_ids) / len(top_ids),
        "winner_probability": probabilities[winner_id],
    }
    if output_format == "joint":
        votes = {str(key): int(value) for key, value in label["votes"].items()}
        total_votes = sum(votes.values())
        actual_shares = {
            candidate_id: votes[candidate_id] * 100.0 / total_votes for candidate_id in ids
        }
        predicted_shares = clean["vote_shares"]
        result["vote_share_mae"] = statistics.fmean(
            abs(predicted_shares[candidate_id] - actual_shares[candidate_id])
            for candidate_id in ids
        )
        if label.get("turnout_percentage") is not None:
            result["turnout_mae"] = abs(
                clean["turnout_percentage"] - float(label["turnout_percentage"])
            )
    return result


def aggregate_scores(scores: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(scores)
    if not rows:
        raise ValueError("cannot aggregate an empty score set")
    metrics = [
        "brier_score",
        "top_choice_accuracy",
        "winner_probability",
        "vote_share_mae",
        "turnout_mae",
    ]
    aggregate: dict[str, Any] = {"n": len(rows)}
    for metric in metrics:
        values = [float(row[metric]) for row in rows if metric in row]
        if values:
            aggregate[f"mean_{metric}"] = statistics.fmean(values)
    return aggregate


def score_runs(
    questions: Iterable[dict[str, Any]],
    labels: Iterable[dict[str, Any]],
    predictions: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    question_map = {row["question_id"]: row for row in questions}
    label_map = {row["question_id"]: row for row in labels}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    errors: list[dict[str, str]] = []
    for prediction in predictions:
        question_id = prediction["question_id"]
        model = prediction["model"]
        output_format: OutputFormat = prediction["output_format"]
        try:
            score = score_forecast(
                question_map[question_id],
                label_map[question_id],
                prediction["forecast"],
                output_format,
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(
                {
                    "question_id": str(question_id),
                    "model": str(model),
                    "output_format": str(output_format),
                    "error": str(exc),
                }
            )
            continue
        score["model"] = model
        score["output_format"] = output_format
        grouped[(model, output_format)].append(score)
    groups = []
    details = []
    for (model, output_format), rows in sorted(grouped.items()):
        aggregate = aggregate_scores(rows)
        aggregate.update({"model": model, "output_format": output_format})
        groups.append(aggregate)
        details.extend(rows)
    return {"groups": groups, "details": details, "errors": errors}
