"""Strumenti comuni del giro 6 (PROTOCOLLO §19): metà del discovery, t giornaliero, Holm, criteri del §3."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from lab import controller, core

HALVES = {"H1": ("2010-06-07", "2014-12-31"), "H2": ("2015-01-01", "2018-12-31")}


def half_of(sessions) -> np.ndarray:
    s = pd.DatetimeIndex(sessions)
    return np.where(s <= pd.Timestamp(HALVES["H1"][1]), "H1", "H2")


def daily_t(per_session: pd.Series) -> dict:
    """Media, t e p unilaterale (media > 0) su una serie giornaliera (zeri inclusi)."""
    v = per_session.dropna().to_numpy(float)
    if len(v) < 3 or v.std(ddof=1) == 0:
        return {"n_days": len(v), "mean": float(np.mean(v)) if len(v) else np.nan, "t": np.nan, "p_pos": np.nan}
    t = v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))
    return {"n_days": len(v), "mean": float(v.mean()), "t": float(t), "p_pos": float(stats.norm.sf(t))}


def by_half(per_session: pd.Series) -> dict:
    h = half_of(per_session.index)
    return {k: daily_t(per_session[h == k]) for k in HALVES}


def holm(p: dict) -> dict:
    """p corretti di Holm (step-down, monotoni)."""
    keys = sorted(p, key=lambda k: p[k])
    m, out, run = len(keys), {}, 0.0
    for i, k in enumerate(keys):
        run = max(run, min(1.0, (m - i) * p[k]))
        out[k] = run
    return out


def placebo_p(real: float, plac: np.ndarray) -> float:
    plac = np.asarray(plac, float)
    return float((1 + np.sum(plac >= real)) / (len(plac) + 1))


def lab_criteria(bars: pd.DataFrame, trades: pd.DataFrame, alpha: float, cost: float = core.COST_RT_POINTS) -> dict:
    """I quattro criteri del §3 (con l'emendamento 1) calcolati sul discovery: netto p < alpha, netto - beta
    p < alpha, maggioranza degli anni positivi, positivo senza i 20 migliori. `bars` con colonna in_phase."""
    t = trades.copy()
    t["session"] = pd.to_datetime(t["session"])
    net = t["gross_pts"].to_numpy(float) - cost
    beta = controller.beta_component(bars, t)
    st = core.day_block_bootstrap(net, t["session"].values)
    st_b = core.day_block_bootstrap(net - beta, t["session"].values)
    yr = core.yearly(net, t["session"])
    yrs_pos = int((yr["mean"] > 0).sum())
    dt20 = core.drop_top(net, 20)
    crit = {"c1_p": bool(st["mean"] > 0 and st["p_pos"] < alpha),
            "c2_beta": bool(st_b["mean"] > 0 and st_b["p_pos"] < alpha),
            "c3_years": bool(yrs_pos > len(yr) / 2),
            "c4_droptop": bool(dt20 > 0)}
    return {"alpha": alpha, "net": st, "net_minus_beta": st_b, "years_pos": f"{yrs_pos}/{len(yr)}",
            "years": yr["mean"].round(2).to_dict(), "drop_top20": dt20, "crit": crit, "pass": all(crit.values())}
