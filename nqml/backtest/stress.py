"""Stress (spec §10.3): slippage 2/3 tick, commissioni x2, tolti i 5% trade migliori. Decisioni fisse, P&L rivalutato.
Lo slippage di stress si applica per lato: sull'ingresso e su ogni uscita a mercato (stop, time-stop); il target
resta un ordine limite (nessuno slippage) — vedi apply_costs."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from nqml.backtest.metrics import summarize
from nqml.labels.labeler import apply_costs


def stress_scenarios(cfg: dict) -> list[dict]:
    c, b = cfg["costs"], cfg["backtest"]
    base = dict(slippage_ticks=c["slippage_ticks_per_side"], commission=c["commission_per_side_usd"], drop_top_pct=0.0)
    out = [dict(name="base", **base)]
    for t in b["stress_slippage_ticks"]:
        out.append(dict(name=f"slip_{t}", **{**base, "slippage_ticks": t}))
    out.append(dict(name="comm_x2", **{**base, "commission": c["commission_per_side_usd"] * b["stress_commission_mult"]}))
    out.append(dict(name=f"drop_top_{int(round(b['stress_drop_top_pct'] * 100))}pct", **{**base, "drop_top_pct": b["stress_drop_top_pct"]}))
    return out


def revalue(trades_taken: pd.DataFrame, scenario: dict, cfg: dict) -> pd.DataFrame:
    out = apply_costs(trades_taken, scenario["slippage_ticks"], scenario["commission"], cfg)
    if scenario["drop_top_pct"] > 0 and len(out):
        k = int(np.ceil(len(out) * scenario["drop_top_pct"]))
        best_first = out.sort_values(["realized_R", "entry_ts"], ascending=[False, False])
        out = out.drop(best_first.index[:k])
    return out


def stress_table(trades_taken: pd.DataFrame, n_days: int, cfg: dict, days: list[dt.date] | None = None) -> pd.DataFrame:
    pv = cfg["instrument"]["point_value_usd"]
    rows = []
    for sc in stress_scenarios(cfg):
        rows.append({"name": sc["name"], **summarize(revalue(trades_taken, sc, cfg), n_days, pv, days=days)})
    return pd.DataFrame(rows)
