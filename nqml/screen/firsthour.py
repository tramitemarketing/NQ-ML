"""Candidato 3 — Estremi della prima ora: FHH/FHL sulle 60 barre 1m dalle 09:30:00 alle 10:29:59 ET, rottura
dalle 10:30 (pre-registrazione `docs/superpowers/specs/2026-09-22-screening-candidati-2-3-4.md`, candidato 3).
Stessa struttura dell'ORB15 (nqml/screen/orb.py) su una finestra di un'ora invece di 15 minuti; nessun filtro."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from nqml.detector.run_day import entry_allowed
from nqml.profile.sessions import _hm, ny_minutes, rth_open_utc

RTH_OPEN = "09:30"
WINDOW_MINUTES = 60

# Ordine fisso delle 8 geometrie: S1 poi S2, dentro ciascuno T0.5..T2 (spec candidato 3).
TARGET_MULT = {"T0.5": 0.5, "T1": 1.0, "T1.5": 1.5, "T2": 2.0}


def first_hour_range(rth1m_day: pd.DataFrame, minutes: int = WINDOW_MINUTES) -> tuple[float, float] | None:
    """Massimo (FHH) e minimo (FHL) delle prime `minutes` barre 1m di RTH, dalle 09:30:00 ET.
    None se il giorno ha meno di `minutes` barre in quella finestra (prima ora incompleta)."""
    open_min = _hm(RTH_OPEN)
    m = ny_minutes(rth1m_day.index)
    window = rth1m_day.loc[(m >= open_min) & (m < open_min + minutes)]
    if len(window) < minutes:
        return None
    return float(window["high"].max()), float(window["low"].min())


def firsthour_events(rth1m_day: pd.DataFrame, session_date: dt.date, cfg: dict, minutes: int = WINDOW_MINUTES) -> list[dict]:
    """Eventi del giorno: dalle 10:30 ET, la prima barra 1m che chiude sopra FHH da' un evento long, la prima
    che chiude sotto FHL uno short; al massimo un evento per lato (entrambi possono scattare). Salta un lato
    se manca la barra successiva (ingresso), se la barra d'ingresso e' oltre l'ultimo ingresso configurato, o
    l'intero giorno se la prima ora non e' completa o FH_range <= 0."""
    rng = first_hour_range(rth1m_day, minutes)
    if rng is None:
        return []
    fhh, fhl = rng
    fh_range = fhh - fhl
    if fh_range <= 0:
        return []

    open_min = _hm(RTH_OPEN)
    m = ny_minutes(rth1m_day.index)
    after = rth1m_day.loc[m >= open_min + minutes]
    last_entry = cfg["detector"]["last_entry"]

    events: list[dict] = []
    fired = {"long": False, "short": False}
    rows = list(after.itertuples())
    for i, r in enumerate(rows):
        if fired["long"] and fired["short"]:
            break
        for side, broke in (("long", r.close > fhh), ("short", r.close < fhl)):
            if fired[side] or not broke:
                continue
            fired[side] = True
            if i + 1 >= len(rows):
                continue
            nxt = rows[i + 1]
            if not entry_allowed(nxt.Index, last_entry):
                continue
            events.append(dict(
                event_id=f"{session_date}_{side}", session_date=session_date, side=side,
                break_ts=r.Index, entry_ref_price=float(r.close),
                entry_ts=nxt.Index, entry_price=float(nxt.open),
                fhh=fhh, fhl=fhl, fh_range=fh_range,
                minutes_since_open=(r.Index - rth_open_utc(session_date, RTH_OPEN)).total_seconds() / 60.0,
            ))
    return events


def geometries(ev: dict, cfg: dict) -> list[dict]:
    """Le 8 righe (2 stop x 4 target) della tabella del muro (candidato 3), con d = fh_range, e = entry_ref_price.
    S1 «largo» = lato opposto della prima ora, 1 tick oltre; S2 «stretto» = lato rotto (rientro), 1 tick dentro.
    Salta una geometria se |entry_ref - stop| <= 0."""
    tick = cfg["instrument"]["tick_size"]
    side = ev["side"]
    u = 1.0 if side == "long" else -1.0
    e, d = ev["entry_ref_price"], ev["fh_range"]
    fhh, fhl = ev["fhh"], ev["fhl"]

    stops = {
        "S1": (fhl - tick) if side == "long" else (fhh + tick),
        "S2": (fhh - tick) if side == "long" else (fhl + tick),
    }
    rows: list[dict] = []
    for s_name, stop in stops.items():
        denom = abs(e - stop)
        if denom <= 0:
            continue
        for t_name, k in TARGET_MULT.items():
            target = e + u * k * d
            rr = abs(target - e) / denom
            rows.append(ev | dict(geom=f"{s_name}_{t_name}", stop_price=float(stop), target_price=float(target), rr_ratio=float(rr)))
    return rows
