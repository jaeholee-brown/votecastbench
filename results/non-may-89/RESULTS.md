# Non-May 89-question results

Primary metric: multiclass Brier score (lower is better). Accuracy is the fractional top-choice accuracy used by the scorer (higher is better). Brackets are paired 95% organisation-cluster bootstrap intervals.

| Rank | Forecaster | Brier [95% CI] | Accuracy % [95% CI] | Vote-share MAE | API cost |
|---:|---|---:|---:|---:|---:|
| 1 | anthropic/claude-sonnet-4-6-max | 0.6339 [0.5590, 0.7093] | 46.1 [35.3, 56.7] | N/A | $5.811 |
| 2 | anthropic/claude-sonnet-5-xhigh | 0.6379 [0.5721, 0.7051] | 48.9 [38.6, 59.3] | N/A | $4.331 |
| 3 | openai/gpt-5.6-terra | 0.6383 [0.5503, 0.7271] | 49.4 [38.9, 60.0] | N/A | $1.401 |
| 4 | openai/gpt-5.5 | 0.6570 [0.5605, 0.7541] | 43.8 [33.7, 54.0] | N/A | $9.730 |
| 5 | openai/gpt-5.6-sol | 0.6588 [0.5596, 0.7590] | 48.3 [37.6, 59.1] | N/A | $4.297 |
| 6 | openai/gpt-5.6-luna | 0.6745 [0.5785, 0.7714] | 48.3 [37.8, 58.8] | N/A | $0.803 |
| 7 | anthropic/claude-sonnet-4-5-thinking-10k | 0.6766 [0.5838, 0.7696] | 46.1 [35.9, 56.3] | N/A | $3.723 |
| 8 | openai/gpt-5.4 | 0.6780 [0.5789, 0.7764] | 43.8 [33.3, 54.5] | N/A | $6.049 |
| 9 | openai/gpt-5.2 | 0.6839 [0.5978, 0.7679] | 40.4 [30.6, 50.6] | N/A | $1.800 |
| 10 | anthropic/claude-haiku-4-5 | 0.6856 [0.6032, 0.7667] | 46.1 [36.1, 56.1] | N/A | $1.349 |
| 11 | openai/gpt-5.4-mini | 0.6909 [0.6034, 0.7815] | 44.9 [34.8, 55.2] | N/A | $2.238 |
| 12 | openai/gpt-5.4-nano | 0.7197 [0.6271, 0.8116] | 46.1 [35.9, 56.4] | N/A | $0.221 |
| 13 | baseline/last-ward-party-share | 0.7310 [0.6346, 0.8282] | 44.4 [34.4, 54.6] | N/A | $0.000 |
| 14 | baseline/uniform | 0.7978 [0.7895, 0.8054] | 20.2 [19.5, 21.0] | N/A | $0.000 |

Non-May 89-question model-panel estimated cost: $41.752197. All-in cumulative estimated cost including prior work: $300.527784.

Vote-share MAE is N/A because the protected run requested only winner probabilities; winner probabilities are not reinterpreted as vote shares. Rationale length had no prompt-level limit.

The last-ward baseline uses a documented uniform fallback for the 3/89 packets with no supplied same-ward history.

Intervals resample 72 councils and capture question/organisation sampling uncertainty, not model sampling variance; every model-question cell has one successful forecast.
