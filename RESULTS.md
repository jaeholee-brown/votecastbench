# Results

## Protected winner-only benchmark

All 240 API forecasts completed and passed output validation. Lower Brier is
better. Rows are ordered by point estimate only; they are not a statistically
resolved ranking. The intervals are 95% paired question-bootstrap intervals.
Per-model cost covers the 20 successful panel forecasts.

| Forecaster | Setting | Mean Brier (95% interval) | Accuracy | Mean probability on winner | Est. cost |
|---|---|---:|---:|---:|---:|
| GPT-5.6 Luna | high | **0.5306** [0.3486, 0.7393] | **70%** | 0.4800 | $0.22 |
| GPT-5.6 Terra | high | 0.5418 [0.3608, 0.7401] | 65% | 0.4673 | $0.39 |
| Claude Sonnet 4.6 | adaptive max | 0.5660 [0.3997, 0.7500] | 60% | 0.4240 | $1.60 |
| Claude Sonnet 4.5 | 10k thinking | 0.5692 [0.3780, 0.7817] | 60% | 0.4565 | $1.03 |
| GPT-5.6 Sol | high | 0.5720 [0.3534, 0.8241] | **70%** | **0.4895** | $1.28 |
| GPT-5.5 | high | 0.5740 [0.3605, 0.8191] | 65% | 0.4738 | $2.71 |
| Claude Sonnet 5 | adaptive xhigh | 0.5769 [0.4143, 0.7669] | 67.5% | 0.4170 | $1.21 |
| Claude Haiku 4.5 | 4,096 thinking | 0.5962 [0.3836, 0.8271] | 65% | 0.4487 | $0.38 |
| Last-ward baseline | deterministic | 0.6056 [0.4690, 0.7568] | 65% | 0.3667 | — |
| GPT-5.4 | high | 0.6230 [0.3905, 0.8836] | 60% | 0.4598 | $1.75 |
| GPT-5.2 | high | 0.6295 [0.4254, 0.8581] | 65% | 0.4232 | $0.51 |
| GPT-5.4 nano | high | 0.6325 [0.4198, 0.8735] | 60% | 0.4140 | $0.06 |
| GPT-5.4 mini | high | 0.6507 [0.4453, 0.8826] | 65% | 0.3955 | $0.60 |
| Uniform baseline | deterministic | 0.8133 [0.8067, 0.8200] | 18.7% | 0.1867 | — |

## Uncertainty and ranking stability

The apparent fine-grained order is mostly noise. In 100,000 paired bootstrap
resamples, Luna was the best API model 48.3% of the time and Terra 24.9%.
Luna's central 95% rank range was 1–7; Terra's was 1–6. Pairwise Brier
difference intervals versus Luna included zero for every API model except
GPT-5.2, GPT-5.4 nano, and GPT-5.4 mini. These exploratory intervals are not
adjusted for multiple comparisons.

The point order is also sensitive to individual elections. On Plymouth Sutton
and Mount Gould, every API model assigned the eventual winner at most 30%;
Terra's Brier was 0.433 worse than Luna's on that one question. Removing only
that case puts Terra first at 0.5097, Luna second at 0.5207, and GPT-5.5 third
at 0.5266. One case is 5% of this pilot, and multiclass Brier correctly
penalizes confident mistakes heavily.

The bootstrap is paired: each replicate resamples the same 20 question indices
for every forecaster. It captures sensitivity to this question set, not model
sampling variance. Because the questions were purposively curated rather than
drawn IID, the intervals are diagnostics rather than population confidence
guarantees. Repeated calls and substantially more questions are needed for a
serious model ranking.

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
- `results/panel/uncertainty.json`: paired-bootstrap intervals and rank stability
- `results/panel/manifest.json`: hashes, coverage, usage, and cumulative costs
- `results/full/`: original four-model artifacts retained unchanged
- `results/ablation/predictions.jsonl`: 40 paired-format forecasts
- `results/ablation/scores.json`: aggregate and paired question-level scores
- `results/baselines/`: deterministic forecasts and scores
