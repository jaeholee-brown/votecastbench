# Curated data

- `questions.jsonl` contains the model-visible forecast packets.
- `labels.jsonl` contains resolved outcomes and should be withheld from models.
- `manifest.json` records the sample definition and hashes of the source CSV
  exports used for this build.

Every question is a single-seat first-past-the-post contest held on 7 May
2026 and has a forecast timestamp of 1 May 2026. Current-election vote,
winner, turnout, and result-source fields appear only in `labels.jsonl`.

Candidate statements and public profile fields are included only when their
Democracy Club timestamps were no later than the forecast timestamp. Photos,
gender, birth dates, and inferred protected characteristics are excluded.
Historical context is deliberately standardized: candidate and exact-post
results from the regular May local-election exports for 2021–2025. This does
not claim to capture every campaign webpage, news report, or election before
2021.

The labels are committed because this is an auditable public benchmark. A
blind evaluation should expose only `questions.jsonl` to the forecasting
system and score predictions in a separate process.

