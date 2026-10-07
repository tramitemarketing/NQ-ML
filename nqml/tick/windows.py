"""Finestre di escursione unite per giorno e loader dei trade in cache."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

TRADE_COLS = ["price", "size", "side"]


def merge_intervals(intervals):
    out: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def windows_for_days(events: pd.DataFrame, sampled_days: pd.DataFrame) -> pd.DataFrame:
    keep = set(pd.to_datetime(sampled_days["session_date"]).dt.date)
    ev = events[pd.to_datetime(events["session_date"]).dt.date.isin(keep)]
    rows = []
    for sd, g in ev.groupby(pd.to_datetime(ev["session_date"]).dt.date):
        for s, e in merge_intervals(list(zip(pd.to_datetime(g["break_ts"]), pd.to_datetime(g["reentry_ts"])))):
            rows.append(dict(session_date=sd, win_start=s, win_end=e))
    return pd.DataFrame(rows, columns=["session_date", "win_start", "win_end"])


def window_path(trades_dir: Path, session_date: dt.date, win_start: pd.Timestamp, win_end: pd.Timestamp) -> Path:
    return Path(trades_dir) / session_date.isoformat() / f"{win_start.strftime('%H%M')}-{win_end.strftime('%H%M')}.parquet"


def load_day_trades(trades_dir: Path, session_date: dt.date) -> pd.DataFrame | None:
    d = Path(trades_dir) / session_date.isoformat()
    files = sorted(d.glob("*.parquet")) if d.exists() else []
    if not files:
        return None
    tr = pd.concat(pd.read_parquet(f)[TRADE_COLS] for f in files).sort_index(kind="stable")
    tr.index.name = "ts_event"
    return tr
