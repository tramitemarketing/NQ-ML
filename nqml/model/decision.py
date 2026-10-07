"""Decisione via valore atteso in unità di rischio (spec §8)."""
from __future__ import annotations

import numpy as np


def costs_in_r(stop_dist_pts, cfg: dict, slippage_ticks: int | None = None, commission: float | None = None):
    c = cfg["costs"]
    tick, pv = cfg["instrument"]["tick_size"], cfg["instrument"]["point_value_usd"]
    slip = (c["slippage_ticks_per_side"] if slippage_ticks is None else slippage_ticks) * tick
    comm = c["commission_per_side_usd"] if commission is None else commission
    cost_usd = 2.0 * comm + 2.0 * slip * pv
    return cost_usd / (np.asarray(stop_dist_pts, dtype=float) * pv) if np.ndim(stop_dist_pts) else cost_usd / (float(stop_dist_pts) * pv)


def ev_r(p, rr, costs_r):
    p, rr = np.asarray(p, dtype=float), np.asarray(rr, dtype=float)
    out = p * rr - (1.0 - p) - np.asarray(costs_r, dtype=float)
    return float(out) if out.ndim == 0 else out


def take(ev, margin_r: float):
    ev = np.asarray(ev, dtype=float)
    out = ev > margin_r
    return bool(out) if out.ndim == 0 else out
