# Fresh 500-question expansion

This directory is a separate, outcome-blind expansion wave. It contains 500
questions selected after excluding every ballot in the original 20-question
pilot. The published seed is `votecastbench-uk-local-500-v1`.

`questions-500.jsonl` and `labels-500.jsonl` are the canonical evaluation set.
Both curation and model inference operate once over this combined 500-question
file; there are no artificial evaluation tranches.

`resolved_on` records the target poll/event date. It is not intended to be the
publication timestamp of the result page or declaration document; some formal
declarations are dated the following day.

Run the complete launch gate with:

```shell
uv run python scripts/audit_expansion.py
```

The resulting `audit-report.json` reconciles every historical record with the
hashed 2021–2025 exports, verifies all 500 API cache hashes, scans all rendered
winner-only prompts for target-only fields and result URLs, and incorporates the
five-case manual official-source audit.
