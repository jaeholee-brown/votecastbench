# Results

## Fresh outcome-blind 500-question panel

All 6,000 API forecasts completed and passed validation. Brackets are paired
95% organisation-cluster bootstrap intervals over 95 councils. The complete
machine-rendered table is preserved in
[`results/fresh-500/RESULTS.md`](results/fresh-500/RESULTS.md).

| Rank | Forecaster | Brier [95% CI] | Accuracy [95% CI] | Est. cost |
|---:|---|---:|---:|---:|
| 1 | Claude Sonnet 5, adaptive xhigh | **0.5918** [0.5479, 0.6365] | **56.4%** [50.9%, 61.9%] | $26.21 |
| 2 | Claude Sonnet 4.6, adaptive max | 0.6073 [0.5524, 0.6627] | 54.0% [48.1%, 59.9%] | $33.05 |
| 3 | GPT-5.6 Terra, high | 0.6718 [0.6030, 0.7413] | 49.8% [43.7%, 56.0%] | $8.26 |
| 4 | GPT-5.5, high | 0.7032 [0.6276, 0.7799] | 49.2% [43.4%, 55.0%] | $59.02 |
| 5 | GPT-5.6 Sol, high | 0.7104 [0.6322, 0.7898] | 49.0% [43.0%, 55.0%] | $25.93 |
| 6 | GPT-5.6 Luna, high | 0.7201 [0.6473, 0.7937] | 48.8% [42.6%, 55.0%] | $4.51 |
| 7 | GPT-5.4 mini, high | 0.7268 [0.6557, 0.7986] | 46.0% [39.9%, 52.1%] | $13.64 |
| 8 | Claude Sonnet 4.5, 10k thinking | 0.7274 [0.6567, 0.7983] | 45.9% [40.0%, 51.9%] | $21.50 |
| 9 | GPT-5.2, high | 0.7424 [0.6674, 0.8181] | 46.0% [40.0%, 52.1%] | $10.76 |
| 10 | Claude Haiku 4.5, 4,096 thinking | 0.7596 [0.6843, 0.8347] | 47.4% [41.4%, 53.5%] | $7.62 |
| 11 | GPT-5.4, high | 0.7635 [0.6777, 0.8496] | 46.4% [40.2%, 52.7%] | $33.88 |
| 12 | GPT-5.4 nano, high | 0.7834 [0.7059, 0.8609] | 47.3% [41.2%, 53.4%] | $1.41 |
| 13 | Uniform baseline | 0.7945 [0.7888, 0.7996] | 20.6% [20.0%, 21.1%] | — |
| 14 | Last-ward party-share baseline | 0.8204 [0.7546, 0.8869] | 43.4% [37.3%, 49.6%] | — |

Sonnet 5 was the best API model in 91.3% of bootstrap resamples. Its paired
Brier advantage over Sonnet 4.6 was 0.0155, with a 95% interval from -0.0067 to
0.0386, so the top two are not separated at the 95% level. GPT-5.6 Terra's
paired deficit versus Sonnet 5 was 0.0800 [0.0460, 0.1155].

The fresh panel cost an estimated **$245.78**. Including the prior pilot,
ablation, and probes, cumulative estimated model-API spend is **$258.78**.
There were 6,009 attempts for 6,000 successful observations; all nine retried
cells retain attempt-level usage in the committed records.

Vote-share MAE is not reported for this protected panel because it requested
winner probabilities only. Winner probabilities are not treated as vote
shares.

## Original 20-question protected winner-only pilot

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
