# Non-May 89-question run

This directory contains the complete winner-only run over the independently
curated non-May temporal stratum:

- 89 questions across 20 election dates and 72 councils
- 12 API models, with the same inference configurations as `fresh-500`
- 1,068/1,068 successful model-question cells
- zero refusals or terminal errors
- two successful second attempts after probability-sum validation errors
- $41.752197 estimated incremental API cost

No provider tools or web search were attached. The system prompt prohibited
web access, and rationales had no prompt-level length limit.

Reproduce scoring and uncertainty:

```bash
uv run votecastbench score \
  --questions data/non-may-89/questions.jsonl \
  --labels data/non-may-89/labels.jsonl \
  --predictions results/non-may-89/predictions.jsonl \
  --output results/non-may-89/scores.json

uv run python scripts/bootstrap_uncertainty.py \
  --scores results/non-may-89/scores.json \
  --scores results/non-may-89/baselines/scores.json \
  --questions data/non-may-89/questions.jsonl \
  --output results/non-may-89/uncertainty.json \
  --replicates 100000 \
  --seed 20260724
```
