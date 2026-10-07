"""Candidato 5 — Ritorno alla media sul VWAP (pre-registrazione
`docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`, candidato 5). Nessun parametro libero
oltre a quelli elencati nella spec; nessun filtro."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from nqml.detector.run_day import entry_allowed
from nqml.profile.sessions import _hm, ny_minutes

SIGNAL_START = "10:00"
K_SIGMA = 2.0
# Ordine fisso delle 6 geometrie: TVWAP poi TMID, dentro ciascuno A1.0..A2.0 (spec candidato 5).
STOP_MULT = {"A1.0": 1.0, "A1.5": 1.5, "A2.0": 2.0}


def _vwap_sigma(day_rth: pd.DataFrame) -> pd.DataFrame:
    """VWAP e sigma (pesata per volume) espansi dall'apertura RTH, sui prezzi tipici (H+L+C)/3, calcolati
    fino alla barra corrente INCLUSA ("nella sessione fino a quel momento", spec candidato 5): tutte le
    grandezze di una barra sono note alla sua chiusura, quindi includerla non e' lookahead."""
    tp = (day_rth["high"] + day_rth["low"] + day_rth["close"]) / 3.0
    vol = day_rth["volume"].astype(float)
    cum_vol = vol.cumsum()
    cum_pv = (tp * vol).cumsum()
    cum_pv2 = (tp * tp * vol).cumsum()
    vwap = cum_pv / cum_vol
    var = cum_pv2 / cum_vol - vwap * vwap
    sigma = np.sqrt(var.clip(lower=0.0))
    return pd.DataFrame({"vwap": vwap, "sigma": sigma}, index=day_rth.index)


def vwap_events(day_rth: pd.DataFrame, session_date: dt.date, cfg: dict, atr_prev_day: float | None) -> list[dict]:
    """Eventi del giorno: dalle 10:00 ET, la prima barra 1m che chiude a piu' di 2 sigma sopra il VWAP genera
    uno short, la prima a piu' di 2 sigma sotto un long (ritorno alla media). Al massimo un evento per lato.
    Salta un lato se sigma non e' positiva (dati degeneri), se manca la barra d'ingresso, o se l'ingresso e'
    oltre l'ultimo consentito. `atr_prev_day` (puo' essere None: primo giorno del periodo) e' portato
    sull'evento per le geometrie, che lo richiedono come unita' di misura dello stop."""
    vs = _vwap_sigma(day_rth)
    m = ny_minutes(day_rth.index)
    signal_min = _hm(SIGNAL_START)
    last_entry = cfg["detector"]["last_entry"]

    rows = list(day_rth.itertuples())
    vwap_arr, sigma_arr = vs["vwap"].to_numpy(), vs["sigma"].to_numpy()
    events: list[dict] = []
    fired = {"long": False, "short": False}
    for i, r in enumerate(rows):
        if fired["long"] and fired["short"]:
            break
        if m[i] < signal_min:
            continue
        vwap_i, sigma_i = vwap_arr[i], sigma_arr[i]
        if not (sigma_i > 0):
            continue
        upper, lower = vwap_i + K_SIGMA * sigma_i, vwap_i - K_SIGMA * sigma_i
        for side, triggered in (("short", r.close > upper), ("long", r.close < lower)):
            if fired[side] or not triggered:
                continue
            fired[side] = True
            if i + 1 >= len(rows):
                continue
            nxt = rows[i + 1]
            if not entry_allowed(nxt.Index, last_entry):
                continue
            events.append(dict(
                event_id=f"{session_date}_{side}", session_date=session_date, side=side,
                signal_ts=r.Index, entry_ref_price=float(r.close),
                entry_ts=nxt.Index, entry_price=float(nxt.open),
                vwap=float(vwap_i), sigma=float(sigma_i), atr=atr_prev_day,
            ))
    return events


def geometries(ev: dict, cfg: dict) -> list[dict]:
    """Le 6 righe (2 target x 3 stop) del muro (candidato 5). e = entry_ref_price (chiusura del segnale),
    A = ATR(14) del giorno precedente. TVWAP = ritorno pieno al VWAP; TMID = a meta' strada fra e e VWAP.
    Stop dal lato opposto alla direzione del trade, in multipli di A. Salta se A e' mancante/non positivo o
    |entry_ref - stop| <= 0."""
    side = ev["side"]
    u = 1.0 if side == "long" else -1.0
    e, vwap, A = ev["entry_ref_price"], ev["vwap"], ev["atr"]
    if A is None or A <= 0:
        return []

    targets = {"TVWAP": vwap, "TMID": (e + vwap) / 2.0}
    rows: list[dict] = []
    for t_name, target in targets.items():
        if u * (target - e) <= 0:
            continue
        for s_name, k in STOP_MULT.items():
            stop = e - u * k * A
            denom = abs(e - stop)
            if denom <= 0:
                continue
            rr = abs(target - e) / denom
            rows.append(ev | dict(geom=f"{t_name}_{s_name}", stop_price=float(stop), target_price=float(target), rr_ratio=float(rr)))
    return rows
