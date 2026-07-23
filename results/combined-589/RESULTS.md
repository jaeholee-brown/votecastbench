# Combined 589-question results

Primary metric: multiclass Brier score (lower is better). Accuracy is the fractional top-choice accuracy used by the scorer (higher is better). Brackets are paired 95% organisation-cluster bootstrap intervals.

| Rank | Forecaster | Brier [95% CI] | Accuracy % [95% CI] | Vote-share MAE | API cost |
|---:|---|---:|---:|---:|---:|
| 1 | anthropic/claude-sonnet-5-xhigh | 0.5988 [0.5600, 0.6379] | 55.3 [50.4, 60.2] | N/A | $30.544 |
| 2 | anthropic/claude-sonnet-4-6-max | 0.6113 [0.5633, 0.6594] | 52.8 [47.6, 58.0] | N/A | $38.859 |
| 3 | openai/gpt-5.6-terra | 0.6668 [0.6073, 0.7269] | 49.7 [44.4, 55.2] | N/A | $9.658 |
| 4 | openai/gpt-5.5 | 0.6962 [0.6303, 0.7625] | 48.4 [43.1, 53.6] | N/A | $68.748 |
| 5 | openai/gpt-5.6-sol | 0.7026 [0.6344, 0.7713] | 48.9 [43.5, 54.3] | N/A | $30.226 |
| 6 | openai/gpt-5.6-luna | 0.7132 [0.6496, 0.7768] | 48.7 [43.3, 54.2] | N/A | $5.316 |
| 7 | anthropic/claude-sonnet-4-5-thinking-10k | 0.7197 [0.6574, 0.7815] | 45.9 [40.6, 51.3] | N/A | $25.222 |
| 8 | openai/gpt-5.4-mini | 0.7213 [0.6583, 0.7839] | 45.8 [40.4, 51.3] | N/A | $15.877 |
| 9 | openai/gpt-5.2 | 0.7336 [0.6677, 0.7990] | 45.2 [39.7, 50.7] | N/A | $12.557 |
| 10 | anthropic/claude-haiku-4-5 | 0.7484 [0.6832, 0.8130] | 47.2 [41.8, 52.6] | N/A | $8.967 |
| 11 | openai/gpt-5.4 | 0.7505 [0.6757, 0.8251] | 46.0 [40.4, 51.7] | N/A | $39.927 |
| 12 | openai/gpt-5.4-nano | 0.7738 [0.7058, 0.8412] | 47.1 [41.7, 52.6] | N/A | $1.633 |
| 13 | baseline/uniform | 0.7950 [0.7899, 0.7996] | 20.5 [20.0, 21.0] | N/A | $0.000 |
| 14 | baseline/last-ward-party-share | 0.8069 [0.7479, 0.8656] | 43.5 [38.1, 49.1] | N/A | $0.000 |

Combined 589-question model-panel estimated cost: $287.534044. All-in cumulative estimated cost including prior work: $300.527784.

Vote-share MAE is N/A because the protected run requested only winner probabilities; winner probabilities are not reinterpreted as vote shares. Rationale length had no prompt-level limit.

The last-ward baseline uses a documented uniform fallback for the 25/589 packets with no supplied same-ward history.

Intervals resample 155 councils and capture question/organisation sampling uncertainty, not model sampling variance; every model-question cell has one successful forecast.
