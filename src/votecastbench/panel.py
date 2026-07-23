"""Pooling, coverage, and cost accounting for durable result panels."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from votecastbench.prompting import SYSTEM_PROMPT, build_user_prompt
from votecastbench.provenance import (
    BENCHMARK_ID,
    BENCHMARK_VERSION,
    canonical_sha256,
    inference_config,
    provenance_fields,
)
from votecastbench.runner import prompt_hash


def enrich_record(
    record: dict[str, Any],
    questions: dict[str, dict[str, Any]],
    specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    question = questions[str(record["question_id"])]
    spec = specs[str(record["model"])]
    output_format = str(record["output_format"])
    digest = record.get("prompt_sha256") or prompt_hash(
        SYSTEM_PROMPT,
        build_user_prompt(question, output_format),
    )
    generated = provenance_fields(question, spec, output_format, digest)
    return {
        **generated,
        **record,
        "prompt_sha256": digest,
    }


def pool_records(
    inputs: list[list[dict[str, Any]]],
    questions: list[dict[str, Any]],
    specs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    question_map = {str(row["question_id"]): row for row in questions}
    spec_map = {str(row["id"]): row for row in specs}
    by_observation: dict[str, dict[str, Any]] = {}
    cell_ids: dict[tuple[str, str, str], str] = {}
    for rows in inputs:
        for raw in rows:
            row = enrich_record(raw, question_map, spec_map)
            observation = str(row["observation_id"])
            cell = (
                str(row["question_id"]),
                str(row["model"]),
                str(row["output_format"]),
            )
            prior_observation = cell_ids.get(cell)
            if prior_observation and prior_observation != observation:
                raise ValueError(
                    "conflicting inference configurations for panel cell "
                    f"{cell}: {prior_observation} != {observation}"
                )
            cell_ids[cell] = observation
            prior = by_observation.get(observation)
            if prior is None or (prior.get("status") != "ok" and row.get("status") == "ok"):
                by_observation[observation] = row
    return sorted(
        by_observation.values(),
        key=lambda row: (row["model"], row["output_format"], row["question_id"]),
    )


def estimate_record_cost(record: dict[str, Any], spec: dict[str, Any]) -> float:
    usage = record.get("usage", {})
    pricing = spec["pricing_usd_per_million_tokens"]
    input_tokens = int(usage.get("input_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    return (
        input_tokens * float(pricing["input"]) + output_tokens * float(pricing["output"])
    ) / 1_000_000


def build_panel_manifest(
    questions: list[dict[str, Any]],
    specs: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    output_format: str = "winner_only",
    additional_historical_cost_usd: float = 0.0,
    additional_costs_usd: dict[str, float] | None = None,
    budget_reference_usd: float = 50.0,
) -> dict[str, Any]:
    question_ids = [str(row["question_id"]) for row in questions]
    model_ids = [str(row["id"]) for row in specs]
    spec_map = {str(row["id"]): row for row in specs}
    selected = [
        row
        for row in predictions
        if row.get("output_format") == output_format and row.get("model") in spec_map
    ]
    cell_map = {
        (str(row["question_id"]), str(row["model"])): row
        for row in selected
        if row.get("status") == "ok"
    }
    missing = [
        {"question_id": question_id, "model": model_id}
        for model_id in model_ids
        for question_id in question_ids
        if (question_id, model_id) not in cell_map
    ]
    errors = [
        {
            "question_id": row.get("question_id"),
            "model": row.get("model"),
            "errors": row.get("errors", []),
        }
        for row in selected
        if row.get("status") == "error"
    ]
    model_costs: dict[str, float] = defaultdict(float)
    token_usage: dict[str, dict[str, int]] = defaultdict(
        lambda: {"input_tokens": 0, "output_tokens": 0}
    )
    for row in cell_map.values():
        model_id = str(row["model"])
        model_costs[model_id] += estimate_record_cost(row, spec_map[model_id])
        usage = row.get("usage", {})
        token_usage[model_id]["input_tokens"] += int(usage.get("input_tokens", 0))
        token_usage[model_id]["output_tokens"] += int(usage.get("output_tokens", 0))
    panel_cost = sum(model_costs.values())
    additional_costs = dict(additional_costs_usd or {})
    if additional_historical_cost_usd:
        additional_costs["historical_non_panel_calls"] = additional_historical_cost_usd
    additional_cost_total = sum(additional_costs.values())
    cumulative_cost = panel_cost + additional_cost_total
    return {
        "benchmark_id": BENCHMARK_ID,
        "benchmark_version": BENCHMARK_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "output_format": output_format,
        "question_count": len(question_ids),
        "model_count": len(model_ids),
        "expected_observations": len(question_ids) * len(model_ids),
        "completed_observations": len(cell_map),
        "missing_observations": missing,
        "error_observations": errors,
        "question_sha256": {str(row["question_id"]): canonical_sha256(row) for row in questions},
        "models": {
            model_id: {
                "inference_config": inference_config(spec_map[model_id]),
                "inference_config_sha256": canonical_sha256(inference_config(spec_map[model_id])),
                "usage": token_usage[model_id],
                "estimated_cost_usd": round(model_costs[model_id], 6),
            }
            for model_id in model_ids
        },
        "panel_estimated_cost_usd": round(panel_cost, 6),
        "additional_costs_usd": {
            label: round(cost, 6) for label, cost in sorted(additional_costs.items())
        },
        "additional_cost_total_usd": round(additional_cost_total, 6),
        "cumulative_estimated_cost_usd": round(cumulative_cost, 6),
        "budget_reference_usd": budget_reference_usd,
        "within_budget_reference": cumulative_cost <= budget_reference_usd,
        "cost_is_estimate": True,
    }
