# Fresh 500-question results

Primary metric: multiclass Brier score (lower is better). Accuracy is the fractional top-choice accuracy used by the scorer (higher is better). Brackets are paired 95% organisation-cluster bootstrap intervals.

| Rank | Forecaster | Brier [95% CI] | Accuracy % [95% CI] | Vote-share MAE | API cost |
|---:|---|---:|---:|---:|---:|
| 1 | anthropic/claude-sonnet-5-xhigh | 0.5918 [0.5479, 0.6365] | 56.4 [50.9, 61.9] | N/A | $26.213 |
| 2 | anthropic/claude-sonnet-4-6-max | 0.6073 [0.5524, 0.6627] | 54.0 [48.1, 59.9] | N/A | $33.048 |
| 3 | openai/gpt-5.6-terra | 0.6718 [0.6030, 0.7413] | 49.8 [43.7, 56.0] | N/A | $8.257 |
| 4 | openai/gpt-5.5 | 0.7032 [0.6276, 0.7799] | 49.2 [43.4, 55.0] | N/A | $59.018 |
| 5 | openai/gpt-5.6-sol | 0.7104 [0.6322, 0.7898] | 49.0 [43.0, 55.0] | N/A | $25.929 |
| 6 | openai/gpt-5.6-luna | 0.7201 [0.6473, 0.7937] | 48.8 [42.6, 55.0] | N/A | $4.513 |
| 7 | openai/gpt-5.4-mini | 0.7268 [0.6557, 0.7986] | 46.0 [39.9, 52.1] | N/A | $13.640 |
| 8 | anthropic/claude-sonnet-4-5-thinking-10k | 0.7274 [0.6567, 0.7983] | 45.9 [40.0, 51.9] | N/A | $21.499 |
| 9 | openai/gpt-5.2 | 0.7424 [0.6674, 0.8181] | 46.0 [40.0, 52.1] | N/A | $10.758 |
| 10 | anthropic/claude-haiku-4-5 | 0.7596 [0.6843, 0.8347] | 47.4 [41.4, 53.5] | N/A | $7.618 |
| 11 | openai/gpt-5.4 | 0.7635 [0.6777, 0.8496] | 46.4 [40.2, 52.7] | N/A | $33.877 |
| 12 | openai/gpt-5.4-nano | 0.7834 [0.7059, 0.8609] | 47.3 [41.2, 53.4] | N/A | $1.413 |
| 13 | baseline/uniform | 0.7945 [0.7888, 0.7996] | 20.6 [20.0, 21.1] | N/A | $0.000 |
| 14 | baseline/last-ward-party-share | 0.8204 [0.7546, 0.8869] | 43.4 [37.3, 49.6] | N/A | $0.000 |

Fresh model-panel estimated cost: $245.781847. All-in cumulative estimated cost including prior work: $258.775587.

Vote-share MAE is N/A because the protected run requested only winner probabilities; winner probabilities are not reinterpreted as vote shares. Rationale length had no prompt-level limit.

The last-ward baseline uses a documented uniform fallback for the 22/500 packets with no supplied same-ward history.

Intervals resample 95 councils and capture question/organisation sampling uncertainty, not model sampling variance; every model-question cell has one successful forecast.
