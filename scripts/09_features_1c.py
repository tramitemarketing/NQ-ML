"""Milestone 1c: features_1c.parquet = features_1a (tutti gli eventi) + le 3 feature order flow core della 1b (NaN altrove).
Uso: .venv\\Scripts\\python scripts\\09_features_1c.py  — nessuna rete, nessun ricalcolo."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from nqml.config import load_config
from nqml.features.build import ORDERFLOW_CORE
from nqml.features.union import union_tick


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    d = Path(cfg["features"]["features_dir"])
    fa, fb = pd.read_parquet(d / "features_1a.parquet"), pd.read_parquet(d / "features_1b.parquet")
    out = union_tick(fa, fb, ORDERFLOW_CORE)
    n_tick = int(out[ORDERFLOW_CORE[0]].notna().sum())
    assert len(out) == len(fa) and n_tick == len(fb), (len(out), len(fa), n_tick, len(fb))
    tmp = d / "features_1c.parquet.tmp"
    out.to_parquet(tmp, index=False); tmp.replace(d / "features_1c.parquet")
    print(f"features_1c: {len(out)} eventi, {n_tick} con order flow ({n_tick / len(out):.1%}), colonne {len(out.columns)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
