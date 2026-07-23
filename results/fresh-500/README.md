# Fresh-500 result panel

This directory contains the complete 500-question by 12-model winner-only
panel. All provider responses are saved in independently resumable shards and
then pooled into `predictions.jsonl`.

## Durable artifacts

- `shards/openai.jsonl`: eight OpenAI models, 4,000 observations
- `shards/anthropic-unstructured.jsonl`: Haiku 4.5 and Sonnet 4.5, 1,000
  observations
- `shards/anthropic-structured.jsonl`: Sonnet 4.6 and Sonnet 5, 1,000
  observations
- `predictions.jsonl`: the pooled 6,000 observations
- `scores.json`: aggregate and per-question scores
- `uncertainty.json`: 100,000-replicate paired council-cluster bootstrap
- `manifest.json`: coverage, inference hashes, attempts, token usage, and costs
- `RESULTS.md`: one table containing all API models and baselines

No model request attached web-search, browsing, or other tools. Each request
contained only the system prompt, one forecast packet, and the output schema.

## Adding questions

Append newly curated questions and labels to a new versioned question set; do
not edit a packet after its first inference call. Rerun each provider lane
against that set using the same model configuration. The runner skips existing
successful observation IDs and appends only missing cells. Keep one output file
per process so concurrent writers never share a JSONL file.

Pool shards with:

```shell
uv run votecastbench pool \
  --questions data/expansion/questions-500.jsonl \
  --models configs/models.json \
  --input results/fresh-500/shards/openai.jsonl \
  --input results/fresh-500/shards/anthropic-unstructured.jsonl \
  --input results/fresh-500/shards/anthropic-structured.jsonl \
  --output results/fresh-500/predictions.jsonl
```

Pooling is idempotent, preserves original question/prompt/configuration hashes,
rejects conflicting successful responses for one observation, and carries
billable usage across invalid attempts or resumed runs.
