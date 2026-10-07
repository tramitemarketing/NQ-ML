"""Motore event-driven minimale (spec §10.1): una posizione alla volta, duplicati, ingresso all'open successivo."""
from __future__ import annotations

import pandas as pd


def simulate_one_position(df: pd.DataFrame, take_col: str) -> pd.DataFrame:
    out = df.sort_values(["entry_ts", "ev_r"], ascending=[True, False]).copy()
    status = []
    last_exit = None
    last_entry = None
    for r in out.itertuples():
        if not getattr(r, take_col):
            status.append("not_taken")
        elif last_entry is not None and r.entry_ts == last_entry:
            status.append("duplicate")
        elif last_exit is not None and r.entry_ts <= last_exit:
            status.append("skipped_in_position")
        else:
            status.append("taken")
            last_exit, last_entry = r.exit_ts, r.entry_ts
    out["status"] = status
    return out


def taken(df: pd.DataFrame, take_col: str) -> pd.DataFrame:
    sim = simulate_one_position(df, take_col)
    return sim[sim["status"] == "taken"]
