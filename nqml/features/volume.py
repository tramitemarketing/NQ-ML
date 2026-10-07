"""Feature di volume da barre 1m e 5m (spec §6): pendenze, climax, rientro, volume relativo, ATR, range."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from nqml.features.day_context import DayContext, bars5_upto

NAN = float("nan")


def norm_slope(v: np.ndarray) -> float:
    v = np.asarray(v, dtype=float)
    if len(v) < 2 or v.mean() == 0:
        return NAN
    x = np.arange(len(v), dtype=float)
    xc, vc = x - x.mean(), v - v.mean()
    slope = float((xc * vc).sum() / (xc * xc).sum())
    return slope / float(v.mean())


def atr_at(ctx: DayContext, ts_close: pd.Timestamp) -> float:
    b = ctx.bars5.loc[ctx.bars5["ts_close"] == ts_close]
    return float(b["atr"].iloc[0]) if len(b) else NAN


def _div(a: float, b: float) -> float:
    return a / b if b and not math.isnan(b) else NAN


def volume_features(row: dict, ctx: DayContext, rel_vol_baseline: float | None, cfg: dict) -> dict:
    fc = cfg["features"]
    side = row["side"]
    break_ts, reentry_ts = pd.Timestamp(row["break_ts"]), pd.Timestamp(row["reentry_ts"])
    rth = ctx.rth1m
    win = rth.loc[(rth.index >= break_ts) & (rth.index < reentry_ts)]
    vols = win["volume"].to_numpy(dtype=float)
    mean_win = vols.mean() if len(vols) else NAN

    ext = row["extreme_price"]
    hit = win.loc[win["low"] == ext] if side == "long" else win.loc[win["high"] == ext]
    vol_at_extreme = _div(float(hit["volume"].iloc[0]), mean_win) if len(hit) else NAN

    b5 = ctx.bars5
    reentry5 = b5.loc[b5["ts_close"] == reentry_ts]
    prior5 = b5.loc[b5["ts_close"] < reentry_ts]
    vol_reentry_bar = _div(float(reentry5["volume"].iloc[0]), float(prior5["volume"].mean())) if len(reentry5) and len(prior5) else NAN

    pre = ctx.bars1m.loc[(ctx.bars1m.index >= break_ts - pd.Timedelta(minutes=fc["pre_break_minutes"])) & (ctx.bars1m.index < break_ts)]
    vol_excursion_vs_pre = _div(mean_win, float(pre["volume"].mean())) if len(pre) else NAN

    last = rth.loc[rth.index < reentry_ts]["volume"].to_numpy(dtype=float)[-fc["reentry_slope_bars"]:]
    vol_reentry_slope = norm_slope(last)

    cum = float(reentry5["cum_vol"].iloc[0]) if len(reentry5) else NAN
    rel_vol = _div(cum, float(rel_vol_baseline)) if rel_vol_baseline else NAN

    atr = atr_at(ctx, reentry_ts)
    sofar = rth.loc[rth.index < reentry_ts]
    day_range = float(sofar["high"].max() - sofar["low"].min()) if len(sofar) else NAN

    return {
        "vol_slope_excursion": norm_slope(vols),
        "vol_at_extreme": vol_at_extreme,
        "vol_reentry_bar": vol_reentry_bar,
        "vol_excursion_vs_pre": vol_excursion_vs_pre,
        "vol_reentry_slope": vol_reentry_slope,
        "rel_vol_session": rel_vol,
        "atr_14_5m": atr,
        "day_range_atr": _div(day_range, atr),
    }
