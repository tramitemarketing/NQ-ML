"""Candidato 8 — Apertura fuori dalla value area di ieri (pre-registrazione
`docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`, candidato 8). Nessun parametro
libero oltre a quelli elencati nella spec; nessun filtro.

Nota sulle 8 geometrie: la spec elenca esplicitamente solo k in {0,25; 0,5} per famiglia e poi dice "le
restanti 4 si ottengono con il multiplo 0,75w", il che non torna a 8 (2 famiglie x 3 k = 6). Qui si segue la
stessa convenzione gia' usata dal progetto per le altre strutture "2 stop/target x larghezza" (vedi
`nqml/screen/vabreak.py::TARGET_MULT`, T0.25..T1.0): k in {0,25; 0,5; 0,75; 1,0}, 4 valori per famiglia,
2 famiglie x 4 = 8. Scelta dichiarata nel report, non nascosta."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from nqml.detector.run_day import entry_allowed
from nqml.profile.volume_profile import ValueArea, VolumeProfile

# Ordine fisso delle 8 geometrie: famiglia R poi C, dentro ciascuna K0.25..K1.0 (vedi nota sopra).
K_MULT = {"K0.25": 0.25, "K0.5": 0.5, "K0.75": 0.75, "K1.0": 1.0}


def prev_day_value_area(prev_day_rth: pd.DataFrame, cfg: dict) -> ValueArea | None:
    """Value area (70%) del profilo RTH completo della sessione precedente (non ON, non in sviluppo:
    l'intera giornata, spec candidato 8: `VA_prec`)."""
    if len(prev_day_rth) == 0:
        return None
    vp = VolumeProfile(cfg["instrument"]["tick_size"])
    vp.add_bars(prev_day_rth)
    return vp.value_area(cfg["detector"]["value_area_pct"])


def prevva_events(day_rth: pd.DataFrame, session_date: dt.date, cfg: dict, va_prec: ValueArea | None) -> list[dict]:
    """Evento: se l'apertura RTH di oggi e' sopra VAH_prec o sotto VAL_prec, un evento per famiglia (R
    ritorno, C continuazione) alla prima barra 1m dalle 09:30. `e` = apertura RTH (nota all'apertura, prima
    ancora che la barra si chiuda); per la regola generale "ingresso alla barra 1m successiva al segnale" la
    barra del segnale e' la prima barra RTH stessa e l'ingresso e' sulla seconda (stessa costruzione di
    `nqml.screen.gap.gap_event`). None/[] se manca VA_prec, se il giorno ha meno di 2 barre RTH, se
    l'apertura e' dentro VA_prec, o se l'ingresso e' oltre l'ultimo consentito."""
    if va_prec is None or len(day_rth) < 2:
        return []
    open_bar = day_rth.iloc[0]
    e = float(open_bar["open"])
    vah, val = va_prec.vah, va_prec.val
    if val <= e <= vah:
        return []
    deviation = "above" if e > vah else "below"
    w = vah - val
    if w <= 0:
        return []

    entry_ts = day_rth.index[1]
    if not entry_allowed(entry_ts, cfg["detector"]["last_entry"]):
        return []
    entry_price = float(day_rth.iloc[1]["open"])

    # Direzione: sopra VA -> continuazione long (side_c), ritorno short verso VAH (side_r);
    # sotto VA -> continuazione short, ritorno long verso VAL.
    side_c = "long" if deviation == "above" else "short"
    side_r = "short" if deviation == "above" else "long"
    nearest_edge = vah if deviation == "above" else val

    common = dict(session_date=session_date, signal_ts=day_rth.index[0], entry_ref_price=e,
                  entry_ts=entry_ts, entry_price=entry_price, vah_prec=float(vah), val_prec=float(val), w=float(w))
    return [
        common | dict(event_id=f"{session_date}_R", family="R", side=side_r, nearest_edge=float(nearest_edge)),
        common | dict(event_id=f"{session_date}_C", family="C", side=side_c, nearest_edge=float(nearest_edge)),
    ]


def geometries(ev: dict, cfg: dict) -> list[dict]:
    """Le 4 righe per famiglia (8 totali su R+C). R: target = bordo piu' vicino di VA_prec (fisso), stop in
    multipli di w. C: stop = bordo piu' vicino (fisso), target in multipli di w. Salta una geometria se
    |entry_ref - stop| <= 0."""
    side = ev["side"]
    u = 1.0 if side == "long" else -1.0
    e, w, edge, family = ev["entry_ref_price"], ev["w"], ev["nearest_edge"], ev["family"]

    rows: list[dict] = []
    if family == "R":
        target = edge
        if u * (target - e) <= 0:
            return []
        for k_name, k in K_MULT.items():
            stop = e - u * k * w
            denom = abs(e - stop)
            if denom <= 0:
                continue
            rr = abs(target - e) / denom
            rows.append(ev | dict(geom=f"R_{k_name}", stop_price=float(stop), target_price=float(target), rr_ratio=float(rr)))
    else:  # "C"
        stop = edge
        denom = abs(e - stop)
        if denom <= 0:
            return []
        for k_name, k in K_MULT.items():
            target = e + u * k * w
            if u * (target - e) <= 0:
                continue
            rr = abs(target - e) / denom
            rows.append(ev | dict(geom=f"C_{k_name}", stop_price=float(stop), target_price=float(target), rr_ratio=float(rr)))
    return rows
