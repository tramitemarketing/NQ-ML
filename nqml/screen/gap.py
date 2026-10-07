"""Candidato 2 — Gap di apertura: chiusura del gap (F) contro prosecuzione (P), tre geometrie ciascuna
(pre-registrazione `docs/superpowers/specs/2026-09-22-screening-candidati-2-3-4.md`, candidato 2). Nessun
parametro libero oltre a quelli elencati nella spec; nessun filtro."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from nqml.detector.run_day import entry_allowed

GAP_MIN_PTS = 2.0
K_VALUES = (0.5, 1.0, 2.0)
K_LABEL = {0.5: "k0.5", 1.0: "k1", 2.0: "k2"}


def gap_event(day_rth: pd.DataFrame, session_date: dt.date, prev_close: float | None, cfg: dict) -> dict | None:
    """Evento del giorno: gap = apertura RTH (prima barra 1m) - chiusura RTH del giorno precedente
    (ultima barra 1m nota). None se manca una chiusura precedente, se il giorno non ha barre RTH, se
    |gap| < 2 punti (8 tick), se manca la barra d'ingresso, o se l'ingresso e' oltre l'ultimo consentito."""
    if prev_close is None or len(day_rth) < 2:
        return None
    open_bar = day_rth.iloc[0]
    e = float(open_bar["open"])
    gap = e - float(prev_close)
    if abs(gap) < GAP_MIN_PTS:
        return None
    entry_ts = day_rth.index[1]
    if not entry_allowed(entry_ts, cfg["detector"]["last_entry"]):
        return None
    return dict(
        event_id=f"{session_date}_gap", session_date=session_date,
        open_ts=day_rth.index[0], entry_ref_price=e,
        entry_ts=entry_ts, entry_price=float(day_rth.iloc[1]["open"]),
        gap=gap, prev_close=float(prev_close),
    )


def geometries(ev: dict, cfg: dict) -> list[dict]:
    """Le 6 righe (F chiusura del gap, P prosecuzione; 3 k ciascuna), candidato 2. G = |gap|; C = prev_close.
    F va verso C (target = C, stop = e -+ k*G, rr = 1/k); P va nella direzione del gap
    (target = e +- k*G, stop = C, rr = k). Le due famiglie sono speculari per costruzione (§ candidato 2)."""
    e, gap, C = ev["entry_ref_price"], ev["gap"], ev["prev_close"]
    G = abs(gap)
    u_p = 1.0 if gap > 0 else -1.0  # prosecuzione: stessa direzione del gap
    u_f = -u_p                       # chiusura del gap: verso C, direzione opposta al gap

    rows: list[dict] = []
    for k in K_VALUES:
        stop_f = e - u_f * k * G
        denom_f = abs(e - stop_f)
        if denom_f <= 0:
            continue
        side_f = "long" if u_f > 0 else "short"
        rr_f = abs(C - e) / denom_f
        rows.append(ev | dict(geom=f"F_{K_LABEL[k]}", side=side_f, stop_price=float(stop_f),
                               target_price=float(C), rr_ratio=float(rr_f)))
    for k in K_VALUES:
        target_p = e + u_p * k * G
        denom_p = abs(e - C)
        if denom_p <= 0:
            continue
        side_p = "long" if u_p > 0 else "short"
        rr_p = abs(target_p - e) / denom_p
        rows.append(ev | dict(geom=f"P_{K_LABEL[k]}", side=side_p, stop_price=float(C),
                               target_price=float(target_p), rr_ratio=float(rr_p)))
    return rows
