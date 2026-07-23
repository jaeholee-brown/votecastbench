# VoteCastBench

VoteCastBench is a small, auditable benchmark for forecasting UK election
results that resolved after a model knowledge cutoff. It contains 20
single-winner local-election questions from 7 May 2026, leakage-controlled
forecast packets, hidden-label-compatible scoring, and reproducible model
run artifacts.

The primary metric is multiclass Brier score. Candidate vote-share mean
absolute error is reported as a secondary metric when a run requests vote
shares.

The repository is under active construction. See `METHODOLOGY.md` for the
final curation and evaluation protocol.

