# Methodology

## Benchmark unit

Each question is one contested, single-seat, first-past-the-post ward election
held on 7 May 2026. The forecast timestamp is
`2026-05-01T23:59:59+01:00`. All target outcomes therefore resolved after the
most recent tested model cutoff, GPT-5.6 Luna's 16 February 2026 cutoff.

The 20 cases were hand-selected from eligible Democracy Club records to vary:

- council and English region;
- winning party;
- candidate count and competitiveness;
- the amount of same-ward and candidate electoral history.

The final set covers 20 councils, eight regions, 108 candidates, and seven
winner-party labels. This is a purposive pilot sample, not a random or
population-representative sample.

The primary expansion is a separate set of 500 fresh questions with zero
overlap with the pilot. From 1,606 preliminarily eligible ballots, it uses the
published seed `votecastbench-uk-local-500-v1` to select five by-elections and
495 regular contests across 95 authorities. Regular contests are capped at
five per authority plus seeded sixth slots, then ordered by seeded ballot
hashes within each authority. Winner identity, winner party, margin, turnout,
and vote values are not used for selection; outcome values are inspected only
to require a complete, uniquely resolvable label. The set covers nine regions
and 2,491 candidates.

## Information shown to models

Every forecast packet contains:

- election name, ward, date, voting system, and official candidate-list source;
- every candidate's stable Democracy Club ID, name, ballot party description,
  and party;
- candidate statements whose own update timestamp is no later than the
  forecast timestamp;
- public profile links only when the profile update timestamp is no later than
  the forecast timestamp;
- each candidate's results in the regular May 2021–2025 local-election
  exports;
- exact-post ward results in the same 2021–2025 exports.

The main track deliberately excludes photos, gender, birth dates, inferred
ethnicity, and other protected-characteristic proxies. It also excludes tools,
web access, and any current-election result fields.

## Temporal leakage controls

`questions.jsonl` and `labels.jsonl` are separate. Dataset validation checks
that:

1. the candidate list was locked and every candidacy was created before the
   forecast timestamp;
2. included statements and profile fields pass their timestamp gates;
3. all candidate and ward result records predate the target election;
4. the target winner, vote totals, turnout, result source, and resolution
   fields occur only in labels;
5. every label has the same candidate set as its question and the labelled
   winner has the highest vote total.

The original raw source hashes and selected ballot IDs are recorded in
`data/manifest.json`. Expansion selection, hashes, API lineage, and a
deterministic five-case manual audit are in `data/expansion/`. Its automated
gate reconciles all 1,306 ward-history records and 2,736 candidate-history
records to hashed exports, verifies 500 API cache records, and scans all 500
rendered prompts for target-only fields and result URLs.

### Reconstruction limitation

Curation occurred after the elections resolved. Democracy Club exposes field
timestamps and source history, but the committed packets are not byte-for-byte
archives captured on 1 May. Names, parties, and other upstream records could
have received later corrections even where no outcome field is included.
Candidate history is standardized to regular May exports from 2021–2025 and
does not include every older election, campaign page, local news story, or
private polling source. These limits make the benchmark auditable and useful
for a pilot, but not proof against every form of post-event contamination.

## Forecast formats

The protected `winner_only` format requests:

1. one winning probability per candidate, summing to one;
2. an unrestricted-length rationale.

The exploratory `joint` format additionally requests:

1. one valid-vote share per candidate, summing to 100;
2. turnout percentage.

No prompt-level rationale word or token limit is imposed. Provider calls still
have a 12,000-token output safety ceiling.

## Metrics

For question \(q\), candidate \(c\), forecast probability \(p_{qc}\), and
winner indicator \(y_{qc}\), multiclass Brier score is:

\[
\operatorname{Brier}_q = \sum_c (p_{qc} - y_{qc})^2.
\]

It ranges from 0 to 2 and is macro-averaged across questions. Lower is better.
This is the primary metric. Top-choice accuracy is descriptive only; tied
maximum probabilities receive fractional credit.

For joint forecasts, actual candidate vote share is calculated from the sum of
valid candidate votes. Vote-share MAE is first averaged across candidates
within a question and then across questions, so ballots with more candidates
do not dominate. Turnout MAE is reported only where turnout is available.

Probability totals within 0.02 of one are normalized; wider discrepancies are
invalid. Vote-share totals within two percentage points of 100 are normalized;
wider discrepancies are invalid. All committed API forecasts passed validation.

### Uncertainty

The fresh-panel error bars use 100,000 paired nonparametric bootstrap resamples
of the 95 sampled organisations with a fixed seed. Each sampled organisation
contributes all of its questions. The repository reports percentile 95%
intervals for mean Brier and top-choice accuracy, model-rank distributions,
probability of being the best API model, probability of beating the last-ward
baseline, and paired Brier differences. The original pilot retains its
question-level bootstrap.

These intervals measure sensitivity to the included questions only. They do not
include model sampling variance because each model/question cell has one API
call. The purposive cases are not an IID sample of all elections, so the bars
should not be interpreted as population confidence guarantees.

## Models and inference

The run on 23 July 2026 used:

| Model | Provider setting | Knowledge cutoff |
|---|---|---|
| `gpt-5.2-2025-12-11` | reasoning effort `high` | 31 Aug 2025 |
| `gpt-5.4-2026-03-05` | reasoning effort `high` | 31 Aug 2025 |
| `gpt-5.4-mini` | reasoning effort `high` | 31 Aug 2025 |
| `gpt-5.4-nano` | reasoning effort `high` | 31 Aug 2025 |
| `gpt-5.5-2026-04-23` | reasoning effort `high` | 1 Dec 2025 |
| `gpt-5.6-luna` | reasoning effort `high` | 16 Feb 2026 |
| `gpt-5.6-sol` | reasoning effort `high` | 16 Feb 2026 |
| `gpt-5.6-terra` | reasoning effort `high` | 16 Feb 2026 |
| `claude-haiku-4-5-20251001` | extended thinking, 4,096 tokens | reliable: Feb 2025; training: Jul 2025 |
| `claude-sonnet-4-5-20250929` | extended thinking, 10,000 tokens | reliable: Feb 2025; training: Jul 2025 |
| `claude-sonnet-4-6` | adaptive thinking, effort `max` | reliable: Aug 2025; training: Jan 2026 |
| `claude-sonnet-5` | adaptive thinking, effort `xhigh` | Jan 2026 |

Every OpenAI model used the regular `high` reasoning tier. Sonnet 4.6 used its
highest supported `max` tier. Sonnet 5 `max` produced no final answer even
after raising the combined thinking/output allowance to 32,000 tokens, so the
scorable panel uses the next-highest `xhigh` tier with the same allowance.
Sonnet 4.5 does not support adaptive effort and instead used a 10,000-token
manual thinking budget. Model documentation and run-date token prices are
recorded in `configs/models.json`.

The fresh wave used independent append-only shards: eight OpenAI models at
async concurrency 128, two prompt-only Anthropic models at 64, and two
structured Sonnet models at 64. The structured adapter omits
question-specific candidate-ID enums from Anthropic's native grammar so one
portable grammar can be reused, while the prompt still supplies exact IDs and
local validation still enforces them. The runner
records requested and resolved model IDs, response IDs, usage, latency,
timestamps, prompt hashes, question hashes, full inference-configuration
hashes, stable observation IDs, and validated forecast objects. It does not
store credentials or hidden chain-of-thought.

`results/fresh-500/shards/` preserves the independently resumable provider
lanes, and `results/fresh-500/predictions.jsonl` is the pooled 6,000-cell panel.
Adding questions and rerunning a shard schedules only missing observation IDs.
The runner and pooler retain billable usage from invalid and resumed attempts
without double-counting identical records. The manifest records coverage,
attempt counts, per-model token usage and price estimates, and cumulative
non-panel costs.

The panels use one stochastic call per question/model/format. Replicated runs
would be needed to quantify sampling variance.

## Baselines

`baseline/uniform` assigns equal probability to every candidate.

`baseline/last-ward-party-share` carries forward votes by party from the latest
same-post result, maps Labour and Labour & Co-operative to one party family,
and adds smoothing equal to 1% of the prior valid-vote total to every current
candidate before normalization. It uses no candidate identity or profile
information. For 22 of the fresh 500 packets with no same-ward history, it uses
the uniform forecast as an explicit fallback.
