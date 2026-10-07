"""Feature di contesto, geometria della VA, cross-VA e rischio/rendimento. Mai prezzi assoluti."""
from __future__ import annotations

import math

import pandas as pd

from nqml.features.day_context import DayContext, bars5_upto
from nqml.features.direction import broken_edge, far_edge, toward_target
from nqml.profile.sessions import rth_open_utc
from nqml.profile.volume_profile import ValueArea

NAN = float("nan")


def _div(a: float, b: float) -> float:
    return a / b if b not in (0, 0.0) and not math.isnan(b) else NAN


def _overlap(a: ValueArea, b: ValueArea) -> float:
    inter = max(0.0, min(a.vah, b.vah) - max(a.val, b.val))
    return _div(inter, max(a.vah - a.val, b.vah - b.val))


def geometry_features(row: dict, ctx: DayContext, other_va: ValueArea | None, atr: float) -> dict:
    side = row["side"]
    close = float(row["entry_ref_price"])
    w = row["vah_reentry"] - row["val_reentry"]
    w_break = row["vah_break"] - row["val_break"]
    edge_b = broken_edge(side, row["vah_break"], row["val_break"])
    edge_r = broken_edge(side, row["vah_reentry"], row["val_reentry"])
    stop_dist = abs(close - row["stop_price"])
    target_dist = abs(row["target_price"] - close)
    reentry_ts = pd.Timestamp(row["reentry_ts"])
    va_ref = ValueArea(poc=row["poc_reentry"], vah=row["vah_reentry"], val=row["val_reentry"], total_volume=0.0, n_levels=0)

    if row["va_type"] == "DEV":
        bars_in_profile = int(len(bars5_upto(ctx, reentry_ts)))
    else:
        bars_in_profile = ctx.n_on_bars / 5

    if ctx.on_va is None or ctx.rth_open_price is None:
        open_vs = NAN
    else:
        o = ctx.rth_open_price
        if toward_target(side, broken_edge(side, ctx.on_va.vah, ctx.on_va.val), o) < 0:
            open_vs = -1
        elif toward_target(side, far_edge(side, ctx.on_va.vah, ctx.on_va.val), o) > 0:
            open_vs = 1
        else:
            open_vs = 0

    if other_va is None:
        in_other = near = far = overlap = NAN
    else:
        in_other = 1 if other_va.val <= close <= other_va.vah else 0
        near = _div(toward_target(side, close, broken_edge(side, other_va.vah, other_va.val)), atr)
        far = _div(toward_target(side, close, far_edge(side, other_va.vah, other_va.val)), atr)
        overlap = _overlap(va_ref, other_va)

    return {
        "va_type": 0 if row["va_type"] == "ON" else 1,
        "minutes_since_open": (reentry_ts - rth_open_utc(row["session_date"])).total_seconds() / 60.0,
        "bars_in_profile": bars_in_profile,
        "open_vs_on_va": open_vs,
        "va_width_atr": _div(w, atr),
        "excursion_depth": _div(toward_target(side, row["extreme_price"], edge_b), w_break),
        "excursion_minutes": float(row["excursion_minutes"]),
        "bars_outside": float(row["bars_outside"]),
        "reentry_close_pos": _div(toward_target(side, edge_r, close), w),
        "va_shift": _div(toward_target(side, edge_r, edge_b), w_break),
        "poc_pos": 1 if toward_target(side, close, row["poc_reentry"]) > 0 else 0,
        "in_other_va": in_other,
        "dist_other_near_atr": near,
        "dist_other_far_atr": far,
        "overlap_on_dev": overlap,
        "stop_dist_atr": _div(stop_dist, atr),
        "target_dist_atr": _div(target_dist, atr),
        "rr_ratio": _div(target_dist, stop_dist),
    }
