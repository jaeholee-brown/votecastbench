# Results

## Protected winner-only benchmark

All 80 model forecasts completed and passed output validation. Lower Brier is
better.

| Rank | Forecaster | Mean Brier | Top-choice accuracy | Mean probability on winner |
|---:|---|---:|---:|---:|
| 1 | GPT-5.6 Luna | **0.5306** | **70%** | **0.4800** |
| 2 | Claude Haiku 4.5 | 0.5962 | 65% | 0.4487 |
| — | Last-ward party-share baseline | 0.6056 | 65% | 0.3667 |
| 3 | GPT-5.4 nano | 0.6325 | 60% | 0.4140 |
| 4 | GPT-5.4 mini | 0.6507 | 65% | 0.3955 |
| — | Uniform baseline | 0.8133 | 18.7% | 0.1867 |

Only Luna clearly beat the simple local-history baseline in this one-run,
20-question sample. Haiku was slightly better by Brier, while nano and mini
were worse. These differences should not be overinterpreted without more
questions and repeated samples.

## Did vote-share and turnout targets muddy winner forecasts?

The paired ablation used the same first five questions, all four models, and
the same high-effort settings. `Delta` is joint Brier minus winner-only Brier,
so a positive value means the extra targets worsened winner calibration.

| Model | Winner-only Brier | Joint Brier | Delta | Joint vote-share MAE | Joint turnout MAE |
|---|---:|---:|---:|---:|---:|
| Claude Haiku 4.5 | 0.4573 | 0.4921 | +0.0348 | 8.51 pp | 9.24 pp |
| GPT-5.4 mini | 0.4556 | 0.5695 | +0.1139 | 8.74 pp | 8.96 pp |
| GPT-5.4 nano | 0.4713 | 0.4362 | -0.0350 | 8.09 pp | 9.74 pp |
| GPT-5.6 Luna | 0.4269 | 0.4793 | +0.0524 | **7.09 pp** | 9.11 pp |
| **Pooled** | **0.4528** | **0.4943** | **+0.0415** | **8.11 pp** | **9.26 pp** |

Joint output was worse for three of four models on mean Brier and raised pooled
Brier by about 9.2% relative to winner-only. At the individual paired-run
level, joint was worse in 10 of 20 comparisons, so the direction was not
universal. With only five questions, this is a decision-oriented diagnostic,
not a statistically conclusive causal result.

The repository therefore makes `winner_only` the primary task. Vote-share MAE
remains available as a secondary metric for explicitly joint runs.

## Usage and approximate cost

The full winner-only run consumed:

| Model | Input tokens | Output tokens |
|---|---:|---:|
| Claude Haiku 4.5 | 87,321 | 57,678 |
| GPT-5.4 mini | 74,795 | 120,690 |
| GPT-5.4 nano | 74,795 | 35,748 |
| GPT-5.6 Luna | 74,795 | 23,993 |

Using the run-date list prices recorded in `configs/models.json`, the full
80-call run cost approximately **$1.25**. The 20 additional joint-format calls
used by the ablation cost approximately **$0.47**, for about **$1.73** across
the committed unique API calls. Estimates include provider-reported output
tokens, including reasoning/thinking where billed, and exclude any account
discounts.

## Artifacts

- `results/full/predictions.jsonl`: 80 raw validated winner-only forecasts
- `results/full/scores.json`: aggregate and question-level scores
- `results/ablation/predictions.jsonl`: 40 paired-format forecasts
- `results/ablation/scores.json`: aggregate and paired question-level scores
- `results/baselines/`: deterministic forecasts and scores

