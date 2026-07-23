# VoteCastBench

VoteCastBench is a small, auditable benchmark for forecasting UK elections
that resolved after the tested models' knowledge cutoffs. Version 1 contains
20 single-winner English local-election questions from 7 May 2026, with
standardized candidate profiles and local electoral history frozen to a
1 May 2026 forecast timestamp.

The primary task asks only for calibrated winner probabilities and an
unrestricted-length rationale. A paired ablation found that additionally
requesting vote shares and turnout worsened mean Brier score on this sample,
so those targets are retained only as an exploratory secondary track.

## Headline results

Lower Brier score is better. Each model made one high-effort forecast for each
of the 20 questions.

| Forecaster | Brier | Top-choice accuracy |
|---|---:|---:|
| GPT-5.6 Luna (high) | **0.5306** | **70%** |
| Claude Haiku 4.5 (4,096 thinking tokens) | 0.5962 | 65% |
| Last-ward party-share baseline | 0.6056 | 65% |
| GPT-5.4 nano (high) | 0.6325 | 60% |
| GPT-5.4 mini (high) | 0.6507 | 65% |
| Uniform baseline | 0.8133 | 18.7% |

See [RESULTS.md](RESULTS.md) for the output-format ablation, token use, and
interpretation. This is a 20-question pilot, not a definitive model ranking.

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
  --concurrency 32 \
  --attempts 3
```

Score a run:

```bash
uv run votecastbench score \
  --predictions results/full/predictions.jsonl \
  --output results/full/scores.json
```

Rebuild the curated data from Democracy Club:

```bash
uv run python scripts/curate.py
```

## Repository map

- `data/questions.jsonl`: model-visible forecast packets
- `data/labels.jsonl`: resolved outcomes, withheld during forecasting
- `configs/models.json`: provider IDs, high-effort settings, cutoffs, and prices
- `src/votecastbench/`: validation, prompting, async runners, and scoring
- `results/`: committed raw predictions and score reports
- `METHODOLOGY.md`: curation, leakage controls, and metric definitions

## Data source and caveat

The dataset is derived from
[Democracy Club candidate data](https://democracyclub.org.uk/data_apis/data/)
and its [candidate API](https://candidates.democracyclub.org.uk/api/docs/next/).
The forecast packets are post-election reconstructions: timestamps are used to
exclude late statements and profile edits, but this pilot is not a
cryptographically archived pre-election snapshot. Read the limitations in
[METHODOLOGY.md](METHODOLOGY.md) before treating it as a contamination-proof
evaluation.

