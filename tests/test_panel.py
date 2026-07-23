from votecastbench.panel import build_panel_manifest, estimate_record_cost, pool_records
from votecastbench.provenance import canonical_sha256, inference_config

QUESTION = {"question_id": "q1", "question": "Who wins?", "candidates": []}
SPEC = {
    "id": "openai/example",
    "provider": "openai",
    "model": "example-snapshot",
    "reasoning_effort": "high",
    "max_output_tokens": 12000,
    "pricing_usd_per_million_tokens": {"input": 2.0, "output": 10.0},
}


def test_inference_hash_ignores_pricing() -> None:
    changed_price = {
        **SPEC,
        "pricing_usd_per_million_tokens": {"input": 200.0, "output": 1000.0},
    }
    assert canonical_sha256(inference_config(SPEC)) == canonical_sha256(
        inference_config(changed_price)
    )


def test_pool_enriches_legacy_record() -> None:
    legacy = {
        "question_id": "q1",
        "model": "openai/example",
        "output_format": "winner_only",
        "status": "ok",
        "forecast": {"winner_probabilities": [], "rationale": ""},
        "usage": {"input_tokens": 100, "output_tokens": 20},
    }
    rows = pool_records([[legacy]], [QUESTION], [SPEC])
    assert len(rows) == 1
    assert rows[0]["benchmark_version"] == "1.0.0"
    assert len(rows[0]["observation_id"]) == 64


def test_pool_preserves_existing_provenance() -> None:
    record = {
        "question_id": "q1",
        "model": "openai/example",
        "output_format": "winner_only",
        "status": "ok",
        "forecast": {"winner_probabilities": [], "rationale": ""},
        "usage": {"input_tokens": 100, "output_tokens": 20},
        "benchmark_version": "old-version",
        "question_sha256": "old-question-hash",
        "inference_config": {"adapter_version": "old-adapter"},
        "inference_config_sha256": "old-config-hash",
        "observation_id": "old-observation-id",
    }
    rows = pool_records([[record]], [QUESTION], [SPEC])
    assert rows[0]["benchmark_version"] == "old-version"
    assert rows[0]["question_sha256"] == "old-question-hash"
    assert rows[0]["inference_config"]["adapter_version"] == "old-adapter"
    assert rows[0]["observation_id"] == "old-observation-id"


def test_cost_and_manifest_coverage() -> None:
    record = {
        "question_id": "q1",
        "model": "openai/example",
        "output_format": "winner_only",
        "status": "ok",
        "usage": {"input_tokens": 100_000, "output_tokens": 20_000},
    }
    assert estimate_record_cost(record, SPEC) == 0.4
    manifest = build_panel_manifest(
        [QUESTION],
        [SPEC],
        [record],
        additional_historical_cost_usd=0.6,
        additional_costs_usd={"probe": 0.2},
    )
    assert manifest["completed_observations"] == 1
    assert manifest["additional_costs_usd"] == {
        "historical_non_panel_calls": 0.6,
        "probe": 0.2,
    }
    assert manifest["cumulative_estimated_cost_usd"] == 1.2
