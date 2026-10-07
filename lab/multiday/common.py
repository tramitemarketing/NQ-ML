"""Strumenti comuni della famiglia multiday.

CONVENZIONI (dichiarate PRIMA di guardare qualunque risultato):
- Prezzo di riferimento giornaliero P_t = apertura della prima barra 16:00-16:59 NY della sessione t
  (un minuto dopo la chiusura RTH). Se manca (mezze giornate) = ultima chiusura della sessione.
  I segnali usano solo dati fino alla barra 15:59 della sessione t (rth_* della tabella daily);
  il trade entra a P_t ed esce a P_{t+h}. Nessun look-ahead: tra l'informazione e l'ingresso c'e' 1 minuto.
- Punti: differenze di prezzi adj_* (roll aggiustati additivamente).
- Unita' primaria di esplorazione: RENDIMENTO PERCENTUALE = (dP_adj) / P_raw_{t-1}. Attenzione:
  gli adj_* sono aggiustati ADDITIVAMENTE all'indietro dal 2026, quindi nel 2010 adj ~ 3x raw; un
  rendimento % calcolato su adj sarebbe sottostimato di ~3x negli anni vecchi. Si divide per il raw.
- Controllo beta: rendimento in eccesso = side * (r - mu), mu = deriva media giornaliera del discovery
  (x h giorni per i trade a h giorni). Equivale a "EV al netto dell'esposizione passiva equivalente".
- Inferenza: serie giornaliera di P&L della posizione, bootstrap a blocchi MENSILI (core.day_block_bootstrap
  con days = mese), perche' i trade a piu' giorni si sovrappongono e i rendimenti hanno cluster di vol.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core

FAM = "multiday"


def build_daily(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Tabella giornaliera con P (adj), Praw, OHLC RTH, rendimenti, ATR."""
    post = bars[(bars["ny_min"] >= 960) & (bars["ny_min"] < 1020)]
    first_post = post.groupby("session").head(1).set_index("session")
    last = bars.groupby("session").tail(1).set_index("session")
    # sessioni senza RTH (festivi con solo Globex, buchi di dati: 15 nel discovery) tolte: altrimenti le
    # medie mobili diventano NaN per settimane (bug trovato alla prima esecuzione, run "rev1" nel registro).
    # Il rendimento attraverso la sessione tolta confluisce nel giorno successivo (diff su P).
    d = daily[daily["rth_close"].notna()].copy()
    idx = d.index
    P = first_post["adj_open"].reindex(idx)
    Praw = first_post["open"].reindex(idx)
    first_post_ts = pd.Series(post.index, index=post["session"].to_numpy()).groupby(level=0).first()
    last_ts = pd.Series(bars.index, index=bars["session"].to_numpy()).groupby(level=0).last()
    miss = P.isna()
    P = P.fillna(last["adj_close"].reindex(idx))
    Praw = Praw.fillna(last["close"].reindex(idx))
    d["P"] = P
    d["Praw"] = Praw
    d["P_ts"] = first_post_ts.reindex(idx)
    d.loc[miss, "P_ts"] = last_ts.reindex(idx)[miss]
    d["P_missing"] = miss
    # rth raw close per rendimenti %
    d["dP"] = d["P"].diff()                       # punti adj da P_{t-1} a P_t
    d["r"] = d["dP"] / d["Praw"].shift(1)         # rendimento % giornaliero (close-to-close 16:00)
    # quantita' RTH del giorno (note alle 15:59)
    d["rng"] = d["rth_high"] - d["rth_low"]
    prev_c = d["rth_close"].shift(1)
    d["tr"] = np.maximum(d["rth_high"], prev_c) - np.minimum(d["rth_low"], prev_c)
    d["atr14"] = d["tr"].rolling(14).mean()
    d["atr20"] = d["tr"].rolling(20).mean()
    d["ret_cc"] = d["rth_close"].diff()           # punti close-to-close RTH (segnale)
    d["ret_cc_pct"] = d["ret_cc"] / (d["Praw"].shift(1))
    return d


def load_daily(phase: str = "discovery", warmup_days: int = 0):
    bars, daily = core.load(phase, warmup_days=warmup_days)
    return build_daily(bars, daily), bars


def fwd(d: pd.DataFrame, h: int):
    """Rendimento in avanti da P_t a P_{t+h}: (% su raw, punti adj)."""
    pts = d["P"].shift(-h) - d["P"]
    pct = pts / d["Praw"]
    return pct, pts


def month_key(idx) -> np.ndarray:
    idx = pd.DatetimeIndex(idx)
    return (idx.year * 100 + idx.month).to_numpy()


def boot(values, idx, block="month", n_boot=5000, seed=0):
    days = month_key(idx) if block == "month" else pd.DatetimeIndex(idx).to_numpy()
    return core.day_block_bootstrap(np.asarray(values, float), days, n_boot=n_boot, seed=seed)


def years_pos(values, idx) -> str:
    y = core.yearly(np.asarray(values, float), idx)
    y = y[y["count"] > 0]
    return f"{int((y['mean'] > 0).sum())}/{len(y)}"


def event_test(d: pd.DataFrame, mask: pd.Series, h: int, side: int, mu: float, valid=None):
    """Evento con posizione `side` per h giorni. Ritorna dict con statistiche %, eccesso, punti.
    Non sovrapposizione NON imposta qui (serve a misurare l'effetto); CI a blocchi mensili."""
    pct, pts = fwd(d, h)
    m = mask.fillna(False) & pct.notna()
    if valid is not None:
        m &= valid
    idx = d.index[m]
    raw = side * pct[m].to_numpy()
    exc = side * (pct[m].to_numpy() - mu * h)
    ptsv = side * pts[m].to_numpy()
    st = boot(exc * 1e4, idx)          # eccesso in punti base
    out = dict(n=int(m.sum()), n_days=st["n_days"], mean=st["mean"], lo=st["lo"], hi=st["hi"],
               p_two=st["p_two"], p_pos=st["p_pos"], unit="bp eccesso su deriva", h=h, side=side,
               mean_raw_bp=float(np.nanmean(raw) * 1e4), mean_exc_bp=st["mean"], lo_exc=st["lo"], hi_exc=st["hi"],
               p_two_exc=st["p_two"], p_pos_exc=st["p_pos"],
               mean_pts=float(np.nanmean(ptsv)), years_pos_exc=years_pos(exc, idx),
               n_per_year=float(m.sum() / 8.55))
    return out


def position_eval(d: pd.DataFrame, pos: pd.Series, mu: float, cost_pts: float = core.COST_RT_POINTS):
    """Posizione pos_t (decisa con info fino a t, tenuta da P_t a P_{t+1}).
    Ritorna serie giornaliere di P&L % e punti (netti dei costi sul cambio di posizione)."""
    pos = pos.fillna(0.0)
    r_next = d["r"].shift(-1)
    dp_next = d["dP"].shift(-1)
    ok = r_next.notna()
    turn = pos.diff().abs().fillna(pos.abs())
    cost_pct = turn * (cost_pts / 2) / d["Praw"]     # meta' costo a/r per ogni unita' scambiata
    pnl = (pos * r_next - cost_pct)[ok]
    pnl_gross = (pos * r_next)[ok]
    exc = (pos * (r_next - mu))[ok]
    pts = (pos * dp_next - turn * cost_pts / 2)[ok]
    return pd.DataFrame({"pnl": pnl, "gross": pnl_gross, "exc": exc, "pts": pts, "pos": pos[ok]})


def sharpe(x) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else np.nan


def sharpe_diff_boot(a: pd.Series, b: pd.Series, n_boot=5000, seed=0, block=21):
    """Differenza di Sharpe (a - b) con bootstrap a blocchi mobili di `block` giorni (stazionario)."""
    A, B = a.to_numpy(), b.to_numpy()
    n = len(A)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    diffs = np.empty(n_boot)
    for k in range(n_boot):
        starts = rng.integers(0, n - block, size=nb)
        ii = (starts[:, None] + np.arange(block)).ravel()[:n]
        diffs[k] = sharpe(A[ii]) - sharpe(B[ii])
    point = sharpe(A) - sharpe(B)
    cen = diffs - point
    return dict(sr_a=sharpe(A), sr_b=sharpe(B), diff=point, lo=float(np.percentile(diffs, 2.5)),
                hi=float(np.percentile(diffs, 97.5)), p_pos=float(max((cen >= point).mean(), 1 / n_boot)))


REV = 2   # rev1 = prima esecuzione con il bug dei NaN (vedi build_daily)


def rec(test_id: str, desc: str, stats: dict, **extra):
    core.record(FAM, test_id, desc, "discovery", stats, rev=REV, **extra)
