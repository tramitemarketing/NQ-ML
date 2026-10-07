"""Candidati congelati della famiglia intraday_momentum (discovery 2010-06 -> 2018-12).

Unita' dichiarata: punti per contratto (gross_pts), come richiesto dal controller. Nel REPORT anche bps.
Regole di tempo: prezzo "alle HH:MM" = close della barra che chiude a HH:MM; ingresso alle 15:30 =
open della barra 15:30 (dopo la chiusura della barra 15:29 che completa il segnale); uscita = close
della barra 15:59 (16:00 NY). Rendimenti RTH: nessun roll attraversato.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.intraday_momentum.common import build, ret

T_IN, T_OUT = 930, 960        # 15:30 -> 16:00 NY


def _ts(bars: pd.DataFrame, ny_min: int) -> pd.Series:
    """Timestamp UTC di inizio della barra `ny_min` per sessione (solo RTH)."""
    b = bars[bars["rth"] & (bars["ny_min"] == ny_min)]
    return pd.Series(b.index, index=pd.DatetimeIndex(b["session"])).groupby(level=0).first()


def _signal_trades(bars, daily, mask_fn) -> pd.DataFrame:
    M = build(bars, daily)
    ok = M["ok"]
    rin = ret(M, 570, T_IN)                      # 09:30 -> 15:30, noto alle 15:30
    side = np.sign(rin)
    mask = ok & side.ne(0) & mask_fn(M, ok)
    e = M["adj_open"][T_IN]
    x = M["adj_close"][T_OUT - 1]
    mask &= e.notna() & x.notna()
    sess = M["sess"][mask.to_numpy()]
    t_in = _ts(bars, T_IN).reindex(sess)
    t_out = _ts(bars, T_OUT - 1).reindex(sess) + pd.Timedelta(minutes=1)
    return pd.DataFrame({
        "session": pd.DatetimeIndex(sess).values.astype("datetime64[ns]"),
        "entry_ts": t_in.to_numpy(),
        "exit_ts": t_out.to_numpy(),
        "side": side[mask].astype(int).to_numpy(),
        "gross_pts": ((x - e) * side)[mask].to_numpy(),
    })


def _hivol(M, ok, L=20, q=0.67, window=250):
    """Regime di alta volatilita': media delle ultime L vol realizzate RTH (std dei rendimenti 1m,
    sessioni valide PRECEDENTI) > quantile q della stessa media sulle `window` sessioni precedenti."""
    r1m = M["adj_close"].diff(axis=1) / M["close"]
    rv = r1m.std(axis=1).where(ok)
    v = rv.rolling(L, min_periods=int(L * 0.75)).mean().shift(1)
    thr = v.rolling(window, min_periods=120).quantile(q)
    return (v > thr).fillna(False)


def hivol_last30(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    return _signal_trades(bars, daily, _hivol)


def rin_last30_all(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    return _signal_trades(bars, daily, lambda M, ok: pd.Series(True, index=M["sess"]))


CANDIDATES = [
    dict(
        id="intraday_momentum_hivol_last30",
        description=("Nelle sessioni in regime di alta volatilita' (media della vol realizzata RTH a 1m delle 20 "
                     "sessioni precedenti > suo quantile 0,67 sulle 250 sessioni precedenti), alle 15:30 NY entra "
                     "nella direzione del rendimento 09:30->15:30 ed esce alle 16:00 (close barra 15:59). 1 contratto."),
        rationale=("Market intraday momentum (Gao-Han-Li-Zhou 2018; Baltussen-Da-Lammers-Martens 2021): il "
                   "rendimento accumulato nel giorno predice l'ultima mezz'ora per ribilanciamento tardivo e "
                   "copertura gamma dei dealer corti gamma; entrambi i lavori trovano l'effetto concentrato nei "
                   "periodi di alta volatilita'. Su NQ 2010-2018 l'effetto incondizionato e' sotto i costi, quello "
                   "condizionato al regime no."),
        warmup_days=280,
        kind="tradeable",
        fn=hivol_last30,
        discovery=dict(n=587, mean_net=2.290, lo=0.862, hi=3.742, p_pos=0.0017, years_pos="5/8",
                       drop20=0.097, beta_adj_net=2.305, exposure=0.06, bps_net=5.26, hit=0.543,
                       note="2010 senza trade (warmup del regime); senza 2018: +1,30 [+0,24;+2,41] p 0,010"),
    ),
    dict(
        id="intraday_momentum_rin_last30_gross",
        description=("Regolarita' (lordo, bilaterale): in TUTTE le sessioni valide, posizione alle 15:30 nella "
                     "direzione del rendimento 09:30->15:30, uscita 16:00; quantita' misurata = punti lordi."),
        rationale=("Test diretto dell'intraday momentum della letteratura (GHLZ 2018, BDLM 2021) su NQ senza "
                   "condizionamenti: esiste una predittivita' lorda dell'ultima mezz'ora? In discovery e' "
                   "positiva ma sotto il costo (0,62 < 0,75 punti) e concentrata negli anni volatili."),
        warmup_days=0,
        kind="regularity",
        fn=rin_last30_all,
        discovery=dict(n=2114, mean_gross=0.6205, lo=0.1594, hi=1.1034, p_two=0.0112, years_pos="4/9",
                       hit=0.488, note="netto -0,129; senza il 2018 il lordo e' +0,226"),
    ),
]
