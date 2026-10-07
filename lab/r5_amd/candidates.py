"""Candidati congelati della famiglia r5_amd (modello AMD/ICT del video di Tmac, discovery chiuso il 2026-09-28).

NESSUN CANDIDATO. Il primario pre-registrato P0 perde (-0,26 punti netti, 1/9 anni), la meta' contro-trend
(la tesi esplicita del video) perde di piu' (-0,89, 2/9), e nessuna delle tre proposte dell'addendum 1 supera
i criteri di discovery (la migliore, PB, +1,20 p 0,084, e' tutta nel 2018 e ha d20 negativo). Dettagli in
lab/r5_amd/REPORT.md. La funzione sotto NON e' un candidato: riproduce P0 per test_candidates.py.
"""
from __future__ import annotations

import pandas as pd

from lab.r5_amd import common as C


def observation_p0(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """P0 (PREREG.md): sweep del massimo/minimo notturno + primo tocco di un OB 4h, limite alla mitigazione
    dell'OB 2m di manipolazione, stop oltre l'estremo, obiettivo estremo asiatico, uscita 15:59."""
    t = C.simulate(C.Data(bars, daily))
    return t[["session", "entry_ts", "exit_ts", "side", "gross_pts"]]


CANDIDATES: list[dict] = []
