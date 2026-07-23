"""Paired-bootstrap uncertainty for benchmark score panels."""

from __future__ import annotations

import random
from collections import Counter
from pathlib import Path
from typing import Any

from votecastbench.io import read_json, read_jsonl


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


def load_metric_matrix(
    paths: list[Path],
    metric: str,
) -> tuple[list[str], list[str], list[list[float]]]:
    details = []
    for path in paths:
        details.extend(read_json(path)["details"])
    model_ids = sorted({str(row["model"]) for row in details})
    by_model: dict[str, dict[str, float]] = {model_id: {} for model_id in model_ids}
    for row in details:
        by_model[str(row["model"])][str(row["question_id"])] = float(row[metric])
    question_sets = {tuple(sorted(rows)) for rows in by_model.values()}
    if len(question_sets) != 1:
        raise ValueError("all forecasters must have scores for the same questions")
    question_ids = list(next(iter(question_sets)))
    matrix = [
        [by_model[model_id][question_id] for question_id in question_ids] for model_id in model_ids
    ]
    return model_ids, question_ids, matrix


def load_brier_matrix(paths: list[Path]) -> tuple[list[str], list[str], list[list[float]]]:
    return load_metric_matrix(paths, "brier_score")


def load_organisation_ids(path: Path, question_ids: list[str]) -> list[str]:
    """Load election organisations aligned to an ordered set of question IDs."""
    by_question: dict[str, str] = {}
    for row in read_jsonl(path):
        question_id = str(row.get("question_id", ""))
        if not question_id:
            raise ValueError(f"{path}: question is missing question_id")
        if question_id in by_question:
            raise ValueError(f"{path}: duplicate question_id {question_id!r}")
        election = row.get("election")
        organisation = election.get("organisation") if isinstance(election, dict) else None
        if not isinstance(organisation, str) or not organisation.strip():
            raise ValueError(f"{path}: question {question_id!r} is missing election.organisation")
        by_question[question_id] = organisation

    missing = sorted(set(question_ids) - set(by_question))
    if missing:
        raise ValueError(f"{path}: missing scored question IDs: {missing}")
    return [by_question[question_id] for question_id in question_ids]


def _resampling_groups(
    question_ids: list[str],
    organisation_ids: list[str] | None,
) -> tuple[list[list[int]], str]:
    if organisation_ids is None:
        return [[index] for index in range(len(question_ids))], "question"
    if len(organisation_ids) != len(question_ids):
        raise ValueError("organisation_ids must align one-to-one with question_ids")
    if any(not organisation_id for organisation_id in organisation_ids):
        raise ValueError("organisation_ids cannot contain empty values")
    by_organisation: dict[str, list[int]] = {}
    for index, organisation_id in enumerate(organisation_ids):
        by_organisation.setdefault(organisation_id, []).append(index)
    return list(by_organisation.values()), "organisation"


def bootstrap_report(
    model_ids: list[str],
    question_ids: list[str],
    matrix: list[list[float]],
    *,
    replicates: int,
    seed: int,
    organisation_ids: list[str] | None = None,
    accuracy_matrix: list[list[float]] | None = None,
) -> dict[str, Any]:
    randomizer = random.Random(seed)
    question_count = len(question_ids)
    groups, resampling_unit = _resampling_groups(question_ids, organisation_ids)
    group_count = len(groups)
    samples = [[] for _ in model_ids]
    accuracy_samples = [[] for _ in model_ids] if accuracy_matrix is not None else None
    api_indexes = [
        index for index, model_id in enumerate(model_ids) if not model_id.startswith("baseline/")
    ]
    rank_counts = {index: Counter() for index in api_indexes}
    best_credit = Counter()
    for _ in range(replicates):
        selected_groups = [groups[randomizer.randrange(group_count)] for _ in range(group_count)]
        selected = [index for group in selected_groups for index in group]
        replicate_question_count = len(selected)
        means = [
            sum(values[index] for index in selected) / replicate_question_count
            for values in matrix
        ]
        for index, mean in enumerate(means):
            samples[index].append(mean)
        if accuracy_matrix is not None and accuracy_samples is not None:
            accuracy_means = [
                sum(values[index] for index in selected) / replicate_question_count
                for values in accuracy_matrix
            ]
            for index, mean in enumerate(accuracy_means):
                accuracy_samples[index].append(mean)
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
        if accuracy_matrix is not None and accuracy_samples is not None:
            ordered_accuracy = sorted(accuracy_samples[index])
            result.update(
                {
                    "mean_top_choice_accuracy": sum(accuracy_matrix[index])
                    / question_count,
                    "top_choice_accuracy_95_interval": [
                        percentile(ordered_accuracy, 0.025),
                        percentile(ordered_accuracy, 0.975),
                    ],
                }
            )
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
    clustered = resampling_unit == "organisation"
    notes = (
        [
            "Every replicate resamples the same organisation clusters for every forecaster.",
            (
                "Each sampled organisation contributes all of its questions; organisations are "
                "sampled with replacement."
            ),
            "Intervals capture organisation-sampling uncertainty only.",
            "They do not capture model sampling variance because each cell has one API call.",
        ]
        if clustered
        else [
            "Every replicate resamples the same question indices for every forecaster.",
            "Intervals capture question-sampling uncertainty only.",
            "They do not capture model sampling variance because each cell has one API call.",
            "The 20 questions are purposively curated rather than an IID random sample.",
        ]
    )
    return {
        "method": (
            "paired nonparametric cluster bootstrap over organisations"
            if clustered
            else "paired nonparametric bootstrap over questions"
        ),
        "resampling_unit": resampling_unit,
        "interval": "percentile 95%",
        "replicates": replicates,
        "seed": seed,
        "question_count": question_count,
        "organisation_count": group_count if clustered else None,
        "notes": notes,
        "forecasters": sorted(results, key=lambda row: row["mean_brier_score"]),
    }
