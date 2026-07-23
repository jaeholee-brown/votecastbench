# Combined 589-question panel

This directory contains scoring and uncertainty summaries for the pooled
`fresh-500` and `non-may-89` strata. Raw pooled predictions are intentionally
not duplicated: the immutable source predictions remain in their respective
result directories.

Rebuild the temporary pooled files and scores:

```bash
uv run python scripts/combine_jsonl.py \
  --input data/expansion/questions-500.jsonl \
  --input data/non-may-89/questions.jsonl \
  --output data/combined-589/questions.jsonl

uv run python scripts/combine_jsonl.py \
  --input data/expansion/labels-500.jsonl \
  --input data/non-may-89/labels.jsonl \
  --output data/combined-589/labels.jsonl

uv run votecastbench pool \
  --questions data/combined-589/questions.jsonl \
  --models configs/models.json \
  --input results/fresh-500/predictions.jsonl \
  --input results/non-may-89/predictions.jsonl \
  --output results/combined-589/predictions.jsonl
```

The pooled panel has 7,068/7,068 successful cells. Its $287.534044 estimated
model-panel cost plus $12.993740 of prior non-panel work gives an all-in
cumulative estimate of $300.527784.
