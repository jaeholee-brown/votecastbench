# Results

## Protected winner-only benchmark

All 240 API forecasts completed and passed output validation. Lower Brier is
better. Per-model cost covers the 20 successful panel forecasts and uses the
run-date prices in `configs/models.json`.

| Rank | Forecaster | Inference setting | Mean Brier | Top-choice accuracy | Mean probability on winner | Est. cost |
|---:|---|---|---:|---:|---:|---:|
| 1 | GPT-5.6 Luna | high | **0.5306** | **70%** | 0.4800 | $0.22 |
| 2 | GPT-5.6 Terra | high | 0.5418 | 65% | 0.4673 | $0.39 |
| 3 | Claude Sonnet 4.6 | adaptive max | 0.5660 | 60% | 0.4240 | $1.60 |
| 4 | Claude Sonnet 4.5 | 10k thinking | 0.5692 | 60% | 0.4565 | $1.03 |
| 5 | GPT-5.6 Sol | high | 0.5720 | **70%** | **0.4895** | $1.28 |
| 6 | GPT-5.5 | high | 0.5740 | 65% | 0.4738 | $2.71 |
| 7 | Claude Sonnet 5 | adaptive xhigh | 0.5769 | 67.5% | 0.4170 | $1.21 |
| 8 | Claude Haiku 4.5 | 4,096 thinking | 0.5962 | 65% | 0.4487 | $0.38 |
| 9 | Last-ward party-share baseline | deterministic | 0.6056 | 65% | 0.3667 | — |
| 10 | GPT-5.4 | high | 0.6230 | 60% | 0.4598 | $1.75 |
| 11 | GPT-5.2 | high | 0.6295 | 65% | 0.4232 | $0.51 |
| 12 | GPT-5.4 nano | high | 0.6325 | 60% | 0.4140 | $0.06 |
| 13 | GPT-5.4 mini | high | 0.6507 | 65% | 0.3955 | $0.60 |
| 14 | Uniform baseline | deterministic | 0.8133 | 18.7% | 0.1867 | — |

Seven of the twelve API models beat the simple local-history baseline on this
run. GPT-5.6 Luna remained first, with Terra second. These differences should
not be overinterpreted without more questions and repeated samples.

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

| Model | Input tokens | Output tokens | Est. cost |
|---|---:|---:|---:|
| Claude Haiku 4.5 | 87,321 | 57,678 | $0.38 |
| Claude Sonnet 4.5 | 87,321 | 51,400 | $1.03 |
| Claude Sonnet 4.6 | 92,808 | 88,355 | $1.60 |
| Claude Sonnet 5 | 114,452 | 98,143 | $1.21 |
| GPT-5.2 | 74,795 | 26,843 | $0.51 |
| GPT-5.4 | 74,795 | 103,902 | $1.75 |
| GPT-5.4 mini | 74,795 | 120,690 | $0.60 |
| GPT-5.4 nano | 74,795 | 35,748 | $0.06 |
| GPT-5.5 | 74,795 | 77,823 | $2.71 |
| GPT-5.6 Luna | 74,795 | 23,993 | $0.22 |
| GPT-5.6 Sol | 74,795 | 30,242 | $1.28 |
| GPT-5.6 Terra | 74,795 | 13,766 | $0.39 |
| **Successful panel total** | **980,262** | **728,583** | **$11.74** |

The earlier joint-format ablation cost about $0.47. Sonnet 5 `max` spent its
entire response allowance on thinking and produced no forecast in three probes;
their conservative allowance-based upper bound is $0.78. Including both
items, estimated cumulative API spend is **$12.99**, well below the $50
reference budget. The estimate includes provider-reported reasoning/thinking
tokens where available and excludes account discounts. The machine-readable
breakdown is in `results/panel/manifest.json`.

## Artifacts

- `results/panel/predictions.jsonl`: 240 raw validated winner-only forecasts
- `results/panel/scores.json`: aggregate and question-level panel scores
- `results/panel/manifest.json`: hashes, coverage, usage, and cumulative costs
- `results/full/`: original four-model artifacts retained unchanged
- `results/ablation/predictions.jsonl`: 40 paired-format forecasts
- `results/ablation/scores.json`: aggregate and paired question-level scores
- `results/baselines/`: deterministic forecasts and scores
