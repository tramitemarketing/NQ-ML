"""Opening Range Breakout (ORB15): opening range, rilevazione della rottura e le 8 geometrie del test del muro
(pre-registrazione `docs/superpowers/specs/2026-09-22-screening-nuovi-setup.md`, §2). Nessun parametro libero oltre
a quelli elencati nella spec; nessun filtro."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from nqml.detector.run_day import entry_allowed
from nqml.profile.sessions import _hm, ny_minutes, rth_open_utc

RTH_OPEN = "09:30"

# Ordine fisso delle 8 geometrie: S1 poi S2, dentro ciascuno T0.5..T2 (spec §2).
TARGET_MULT = {"T0.5": 0.5, "T1": 1.0, "T1.5": 1.5, "T2": 2.0}


def opening_range(rth1m_day: pd.DataFrame, minutes: int = 15) -> tuple[float, float] | None:
    """Massimo (ORH) e minimo (ORL) delle prime `minutes` barre 1m di RTH, dalle 09:30:00 ET.
    None se il giorno ha meno di `minutes` barre in quella finestra (opening range incompleto)."""
    open_min = _hm(RTH_OPEN)
    m = ny_minutes(rth1m_day.index)
    window = rth1m_day.loc[(m >= open_min) & (m < open_min + minutes)]
    if len(window) < minutes:
        return None
    return float(window["high"].max()), float(window["low"].min())


def orb_events(rth1m_day: pd.DataFrame, session_date: dt.date, cfg: dict, minutes: int = 15) -> list[dict]:
    """Eventi del giorno: dalle 09:45 ET, la prima barra 1m che chiude sopra ORH da' un evento long, la prima
    che chiude sotto ORL un evento short; al massimo un evento per lato (entrambi possono scattare). Salta un
    lato se manca la barra successiva (ingresso), se la barra d'ingresso e' oltre l'ultimo ingresso configurato,
    o l'intero giorno se l'opening range non e' completo o OR_range <= 0."""
    orng = opening_range(rth1m_day, minutes)
    if orng is None:
        return []
    orh, orl = orng
    or_range = orh - orl
    if or_range <= 0:
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
        for side, broke in (("long", r.close > orh), ("short", r.close < orl)):
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
                orh=orh, orl=orl, or_range=or_range,
                minutes_since_open=(r.Index - rth_open_utc(session_date, RTH_OPEN)).total_seconds() / 60.0,
            ))
    return events


def geometries(ev: dict, cfg: dict) -> list[dict]:
    """Le 8 righe (2 stop x 4 target) della tabella del muro (spec §2), con d = OR_range, e = entry_ref_price.
    S1 «largo» = lato opposto dell'opening range, 1 tick oltre; S2 «stretto» = lato rotto (rientro), 1 tick dentro.
    Salta una geometria se |entry_ref - stop| <= 0."""
    tick = cfg["instrument"]["tick_size"]
    side = ev["side"]
    u = 1.0 if side == "long" else -1.0
    e, d = ev["entry_ref_price"], ev["or_range"]
    orh, orl = ev["orh"], ev["orl"]

    stops = {
        "S1": (orl - tick) if side == "long" else (orh + tick),
        "S2": (orh - tick) if side == "long" else (orl + tick),
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
