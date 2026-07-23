"""Validation and provider-neutral output schemas."""

from __future__ import annotations

import math
from typing import Any, Literal

OutputFormat = Literal["winner_only", "joint"]


def candidate_ids(question: dict[str, Any]) -> list[str]:
    return [str(candidate["candidate_id"]) for candidate in question["candidates"]]


def validate_question(question: dict[str, Any]) -> None:
    required = {"question_id", "forecast_as_of", "question", "election", "candidates"}
    missing = required - question.keys()
    if missing:
        raise ValueError(f"question is missing fields: {sorted(missing)}")
    candidates = question["candidates"]
    if not isinstance(candidates, list) or len(candidates) < 2:
        raise ValueError("question must contain at least two candidates")
    ids = candidate_ids(question)
    if len(ids) != len(set(ids)):
        raise ValueError("candidate_id values must be unique within a question")
    if question["election"].get("seats") != 1:
        raise ValueError("v1 supports only single-winner questions")
    if question["election"].get("voting_system") != "FPTP":
        raise ValueError("v1 supports only first-past-the-post questions")


def forecast_json_schema(question: dict[str, Any], output_format: OutputFormat) -> dict[str, Any]:
    """Return the strict JSON schema supplied to providers."""
    ids = candidate_ids(question)
    probability_item = {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string", "enum": ids},
            "probability": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["candidate_id", "probability"],
        "additionalProperties": False,
    }
    properties: dict[str, Any] = {
        "winner_probabilities": {
            "type": "array",
            "items": probability_item,
            "minItems": len(ids),
            "maxItems": len(ids),
        },
        "rationale": {"type": "string"},
    }
    required = ["winner_probabilities", "rationale"]
    if output_format == "joint":
        properties["vote_shares"] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string", "enum": ids},
                    "percentage": {"type": "number", "minimum": 0, "maximum": 100},
                },
                "required": ["candidate_id", "percentage"],
                "additionalProperties": False,
            },
            "minItems": len(ids),
            "maxItems": len(ids),
        }
        properties["turnout_percentage"] = {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
        }
        required.extend(["vote_shares", "turnout_percentage"])
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _validate_distribution(
    rows: Any,
    ids: list[str],
    *,
    value_key: str,
    target_sum: float,
    tolerance: float,
) -> dict[str, float]:
    if not isinstance(rows, list):
        raise ValueError(f"{value_key} distribution must be a list")
    parsed: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict) or "candidate_id" not in row or value_key not in row:
            raise ValueError(f"malformed {value_key} row")
        candidate_id = str(row["candidate_id"])
        if candidate_id in parsed:
            raise ValueError(f"duplicate candidate_id in {value_key}: {candidate_id}")
        try:
            value = float(row[value_key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"non-numeric {value_key} for {candidate_id}") from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"invalid {value_key} for {candidate_id}")
        parsed[candidate_id] = value
    if set(parsed) != set(ids):
        raise ValueError(f"{value_key} candidate set does not match the question")
    total = sum(parsed.values())
    if abs(total - target_sum) > tolerance:
        raise ValueError(
            f"{value_key} values sum to {total:.6g}; expected {target_sum} ± {tolerance}"
        )
    if total <= 0:
        raise ValueError(f"{value_key} distribution has zero mass")
    scale = target_sum / total
    return {candidate_id: value * scale for candidate_id, value in parsed.items()}


def validate_forecast(
    forecast: dict[str, Any],
    question: dict[str, Any],
    output_format: OutputFormat,
) -> dict[str, Any]:
    """Validate and minimally normalise a forecast for scoring.

    Probability sums within 0.02 and vote-share sums within two percentage
    points are normalised exactly. Wider discrepancies are invalid.
    """
    ids = candidate_ids(question)
    probabilities = _validate_distribution(
        forecast.get("winner_probabilities"),
        ids,
        value_key="probability",
        target_sum=1.0,
        tolerance=0.02,
    )
    rationale = forecast.get("rationale")
    if not isinstance(rationale, str):
        raise ValueError("rationale must be a string")
    clean: dict[str, Any] = {
        "winner_probabilities": probabilities,
        "rationale": rationale,
    }
    if output_format == "joint":
        shares = _validate_distribution(
            forecast.get("vote_shares"),
            ids,
            value_key="percentage",
            target_sum=100.0,
            tolerance=2.0,
        )
        turnout = float(forecast["turnout_percentage"])
        if not math.isfinite(turnout) or not 0 <= turnout <= 100:
            raise ValueError("turnout_percentage must be in [0, 100]")
        clean["vote_shares"] = shares
        clean["turnout_percentage"] = turnout
    return clean
