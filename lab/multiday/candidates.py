"""Candidati congelati della famiglia multiday (fase discovery chiusa il 2026-09-23).

I due candidati sono NIDIFICATI (il secondo e' la gamba long del primo): non sono due prove indipendenti.
Convenzione d'esecuzione comune: segnale con le chiusure RTH (barra 15:59 NY) fino alla sessione t;
ingresso/uscita al prezzo P = apertura della prima barra 16:00-16:59 NY della sessione (1 minuto dopo);
se in quella sessione manca (mezze giornate) P = ultima barra della sessione. Prezzi adj_* (roll aggiustati),
gross_pts in punti adj per 1 contratto. Posizione tenuta attraverso le notti finche' il segnale non cambia.
L'ultimo trade aperto viene chiuso all'ultima sessione disponibile dei dati passati.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.multiday.common import build_daily

K = 10


def _signal(daily_t: pd.DataFrame) -> pd.Series:
    c = daily_t["rth_close"]
    return -np.sign(c - c.shift(K)).fillna(0.0)


def _runs_to_trades(d: pd.DataFrame, pos: pd.Series) -> pd.DataFrame:
    P, Pts = d["P"], d["P_ts"]
    rows = []
    cur, start = 0.0, None
    sess = list(pos.index)
    vals = pos.to_numpy()
    for t, v in zip(sess, vals):
        if v != cur:
            if cur != 0:
                rows.append((start, t, cur))
            cur, start = v, t
    if cur != 0 and start != sess[-1]:
        rows.append((start, sess[-1], cur))
    tr = pd.DataFrame(rows, columns=["session", "exit_session", "side"])
    tr["entry_ts"] = Pts.loc[tr["session"]].to_numpy()
    tr["exit_ts"] = Pts.loc[tr["exit_session"]].to_numpy()
    tr["gross_pts"] = tr["side"] * (P.loc[tr["exit_session"]].to_numpy() - P.loc[tr["session"]].to_numpy())
    tr["hold_days"] = [pos.index.get_loc(b) - pos.index.get_loc(a) for a, b in zip(tr["session"], tr["exit_session"])]
    tr["side"] = tr["side"].astype(int)
    tr["session"] = pd.to_datetime(tr["session"]).astype("datetime64[ns]")
    return tr[["session", "entry_ts", "exit_ts", "side", "gross_pts", "hold_days", "exit_session"]]


def contra10_ls(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    d = build_daily(bars, daily)
    return _runs_to_trades(d, _signal(d))


def contra10_long(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    d = build_daily(bars, daily)
    return _runs_to_trades(d, _signal(d).clip(lower=0.0))


CANDIDATES = [
    dict(
        id="multiday_contra10_ls",
        description=("Posizione = -segno(chiusura RTH di oggi - chiusura RTH di 10 sessioni fa): long se NQ e' sceso "
                     "nelle ultime 10 sessioni, short se e' salito; ingresso/uscita alle 16:00 NY del giorno del segnale, "
                     "si tiene fino al cambio di segno (un trade per sequenza, ~7 sessioni in media)."),
        rationale=("Reversal a breve (1-3 settimane) degli indici azionari: fornitura di liquidita' / ribilanciamenti "
                   "meccanici (vol-targeting, hedging dei dealer) che spingono il prezzo oltre e poi rientrano. Nel "
                   "discovery: TSMOM a 1-2 settimane significativamente negativo, VR(20)=0,64, autocorrelazioni negative."),
        warmup_days=15,
        kind="tradeable",
        fn=contra10_ls,
        discovery=dict(n=300, mean_net=9.82, lo=-1.90, hi=20.95, p_pos=0.044, years_pos="6/9",
                       beta_adj=13.59, beta_lo=2.68, beta_years_pos="7/9", drop20=-2.23),
    ),
    dict(
        id="multiday_contra10_long",
        description=("Gamba long del precedente: long alle 16:00 NY quando la chiusura RTH di oggi e' sotto quella di "
                     "10 sessioni fa, flat altrimenti; uscita alle 16:00 del primo giorno in cui torna sopra."),
        rationale=("Stesso meccanismo (reversal a 1-3 settimane) nella versione che un operatore long-only userebbe; "
                   "NIDIFICATO nel primo, non indipendente."),
        warmup_days=15,
        kind="tradeable",
        fn=contra10_long,
        discovery=dict(n=150, mean_net=24.31, lo=8.48, hi=38.58, p_pos=0.0001, years_pos="9/9",
                       beta_adj=13.09, beta_lo=-3.56, beta_years_pos="7/9", drop20=6.72),
    ),
]
