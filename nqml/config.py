"""Unica porta d'accesso a config.yaml e ai metadati di riproducibilità."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import yaml


def load_config(path: str | Path = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def config_hash(path: str | Path = "config.yaml") -> str:
    text = Path(path).read_bytes()
    return hashlib.sha256(text).hexdigest()[:12]


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"
