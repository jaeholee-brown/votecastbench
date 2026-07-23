# VoteCastBench

VoteCastBench is an auditable benchmark for forecasting UK elections that
resolved after the tested models' knowledge cutoffs. Its primary evaluation is
an outcome-blind sample of 500 single-winner English local-election questions
from 7 May 2026, excluding every case in the original 20-question pilot.
Candidate profiles and local electoral history are frozen to a 1 May 2026
forecast timestamp.

The primary task asks only for calibrated winner probabilities and an
unrestricted-length rationale. A paired ablation found that additionally
requesting vote shares and turnout worsened mean Brier score on this sample,
so those targets are retained only as an exploratory secondary track.

## Headline results

Lower Brier score is better. Each API model made one high-effort forecast for
each of the 500 fresh questions. The 6,000-cell panel is complete.

Intervals are 95% paired bootstrap intervals over the 95 sampled councils.

| Forecaster | Brier (95% interval) | Accuracy (95% interval) |
|---|---:|---:|
| Claude Sonnet 5, adaptive xhigh | **0.5918** [0.5479, 0.6365] | **56.4%** [50.9%, 61.9%] |
| Claude Sonnet 4.6, adaptive max | 0.6073 [0.5524, 0.6627] | 54.0% [48.1%, 59.9%] |
| GPT-5.6 Terra, high | 0.6718 [0.6030, 0.7413] | 49.8% [43.7%, 56.0%] |
| GPT-5.5, high | 0.7032 [0.6276, 0.7799] | 49.2% [43.4%, 55.0%] |
| GPT-5.6 Sol, high | 0.7104 [0.6322, 0.7898] | 49.0% [43.0%, 55.0%] |

See [the complete 14-row table](results/fresh-500/RESULTS.md) and
[RESULTS.md](RESULTS.md) for costs, uncertainty, the original pilot, and the
output-format ablation. Sonnet 5 ranked first in 91.3% of council-bootstrap
resamples, but its paired Brier difference from Sonnet 4.6 still included zero.

## Reproduce

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
uv run votecastbench validate
uv run pytest
```

Generate deterministic baselines:

```bash
uv run votecastbench baseline \
  --output results/baselines/predictions.jsonl
```

Run the protected winner-only task. Credentials are read at runtime and are
never copied into this repository:

```bash
uv run votecastbench run \
  --env-file ../rl-env-benchmark/.env \
  --output results/full/predictions.jsonl \
  --formats winner_only \
  --concurrency 128 \
  --attempts 3
```

Pool older results into the append-safe panel, run only missing cells, and
score the combined panel:

```bash
uv run votecastbench pool \
  --input results/full/predictions.jsonl \
  --output results/panel/predictions.jsonl

uv run votecastbench run \
  --env-file ../rl-env-benchmark/.env \
  --output results/panel/predictions.jsonl \
  --formats winner_only \
  --concurrency 128 \
  --attempts 3

uv run votecastbench score \
  --predictions results/panel/predictions.jsonl \
  --output results/panel/scores.json

uv run python scripts/bootstrap_uncertainty.py
```

Rebuild the curated data from Democracy Club:

```bash
uv run python scripts/curate.py
uv run python scripts/curate_expansion.py select
uv run python scripts/curate_expansion.py fetch-ballots
uv run python scripts/curate_expansion.py curate
uv run python scripts/audit_expansion.py
```

## Repository map

- `data/questions.jsonl`: model-visible forecast packets
- `data/labels.jsonl`: resolved outcomes, withheld during forecasting
- `data/expansion/`: fresh questions, labels, selection, lineage, and audit
- `configs/models.json`: provider IDs, high-effort settings, cutoffs, and prices
- `src/votecastbench/`: validation, prompting, async runners, and scoring
- `results/fresh-500/`: 6,000 forecasts, scores, uncertainty, costs, and shards
- `results/panel/`: pooled predictions, scores, uncertainty, coverage, and costs
- `results/full/`: original four-model result set retained for provenance
- `METHODOLOGY.md`: curation, leakage controls, and metric definitions

## Data source and caveat

The dataset is derived from
[Democracy Club candidate data](https://democracyclub.org.uk/data_apis/data/)
and its [candidate API](https://candidates.democracyclub.org.uk/api/docs/next/).
The forecast packets are post-election reconstructions: timestamps are used to
exclude late statements and profile edits, but this benchmark is not a
cryptographically archived pre-election snapshot. Read the limitations in
[METHODOLOGY.md](METHODOLOGY.md) before treating it as a contamination-proof
evaluation.
