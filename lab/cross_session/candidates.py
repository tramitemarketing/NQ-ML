"""Candidati congelati della famiglia cross_session (discovery 2010-06-07 -> 2018-12-31).

Nessun candidato 'tradeable': nessuna regola direzionale fra sessioni ha retto nel discovery
(vedi REPORT.md). I due candidati sono REGOLARITA' (binario 'reale ma non incassabile'):
test bilaterale sul lordo, nessuna pretesa di profitto dopo i costi.

Entrambe le funzioni usano solo prezzi aggiustati (adj_*) e solo informazione nota prima
dell'istante di misura; girano su qualunque fase (il controller filtra in_phase).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.cross_session.common import add_sm, session_table


def _table(bars, daily):
    bars = add_sm(bars)
    t = session_table(bars, daily)
    # timestamp dell'ultima barra prima delle 17:00 (uscita del candidato 2)
    b = bars[(bars["sm"] >= 0) & (bars["sm"] < 1380)]
    last = b[~b["session"].duplicated(keep="last")]
    t["ts_last_pre17"] = pd.Series(last.index, index=pd.DatetimeIndex(last["session"].to_numpy()))
    return t


def onrange_predicts_rthrange(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Regolarita' di volatilita' notte -> giorno.
    on_ratio  = range notturno (18:00-09:30, adj) / media dei range notturni delle 20 sessioni precedenti
    rth_ratio = range RTH (09:30-16:00) / media dei range RTH delle 20 sessioni precedenti
    side = +1 se on_ratio > mediana di on_ratio sulle 250 sessioni PRECEDENTI (min 60), altrimenti -1
    gross_pts = side * (rth_ratio - 1)   [quantita' adimensionale; >0 = la notte anticipa il giorno]
    Solo sessioni valide (>= 300 barre RTH)."""
    t = _table(bars, daily)
    on_rng = t["on_hi"] - t["on_lo"]
    on_ratio = on_rng / on_rng.shift(1).rolling(20, min_periods=10).mean()
    rth_ratio = t["range_rth"] / t["atr20_rth"]
    med = on_ratio.shift(1).rolling(250, min_periods=60).median()
    side = np.sign(on_ratio - med)
    q = side * (rth_ratio - 1)
    ok = q.notna() & (side != 0) & t["valid"].astype(bool) & t["ts_s0930"].notna() & t["ts_s16"].notna()
    return pd.DataFrame({
        "session": pd.DatetimeIndex(t.index[ok]),
        "entry_ts": t.loc[ok, "ts_s0930"].to_numpy(),
        "exit_ts": t.loc[ok, "ts_s16"].to_numpy(),
        "side": side[ok].astype(int).to_numpy(),
        "gross_pts": q[ok].astype(float).to_numpy(),
    })


def rth_direction_continues_after_halt(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Regolarita' di direzione RTH -> sessione serale.
    side = sign(adj_close dell'ultima barra prima delle 16:00 - adj_open della prima barra dalle 09:30)
    gross_pts = side * (adj_close dell'ultima barra prima delle 17:00 - adj_open della prima barra
    dalle 16:15)   [punti; nel 2010-2018 la prima barra dalle 16:15 e' quella delle 16:30, dopo la pausa
    16:15-16:30; se la pausa non c'e' e' quella delle 16:15]. Solo sessioni valide."""
    t = _table(bars, daily)
    side = np.sign(t["sig_s16"] - t["ent_s0930"])
    g = side * (t["sig_s17"] - t["ent_s1615"])
    ok = g.notna() & (side != 0) & t["valid"].astype(bool) & t["ts_s1615"].notna() & t["ts_last_pre17"].notna()
    ok &= t["ts_last_pre17"] > t["ts_s1615"]
    return pd.DataFrame({
        "session": pd.DatetimeIndex(t.index[ok]),
        "entry_ts": t.loc[ok, "ts_s1615"].to_numpy(),
        "exit_ts": t.loc[ok, "ts_last_pre17"].to_numpy(),
        "side": side[ok].astype(int).to_numpy(),
        "gross_pts": g[ok].astype(float).to_numpy(),
    })


CANDIDATES = [
    dict(
        id="cross_session_onrange_rthrange",
        description=("Se il range notturno 18:00-09:30 (rispetto alla media delle 20 notti precedenti) supera la "
                     "sua mediana causale a 250 sessioni, il range RTH (rispetto alla media RTH a 20 sessioni) e' "
                     "sopra 1, e viceversa: quantita' = side*(rth_ratio-1), test bilaterale"),
        rationale=("Persistenza della volatilita' (GARCH/HAR): l'informazione arrivata di notte (Asia, Europa, "
                   "dati delle 08:30) si scarica anche nella RTH. Regolarita' nota, utile per dimensionare stop "
                   "e rischio, non incassabile con il solo future"),
        warmup_days=280,
        kind="regularity",
        fn=onrange_predicts_rthrange,
        discovery=dict(n=2053, mean_gross=0.1469, lo=0.1253, hi=0.1685, p_two=0.0001, years_pos="9/9",
                       drop20_gross=0.1252, mean_net=None,
                       note="gross adimensionale (rapporto di range - 1); spearman 0,385; coeff. parziale 0,33 (t 16) "
                            "controllando per il range RTH e notturno di ieri"),
    ),
    dict(
        id="cross_session_rth_to_evening",
        description=("Il segno del rendimento RTH (09:30->16:00) predice il segno del movimento 16:15/16:30->17:00: "
                     "gross = sign(RTH) * (close 16:59 - open prima barra dalle 16:15), test bilaterale"),
        rationale=("Continuazione dei flussi di fine giornata nella sessione serale sottile (ribilanciamenti e "
                   "coperture che non si completano entro le 16:00, reazioni agli utili dopo chiusura). Post hoc: "
                   "scelto dopo un grappolo di 16 varianti fine-RTH -> 16-17 (vedi REPORT); ~0,32 punti, sotto i costi"),
        warmup_days=5,
        kind="regularity",
        fn=rth_direction_continues_after_halt,
        discovery=dict(n=1988, mean_gross=0.3211, lo=0.0926, hi=0.5458, p_two=0.0056, mean_net=-0.429,
                       p_pos=1.0, drop20_gross=0.0686, years_pos="7/9 lordo (1/9 netto)",
                       note="regolarita': giudizio sul lordo bilaterale; netto negativo per costruzione (0,32 < 0,75)"),
    ),
]
