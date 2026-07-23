"""Prompt construction for the protected and joint forecasting formats."""

from __future__ import annotations

import json
from typing import Any

from votecastbench.schemas import OutputFormat, forecast_json_schema

SYSTEM_PROMPT = """\
You are an election forecaster. Work only from the supplied forecast packet and
reason as of its forecast_as_of timestamp. Do not use web access, tools, or any
knowledge of the eventual result. Produce calibrated probabilities, reflecting
uncertainty rather than forcing confidence. Candidate IDs must be copied exactly.

Return only a JSON object matching the requested schema. The rationale may be as
long as useful; it has no requested word or token limit. Probabilities must sum
to 1. In the joint format, vote shares must sum to 100.
"""


def build_user_prompt(question: dict[str, Any], output_format: OutputFormat) -> str:
    objective = (
        "Estimate each candidate's probability of winning this single seat."
        if output_format == "winner_only"
        else (
            "Estimate each candidate's probability of winning, each candidate's "
            "share of valid candidate votes, and turnout."
        )
    )
    schema = forecast_json_schema(question, output_format)
    return "\n\n".join(
        [
            f"OBJECTIVE\n{objective}",
            "FORECAST PACKET\n"
            + json.dumps(question, ensure_ascii=False, indent=2, sort_keys=True),
            "OUTPUT JSON SCHEMA\n"
            + json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True),
        ]
    )
