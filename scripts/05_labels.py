"""Label (target prima dello stop?) e P&L per ogni evento, dalle barre 1m in cache. Nessuna rete.
Uso: .venv\\Scripts\\python scripts\\05_labels.py"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

import pandas as pd

from nqml.config import load_config
from nqml.data.bars import load_bars, rth_bars, sessions_iter
from nqml.labels.labeler import apply_costs, label_event


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    s = cfg["sessions"]
    out_dir = Path(cfg["labels"]["labels_dir"]); out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    events = pd.read_parquet(Path(cfg["data"]["events_dir"]) / "events.parquet")
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    ev_by_day = {sd: g for sd, g in events.groupby(pd.to_datetime(events["session_date"]).dt.date)}
    rows = []
    for sd, day in sessions_iter(bars):
        g = ev_by_day.get(sd)
        if g is None:
            continue
        rth = rth_bars(day, s["rth_open"], s["rth_close"])
        for _, r in g.iterrows():
            rows.append(label_event(r.to_dict(), rth, cfg))
    lab = pd.DataFrame(rows)
    lab = lab.merge(events[["event_id", "side", "stop_price"]], on="event_id", how="left")
    lab = apply_costs(lab, cfg["costs"]["slippage_ticks_per_side"], cfg["costs"]["commission_per_side_usd"], cfg)
    lab.to_parquet(out_dir / "labels.parquet", index=False)

    # Diagnostiche solo fuori cassaforte (spec §11.2): il parquet scritto sopra contiene comunque tutte le righe.
    vault = dt.date.fromisoformat(cfg["vault"]["start"])
    diag = lab.merge(events[["event_id", "session_date"]], on="event_id", how="left")
    diag = diag[pd.to_datetime(diag["session_date"]).dt.date < vault]
    print(f"diagnostiche su {len(diag)} righe fuori cassaforte")

    print(f"label {len(lab)} in {time.time()-t0:.0f}s")
    print("exit_reason:", diag["exit_reason"].value_counts().to_dict())
    print(f"label=1 rate {diag['label'].mean():.4f}")
    print(f"realized_R: media {diag['realized_R'].mean():.4f}, mediana {diag['realized_R'].median():.4f}, "
          f"min {diag['realized_R'].min():.3f}, max {diag['realized_R'].max():.3f}")
    print(f"pnl_usd totale su tutti i candidati (B0, 1 contratto, senza vincolo di posizione): {diag['pnl_usd'].sum():,.0f} $")
    return 0


if __name__ == "__main__":
    sys.exit(main())
