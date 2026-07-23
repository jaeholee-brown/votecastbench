"""Async provider adapters used by the benchmark runner."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

from votecastbench.schemas import OutputFormat, forecast_json_schema


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderResult:
    text: str
    response_id: str | None
    usage: dict[str, Any]
    resolved_model: str | None


def _openai_output_text(response: dict[str, Any]) -> str:
    parts = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    if not parts:
        raise ProviderError("OpenAI response contained no output_text")
    return "".join(parts)


async def call_openai(
    client: httpx.AsyncClient,
    spec: dict[str, Any],
    question: dict[str, Any],
    output_format: OutputFormat,
    system_prompt: str,
    user_prompt: str,
) -> ProviderResult:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ProviderError("OPENAI_API_KEY is not set")
    body = {
        "model": spec["model"],
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            },
        ],
        "max_output_tokens": int(spec.get("max_output_tokens", 12000)),
        "reasoning": {"effort": spec.get("reasoning_effort", "high")},
        "text": {
            "format": {
                "type": "json_schema",
                "name": f"votecast_{output_format}",
                "strict": True,
                "schema": forecast_json_schema(question, output_format),
            }
        },
    }
    response = await client.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}"},
        json=body,
    )
    if response.is_error:
        raise ProviderError(f"OpenAI HTTP {response.status_code}: {response.text[:1000]}")
    value = response.json()
    return ProviderResult(
        text=_openai_output_text(value),
        response_id=value.get("id"),
        usage=value.get("usage", {}),
        resolved_model=value.get("model"),
    )


async def call_anthropic(
    client: httpx.AsyncClient,
    spec: dict[str, Any],
    question: dict[str, Any],
    output_format: OutputFormat,
    system_prompt: str,
    user_prompt: str,
) -> ProviderResult:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ProviderError("ANTHROPIC_API_KEY is not set")
    schema = forecast_json_schema(question, output_format)
    body: dict[str, Any] = {
        "model": spec["model"],
        "max_tokens": int(spec.get("max_output_tokens", 12000)),
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"{user_prompt}\n\nReturn only the object described by this schema:\n"
                    f"{json.dumps(schema, ensure_ascii=False)}"
                ),
            }
        ],
    }
    thinking_mode = spec.get("thinking_mode")
    thinking_budget = spec.get("thinking_budget_tokens")
    if thinking_mode == "adaptive":
        body["thinking"] = {"type": "adaptive"}
    elif thinking_mode == "manual" or thinking_budget:
        body["thinking"] = {"type": "enabled", "budget_tokens": int(thinking_budget)}
    if spec.get("structured_output"):
        output_config: dict[str, Any] = {"format": {"type": "json_schema", "schema": schema}}
        if spec.get("anthropic_effort"):
            output_config["effort"] = spec["anthropic_effort"]
        body["output_config"] = output_config
    response = await client.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json=body,
    )
    if response.is_error:
        raise ProviderError(f"Anthropic HTTP {response.status_code}: {response.text[:1000]}")
    value = response.json()
    text_parts = [
        block["text"]
        for block in value.get("content", [])
        if block.get("type") == "text" and block.get("text")
    ]
    if not text_parts:
        raise ProviderError("Anthropic response contained no text block")
    return ProviderResult(
        text="".join(text_parts),
        response_id=value.get("id"),
        usage=value.get("usage", {}),
        resolved_model=value.get("model"),
    )


async def call_provider(
    client: httpx.AsyncClient,
    spec: dict[str, Any],
    question: dict[str, Any],
    output_format: OutputFormat,
    system_prompt: str,
    user_prompt: str,
) -> ProviderResult:
    if spec["provider"] == "openai":
        return await call_openai(
            client,
            spec,
            question,
            output_format,
            system_prompt,
            user_prompt,
        )
    if spec["provider"] == "anthropic":
        return await call_anthropic(
            client,
            spec,
            question,
            output_format,
            system_prompt,
            user_prompt,
        )
    raise ProviderError(f"unsupported provider: {spec['provider']}")
