"""Gira il detector su ogni sessione e scrive events.parquet + days.parquet.
Uso: .venv\\Scripts\\python scripts\\02_detect.py"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

from nqml.config import load_config
from nqml.data.bars import load_bars, sessions_iter
from nqml.detector.events import event_to_row
from nqml.detector.run_day import run_day


def main() -> int:
    cfg = load_config("config.yaml")
    raw_dir = Path(cfg["data"]["raw_dir"])
    out_dir = Path(cfg["data"]["events_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    bars = load_bars(raw_dir)
    print(f"barre {len(bars)}, caricate in {time.time()-t0:.0f}s")

    rows, days = [], []
    for i, (sd, day) in enumerate(sessions_iter(bars)):
        res = run_day(day, sd, cfg)
        on = res.on_va
        days.append(dict(session_date=sd, n_rth_bars=res.n_rth_bars, valid=res.valid, n_events=len(res.events),
                         on_vah=on.vah if on else None, on_val=on.val if on else None, on_poc=on.poc if on else None))
        rows.extend(event_to_row(e) for e in res.events)
        if i % 250 == 0:
            print(f"  {sd}  eventi finora {len(rows)}")

    events = pd.DataFrame(rows)
    days_df = pd.DataFrame(days)
    events.to_parquet(out_dir / "events.parquet", index=False)
    days_df.to_parquet(out_dir / "days.parquet", index=False)
    print(f"giorni {len(days_df)} (validi {int(days_df['valid'].sum())}), eventi {len(events)}, {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
