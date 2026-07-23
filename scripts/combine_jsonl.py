#!/usr/bin/env python3
"""Combine versioned JSONL strata while rejecting duplicate identifiers."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from votecastbench.io import read_jsonl, write_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", type=Path, required=True, dest="inputs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--id-key", default="question_id")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [row for path in args.inputs for row in read_jsonl(path)]
    identifiers = [str(row[args.id_key]) for row in rows]
    duplicate_ids = sorted(
        identifier for identifier, count in Counter(identifiers).items() if count > 1
    )
    if duplicate_ids:
        raise ValueError(f"duplicate {args.id_key} values: {duplicate_ids}")
    write_jsonl(args.output, rows)
    print(f"combined {len(rows)} rows from {len(args.inputs)} inputs into {args.output}")


if __name__ == "__main__":
    main()
