"""Candidato 7 — Momentum dell'ultima ora (pre-registrazione
`docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`, candidato 7). Nessun parametro
libero oltre a quelli elencati nella spec; nessun filtro."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from nqml.detector.run_day import entry_allowed
from nqml.profile.sessions import _hm, ny_minutes

SIGNAL_TIME = "15:00"
# Ordine fisso delle 4 geometrie: S0.5 poi S1.0, dentro ciascuno T0.5 e T1.0 (spec candidato 7).
STOP_MULT = {"S0.5": 0.5, "S1.0": 1.0}
TARGET_MULT = {"T0.5": 0.5, "T1.0": 1.0}


def lasthour_event(day_rth: pd.DataFrame, session_date: dt.date, cfg: dict, atr_prev_day: float | None) -> dict | None:
    """Evento: alla barra 1m delle 15:00 ET, se la sua chiusura e' sopra l'apertura RTH del giorno si entra
    long, se sotto short (esattamente uguale: nessun evento, ne' guadagno ne' perdita). None se manca la
    barra delle 15:00, se manca la barra d'ingresso, o se l'ingresso e' oltre l'ultimo consentito.
    `atr_prev_day` e' l'ATR(14) del giorno precedente (None se non disponibile: primo giorno del periodo)."""
    if len(day_rth) == 0:
        return None
    rth_open_price = float(day_rth["open"].iloc[0])
    signal_min = _hm(SIGNAL_TIME)
    m = ny_minutes(day_rth.index)
    at_signal = day_rth.loc[m == signal_min]
    if len(at_signal) == 0:
        return None

    rows = list(day_rth.itertuples())
    idx_signal = day_rth.index.get_loc(at_signal.index[0])
    r = rows[idx_signal]
    e = float(r.close)
    if e == rth_open_price:
        return None
    side = "long" if e > rth_open_price else "short"

    if idx_signal + 1 >= len(rows):
        return None
    nxt = rows[idx_signal + 1]
    if not entry_allowed(nxt.Index, cfg["detector"]["last_entry"]):
        return None
    return dict(
        event_id=f"{session_date}_{side}", session_date=session_date, side=side,
        signal_ts=r.Index, entry_ref_price=e, rth_open_price=rth_open_price,
        entry_ts=nxt.Index, entry_price=float(nxt.open), atr=atr_prev_day,
    )


def geometries(ev: dict, cfg: dict) -> list[dict]:
    """Le 4 righe (2 stop x 2 target) del muro (candidato 7). e = entry_ref_price (chiusura della barra
    delle 15:00), A = ATR(14) del giorno precedente. Salta se A e' mancante/non positivo o
    |entry_ref - stop| <= 0."""
    side = ev["side"]
    u = 1.0 if side == "long" else -1.0
    e, A = ev["entry_ref_price"], ev["atr"]
    if A is None or A <= 0:
        return []
    rows: list[dict] = []
    for s_name, ks in STOP_MULT.items():
        stop = e - u * ks * A
        denom = abs(e - stop)
        if denom <= 0:
            continue
        for t_name, kt in TARGET_MULT.items():
            target = e + u * kt * A
            rr = abs(target - e) / denom
            rows.append(ev | dict(geom=f"{s_name}_{t_name}", stop_price=float(stop), target_price=float(target), rr_ratio=float(rr)))
    return rows
