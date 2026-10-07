"""Strumenti comuni della famiglia r4_macro (giro 4: tassi, curva, dollaro -> NQ).

CONVENZIONI (fissate PRIMA di guardare qualunque risultato):
- Dati esterni SOLO da extdata.known_at_open (valori gia' ritardati: tassi +2 g.l., dollaro +8 g. cal.).
  Per avere lookback lunghi le serie vengono chieste su un calendario di giorni lavorativi che parte
  400 giorni prima della prima sessione, e poi riallineate alle sessioni NQ (valore noto all'apertura RTH).
- Esecuzione: ingresso all'APERTURA RTH (open della prima barra RTH, 09:30 NY) della sessione S, uscita
  all'apertura RTH della sessione S+h. Tutto cio' che il segnale usa e' noto prima delle 09:30 di S:
  serie esterne note all'apertura di S, NQ fino alla chiusura RTH di S-1.
- Punti = differenze di adj_open (roll aggiustati). Unita' di esplorazione: RENDIMENTO % = dPunti / open GREZZO
  all'ingresso (mai adj/adj). Il P&L dei trade candidati e' in punti (come vuole il controller).
- Beta: deriva media giornaliera open->open del discovery x giorni tenuti x lato; per i candidati si usa anche
  lab.controller.beta_component (la misura esatta del controller).
- Inferenza sulle regressioni/IC: bootstrap a blocchi MENSILI (le finestre a h giorni si sovrappongono).
- Regime dei tassi: il discovery 2010-2018 e' quasi tutto ZIRP (3 mesi ~0 fino a fine 2015) e poi rialzi
  lenti; il regime 2022 (inflazione, rialzi rapidi, correlazione azioni-tassi negativa) e' FUORI campione.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core, extdata

FAM = "r4_macro"
EXT_COLS = ["DGS10", "DGS3MO", "T10Y2Y", "USD", "VIX"]


def ext_known(sessions: pd.DatetimeIndex) -> pd.DataFrame:
    """Serie esterne note all'apertura di ogni sessione, con storia lunga per i lookback (in g.l.)."""
    sessions = pd.DatetimeIndex(sessions)
    cal = pd.bdate_range(sessions.min() - pd.Timedelta(days=400), sessions.max())
    cal = cal.union(sessions)
    k = extdata.known_at_open(cal)[EXT_COLS]
    return k


def ext_features(sessions: pd.DatetimeIndex) -> pd.DataFrame:
    """Feature calcolate sul calendario lavorativo (g.l.) e poi lette alle sessioni NQ."""
    k = ext_known(sessions)
    f = pd.DataFrame(index=k.index)
    for c in ("DGS10", "DGS3MO", "T10Y2Y"):
        f[c] = k[c]
        for h in (1, 5, 20, 60):
            f[f"d{h}_{c}"] = k[c] - k[c].shift(h)                    # punti percentuali (bp/100)
        f[f"z250_{c}"] = (k[c] - k[c].rolling(250).mean()) / k[c].rolling(250).std()
        f[f"sd20_d1_{c}"] = (k[c] - k[c].shift(1)).rolling(20).std()
        f[f"sd250_d1_{c}"] = (k[c] - k[c].shift(1)).rolling(250).std()
    f["USD"] = k["USD"]
    for h in (1, 5, 20, 60):
        f[f"r{h}_USD"] = np.log(k["USD"]).diff(h)
    f["VIX"] = k["VIX"]
    return f.reindex(pd.DatetimeIndex(sessions))


def build(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Tabella per sessione: open RTH (adj/raw/ts), rendimenti NQ passati, feature esterne note all'apertura."""
    rth = bars[bars["rth"]]
    first = rth.groupby("session").head(1).set_index("session")
    d = daily[daily["rth_close"].notna()].copy()
    idx = d.index
    d["O"] = first["adj_open"].reindex(idx)
    d["Oraw"] = first["open"].reindex(idx)
    ts = pd.Series(rth.index, index=rth["session"].to_numpy()).groupby(level=0).first()
    d["O_ts"] = ts.reindex(idx)
    last_rth = rth.groupby("session").tail(1).set_index("session")
    d["Craw"] = last_rth["close"].reindex(idx)
    # rendimenti NQ passati (noti all'apertura di S): chiusura RTH fino a S-1
    c = d["rth_close"]
    rc = c.diff() / d["Craw"].shift(1)                              # ret close-to-close della sessione
    d["nq_ret_cc"] = rc                                             # ret della sessione S (NON noto a S open)
    d["nq_prev"] = rc.shift(1)                                      # ret di S-1, noto all'apertura di S
    for h in (5, 20, 60):
        d[f"nq_mom{h}"] = (c.shift(1) - c.shift(1 + h)) / d["Craw"].shift(1 + h)
    # rendimento realizzato: vol a 20 g dei ret cc (noto all'apertura)
    d["nq_rv20"] = rc.shift(1).rolling(20).std()
    f = ext_features(idx)
    d = d.join(f)
    d["drift_day_pts"] = np.nan
    return d


def fwd(d: pd.DataFrame, h: int):
    """Da open RTH di S a open RTH di S+h: (% su raw all'ingresso, punti adj)."""
    pts = d["O"].shift(-h) - d["O"]
    return pts / d["Oraw"], pts


def month_key(idx) -> np.ndarray:
    idx = pd.DatetimeIndex(idx)
    return (idx.year * 100 + idx.month).to_numpy()


def ic_test(x: pd.Series, y: pd.Series, n_boot: int = 4000, seed: int = 0) -> dict:
    """Correlazione di Spearman (rank-IC) con bootstrap a blocchi mensili."""
    m = pd.concat([x, y], axis=1).dropna()
    m.columns = ["x", "y"]
    if len(m) < 30:
        return dict(n=len(m), ic=np.nan, lo=np.nan, hi=np.nan, p_two=np.nan)
    rx = m["x"].rank().to_numpy(); ry = m["y"].rank().to_numpy()
    rx = (rx - rx.mean()) / rx.std(); ry = (ry - ry.mean()) / ry.std()
    prod = rx * ry
    st = core.day_block_bootstrap(prod, month_key(m.index), n_boot=n_boot, seed=seed)
    yrs = pd.Series(prod, index=m.index).groupby(m.index.year).mean()
    return dict(n=len(m), n_months=st["n_days"], ic=st["mean"], lo=st["lo"], hi=st["hi"], p_two=st["p_two"],
                years_pos=f"{int((yrs > 0).sum())}/{len(yrs)}", years={int(k): round(float(v), 3) for k, v in yrs.items()})


def cond_mean(y: pd.Series, mask: pd.Series, n_boot: int = 4000) -> dict:
    """Media di y (es. rendimento fwd %) dove mask e' vero, con bootstrap mensile e differenza vs resto."""
    m = pd.concat([y, mask], axis=1).dropna()
    m.columns = ["y", "m"]
    a = m.loc[m["m"].astype(bool), "y"]; b = m.loc[~m["m"].astype(bool), "y"]
    st = core.day_block_bootstrap(a.to_numpy(), month_key(a.index), n_boot=n_boot)
    # differenza: y - media del resto, sui soli casi
    diff = a - b.mean()
    sd = core.day_block_bootstrap(diff.to_numpy(), month_key(a.index), n_boot=n_boot)
    yrs = diff.groupby(diff.index.year).mean()
    return dict(n=len(a), mean=st["mean"], lo=st["lo"], hi=st["hi"], p_two=st["p_two"], rest_mean=float(b.mean()),
                diff=sd["mean"], diff_lo=sd["lo"], diff_hi=sd["hi"], diff_p_two=sd["p_two"],
                years_pos=f"{int((yrs > 0).sum())}/{len(yrs)}")


def load(warmup_days: int = 0):
    bars, daily = core.load("discovery", warmup_days=warmup_days)
    d = build(bars, daily)
    return d, bars, daily
