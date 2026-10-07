"""Diagnostica obbligatoria di sovrapposizione fra i setup (spec
`docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`, §2): per ogni coppia ORDINATA di
candidati, la quota degli eventi del primo che hanno un evento del secondo nello stesso giorno, stesso lato,
entro 15 minuti (di `signal_ts`). Descrittivo: nessun criterio, non decide nulla da solo."""
from __future__ import annotations

import pandas as pd

DEFAULT_WINDOW_MINUTES = 15


def overlap_share(a: pd.DataFrame, b: pd.DataFrame, window_minutes: int = DEFAULT_WINDOW_MINUTES) -> float:
    """Quota degli eventi di `a` (0..1) che hanno almeno un evento di `b` con la stessa `session_date`, lo
    stesso `side`, e |signal_ts_a - signal_ts_b| <= window_minutes. NaN se `a` e' vuoto."""
    if len(a) == 0:
        return float("nan")
    window = pd.Timedelta(minutes=window_minutes)
    by_key: dict[tuple, list[pd.Timestamp]] = {}
    for (sd, side), g in b.groupby(["session_date", "side"]):
        by_key[(sd, side)] = list(pd.DatetimeIndex(g["signal_ts"]))

    hits = 0
    for _, r in a.iterrows():
        times = by_key.get((r["session_date"], r["side"]))
        if not times:
            continue
        ts = pd.Timestamp(r["signal_ts"])
        if any(abs(t - ts) <= window for t in times):
            hits += 1
    return hits / len(a)


def overlap_matrix(events: dict[str, pd.DataFrame], window_minutes: int = DEFAULT_WINDOW_MINUTES) -> pd.DataFrame:
    """Matrice quadrata (nomi in `events`, stesso ordine su righe e colonne): cella [i, j] = quota degli
    eventi del candidato i che hanno un evento del candidato j entro la finestra. Diagonale = NaN (un
    candidato non si confronta con se stesso)."""
    names = list(events)
    m = pd.DataFrame(index=names, columns=names, dtype=float)
    for i in names:
        for j in names:
            m.loc[i, j] = float("nan") if i == j else overlap_share(events[i], events[j], window_minutes)
    return m
