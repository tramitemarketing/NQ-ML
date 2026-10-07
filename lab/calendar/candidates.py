"""Candidati congelati della famiglia calendar (2026-09-23). Vedi REPORT.md.

Un solo candidato: gli altri due finalisti (short il venerdi' di scadenza, ribilanciamento di fine mese)
falliscono gia' nel discovery il criterio 4 del protocollo (EV senza i 20 trade migliori > 0) e con ~57
eventi in validazione non potrebbero superarlo; promuoverli alzerebbe soltanto K per tutte le famiglie.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.calendar.common import Px, hm, RTH_OPEN, RTH_CLOSE


def turnaround_tue_am(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Long martedi' 9:30 -> 12:00 NY se la sessione precedente e' un lunedi' valido con RTH
    (open 9:30 -> 16:00) in calo. Il segnale usa solo il lunedi' (noto alle 16:00 di lunedi')."""
    px = Px(bars, daily)
    S = px.sessions
    valid = daily["valid"].reindex(S).to_numpy()
    p_open = px.price(RTH_OPEN)
    p_close = px.price(RTH_CLOSE)
    p_exit = px.price(hm(12, 0))
    ts_in = px.ts(RTH_OPEN)
    ts_out = px.ts(hm(12, 0))
    dow = S.dayofweek.to_numpy()
    rth = np.where(valid, p_close - p_open, np.nan)
    rows = []
    for i in range(1, len(S)):
        if dow[i] != 1 or not valid[i] or dow[i - 1] != 0 or not valid[i - 1]:
            continue
        if not (rth[i - 1] < 0):
            continue
        if np.isnan(p_open[i]) or np.isnan(p_exit[i]) or np.isnat(ts_in[i]) or np.isnat(ts_out[i]):
            continue
        rows.append(dict(session=S[i], entry_ts=pd.Timestamp(ts_in[i], tz="UTC"),
                         exit_ts=pd.Timestamp(ts_out[i], tz="UTC"), side=1,
                         gross_pts=float(p_exit[i] - p_open[i])))
    out = pd.DataFrame(rows, columns=["session", "entry_ts", "exit_ts", "side", "gross_pts"])
    out["session"] = pd.to_datetime(out["session"])
    return out


CANDIDATES = [
    dict(
        id="calendar_turnaround_tue_am",
        description=("Long NQ martedi' dall'open RTH 9:30 alle 12:00 NY se il lunedi' precedente (sessione valida, "
                     "giorno di borsa immediatamente prima) ha chiuso l'RTH 9:30-16:00 in calo; nessun trade se "
                     "il lunedi' era festivo o il lunedi' e' salito."),
        rationale=("'Turnaround Tuesday': il ribasso del lunedi' (effetto weekend/lunedi', vendite concentrate di "
                   "investitori retail il lunedi', Abraham-Ikenberry 1994) viene parzialmente riassorbito il "
                   "martedi' mattina. Nel discovery l'effetto e' specifico del martedi' (placebo 'giorno dopo un "
                   "calo' negativo per lun/mer/gio/ven) e unilaterale (lo specchio short dopo un lunedi' in rialzo "
                   "e' nullo). La finestra 12:00 e' stata scelta DOPO aver visto la versione RTH intera: post hoc."),
        warmup_days=5,
        kind="tradeable",
        fn=turnaround_tue_am,
        discovery=dict(n=178, mean_net=7.383, lo=3.197, hi=11.674, p_pos=0.0003, years_pos="8/9",
                       drop20=0.473, beta_pts=0.309, net_minus_beta=7.074, mean_gross=8.133, bp_mean=9.31),
    ),
]
