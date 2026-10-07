"""Feature per ogni evento, da barre 1m in cache (+ trade tick per le versioni con order flow). Nessuna rete.
Uso: .venv\\Scripts\\python scripts\\04_features.py [--version 1a|1b]"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import pandas as pd

from nqml.config import load_config
from nqml.data.bars import load_bars
from nqml.features.build import build_features, feature_set
from nqml.tick.windows import load_day_trades


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")

    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=cfg["features"]["version"])
    args = ap.parse_args()
    version = args.version
    fs = feature_set(version)

    ev_dir = Path(cfg["data"]["events_dir"])
    out_dir = Path(cfg["features"]["features_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"features_{version}.parquet"

    t0 = time.time()
    events = pd.read_parquet(ev_dir / "events.parquet")
    days = pd.read_parquet(ev_dir / "days.parquet")
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    print(f"eventi {len(events)}, giorni {len(days)}, barre {len(bars)}, caricati in {time.time()-t0:.0f}s")

    trades_loader, only_days = None, None
    if fs["has_orderflow"]:
        trades_dir = Path(cfg["tick"]["trades_dir"])
        sampled = pd.read_parquet(Path(cfg["tick"]["tick_dir"]) / "sampled_days.parquet")
        only_days = set(pd.to_datetime(sampled["session_date"]).dt.date)
        trades_loader = lambda sd: load_day_trades(trades_dir, sd)
        print(f"versione {version}: order flow attivo, {len(only_days)} giorni campionati")

    feats = build_features(events, days, bars, cfg, version=version,
                           trades_loader=trades_loader, only_days=only_days, progress=True)
    feats.to_parquet(out, index=False)
    print(f"scritto {out}: {len(feats)} righe, {time.time()-t0:.0f}s")

    # Diagnostiche solo fuori cassaforte (spec §11.2): il parquet scritto sopra contiene comunque tutte le righe.
    vault = dt.date.fromisoformat(cfg["vault"]["start"])
    diag = feats[pd.to_datetime(feats["session_date"]).dt.date < vault]
    print(f"\ndiagnostiche su {len(diag)} righe fuori cassaforte")

    nan_rate = diag[fs["all"]].isna().mean().sort_values(ascending=False)
    print("\nquota NaN per feature (attese: rel_vol_session nei primi 20 giorni; il resto ~0; "
          "delta_at_extreme puo' avere NaN se l'estremo e' nei primi minuti della finestra):")
    print(nan_rate[nan_rate > 0].round(4).to_string() if (nan_rate > 0).any() else "  nessun NaN")
    print("\nquantili core (q05 | q50 | q95):")
    q = diag[fs["core"]].quantile([0.05, 0.5, 0.95]).T
    print(q.round(3).to_string())

    if fs["has_orderflow"] and "delta_excursion" in diag.columns:
        print("\ndelta_excursion mediano per side (invariante: stesso segno per long e short):")
        print(diag.groupby("side")["delta_excursion"].median().round(4).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
