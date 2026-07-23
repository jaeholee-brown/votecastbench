"""Minimal .env loading without copying secrets into the repository."""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str | Path, *, override: bool = False) -> set[str]:
    loaded: set[str] = set()
    with Path(path).open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value and value[0] in {'"', "'"} and value[-1:] == value[0]:
                value = value[1:-1]
            if not override and key in os.environ:
                continue
            os.environ[key] = value
            loaded.add(key)
    return loaded
