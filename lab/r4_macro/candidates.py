"""Candidati congelati della famiglia r4_macro (giro 4, discovery chiuso il 2026-09-23).

NESSUN CANDIDATO. Motivazione completa in lab/r4_macro/REPORT.md. In breve: l'unico segnale con un'ombra di
evidenza (variazione a 40 g.l. del rendimento Treasury 10 anni, segno negativo sul rendimento NQ successivo)
nella forma che il controller puo' giudicare correttamente (righe giornaliere non sovrapposte) ha in discovery
+4,4 bp/giorno, p bilaterale 0,053, scelto come migliore di 4 lookback (L=20 ha segno opposto), dopo ~16
segnali esplorati; la versione negoziabile fallisce gia' in discovery il criterio 'senza i 20 migliori' (-13,2
punti). Inoltre l'agente conosce qualitativamente il regime 2022 (tassi su, Nasdaq giu'), che favorirebbe
proprio questo segno: un eventuale PASS in validazione sarebbe contaminato. Occupare uno slot di Bonferroni
(K del giro 4) con questo segnale ridurrebbe la potenza degli altri candidati del giro.

La funzione sotto NON e' un candidato: documenta l'osservazione (per riproduzione, vedi test_candidates.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.r4_macro import common as C


def observation_d40_daily(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Osservazione (non candidata): -segno(d40_DGS10 noto all'apertura) x rendimento NQ open RTH -> open RTH
    della sessione dopo, in punti adj (gross_pts) e in bp (gross_bp)."""
    d = C.build(bars, daily)
    k = C.ext_known(d.index)["DGS10"]
    d = d[d["O"].notna()].copy()
    d40 = (k - k.shift(40)).reindex(d.index)
    side = -np.sign(d40)
    nxt = d["O"].shift(-1)
    out = pd.DataFrame({
        "session": pd.to_datetime(d.index).astype("datetime64[ns]"),
        "entry_ts": d["O_ts"].to_numpy(),
        "exit_ts": d["O_ts"].shift(-1).to_numpy(),
        "side": side.to_numpy(),
        "gross_pts": (side * (nxt - d["O"])).to_numpy(),
        "gross_bp": (side * (nxt - d["O"]) / d["Oraw"] * 1e4).to_numpy(),
    })
    out = out.dropna()
    out = out[out["side"] != 0]
    out["side"] = out["side"].astype(int)
    return out.reset_index(drop=True)


CANDIDATES: list[dict] = []
