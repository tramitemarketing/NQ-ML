"""Statistica del P&L: bootstrap a blocchi per giorno, Sharpe e Deflated Sharpe Ratio,
anno per anno, senza i migliori, drawdown, potenza e numerosità.

Generalizza `lab/core.py` (day_block_bootstrap, yearly, drop_top) a qualunque cliente.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats as sps

EULER_GAMMA = 0.5772156649015329


# --------------------------------------------------------------------------- bootstrap
def day_block_bootstrap(values, days, n_boot: int = 10000, seed: int = 0, alpha: float = 0.05,
                        return_dist: bool = False) -> dict:
    """Media per trade con intervallo e p-value dal bootstrap a blocchi per giorno: i trade dello
    stesso giorno restano insieme (sono correlati). p_two: bilaterale contro 0 (bootstrap
    centrato); p_pos: unilaterale per media > 0. Identico a lab.core.day_block_bootstrap."""
    values = np.asarray(values, float)
    days = np.asarray(days)
    ok = np.isfinite(values)
    values, days = values[ok], days[ok]
    if len(values) == 0:
        out = {"n": 0, "n_days": 0, "mean": np.nan, "lo": np.nan, "hi": np.nan, "se": np.nan,
               "p_two": np.nan, "p_pos": np.nan}
        if return_dist:
            out["dist"] = np.array([])
        return out
    codes, _ = pd.factorize(days)
    s = np.bincount(codes, weights=values)
    n = np.bincount(codes).astype(float)
    nd = len(s)
    point = s.sum() / n.sum()
    rng = np.random.default_rng(seed)
    dist = np.empty(n_boot)
    chunk = max(1, int(2e7 // max(nd, 1)))
    for a in range(0, n_boot, chunk):
        b = min(n_boot, a + chunk)
        idx = rng.integers(0, nd, size=(b - a, nd), dtype=np.int32)
        dist[a:b] = s[idx].sum(1) / n[idx].sum(1)
    centered = dist - point
    p_two = float((np.abs(centered) >= abs(point)).mean())
    p_pos = float((centered >= point).mean())
    out = {"n": int(n.sum()), "n_days": int(nd), "mean": float(point),
           "lo": float(np.percentile(dist, 100 * alpha / 2)), "hi": float(np.percentile(dist, 100 * (1 - alpha / 2))),
           "se": float(dist.std(ddof=1)) if n_boot > 1 else np.nan,
           "p_two": max(p_two, 1 / n_boot), "p_pos": max(p_pos, 1 / n_boot)}
    if return_dist:
        out["dist"] = dist
    return out


# --------------------------------------------------------------------------- Sharpe / DSR
def expected_max_sr(n_trials: int, sr_var: float) -> float:
    """E[max SR] fra N tentativi indipendenti a SR vero nullo (Bailey & Lopez de Prado 2014, eq. 5
    via teorema di Fisher-Tippett-Gumbel): sqrt(V) * ((1-g) Z^-1(1-1/N) + g Z^-1(1-1/(N e)))."""
    if n_trials <= 1:
        return 0.0
    z1 = sps.norm.ppf(1 - 1 / n_trials)
    z2 = sps.norm.ppf(1 - 1 / (n_trials * math.e))
    return math.sqrt(sr_var) * ((1 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)


def probabilistic_sr(sr: float, sr_ref: float, T: int, skew: float, kurt: float) -> float:
    """PSR(SR*) = Phi( (SR - SR*) sqrt(T-1) / sqrt(1 - g3 SR + (g4-1)/4 SR^2) ), SR non annualizzato,
    g4 = curtosi NON in eccesso (normale = 3)."""
    den = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if T < 3 or not np.isfinite(sr) or den <= 0:
        return np.nan
    return float(sps.norm.cdf((sr - sr_ref) * math.sqrt(T - 1) / math.sqrt(den)))


def deflated_sharpe(returns, n_trials: int, sr_var: float | None = None) -> dict:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado, J. Portfolio Management 2014).
    `returns`: serie per periodo (qui: P&L netto giornaliero, zero nei giorni senza trade).
    `n_trials`: quante varianti/strategie sono state provate prima di scegliere questa.
    `sr_var`: varianza degli SR (per periodo) fra i tentativi; se ignota si usa la varianza dello
    stimatore sotto l'ipotesi nulla, 1/(T-1): cioè "N tentativi senza alcun vantaggio vero"."""
    r = np.asarray(returns, float)
    r = r[np.isfinite(r)]
    T = len(r)
    if T < 3 or r.std(ddof=1) == 0:
        return {"T": T, "sr": np.nan, "sr0": np.nan, "psr": np.nan, "dsr": np.nan, "skew": np.nan, "kurt": np.nan,
                "n_trials": n_trials}
    sr = r.mean() / r.std(ddof=1)
    g3 = float(sps.skew(r))
    g4 = float(sps.kurtosis(r, fisher=False))
    v = sr_var if sr_var is not None else 1.0 / (T - 1)
    sr0 = expected_max_sr(n_trials, v)
    return {"T": T, "sr": float(sr), "sr0": float(sr0), "skew": g3, "kurt": g4, "n_trials": int(n_trials),
            "sr_var": float(v), "psr": probabilistic_sr(sr, 0.0, T, g3, g4),
            "dsr": probabilistic_sr(sr, sr0, T, g3, g4)}


def daily_series(net_pts, sessions, calendar: pd.DatetimeIndex | None = None) -> pd.Series:
    """P&L netto per sessione; con un calendario, i giorni senza trade valgono zero."""
    s = pd.Series(np.asarray(net_pts, float), index=pd.DatetimeIndex(sessions)).groupby(level=0).sum()
    if calendar is not None and len(calendar):
        cal = calendar[(calendar >= s.index.min()) & (calendar <= s.index.max())]
        s = s.reindex(cal.union(s.index), fill_value=0.0)
    else:
        cal = pd.bdate_range(s.index.min(), s.index.max())
        s = s.reindex(cal.union(s.index), fill_value=0.0)
    return s


# --------------------------------------------------------------------------- robustezza
def yearly(values, days) -> pd.DataFrame:
    d = pd.DataFrame({"v": np.asarray(values, float), "y": pd.DatetimeIndex(days).year})
    return d.groupby("y")["v"].agg(["mean", "count", "sum"])


def default_top_k(n: int) -> int:
    """Quanti trade migliori togliere: 20 come nel laboratorio, ma mai più del 2 % dei trade."""
    return int(max(1, min(20, n // 50)))


def drop_top(values, k: int) -> float:
    v = np.sort(np.asarray(values, float)[np.isfinite(values)])
    return float(v[:-k].mean()) if len(v) > k else np.nan


def drawdown(equity: np.ndarray) -> dict:
    eq = np.concatenate([[0.0], np.asarray(equity, float)])
    peak = np.maximum.accumulate(eq)
    dd = eq - peak
    i_tr = int(np.argmin(dd))
    i_pk = int(np.argmax(eq[: i_tr + 1])) if i_tr > 0 else 0
    rec = np.flatnonzero(eq[i_tr:] >= peak[i_tr])
    under = dd < 0
    longest, cur = 0, 0
    for u in under:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    return {"max_dd": float(-dd.min()), "peak_i": i_pk - 1, "trough_i": i_tr - 1,
            "recovered": bool(len(rec)), "recovery_i": int(i_tr + rec[0] - 1) if len(rec) else None,
            "longest_under_n": int(longest), "dd_curve": dd[1:]}


def bootstrap_max_dd(daily_pnl: np.ndarray, n_boot: int = 1000, seed: int = 1) -> np.ndarray:
    """Distribuzione del massimo drawdown ricampionando i giorni (stessa lunghezza del campione)."""
    x = np.asarray(daily_pnl, float)
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for i in range(n_boot):
        eq = np.cumsum(x[rng.integers(0, len(x), len(x))])
        out[i] = float(np.max(np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq))
    return out


def power(mean: float, se: float, n: int, span_days: float, alpha: float = 0.05, power_: float = 0.80) -> dict:
    """Effetto minimo rilevabile con i dati attuali e trade necessari per rilevare l'effetto osservato.
    Test unilaterale; SE dal bootstrap a blocchi (tiene conto dei trade correlati nello stesso giorno)."""
    z = sps.norm.ppf(1 - alpha) + sps.norm.ppf(power_)
    mde = z * se
    out = {"mde": float(mde), "z": float(z)}
    if mean > 0 and se > 0:
        n_need = n * (z * se / mean) ** 2
        out["n_needed"] = float(n_need)
        per_day = n / max(span_days, 1)
        out["days_needed"] = float(n_need / per_day)
        out["power_now"] = float(sps.norm.cdf(mean / se - sps.norm.ppf(1 - alpha)))
    else:
        out["n_needed"] = np.inf
        out["days_needed"] = np.inf
        out["power_now"] = np.nan
    return out


def basic(net, gross) -> dict:
    net = np.asarray(net, float)
    wins = net[net > 0]
    losses = net[net < 0]
    return {"n": len(net), "gross_mean": float(np.mean(gross)), "net_mean": float(np.mean(net)),
            "net_total": float(np.sum(net)), "win_rate": float((net > 0).mean()) if len(net) else np.nan,
            "avg_win": float(wins.mean()) if len(wins) else np.nan,
            "avg_loss": float(losses.mean()) if len(losses) else np.nan,
            "profit_factor": float(wins.sum() / -losses.sum()) if losses.sum() < 0 else np.inf,
            "std": float(np.std(net, ddof=1)) if len(net) > 1 else np.nan}
