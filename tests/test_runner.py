import asyncio
import json

from votecastbench.providers import ProviderResult, _anthropic_compatible_schema
from votecastbench.runner import _run_one, extract_json_object


def test_extract_json_object_accepts_plain_json() -> None:
    assert extract_json_object('{"a": 1}') == {"a": 1}


def test_extract_json_object_accepts_fenced_json() -> None:
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_object_recovers_surrounding_text() -> None:
    assert extract_json_object('Result:\n{"a": 1}\nDone.') == {"a": 1}


def test_extract_json_object_rejects_non_object() -> None:
    try:
        extract_json_object(json.dumps([1, 2]))
    except ValueError as exc:
        assert "not an object" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_anthropic_schema_removes_unsupported_array_bounds() -> None:
    schema = {
        "type": "array",
        "minItems": 5,
        "maxItems": 5,
        "items": {
            "type": "object",
            "properties": {"probability": {"type": "number", "minimum": 0, "maximum": 1}},
        },
    }
    compatible = _anthropic_compatible_schema(schema)
    assert compatible == {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"probability": {"type": "number"}},
        },
    }


def test_anthropic_portable_schema_removes_question_specific_enums() -> None:
    schema = {
        "type": "object",
        "properties": {
            "candidate_id": {
                "type": "string",
                "enum": ["person.1", "person.2"],
            }
        },
    }
    compatible = _anthropic_compatible_schema(schema, strip_enums=True)
    assert compatible == {
        "type": "object",
        "properties": {"candidate_id": {"type": "string"}},
    }


def test_run_one_accounts_for_usage_from_invalid_retried_response(monkeypatch) -> None:
    responses = iter(
        [
            ProviderResult(
                text="not json",
                response_id="failed-response",
                usage={"input_tokens": 10, "output_tokens": 1},
                resolved_model="test-model",
            ),
            ProviderResult(
                text=json.dumps(
                    {
                        "winner_probabilities": [
                            {"candidate_id": "a", "probability": 0.6},
                            {"candidate_id": "b", "probability": 0.4},
                        ],
                        "rationale": "Test.",
                    }
                ),
                response_id="successful-response",
                usage={"input_tokens": 12, "output_tokens": 3},
                resolved_model="test-model",
            ),
        ]
    )

    async def fake_call_provider(*args, **kwargs):
        return next(responses)

    async def no_sleep(*args, **kwargs):
        return None

    monkeypatch.setattr("votecastbench.runner.call_provider", fake_call_provider)
    monkeypatch.setattr("votecastbench.runner.asyncio.sleep", no_sleep)
    question = {
        "question_id": "q",
        "forecast_as_of": "2026-05-01T00:00:00+00:00",
        "question": "Who wins?",
        "election": {"seats": 1, "voting_system": "FPTP"},
        "candidates": [{"candidate_id": "a"}, {"candidate_id": "b"}],
    }
    spec = {
        "id": "test/model",
        "provider": "openai",
        "model": "test-model",
        "reasoning_effort": "high",
    }
    row = asyncio.run(
        _run_one(
            None,
            asyncio.Semaphore(1),
            question,
            spec,
            "winner_only",
            attempts=2,
        )
    )

    assert row["status"] == "ok"
    assert row["usage"] == {"input_tokens": 22, "output_tokens": 4}
    assert [attempt["status"] for attempt in row["attempt_log"]] == ["error", "ok"]
