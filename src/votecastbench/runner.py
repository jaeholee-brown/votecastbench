"""Highly concurrent, resumable benchmark execution."""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from votecastbench.io import read_jsonl, write_jsonl
from votecastbench.prompting import SYSTEM_PROMPT, build_user_prompt
from votecastbench.provenance import observation_id, provenance_fields
from votecastbench.providers import ProviderError, call_provider
from votecastbench.schemas import OutputFormat, validate_forecast


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        final_fence = stripped.rfind("```")
        if first_newline >= 0 and final_fence > first_newline:
            stripped = stripped[first_newline + 1 : final_fence].strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("provider output did not contain a JSON object") from None
        value = json.loads(stripped[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("provider output JSON is not an object")
    return value


def prompt_hash(system_prompt: str, user_prompt: str) -> str:
    return hashlib.sha256(f"{system_prompt}\n{user_prompt}".encode()).hexdigest()


async def _run_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    question: dict[str, Any],
    spec: dict[str, Any],
    output_format: OutputFormat,
    *,
    attempts: int,
) -> dict[str, Any]:
    user_prompt = build_user_prompt(question, output_format)
    digest = prompt_hash(SYSTEM_PROMPT, user_prompt)
    provenance = provenance_fields(question, spec, output_format, digest)
    started = time.perf_counter()
    errors = []
    for attempt in range(1, attempts + 1):
        try:
            async with semaphore:
                result = await call_provider(
                    client,
                    spec,
                    question,
                    output_format,
                    SYSTEM_PROMPT,
                    user_prompt,
                )
            forecast = extract_json_object(result.text)
            validate_forecast(forecast, question, output_format)
            return {
                "question_id": question["question_id"],
                "model": spec["id"],
                "provider": spec["provider"],
                "requested_model": spec["model"],
                "resolved_model": result.resolved_model,
                "output_format": output_format,
                "reasoning_effort": spec.get("reasoning_effort"),
                "thinking_mode": spec.get("thinking_mode"),
                "anthropic_effort": spec.get("anthropic_effort"),
                "thinking_budget_tokens": spec.get("thinking_budget_tokens"),
                "forecast": forecast,
                "provider_response_id": result.response_id,
                "usage": result.usage,
                "attempts": attempt,
                "latency_seconds": round(time.perf_counter() - started, 3),
                "generated_at": datetime.now(UTC).isoformat(),
                "prompt_sha256": digest,
                "status": "ok",
                **provenance,
            }
        except (httpx.HTTPError, ProviderError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            if attempt < attempts:
                delay = min(2 ** (attempt - 1), 8) + random.random()
                await asyncio.sleep(delay)
    return {
        "question_id": question["question_id"],
        "model": spec["id"],
        "provider": spec["provider"],
        "requested_model": spec["model"],
        "output_format": output_format,
        "reasoning_effort": spec.get("reasoning_effort"),
        "thinking_mode": spec.get("thinking_mode"),
        "anthropic_effort": spec.get("anthropic_effort"),
        "thinking_budget_tokens": spec.get("thinking_budget_tokens"),
        "attempts": attempts,
        "latency_seconds": round(time.perf_counter() - started, 3),
        "generated_at": datetime.now(UTC).isoformat(),
        "prompt_sha256": digest,
        "status": "error",
        "errors": errors,
        **provenance,
    }


async def run_benchmark(
    questions: list[dict[str, Any]],
    specs: list[dict[str, Any]],
    output_formats: list[OutputFormat],
    output_path: str | Path,
    *,
    concurrency: int = 32,
    attempts: int = 3,
) -> list[dict[str, Any]]:
    output = Path(output_path)
    existing = read_jsonl(output) if output.exists() else []
    completed = {
        row["observation_id"]
        for row in existing
        if row.get("status") == "ok" and row.get("observation_id")
    }
    jobs = [
        (question, spec, output_format)
        for question in questions
        for spec in specs
        for output_format in output_formats
        if observation_id(
            question,
            spec,
            output_format,
            prompt_hash(SYSTEM_PROMPT, build_user_prompt(question, output_format)),
        )
        not in completed
    ]
    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(
        max_connections=max(concurrency * 2, 64),
        max_keepalive_connections=max(concurrency, 32),
    )
    timeout = httpx.Timeout(600, connect=30)
    fresh = []
    output.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        tasks = [
            asyncio.create_task(
                _run_one(
                    client,
                    semaphore,
                    question,
                    spec,
                    output_format,
                    attempts=attempts,
                )
            )
            for question, spec, output_format in jobs
        ]
        for task in asyncio.as_completed(tasks):
            row = await task
            fresh.append(row)
            with output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            print(
                f"[{len(fresh)}/{len(tasks)}] {row['status']} {row['model']} "
                f"{row['output_format']} {row['question_id']}",
                flush=True,
            )
    combined_by_key = {
        row.get("observation_id") or (row["question_id"], row["model"], row["output_format"]): row
        for row in [*existing, *fresh]
    }
    combined = sorted(
        combined_by_key.values(),
        key=lambda row: (row["model"], row["output_format"], row["question_id"]),
    )
    write_jsonl(output, combined)
    return combined
