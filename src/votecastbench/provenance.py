"""Stable identities and provenance for appendable benchmark observations."""

from __future__ import annotations

import hashlib
import json
from typing import Any

BENCHMARK_ID = "votecastbench.uk_local"
BENCHMARK_VERSION = "1.0.0"
RECORD_SCHEMA_VERSION = "1.1.0"


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def inference_config(spec: dict[str, Any]) -> dict[str, Any]:
    provider = str(spec["provider"])
    if provider == "openai":
        adapter_version = "openai-responses-v1"
    elif spec.get("structured_output"):
        schema_mode = str(spec.get("anthropic_schema_mode", "exact"))
        if schema_mode == "portable":
            adapter_version = "anthropic-messages-structured-portable-v2"
        else:
            adapter_version = "anthropic-messages-structured-v1"
    else:
        adapter_version = "anthropic-messages-v1"
    config = {
        "provider": provider,
        "requested_model": spec["model"],
        "adapter_version": adapter_version,
        "reasoning_effort": spec.get("reasoning_effort"),
        "thinking_mode": spec.get("thinking_mode"),
        "anthropic_effort": spec.get("anthropic_effort"),
        "thinking_budget_tokens": spec.get("thinking_budget_tokens"),
        "structured_output": bool(spec.get("structured_output", False)),
        "max_output_tokens": int(spec.get("max_output_tokens", 12000)),
    }
    if provider == "anthropic" and spec.get("structured_output"):
        config["anthropic_schema_mode"] = str(spec.get("anthropic_schema_mode", "exact"))
    return config


def observation_id(
    question: dict[str, Any],
    spec: dict[str, Any],
    output_format: str,
    prompt_sha256: str,
) -> str:
    return canonical_sha256(
        {
            "benchmark_id": BENCHMARK_ID,
            "benchmark_version": BENCHMARK_VERSION,
            "question_sha256": canonical_sha256(question),
            "model": spec["id"],
            "output_format": output_format,
            "prompt_sha256": prompt_sha256,
            "inference_config_sha256": canonical_sha256(inference_config(spec)),
        }
    )


def provenance_fields(
    question: dict[str, Any],
    spec: dict[str, Any],
    output_format: str,
    prompt_sha256: str,
) -> dict[str, Any]:
    config = inference_config(spec)
    return {
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "benchmark_version": BENCHMARK_VERSION,
        "question_sha256": canonical_sha256(question),
        "inference_config": config,
        "inference_config_sha256": canonical_sha256(config),
        "observation_id": observation_id(question, spec, output_format, prompt_sha256),
    }
