"""Feature di order flow dai trade tick (spec §6): delta, absorption, trade grandi, divergenza. Direzionali, mai oltre reentry_ts."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from nqml.features.day_context import DayContext

NAN = float("nan")
KEYS = ["delta_excursion", "delta_reentry", "absorption_score", "delta_at_extreme",
        "extreme_zone_delta", "large_trade_share", "large_trade_delta", "cum_delta_divergence"]


def con_side(side: str) -> str:
    """Aggressore nella direzione della rottura: long rompe in basso -> venditori ('A'); short -> compratori ('B')."""
    return "A" if side == "long" else "B"


def contro_side(side: str) -> str:
    return "B" if side == "long" else "A"


def _vol(tr: pd.DataFrame, s: str) -> float:
    return float(tr.loc[tr["side"] == s, "size"].sum()) if len(tr) else 0.0


def delta(tr: pd.DataFrame, side: str) -> float:
    con, contro = _vol(tr, con_side(side)), _vol(tr, contro_side(side))
    return (contro - con) / (con + contro) if (con + contro) > 0 else NAN


def _extreme_ts(row: dict, ctx: DayContext, break_ts, reentry_ts):
    rth = ctx.rth1m
    win = rth.loc[(rth.index >= break_ts) & (rth.index < reentry_ts)]
    hit = win.loc[win["low"] == row["extreme_price"]] if row["side"] == "long" else win.loc[win["high"] == row["extreme_price"]]
    return hit.index[0] if len(hit) else None


def orderflow_features(row: dict, ctx: DayContext, cfg: dict) -> dict:
    if ctx.trades is None:
        return {k: NAN for k in KEYS}
    tk, tick = cfg["tick"], cfg["instrument"]["tick_size"]
    side = row["side"]
    break_ts, reentry_ts = pd.Timestamp(row["break_ts"]), pd.Timestamp(row["reentry_ts"])
    tr = ctx.trades
    W = tr.loc[(tr.index >= break_ts) & (tr.index < reentry_ts)]
    if len(W) == 0:
        return {k: NAN for k in KEYS}
    v_tot = float(W["size"].sum())
    R = tr.loc[(tr.index >= reentry_ts - pd.Timedelta(minutes=5)) & (tr.index < reentry_ts)]
    Z = W.loc[(W["price"] - row["extreme_price"]).abs() <= tk["extreme_zone_ticks"] * tick]
    q = float(W["size"].quantile(tk["large_trade_quantile"]))
    L = W.loc[W["size"] >= q]

    t_ext = _extreme_ts(row, ctx, break_ts, reentry_ts)
    if t_ext is None:
        d_ext, div = NAN, NAN
    else:
        pre = tr.loc[(tr.index >= t_ext - pd.Timedelta(minutes=tk["extreme_delta_minutes"])) & (tr.index < t_ext)]
        d_ext = delta(pre, side)
        signed = np.where(W["side"] == con_side(side), W["size"], np.where(W["side"] == contro_side(side), -W["size"], 0.0))
        c = pd.Series(signed, index=W.index).groupby(W.index.floor("1min")).sum().cumsum()
        before = c.loc[c.index < t_ext]
        c_ext = float(c.loc[c.index <= t_ext].iloc[-1]) if (c.index <= t_ext).any() else NAN
        div = float(len(before) > 0 and not math.isnan(c_ext) and c_ext < float(before.max()))

    return {
        "delta_excursion": delta(W, side),
        "delta_reentry": delta(R, side),
        "absorption_score": _vol(Z, con_side(side)) / v_tot if v_tot > 0 else NAN,
        "delta_at_extreme": d_ext,
        "extreme_zone_delta": delta(Z, side),
        "large_trade_share": float(L["size"].sum()) / v_tot if v_tot > 0 else NAN,
        "large_trade_delta": delta(L, side),
        "cum_delta_divergence": div,
    }
