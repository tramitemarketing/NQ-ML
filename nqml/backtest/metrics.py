"""Metriche di trading e intervalli block-bootstrap per giorno (spec §10.2)."""
from __future__ import annotations

import datetime as dt
from typing import Callable

import numpy as np
import pandas as pd


def _max_drawdown(x: np.ndarray) -> float:
    if len(x) == 0:
        return 0.0
    eq = np.cumsum(x)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return float(np.max(peak - eq))


def summarize(trades: pd.DataFrame, n_days: int, point_value: float, days: list[dt.date] | None = None) -> dict:
    n = len(trades)
    if n == 0:
        return dict(n=0, trades_per_day=0.0, pct_days_active=0.0, win_rate=np.nan, mean_R=np.nan, profit_factor=np.nan,
                    expectancy_usd=np.nan, max_dd_R=0.0, max_dd_usd=0.0, sharpe_daily=np.nan, months_negative=0, months_total=0)
    t = trades.sort_values("entry_ts")
    R, pnl = t["realized_R"].to_numpy(), t["pnl_usd"].to_numpy()
    pos, neg = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    if days is not None:
        # Sharpe e mesi su TUTTI i giorni/mesi di test (non solo quelli con trade): un giorno/mese
        # senza trade pesa 0, non manca dal calcolo.
        daily = t.groupby("session_date")["pnl_usd"].sum().reindex(days).fillna(0.0)
        months = pd.to_datetime(pd.Series(days)).dt.to_period("M").to_numpy()
        monthly = daily.groupby(months).sum()
    else:
        daily = t.groupby("session_date")["pnl_usd"].sum()
        monthly = t.groupby(pd.to_datetime(t["session_date"]).dt.to_period("M"))["pnl_usd"].sum()
    return dict(
        n=int(n), trades_per_day=n / n_days, pct_days_active=t["session_date"].nunique() / n_days,
        win_rate=float((R > 0).mean()), mean_R=float(R.mean()),
        profit_factor=float(pos / neg) if neg > 0 else float("inf"),
        expectancy_usd=float(pnl.mean()), max_dd_R=_max_drawdown(R), max_dd_usd=_max_drawdown(pnl),
        sharpe_daily=float(daily.mean() / daily.std(ddof=1) * np.sqrt(252)) if len(daily) > 1 and daily.std(ddof=1) > 0 else np.nan,
        months_negative=int((monthly < 0).sum()), months_total=int(len(monthly)),
    )


def per_day_table(frames: dict[str, pd.DataFrame], days: list[dt.date]) -> pd.DataFrame:
    tab = pd.DataFrame(index=pd.Index(days, name="session_date"))
    for name, df in frames.items():
        g = df.groupby("session_date")
        tab[f"{name}_sumR"] = g["realized_R"].sum().reindex(days).fillna(0.0)
        tab[f"{name}_n"] = g.size().reindex(days).fillna(0).astype(int)
        tab[f"{name}_pnl"] = g["pnl_usd"].sum().reindex(days).fillna(0.0)
    return tab


def mean_r_stat(name: str) -> Callable[[pd.DataFrame], float]:
    def stat(t: pd.DataFrame) -> float:
        n = t[f"{name}_n"].sum()
        return float(t[f"{name}_sumR"].sum() / n) if n > 0 else np.nan
    return stat


def diff_mean_r_stat(a: str, b: str) -> Callable[[pd.DataFrame], float]:
    sa, sb = mean_r_stat(a), mean_r_stat(b)
    return lambda t: sa(t) - sb(t)


def block_bootstrap_ci(per_day: pd.DataFrame, stat: Callable[[pd.DataFrame], float], n_boot: int, seed: int,
                        alpha: float = 0.05) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(per_day)
    vals = np.empty(n_boot)
    arr = per_day.to_numpy()
    cols = list(per_day.columns)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        vals[i] = stat(pd.DataFrame(arr[idx], columns=cols))
    return float(np.nanpercentile(vals, 100 * alpha / 2)), float(np.nanpercentile(vals, 100 * (1 - alpha / 2)))


def fold_sign_consistency(pred: pd.DataFrame, a_col: str, b_col: str) -> dict[int, float]:
    from nqml.backtest.engine import taken
    out = {}
    for k, g in pred.groupby("fold"):
        ta, tb = taken(g, a_col), taken(g, b_col)
        out[int(k)] = float(ta["realized_R"].mean() - tb["realized_R"].mean()) if len(ta) and len(tb) else np.nan
    return out
