"""Question-level paired bootstrap uncertainty for benchmark score panels."""

from __future__ import annotations

import random
from collections import Counter
from pathlib import Path
from typing import Any

from votecastbench.io import read_json


def percentile(sorted_values: list[float], probability: float) -> float:
    position = probability * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def discrete_percentile(counts: Counter[int], probability: float) -> int:
    target = probability * sum(counts.values())
    cumulative = 0
    for value, count in sorted(counts.items()):
        cumulative += count
        if cumulative >= target:
            return value
    return max(counts)


def load_brier_matrix(paths: list[Path]) -> tuple[list[str], list[str], list[list[float]]]:
    details = []
    for path in paths:
        details.extend(read_json(path)["details"])
    model_ids = sorted({str(row["model"]) for row in details})
    by_model: dict[str, dict[str, float]] = {model_id: {} for model_id in model_ids}
    for row in details:
        by_model[str(row["model"])][str(row["question_id"])] = float(row["brier_score"])
    question_sets = {tuple(sorted(rows)) for rows in by_model.values()}
    if len(question_sets) != 1:
        raise ValueError("all forecasters must have scores for the same questions")
    question_ids = list(next(iter(question_sets)))
    matrix = [
        [by_model[model_id][question_id] for question_id in question_ids] for model_id in model_ids
    ]
    return model_ids, question_ids, matrix


def bootstrap_report(
    model_ids: list[str],
    question_ids: list[str],
    matrix: list[list[float]],
    *,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    randomizer = random.Random(seed)
    question_count = len(question_ids)
    samples = [[] for _ in model_ids]
    api_indexes = [
        index for index, model_id in enumerate(model_ids) if not model_id.startswith("baseline/")
    ]
    rank_counts = {index: Counter() for index in api_indexes}
    best_credit = Counter()
    for _ in range(replicates):
        selected = [randomizer.randrange(question_count) for _ in range(question_count)]
        means = [sum(values[index] for index in selected) / question_count for values in matrix]
        for index, mean in enumerate(means):
            samples[index].append(mean)
        ordered = sorted(api_indexes, key=lambda index: (means[index], model_ids[index]))
        for rank, index in enumerate(ordered, start=1):
            rank_counts[index][rank] += 1
        best_value = means[ordered[0]]
        best_indexes = [index for index in ordered if abs(means[index] - best_value) < 1e-15]
        for index in best_indexes:
            best_credit[index] += 1 / len(best_indexes)

    baseline_index = model_ids.index("baseline/last-ward-party-share")
    luna_index = model_ids.index("openai/gpt-5.6-luna")
    results = []
    for index, model_id in enumerate(model_ids):
        ordered_samples = sorted(samples[index])
        result: dict[str, Any] = {
            "model": model_id,
            "mean_brier_score": sum(matrix[index]) / question_count,
            "brier_95_interval": [
                percentile(ordered_samples, 0.025),
                percentile(ordered_samples, 0.975),
            ],
        }
        if index in rank_counts:
            counts = rank_counts[index]
            result.update(
                {
                    "mean_api_rank": sum(rank * count for rank, count in counts.items())
                    / replicates,
                    "api_rank_95_interval": [
                        discrete_percentile(counts, 0.025),
                        discrete_percentile(counts, 0.975),
                    ],
                    "probability_best_api_model": best_credit[index] / replicates,
                    "probability_beats_last_ward_baseline": sum(
                        value < baseline
                        for value, baseline in zip(
                            samples[index],
                            samples[baseline_index],
                            strict=True,
                        )
                    )
                    / replicates,
                }
            )
            deltas = sorted(
                value - luna
                for value, luna in zip(
                    samples[index],
                    samples[luna_index],
                    strict=True,
                )
            )
            result["brier_delta_vs_luna"] = (
                sum(
                    matrix[index][question] - matrix[luna_index][question]
                    for question in range(question_count)
                )
                / question_count
            )
            result["brier_delta_vs_luna_95_interval"] = [
                percentile(deltas, 0.025),
                percentile(deltas, 0.975),
            ]
        results.append(result)
    return {
        "method": "paired nonparametric bootstrap over questions",
        "interval": "percentile 95%",
        "replicates": replicates,
        "seed": seed,
        "question_count": question_count,
        "notes": [
            "Every replicate resamples the same question indices for every forecaster.",
            "Intervals capture question-sampling uncertainty only.",
            "They do not capture model sampling variance because each cell has one API call.",
            "The 20 questions are purposively curated rather than an IID random sample.",
        ],
        "forecasters": sorted(results, key=lambda row: row["mean_brier_score"]),
    }
