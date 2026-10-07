"""Candidato 4 — Prosecuzione della value area: prima transizione INSIDE -> BROKEN per (tipo di value area x
lato di rottura) per giorno, indipendentemente da cio' che accade dopo (pre-registrazione
`docs/superpowers/specs/2026-09-22-screening-candidati-2-3-4.md`, candidato 4). Gli eventi gia' calcolati in
`data/events/events.parquet` contengono solo le rotture POI RIENTRATE (nqml.detector.state_machine.SetupDetector
emette un Detection solo al rientro), quindi userli introdurrebbe una selezione che favorisce artificialmente il
rientro. Questo modulo guida percio' le stesse barre 5m e lo stesso codice di value area di
nqml/detector/run_day.py (ON fissa per il giorno, DEV ricalcolata a ogni chiusura 5m, esattamente come in
SetupDetector._outside) ma senza usare la classe SetupDetector: emette alla PRIMA chiusura di barra 5m oltre il
bordo della value area, prima di sapere se rientrera' o no."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from nqml.data.bars import five_min_bin, resample_5m, rth_bars
from nqml.detector.run_day import entry_allowed
from nqml.profile.sessions import on_mask
from nqml.profile.volume_profile import ValueArea, VolumeProfile

# Ordine fisso delle 8 geometrie: S1 poi S2, dentro ciascuno T0.25..T1.0 (spec candidato 4).
TARGET_MULT = {"T0.25": 0.25, "T0.5": 0.5, "T0.75": 0.75, "T1.0": 1.0}

# "side" qui e' quello della macchina (nqml.detector.state_machine): "long" traccia la rottura SOTTO la value
# area (close < val, come nel re-ingresso long originale), "short" quella SOPRA (close > vah). La prosecuzione
# va nella direzione della rottura, quindi il lato del trade e' l'OPPOSTO del lato della macchina: rottura in
# giu' (side macchina "long") -> continuazione short; rottura in su (side macchina "short") -> continuazione long.
CONTINUATION_SIDE = {"long": "short", "short": "long"}


def _outside(machine_side: str, close: float, va: ValueArea) -> bool:
    """Stessa condizione di SetupDetector._outside (state_machine.py): solo la chiusura della barra 5m conta."""
    return close < va.val if machine_side == "long" else close > va.vah


def vabreak_events(bars1m_day: pd.DataFrame, session_date: dt.date, cfg: dict) -> list[dict]:
    """Eventi del giorno: per ciascuna delle 4 macchine (va_type ON/DEV x lato di rottura long/short), la prima
    chiusura di barra 5m oltre il bordo della value area. e = chiusura di quella barra 5m; ingresso = apertura
    della barra 1m successiva (= apertura della barra 5m successiva, stesso schema di run_day.py, perche' i bin
    5m sono contigui). Salta un evento se manca la barra 5m successiva o se l'ingresso e' oltre l'ultimo
    consentito; salta l'intero giorno se non ha abbastanza barre RTH."""
    tick = cfg["instrument"]["tick_size"]
    pct = cfg["detector"]["value_area_pct"]
    last_entry = cfg["detector"]["last_entry"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    on_open = cfg["sessions"]["on_open"]

    on = VolumeProfile(tick)
    on.add_bars(bars1m_day.loc[on_mask(bars1m_day.index, on_open, rth_open)])
    on_va = on.value_area(pct)

    rth = rth_bars(bars1m_day, rth_open, rth_close)
    if len(rth) < cfg["sessions"]["min_rth_bars"]:
        return []

    bars5 = resample_5m(rth)
    groups = {ts: g for ts, g in rth.groupby(five_min_bin(rth.index))}
    dev = VolumeProfile(tick)

    fired = {(va_type, side): False for va_type in ("ON", "DEV") for side in ("long", "short")}
    events: list[dict] = []
    rows = list(bars5.itertuples())
    for i, r in enumerate(rows):
        dev.add_bars(groups[r.Index])
        dev_va = dev.value_area(pct)
        for va_type, va in (("ON", on_va), ("DEV", dev_va)):
            if va is None:
                continue
            for machine_side in ("long", "short"):
                key = (va_type, machine_side)
                if fired[key] or not _outside(machine_side, float(r.close), va):
                    continue
                fired[key] = True
                if i + 1 >= len(rows):
                    continue
                nxt = rows[i + 1]
                if not entry_allowed(nxt.Index, last_entry):
                    continue
                cont_side = CONTINUATION_SIDE[machine_side]
                events.append(dict(
                    event_id=f"{session_date}_{va_type}_{cont_side}", session_date=session_date,
                    va_type=va_type, side=cont_side,
                    break_ts=r.Index + pd.Timedelta(minutes=5), entry_ref_price=float(r.close),
                    entry_ts=nxt.Index, entry_price=float(nxt.open),
                    vah=va.vah, val=va.val, poc=va.poc, w=va.vah - va.val,
                ))
    return events


def geometries(ev: dict, cfg: dict) -> list[dict]:
    """Le 8 righe (2 stop x 4 target) del muro (candidato 4). Direzione = quella della rottura (`side`
    dell'evento e' gia' la direzione di continuazione). S1 «rientro» = VAH - 1 tick (rottura in su; VAL + 1 tick
    speculare in giu'); S2 «POC» = POC -+ 1 tick. Target T_k = e +- k*w, w = VAH - VAL alla rottura. Salta una
    geometria se |entry_ref - stop| <= 0."""
    tick = cfg["instrument"]["tick_size"]
    side = ev["side"]
    u = 1.0 if side == "long" else -1.0
    e, w = ev["entry_ref_price"], ev["w"]
    vah, val, poc = ev["vah"], ev["val"], ev["poc"]

    stops = {
        "S1": (vah - tick) if side == "long" else (val + tick),
        "S2": (poc - tick) if side == "long" else (poc + tick),
    }
    rows: list[dict] = []
    for s_name, stop in stops.items():
        denom = abs(e - stop)
        if denom <= 0:
            continue
        for t_name, k in TARGET_MULT.items():
            target = e + u * k * w
            rr = abs(target - e) / denom
            rows.append(ev | dict(geom=f"{s_name}_{t_name}", stop_price=float(stop), target_price=float(target), rr_ratio=float(rr)))
    return rows
