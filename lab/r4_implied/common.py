"""Famiglia r4_implied: volatilita' implicita (VXN, VIX, VIX9D, VIX3M, VVIX, SKEW) e NQ.

Regole (fissate PRIMA di guardare):
- dati esterni SOLO tramite extdata.known_at_open(sessions): per la sessione S il valore e' quello di chiusura
  CBOE del giorno lavorativo precedente (noto dalle 16:15 ET di S-1, cioe' prima delle 18:00 che aprono S).
  Tutti i segnali qui sono quindi utilizzabili all'apertura RTH di S (ingresso rth_open S) o dopo.
- la previsione HAR della varianza di S usa solo sessioni <= S-1 (OLS mobile 500 sessioni, come lab/vol).
- unita': ricerca esplorativa in % del prezzo GREZZO (rendimenti = diff adj / open grezzo di S);
  candidati tradeable in PUNTI NQ per 1 contratto (unita' del controller). Regolarita' in log-varianza.
- multi-giorno: P&L giornaliero "a portafogli sovrapposti" (Jegadeesh-Titman): pos_t = media delle posizioni
  decise nelle ultime h sessioni, P&L_t = pos_t * rendimento open->open di t. Una riga per giorno: il bootstrap
  a blocchi per giorno resta valido (i rendimenti giornalieri sono ~indipendenti).
- beta: "eccesso" = P&L calcolato con il rendimento meno la sua media nel campione (toglie esposizione x deriva).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core, extdata
from lab.vol import common as VC
from lab.vol.candidates import _rolling_ols_pred

FAM = "r4_implied"


def features(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Una riga per sessione valida. Colonne *_s = segnali noti all'apertura RTH della sessione (niente shift
    necessario); colonne misurate a fine sessione (logrv, rendimenti) sono quelle di vol.common."""
    f = VC.daily_features(bars, daily)
    f["har"] = _rolling_ols_pred(f["logrv"], f[["h1", "h5", "h22"]].shift(1))    # previsione per t con dati <= t-1
    E = extdata.known_at_open(f.index)
    for c in ["VXN", "VIX", "VIX3M", "VIX9D", "VVIX", "SKEW"]:
        f[c] = E[c].to_numpy()
    # varianza implicita giornaliera in %^2 (VXN annualizzato, 252 sessioni)
    f["iv_log"] = np.log(f["VXN"] ** 2 / 252.0)
    f["vrp_har_s"] = f["iv_log"] - f["har"]                                   # log(implicita/prevista)
    f["vrp_rv22_s"] = f["iv_log"] - np.log(f["rv"].rolling(22).mean().shift(1))
    f["vrp_rv5_s"] = f["iv_log"] - np.log(f["rv"].rolling(5).mean().shift(1))
    f["vrp_lvl_s"] = f["VXN"] ** 2 / 252.0 - np.exp(f["har"])                  # differenza in livelli (%^2)
    f["vxn_s"] = f["VXN"]
    f["ts_3m_s"] = f["VIX"] / f["VIX3M"]                                       # >1 = backwardation
    f["ts_9d_s"] = f["VIX9D"] / f["VIX"]
    f["vvix_s"] = f["VVIX"]
    f["vvix_vix_s"] = f["VVIX"] / f["VIX"]
    f["skew_s"] = f["SKEW"]
    f["vxn_vix_s"] = f["VXN"] / f["VIX"]
    lv = np.log(f["VXN"])
    f["dvxn1_s"] = lv - lv.shift(1)          # variazione dell'ultimo giorno noto (VXN(S-1)/VXN(S-2))
    f["dvxn5_s"] = lv - lv.shift(5)
    f["vxn_dev20_s"] = lv - lv.rolling(20).mean()
    # rendimenti (adj, % del grezzo di S e punti)
    o = f["rth_open"]
    f["oo1_pts"] = o.shift(-1) - o                                             # open S -> open S+1
    f["oo1_pct"] = f["oo1_pts"] / f["raw_open"] * 100
    f["rth_pts"] = f["rth_close"] - o
    f["night_next_pts"] = o.shift(-1) - f["rth_close"]                         # close S -> open S+1
    for h in (5, 20):
        f[f"oo{h}_pct"] = (o.shift(-h) - o) / f["raw_open"] * 100
    return f


def prank(s: pd.Series, window=250, minp=120) -> pd.Series:
    return VC.rolling_pct_rank(s, window, minp)


def overlap_pnl(pos: pd.Series, r: pd.Series, h: int) -> pd.Series:
    """pos deciso all'apertura di t (noto a t), tenuto h giorni open->open; P&L giornaliero sovrapposto."""
    p = pos.fillna(0.0)
    held = sum(p.shift(j).fillna(0.0) for j in range(h)) / h
    return held * r


def rec(test_id, desc, values, days, **extra):
    values = np.asarray(values, float)
    days = np.asarray(days)
    st = core.day_block_bootstrap(values, days)
    ok = np.isfinite(values)
    yr = core.yearly(values[ok], days[ok])
    st["years_pos"] = f"{int((yr['mean'] > 0).sum())}/{len(yr)}"
    st["drop_top20"] = core.drop_top(values, 20)
    st["yearly"] = yr["mean"].round(4).to_dict()
    core.record(FAM, test_id, desc, "discovery", st, **extra)
    return st


def fmt(tid, st):
    return (f"{tid:42s} n={st['n']:5d} mean={st['mean']:+.4f} [{st['lo']:+.4f};{st['hi']:+.4f}] "
            f"p2={st['p_two']:.4f} yrs={st['years_pos']} dt20={st['drop_top20']:+.4f}")


_CACHE = {}


def load_features():
    if "f" not in _CACHE:
        bars, daily = core.load("discovery", warmup_days=0)
        f = features(bars, daily)
        f = f[f["in_phase"]] if "in_phase" in f else f
        _CACHE["f"] = f
        _CACHE["bars"] = bars
        _CACHE["daily"] = daily
    return _CACHE["f"]
