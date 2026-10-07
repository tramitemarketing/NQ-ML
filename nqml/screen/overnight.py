"""Candidato 6 — Tenuta overnight (pre-registrazione
`docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`, candidato 6). Nessuna condizione:
long alla chiusura RTH, uscita all'apertura RTH successiva. Unica deroga del lotto rispetto alle regole
generali: il time stop non e' alle 15:55 ma all'apertura RTH successiva (e' nella definizione del setup, non
un parametro, spec candidato 6). Per questo l'esito non puo' passare dal `label_event` condiviso (che chiude
sempre entro la stessa sessione, alle 15:55): `label_overnight_event` qui sotto ne rispecchia la stessa
identica logica (stessi campi, stesso controllo hit_stop/hit_target barra per barra, stessa apply_costs a
valle) con due sole differenze, entrambe dettate dalla definizione del setup: (1) il percorso da scandire e'
lo `span` fra la chiusura RTH e l'apertura RTH successiva, non i minuti-NY della stessa giornata; (2) se
nessuno dei due livelli viene toccato, la chiusura e' all'APERTURA dell'ultima barra dello span (l'apertura
RTH successiva), non alla sua chiusura."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from nqml.features.direction import up

# Ordine fisso delle 4 geometrie: S1.0 poi S2.0, dentro ciascuno T1.0 e T2.0 (spec candidato 6).
STOP_MULT = {"S1.0": 1.0, "S2.0": 2.0}
TARGET_MULT = {"T1.0": 1.0, "T2.0": 2.0}


def overnight_event(entry_rth: pd.DataFrame, entry_sd: dt.date, exit_rth: pd.DataFrame, exit_sd: dt.date,
                     cfg: dict, atr_prev_day: float | None) -> dict | None:
    """Evento: ingresso long alla chiusura RTH di `entry_sd` (ultima barra 1m nota, prezzo = la sua
    chiusura), uscita alla PRIMA barra RTH di `exit_sd` (la sessione di trading immediatamente successiva).
    None se una delle due giornate non ha barre RTH. `atr_prev_day` e' l'ATR(14) del giorno precedente
    `entry_sd` (portato dal chiamante, `nqml.screen.atr.previous_day_atr`), None se non disponibile
    (tipicamente il primo giorno del periodo)."""
    if len(entry_rth) == 0 or len(exit_rth) == 0:
        return None
    entry_ts = entry_rth.index[-1]
    entry_price = float(entry_rth["close"].iloc[-1])
    next_open_ts = exit_rth.index[0]
    next_open_price = float(exit_rth["open"].iloc[0])
    return dict(
        event_id=f"{entry_sd}_overnight", session_date=entry_sd, side="long",
        signal_ts=entry_ts, entry_ts=entry_ts, entry_price=entry_price, entry_ref_price=entry_price,
        exit_session_date=exit_sd, next_open_ts=next_open_ts, next_open_price=next_open_price,
        atr=atr_prev_day,
    )


def overnight_span(entry_day_full: pd.DataFrame, entry_ts: pd.Timestamp,
                    exit_day_full: pd.DataFrame, next_open_ts: pd.Timestamp) -> pd.DataFrame:
    """Barre 1m fra la chiusura RTH (esclusa) e l'apertura RTH successiva (inclusa): unisce le barre residue
    del giorno d'ingresso (es. 16:00-16:59, se presenti) e quelle del giorno d'uscita (sessione overnight ON
    + la sua barra di apertura RTH), senza assumere nulla sulla continuita' fra le due (weekend inclusi:
    l'ON della domenica sera e' gia' etichettato con la session_date del lunedi', quindi rientra qui in
    `exit_day_full` senza bisogno di casi speciali)."""
    span = pd.concat([entry_day_full, exit_day_full]).sort_index()
    return span.loc[(span.index > entry_ts) & (span.index <= next_open_ts)]


def geometries(ev: dict, cfg: dict) -> list[dict]:
    """Le 4 righe (2 stop x 2 target) del muro (candidato 6), tutte long. e = entry_ref_price (chiusura
    RTH), A = ATR(14) del giorno precedente. Salta se A e' mancante/non positivo o |entry_ref - stop| <= 0."""
    e, A = ev["entry_ref_price"], ev["atr"]
    if A is None or A <= 0:
        return []
    rows: list[dict] = []
    for s_name, ks in STOP_MULT.items():
        stop = e - ks * A
        denom = abs(e - stop)
        if denom <= 0:
            continue
        for t_name, kt in TARGET_MULT.items():
            target = e + kt * A
            rr = abs(target - e) / denom
            rows.append(ev | dict(geom=f"{s_name}_{t_name}", stop_price=float(stop), target_price=float(target), rr_ratio=float(rr)))
    return rows


def label_overnight_event(row: dict, span: pd.DataFrame, cfg: dict) -> dict:
    """Stessa struttura di `nqml.labels.labeler.label_event` (stessi campi, stesso controllo hit_stop /
    hit_target barra per barra), con le due differenze di definizione del candidato 6 documentate sopra."""
    side = row["side"]
    u = up(side)
    entry = float(row["entry_price"])
    stop, target = float(row["stop_price"]), float(row["target_price"])
    tick = cfg["instrument"]["tick_size"]
    slip = cfg["costs"]["slippage_ticks_per_side"] * tick
    r_unit = abs(entry + u * slip - stop)
    base = dict(event_id=row["event_id"], entry_price_raw=entry, r_unit_pts=r_unit)

    if u * (entry - stop) <= 0 or u * (target - entry) <= 0:
        return base | dict(label=0, exit_reason="gap", exit_ts=row["entry_ts"], exit_price_raw=entry, pnl_pts_raw=0.0)

    if len(span) == 0:
        return base | dict(label=0, exit_reason="no_bars", exit_ts=row["entry_ts"], exit_price_raw=entry, pnl_pts_raw=0.0)

    for ts, b in span.iterrows():
        hit_stop = b["low"] <= stop if side == "long" else b["high"] >= stop
        hit_target = b["high"] >= target if side == "long" else b["low"] <= target
        if hit_stop:
            return base | dict(label=0, exit_reason="stop", exit_ts=ts, exit_price_raw=stop, pnl_pts_raw=u * (stop - entry))
        if hit_target:
            return base | dict(label=1, exit_reason="target", exit_ts=ts, exit_price_raw=target, pnl_pts_raw=u * (target - entry))
    # Ne' stop ne' target toccati entro l'apertura successiva (ultima barra di span): chiuso all'APERTURA
    # di quella barra, non alla sua chiusura (nota di validita', spec candidato 6).
    last_ts, last = span.index[-1], span.iloc[-1]
    open_px = float(last["open"])
    return base | dict(label=0, exit_reason="time", exit_ts=last_ts, exit_price_raw=open_px, pnl_pts_raw=u * (open_px - entry))
