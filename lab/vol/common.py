"""Famiglia vol: feature giornaliere e intraday di volatilita', calcolate SOLO con dati della sessione
stessa o precedenti (nessun look-ahead: ogni previsione per la sessione t usa informazione <= t-1,
salvo le feature esplicitamente "overnight/prima ora" che sono note all'ora dichiarata).

Unita' dichiarate PRIMA di guardare:
- regolarita': varianze e range in log (scale-free), rendimenti in % del prezzo GREZZO;
- strategie: punti NQ per 1 contratto (unita' del controller); diagnostica secondaria in ATR20.

Nota tecnica: adj_* e' aggiustato all'indietro in modo ADDITIVO (nel 2010 adj ~ grezzo + 3800):
per rapporti/percentuali uso i prezzi grezzi (entro la sessione RTH non c'e' mai un roll) oppure
differenze di adj divise per il prezzo grezzo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core

FAM = "vol"


def bars5_rth(bars: pd.DataFrame) -> pd.DataFrame:
    """Barre 5m RTH (78 per sessione piena), prezzi grezzi e adj. Indice: (session, k) con k=0..77."""
    b = bars[bars["rth"]]
    k = ((b["ny_min"].to_numpy() - 570) // 5).astype(int)
    g = b.groupby([b["session"].to_numpy(), k], sort=True)
    out = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last(),
        "adj_open": g["adj_open"].first(), "adj_close": g["adj_close"].last(),
    })
    out.index.names = ["session", "k"]
    return out


def daily_features(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Una riga per sessione valida. Colonne misurate a fine sessione t (usarle con shift(1) per prevedere)."""
    d = daily[daily["valid"]].copy()
    b5 = bars5_rth(bars)
    # rendimenti log 5m RTH (primo: open 9:30 -> close 9:34)
    lc = np.log(b5["close"])
    lo = np.log(b5["open"])
    prev = lc.groupby(level=0).shift(1)
    r5 = (lc - prev).fillna(lc - lo) * 100.0          # in %
    rv = (r5 ** 2).groupby(level=0).sum()
    n5 = r5.groupby(level=0).size()
    d["rv"] = rv.reindex(d.index)
    d["n5"] = n5.reindex(d.index)
    # prezzi grezzi RTH
    rb = bars[bars["rth"]]
    gr = rb.groupby("session")
    d["raw_open"] = gr["open"].first().reindex(d.index)
    d["raw_close"] = gr["close"].last().reindex(d.index)
    d["raw_high"] = gr["high"].max().reindex(d.index)
    d["raw_low"] = gr["low"].min().reindex(d.index)
    # overnight (dalle 18:00 alle 9:29 della sessione): range con adj (attraversa il roll)
    on = bars[(~bars["rth"]) & ((bars["ny_min"] >= 1080) | (bars["ny_min"] < 570))]
    go = on.groupby("session")
    d["on_high"] = go["adj_high"].max().reindex(d.index)
    d["on_low"] = go["adj_low"].min().reindex(d.index)
    d["on_range_pct"] = (d["on_high"] - d["on_low"]) / d["raw_open"] * 100
    # rendimenti
    d["rth_ret_pts"] = d["rth_close"] - d["rth_open"]
    d["rth_ret_pct"] = d["rth_ret_pts"] / d["raw_open"] * 100
    d["rth_range_pts"] = d["rth_high"] - d["rth_low"]
    d["rth_range_pct"] = d["rth_range_pts"] / d["raw_open"] * 100
    pc = d["rth_close"].shift(1)
    d["gap_pts"] = d["rth_open"] - pc                       # adj: attraversa la notte
    d["gap_pct"] = d["gap_pts"] / d["raw_open"] * 100
    d["cc_ret_pct"] = (d["rth_close"] - pc) / d["raw_open"] * 100
    d["logrv"] = np.log(d["rv"])
    d["lograng"] = np.log(d["rth_range_pct"])
    # HAR regressori (noti a fine t): media 1, 5, 22 di logrv
    d["h1"] = d["logrv"]
    d["h5"] = d["logrv"].rolling(5).mean()
    d["h22"] = d["logrv"].rolling(22).mean()
    # ATR20 in punti (range RTH medio delle 20 sessioni valide precedenti, nota a inizio t)
    d["atr20"] = d["rth_range_pts"].rolling(20).mean().shift(1)
    d["year"] = d.index.year
    return d


def har_fit(d: pd.DataFrame, cols=("h1", "h5", "h22"), extra=()):
    """OLS di logrv_t su regressori noti a t-1. Ritorna (coef, X, y) con X includente costante."""
    X = d[list(cols) + list(extra)].shift(1)
    X.insert(0, "c", 1.0)
    y = d["logrv"]
    ok = X.notna().all(1) & y.notna()
    beta, *_ = np.linalg.lstsq(X[ok].to_numpy(), y[ok].to_numpy(), rcond=None)
    return pd.Series(beta, index=X.columns), X, y, ok


def rolling_pct_rank(s: pd.Series, window: int = 250, min_periods: int = 120) -> pd.Series:
    """Percentile di s_t rispetto alle `window` osservazioni precedenti (esclusa t). Causale."""
    v = s.to_numpy()
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        lo = max(0, i - window)
        past = v[lo:i]
        past = past[np.isfinite(past)]
        if len(past) >= min_periods and np.isfinite(v[i]):
            out[i] = (past < v[i]).mean()
    return pd.Series(out, index=s.index)


def rec(test_id, desc, values, days, **extra):
    st = core.day_block_bootstrap(np.asarray(values, float), np.asarray(days))
    core.record(FAM, test_id, desc, "discovery", st, **extra)
    return st


def trade_stats(t: pd.DataFrame, label: str = "", atr: pd.Series | None = None) -> dict:
    """Netto per trade + diagnostica completa (anni, drop top 20, quota long)."""
    net = t["gross_pts"].to_numpy(float) - core.COST_RT_POINTS
    st = core.day_block_bootstrap(net, t["session"].values)
    yr = core.yearly(net, t["session"])
    st["years_pos"] = f"{int((yr['mean'] > 0).sum())}/{len(yr)}"
    st["drop_top20"] = core.drop_top(net, 20)
    st["gross_mean"] = float(np.nanmean(t["gross_pts"]))
    st["long_share"] = float((t["side"] > 0).mean())
    if atr is not None:
        a = atr.reindex(pd.DatetimeIndex(t["session"])).to_numpy()
        st["net_atr_mean"] = float(np.nanmean(net / a))
    st["yearly"] = yr["mean"].round(3).to_dict()
    return st
