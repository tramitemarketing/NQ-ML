"""Candidati congelati della famiglia r2_footprints (giro 2, discovery 2010-06-07 -> 2018-12-31).

Nessun candidato 'tradeable': nessuna regola direzionale basata sulle impronte ha retto ai costi (vedi REPORT.md).
Due REGOLARITA' (binario 'reale ma non incassabile', test bilaterale sul lordo, segno atteso +1), entrambe
impronte degli algoritmi di esecuzione che lavorano "a orologio":

1. r2_footprints_slice_continuation - nei minuti :00/:15/:30/:45 della giornata RTH il rendimento 1m va nel verso
   del trend dell'ora precedente piu' spesso che negli altri minuti.
2. r2_footprints_close_clock_continuation - alle barre-orologio di chiusura (15:45, 15:50, 15:55, 15:59) il verso
   del minuto prosegue nei 15 minuti successivi (misura in unita' di sigma 1m).

Entrambe usano solo prezzi adj_* e informazione disponibile fino alla barra di misura; girano su qualunque fase.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

M0, M1 = 570, 960                 # 09:30, 16:00 (minuti NY)
PRE = 120                         # minuti prima delle 09:30 inclusi per il trend dei primi minuti


def _matrix(bars: pd.DataFrame, lo: int, hi: int):
    """adj_close sessione x minuto NY [lo, hi), riempito in avanti; timestamp della prima/ultima barra RTH."""
    b = bars[(bars["ny_min"] >= lo) & (bars["ny_min"] < hi)]
    P = b.pivot_table(index="session", columns="ny_min", values="adj_close", aggfunc="first")
    P = P.reindex(columns=range(lo, hi)).ffill(axis=1)
    r = bars[bars["rth"]]
    first = r[~r["session"].duplicated(keep="first")]
    last = r[~r["session"].duplicated(keep="last")]
    ts0 = pd.Series(first.index, index=pd.DatetimeIndex(first["session"].to_numpy()))
    ts1 = pd.Series(last.index, index=pd.DatetimeIndex(last["session"].to_numpy()))
    P.index = pd.DatetimeIndex(P.index)
    return P, ts0, ts1


def _out(q: pd.Series, daily: pd.DataFrame, ts0, ts1) -> pd.DataFrame:
    valid = daily["valid"].reindex(q.index).fillna(False).astype(bool)
    q = q[valid & q.notna() & ts0.reindex(q.index).notna() & ts1.reindex(q.index).notna()]
    return pd.DataFrame({
        "session": pd.DatetimeIndex(q.index),
        "entry_ts": ts0.reindex(q.index).to_numpy(),
        "exit_ts": ts1.reindex(q.index).to_numpy(),
        "side": np.ones(len(q), int),
        "gross_pts": q.astype(float).to_numpy(),
    })


def slice_continuation(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Per sessione valida. Barra k = barra 1m RTH che inizia alle 09:30+k. d_k = C_k - C_{k-1};
    trend_k = C_{k-1} - C_{k-61} (C = adj_close riempito in avanti, anche pre-09:30).
    h_k = sign(trend_k) * sign(d_k)   (+1 = il minuto va nel verso del trend dell'ora precedente).
    Minuti ammessi: 10:05-15:39, esclusi 10:30, 11:30, 14:00, 15:00 (orari di notizie/chiusure).
    FETTA = minuto dell'ora in {00,15,30,45}; ALTRI = minuto dell'ora non multiplo di 5.
    gross_pts = media(h) sulle FETTE - media(h) sugli ALTRI   [adimensionale; atteso > 0]."""
    P, ts0, ts1 = _matrix(bars, M0 - PRE - 1, M1)
    Cm = P.to_numpy()
    off = PRE + 1                                     # colonna della barra 09:30
    nk = M1 - M0
    k = np.arange(nk)
    d = Cm[:, off + k] - Cm[:, off + k - 1]
    tr = Cm[:, off + k - 1] - Cm[:, off + k - 61]
    h = np.sign(tr) * np.sign(d)
    hh = (M0 + k) // 60
    mo = (M0 + k) % 60
    tmin = M0 + k
    excl = np.isin(tmin, [630, 690, 840, 900])        # 10:30, 11:30, 14:00, 15:00
    base = (tmin >= 605) & (tmin < 940) & ~excl       # 10:05 - 15:39
    sl = base & (mo % 15 == 0)
    ot = base & (mo % 5 != 0)
    q = pd.Series(np.nanmean(h[:, sl], 1) - np.nanmean(h[:, ot], 1), index=P.index)
    return _out(q, daily, ts0, ts1)


def close_clock_continuation(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Per sessione valida. Per m in {15:45, 15:50, 15:55, 15:59} (barre 1m che iniziano a quell'ora):
    x_m = sign(C_m - C_{m-1}) * (C_{m+15} - C_m) / sigma,   C = adj_close riempito in avanti
    (C_{m+15} della 15:59 = close della barra 16:14).
    sigma = media, sulle 20 sessioni valide PRECEDENTI, della std delle variazioni 1m di adj_close 09:30-15:59.
    gross_pts = media dei quattro x_m   [unita' di sigma 1m; atteso > 0 = continuazione]."""
    P, ts0, ts1 = _matrix(bars, M0 - 1, 975)          # 09:29 -> 16:14
    Cm = P.to_numpy()
    col = lambda t: t - (M0 - 1)
    rth = Cm[:, col(M0 - 1):col(M1)]
    s1 = pd.Series(np.nanstd(np.diff(rth, axis=1), axis=1), index=P.index)
    valid = daily["valid"].reindex(P.index).fillna(False).astype(bool)
    s1[~valid] = np.nan
    sig = s1.dropna().shift(1).rolling(20, min_periods=10).mean().reindex(P.index)
    xs = []
    for m in (945, 950, 955, 959):
        x = np.sign(Cm[:, col(m)] - Cm[:, col(m - 1)]) * (Cm[:, col(m + 15)] - Cm[:, col(m)])
        xs.append(x)
    q = pd.Series(np.nanmean(np.column_stack(xs), 1), index=P.index) / sig
    return _out(q, daily, ts0, ts1)


CANDIDATES = [
    dict(
        id="r2_footprints_slice_continuation",
        description=("Nei minuti :00/:15/:30/:45 fra le 10:05 e le 15:39 (esclusi 10:30, 11:30, 14:00, 15:00) il segno del "
                     "rendimento 1m coincide con il segno del trend dei 60 minuti precedenti piu' spesso che nei minuti non "
                     "multipli di 5: gross = media(sign(trend60)*sign(r1m)) sulle fette - la stessa sugli altri minuti, "
                     "per sessione; test bilaterale, segno atteso +"),
        rationale=("Impronta degli algoritmi di esecuzione (TWAP/VWAP e ordini programmati a orologio): chi sta "
                   "eseguendo un ordine grosso, visibile come trend dell'ultima ora, ne esegue una fetta ai quarti d'ora; "
                   "il volume a quei minuti e' piu' alto (+13% in log) e la direzione segue il trend, mentre gli altri "
                   "minuti mostrano un lieve rientro. Regolarita' di microstruttura, ~0,1 punti per minuto: non incassabile"),
        warmup_days=5,
        kind="regularity",
        expected_sign=1,
        fn=slice_continuation,
        discovery=dict(n=2121, mean_gross=0.0623, lo=0.0522, hi=0.0728, p_two=0.0002, years_pos="9/9",
                       mean_net=None, note="adimensionale (differenza di hit-rate in segno); in punti +0,106 per minuto"),
    ),
    dict(
        id="r2_footprints_close_clock_continuation",
        description=("Alle barre 1m delle 15:45, 15:50, 15:55 e 15:59 il segno del minuto prosegue nei 15 minuti successivi: "
                     "gross = media sulle 4 barre di sign(r_m)*(C_{m+15}-C_m)/sigma1m (sigma1m = std 1m RTH media delle 20 "
                     "sessioni precedenti); test bilaterale, segno atteso +"),
        rationale=("Flussi forzati della chiusura: pubblicazione degli sbilanciamenti MOC / closing cross (15:50; nel "
                   "discovery l'impronta di volume delle 15:50 compare dal 2013 e cresce fino al 2017-18), esecuzioni a "
                   "orologio ogni 5 minuti e finestra di settlement CME 15:59:30-16:00. In tutti i 345 minuti placebo "
                   "10:00-15:44 la stessa misura e' inferiore a quella di ciascuna delle 4 barre-orologio. Scelto dopo "
                   "aver visto i 4 minuti (post hoc dichiarato); lordo ~0,3-0,5 punti per barra, sotto i costi"),
        warmup_days=30,
        kind="regularity",
        expected_sign=1,
        fn=close_clock_continuation,
        discovery=dict(n=2111, mean_gross=0.2612, lo=0.1696, hi=0.3511, p_two=0.0001, years_pos="9/9",
                       drop20_gross=0.1584, mean_net=None,
                       note=("unita' sigma1m; ATTENZIONE: in calo nel tempo (2010-13 +0,354, 2014-18 +0,195, 2016-18 "
                             "+0,090 non significativo); placebo un'ora prima -0,038, due ore prima -0,084")),
    ),
]
