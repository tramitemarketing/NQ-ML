"""Screening v2 — rifacimento integrale con lo strumento corretto (pre-registrazione
`docs/superpowers/specs/2026-09-23-screening-v2-rifacimento.md`). Aritmetico: nessun modello viene
addestrato. Solo gli anni di training (2016-09-20 -> 2023-09-30); OOS di lavoro e cassaforte non vengono
toccati. Rimisura gli 8 candidati gia' screenati (nqml/screen/{orb,gap,firsthour,vabreak,vwap,overnight,
lasthour,prevva}.py) piu' il candidato 0 (setup value-area originale, data/events/events.parquet) con la
statistica di spec §1: R_lordo mark-to-market (target a trade-through di 1 tick, stop al tocco, nessun
costo), nullo 0 per i candidati simmetrici o con deriva (identita' di Wald) per i due direzionali (6, 7),
specchio obbligatorio, co-primaria sul netto, robustezza di unita' (R/$/ATR), molteplicita' BH q=0,10
sull'intera famiglia di 58 test. Usa esclusivamente gli strumenti di misura gia' costruiti e testati in
nqml/screen/wall2.py, nqml/screen/drift.py, nqml/backtest/fastboot.py, nqml/screen/fdr.py: questo script e'
solo il runner, l'esecuzione e il report — nessuna nuova statistica viene inventata qui, salvo la
duplicazione dichiarata di r_gross per il candidato 6 (span overnight invece delle barre RTH della stessa
giornata: stessa deroga gia' documentata da `nqml.screen.overnight.label_overnight_event` rispetto al
labeler condiviso).

Uso: .venv\\Scripts\\python scripts\\25_screen_v2.py
Precondizione: nessuna (rilegge gli eventi da zero dai moduli candidato; non dipende dai parquet salvati da
20/21/24, tranne per la matrice di sovrapposizione che e' copiata letteralmente da reports/screen_batch2.md
come richiesto dal task)."""
from __future__ import annotations

import datetime as dt
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from nqml.config import config_hash, git_commit, load_config
from nqml.data.bars import load_bars, rth_bars, sessions_iter
from nqml.features.direction import up
from nqml.model.walkforward import assert_no_vault
from nqml.screen import firsthour, gap, lasthour, orb, overnight, prevva, vabreak, vwap
from nqml.screen.atr import previous_day_atr
from nqml.screen.drift import segment_drift, wald_null
from nqml.screen.fdr import benjamini_hochberg
from nqml.screen.wall2 import ev_test, mirror_stats, r_gross, units

PERIOD_START = dt.date(2016, 9, 20)
PERIOD_END = dt.date(2023, 9, 30)
BOUNDARY = dt.date(2023, 10, 1)
Q_BH = 0.10
ALPHA_CI = 0.05

SCREEN_DIR = Path("data/screen")
EVENTS0_PATH = Path("data/events/events.parquet")

ORB_GEOM_ORDER = [f"{s}_{t}" for s in ("S1", "S2") for t in ("T0.5", "T1", "T1.5", "T2")]
GAP_GEOM_ORDER = [f"{fam}_k{k}" for fam in ("F", "P") for k in ("0.5", "1", "2")]
FH_GEOM_ORDER = [f"{s}_{t}" for s in ("S1", "S2") for t in ("T0.5", "T1", "T1.5", "T2")]
VA_GEOM_ORDER = [f"{s}_{t}" for s in ("S1", "S2") for t in ("T0.25", "T0.5", "T0.75", "T1.0")]
VWAP_GEOM_ORDER = [f"{t}_{s}" for t in ("TVWAP", "TMID") for s in ("A1.0", "A1.5", "A2.0")]
OVERNIGHT_GEOM_ORDER = [f"{s}_{t}" for s in ("S1.0", "S2.0") for t in ("T1.0", "T2.0")]
LASTHOUR_GEOM_ORDER = [f"{s}_{t}" for s in ("S0.5", "S1.0") for t in ("T0.5", "T1.0")]
PREVVA_GEOM_ORDER = [f"{fam}_{k}" for fam in ("R", "C") for k in ("K0.25", "K0.5", "K0.75", "K1.0")]
CANDIDATE0_ORDER = ["complessiva", "rr_Q1", "rr_Q2", "rr_Q3", "rr_Q4", "rr_Q5"]

CANDIDATE_META = {
    1: ("orb", "ORB 15 minuti", ORB_GEOM_ORDER, "zero"),
    2: ("gap", "Gap di apertura", GAP_GEOM_ORDER, "zero"),
    3: ("firsthour", "Estremi della prima ora", FH_GEOM_ORDER, "zero"),
    4: ("vabreak", "Prosecuzione value area", VA_GEOM_ORDER, "zero"),
    5: ("vwap", "Ritorno al VWAP", VWAP_GEOM_ORDER, "zero"),
    6: ("overnight", "Tenuta overnight", OVERNIGHT_GEOM_ORDER, "wald"),
    7: ("lasthour", "Momentum ultima ora", LASTHOUR_GEOM_ORDER, "wald"),
    8: ("prevva", "Apertura fuori VA di ieri", PREVVA_GEOM_ORDER, "zero"),
    0: ("value_area", "Setup value-area originale (rientro)", CANDIDATE0_ORDER, "zero"),
}


# ---------------------------------------------------------------------------
# Helper condivisi: specchio e la duplicazione dichiarata di r_gross per l'overnight
# ---------------------------------------------------------------------------

def mirror_geometry(row: dict) -> dict:
    """Test dello specchio (spec §1): stesso ingresso, lato opposto, stesse distanze -> riflette stop e
    target intorno al prezzo d'ingresso (2*entry - prezzo) e capovolge il lato. Le distanze (e quindi
    r_unit) restano identiche per costruzione."""
    entry = float(row["entry_price"])
    m = dict(row)
    m["side"] = "short" if row["side"] == "long" else "long"
    m["stop_price"] = 2.0 * entry - float(row["stop_price"])
    m["target_price"] = 2.0 * entry - float(row["target_price"])
    return m


def r_gross_overnight(row: dict, span: pd.DataFrame, cfg: dict) -> dict:
    """Stessa statistica di `nqml.screen.wall2.r_gross` (trade-through di 1 tick sul target, stop al tocco,
    nessun costo), applicata allo `span` overnight invece delle barre RTH della stessa giornata: unica
    deroga del candidato 6 (spec candidati-5-8, candidato 6; spec v2 §1 non la modifica). Duplicazione
    dichiarata, stessa che `nqml.screen.overnight.label_overnight_event` gia' fa rispetto al labeler
    condiviso: due sole differenze, entrambe di definizione del setup, non di statistica — (1) il percorso
    e' lo `span` (chiusura RTH -> apertura RTH successiva), non i minuti-NY della stessa giornata; (2) se ne'
    stop ne' target vengono toccati, la chiusura e' all'APERTURA dell'ultima barra dello span, non alla sua
    chiusura."""
    side = row["side"]
    u = up(side)
    entry_ts = pd.Timestamp(row["entry_ts"])
    entry = float(row["entry_price"])
    stop, target = float(row["stop_price"]), float(row["target_price"])
    tick = cfg["instrument"]["tick_size"]
    r_unit = abs(entry - stop)
    target_through = target + u * tick

    def _finish(label: int, exit_reason: str, exit_ts: pd.Timestamp, exit_price: float, minutes_held: float) -> dict:
        pnl_pts = u * (exit_price - entry)
        R = pnl_pts / r_unit if r_unit > 0 else float("nan")
        return dict(label=label, exit_reason=exit_reason, pnl_pts=pnl_pts, r_unit_pts=r_unit,
                    R_gross=R, minutes_held=minutes_held)

    if u * (entry - stop) <= 0 or u * (target - entry) <= 0:
        return _finish(0, "gap", entry_ts, entry, 0.0)
    if len(span) == 0:
        return _finish(0, "no_bars", entry_ts, entry, 0.0)

    for ts, b in span.iterrows():
        hit_stop = b["low"] <= stop if side == "long" else b["high"] >= stop
        hit_target = b["high"] >= target_through if side == "long" else b["low"] <= target_through
        minutes_held = (ts - entry_ts).total_seconds() / 60.0
        if hit_stop:
            return _finish(0, "stop", ts, stop, minutes_held)
        if hit_target:
            return _finish(1, "target", ts, target, minutes_held)

    last_ts, last = span.index[-1], span.iloc[-1]
    minutes_held = (last_ts - entry_ts).total_seconds() / 60.0
    return _finish(0, "time", last_ts, float(last["open"]), minutes_held)


# ---------------------------------------------------------------------------
# Eventi + etichettatura (originale e specchio) per candidato, 1-8
# ---------------------------------------------------------------------------

def _label_both(g: dict, day_rth: pd.DataFrame, cfg: dict) -> tuple[dict, dict]:
    lab = g | r_gross(g, day_rth, cfg)
    mg = mirror_geometry(g)
    mlab = mg | r_gross(mg, day_rth, cfg)
    return lab, mlab


def run_orb(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events, records, records_mirror = [], [], []
    for sd, day in sessions_iter(bars):
        if sd < PERIOD_START:
            continue
        if sd > PERIOD_END:
            break
        n_days_seen += 1
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        if len(day_rth) < min_rth:
            continue
        n_days_valid += 1
        evs = orb.orb_events(day_rth, sd, cfg, minutes=15)
        if not evs:
            continue
        n_days_with_event += 1
        raw_events.extend(evs)
        for ev in evs:
            for g in orb.geometries(ev, cfg):
                g.setdefault("atr", atr_map.get(sd))
                lab, mlab = _label_both(g, day_rth, cfg)
                records.append(lab)
                records_mirror.append(mlab)
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records), df_mirror=pd.DataFrame(records_mirror))


def run_gap(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events, records, records_mirror = [], [], []
    prev_close = None
    for sd, day in sessions_iter(bars):
        if sd > PERIOD_END:
            break
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        in_period = sd >= PERIOD_START
        valid = len(day_rth) >= min_rth
        if in_period:
            n_days_seen += 1
            n_days_valid += int(valid)
            if valid:
                ev = gap.gap_event(day_rth, sd, prev_close, cfg)
                if ev is not None:
                    n_days_with_event += 1
                    raw_events.append(ev)
                    for g in gap.geometries(ev, cfg):
                        g.setdefault("atr", atr_map.get(sd))
                        lab, mlab = _label_both(g, day_rth, cfg)
                        records.append(lab)
                        records_mirror.append(mlab)
        if len(day_rth) > 0:
            prev_close = float(day_rth["close"].iloc[-1])
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records), df_mirror=pd.DataFrame(records_mirror))


def run_firsthour(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events, records, records_mirror = [], [], []
    for sd, day in sessions_iter(bars):
        if sd < PERIOD_START:
            continue
        if sd > PERIOD_END:
            break
        n_days_seen += 1
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        if len(day_rth) < min_rth:
            continue
        n_days_valid += 1
        evs = firsthour.firsthour_events(day_rth, sd, cfg)
        if not evs:
            continue
        n_days_with_event += 1
        raw_events.extend(evs)
        for ev in evs:
            for g in firsthour.geometries(ev, cfg):
                g.setdefault("atr", atr_map.get(sd))
                lab, mlab = _label_both(g, day_rth, cfg)
                records.append(lab)
                records_mirror.append(mlab)
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records), df_mirror=pd.DataFrame(records_mirror))


def run_vabreak(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events, records, records_mirror = [], [], []
    for sd, day in sessions_iter(bars):
        if sd < PERIOD_START:
            continue
        if sd > PERIOD_END:
            break
        n_days_seen += 1
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        if len(day_rth) < min_rth:
            continue
        n_days_valid += 1
        evs = vabreak.vabreak_events(day, sd, cfg)
        if not evs:
            continue
        n_days_with_event += 1
        raw_events.extend(evs)
        for ev in evs:
            for g in vabreak.geometries(ev, cfg):
                g.setdefault("atr", atr_map.get(sd))
                lab, mlab = _label_both(g, day_rth, cfg)
                records.append(lab)
                records_mirror.append(mlab)
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records), df_mirror=pd.DataFrame(records_mirror))


def run_vwap(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events, records, records_mirror = [], [], []
    for sd, day in sessions_iter(bars):
        if sd < PERIOD_START:
            continue
        if sd > PERIOD_END:
            break
        n_days_seen += 1
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        if len(day_rth) < min_rth:
            continue
        n_days_valid += 1
        evs = vwap.vwap_events(day_rth, sd, cfg, atr_map.get(sd))
        if not evs:
            continue
        n_days_with_event += 1
        raw_events.extend(evs)
        for ev in evs:
            for g in vwap.geometries(ev, cfg):
                lab, mlab = _label_both(g, day_rth, cfg)
                records.append(lab)
                records_mirror.append(mlab)
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records), df_mirror=pd.DataFrame(records_mirror))


def run_lasthour(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events, records, records_mirror = [], [], []
    for sd, day in sessions_iter(bars):
        if sd < PERIOD_START:
            continue
        if sd > PERIOD_END:
            break
        n_days_seen += 1
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        if len(day_rth) < min_rth:
            continue
        n_days_valid += 1
        ev = lasthour.lasthour_event(day_rth, sd, cfg, atr_map.get(sd))
        if ev is None:
            continue
        n_days_with_event += 1
        raw_events.append(ev)
        for g in lasthour.geometries(ev, cfg):
            lab, mlab = _label_both(g, day_rth, cfg)
            records.append(lab)
            records_mirror.append(mlab)
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records), df_mirror=pd.DataFrame(records_mirror))


def run_prevva(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events, records, records_mirror = [], [], []
    prev_day_rth = None
    for sd, day in sessions_iter(bars):
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        valid = len(day_rth) >= min_rth
        if PERIOD_START <= sd <= PERIOD_END:
            n_days_seen += 1
            if valid:
                n_days_valid += 1
                va_prec = prevva.prev_day_value_area(prev_day_rth, cfg) if prev_day_rth is not None else None
                evs = prevva.prevva_events(day_rth, sd, cfg, va_prec)
                if evs:
                    n_days_with_event += 1
                    raw_events.extend(evs)
                    for ev in evs:
                        for g in prevva.geometries(ev, cfg):
                            g.setdefault("atr", atr_map.get(sd))
                            lab, mlab = _label_both(g, day_rth, cfg)
                            records.append(lab)
                            records_mirror.append(mlab)
        if sd > PERIOD_END:
            break
        if valid:
            prev_day_rth = day_rth
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records), df_mirror=pd.DataFrame(records_mirror))


def run_overnight(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_dropped_boundary = 0
    raw_events, records, records_mirror = [], [], []
    prev_sd = prev_rth = prev_full = None
    prev_valid = False
    for sd, day in sessions_iter(bars):
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        valid = len(day_rth) >= min_rth
        if prev_sd is not None and prev_valid and PERIOD_START <= prev_sd <= PERIOD_END:
            n_days_seen += 1
            if sd >= BOUNDARY:
                n_dropped_boundary += 1
            elif valid:
                n_days_valid += 1
                ev = overnight.overnight_event(prev_rth, prev_sd, day_rth, sd, cfg, atr_map.get(prev_sd))
                if ev is not None:
                    raw_events.append(ev)
                    span = overnight.overnight_span(prev_full, ev["entry_ts"], day, ev["next_open_ts"])
                    for g in overnight.geometries(ev, cfg):
                        lab = g | r_gross_overnight(g, span, cfg)
                        mg = mirror_geometry(g)
                        mlab = mg | r_gross_overnight(mg, span, cfg)
                        records.append(lab)
                        records_mirror.append(mlab)
        prev_sd, prev_rth, prev_full, prev_valid = sd, day_rth, day, valid
        if prev_sd > PERIOD_END:
            break
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_dropped_boundary=n_dropped_boundary,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records), df_mirror=pd.DataFrame(records_mirror))


def build_day_rth_cache(bars: pd.DataFrame, cfg: dict, start: dt.date, end: dt.date) -> dict:
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    min_rth = cfg["sessions"]["min_rth_bars"]
    cache = {}
    for sd, day in sessions_iter(bars):
        if sd < start:
            continue
        if sd > end:
            break
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        if len(day_rth) >= min_rth:
            cache[sd] = day_rth
    return cache


def run_candidate0(cfg: dict, atr_map: dict, day_rth_cache: dict) -> dict:
    """Candidato 0 — setup value-area originale (rientro), da `data/events/events.parquet`: unica geometria
    gia' fissata dal detector (nessun k), piu' 5 strati di rr (quintili sul training, dichiarati esplorativi,
    spec v2 §2)."""
    raw = pd.read_parquet(EVENTS0_PATH)
    raw["session_date"] = pd.to_datetime(raw["session_date"]).dt.date
    raw = raw[(raw["session_date"] >= PERIOD_START) & (raw["session_date"] <= PERIOD_END)].copy()

    # Guardia difensiva (stessa convenzione di orb/gap/firsthour/.../geometries(): "salta una geometria se
    # |entry_ref - stop| <= 0"): un solo evento del detector originale ha entry_price == stop_price
    # (20170410-DEV-short-0940, precisione del tick), r_unit = 0 -> rr = inf, R_gross non definito. Scartato
    # qui prima dei quintili, non nella statistica: non e' una scelta di geometria, e' un artefatto di dato.
    denom = (raw["entry_price"] - raw["stop_price"]).abs()
    n_zero_denom = int((denom <= 0).sum())
    raw = raw[denom > 0].copy()

    raw["rr_ratio"] = (raw["target_price"] - raw["entry_price"]).abs() / (raw["entry_price"] - raw["stop_price"]).abs()
    raw["atr"] = raw["session_date"].map(atr_map)
    raw["geom"] = "value_area"

    records, records_mirror = [], []
    n_skipped_no_day = 0
    for row in raw.to_dict("records"):
        day_rth = day_rth_cache.get(row["session_date"])
        if day_rth is None or len(day_rth) == 0:
            n_skipped_no_day += 1
            continue
        records.append(row | r_gross(row, day_rth, cfg))
        mrow = mirror_geometry(row)
        records_mirror.append(mrow | r_gross(mrow, day_rth, cfg))

    df = pd.DataFrame(records)
    df_mirror = pd.DataFrame(records_mirror)

    quint, edges = pd.qcut(df["rr_ratio"], 5, duplicates="drop", retbins=True)
    n_bins = len(edges) - 1
    labels = [f"Q{i + 1}" for i in range(n_bins)]
    quint = pd.qcut(df["rr_ratio"], 5, duplicates="drop", labels=labels)
    df["rr_quintile"] = quint.astype(str)
    df_mirror["rr_quintile"] = quint.astype(str).to_numpy()

    return dict(ev_df=raw, df=df, df_mirror=df_mirror, rr_edges=edges, n_bins=n_bins,
                n_skipped_no_day=n_skipped_no_day, n_zero_denom=n_zero_denom)


# ---------------------------------------------------------------------------
# Statistica per singola riga (geometria o strato): primaria, co-primaria, specchio, unita'
# ---------------------------------------------------------------------------

def compute_stats(sub: pd.DataFrame, sub_mirror: pd.DataFrame, cfg: dict, null_kind: str,
                   drift_series: pd.Series | None, bn: int, bs: int) -> dict:
    n = len(sub)
    u = units(sub, cfg)
    um = units(sub_mirror, cfg)

    if null_kind == "wald":
        u = u.assign(_null=wald_null(u, drift_series))
        um = um.assign(_null=wald_null(um, drift_series))
        null_col = "_null"
    else:
        null_col = None

    ev_lordo = ev_test(u, "R_gross", null_col, bn, bs, ALPHA_CI)
    ev_netto = ev_test(u, "R_net", None, bn, bs, ALPHA_CI)
    ev_lordo_mirror = ev_test(um, "R_gross", null_col, bn, bs, ALPHA_CI)
    mirror = mirror_stats(ev_lordo, ev_lordo_mirror, bn, bs, ALPHA_CI)

    r_net_mean = float(u["R_net"].mean())
    usd_net_mean = float(u["usd_net"].mean())
    atr_col = u["atr_units_net"].dropna()
    atr_net_mean = float(atr_col.mean()) if len(atr_col) > 0 else float("nan")
    signs = [np.sign(x) for x in (r_net_mean, usd_net_mean, atr_net_mean) if not np.isnan(x)]
    sign_agree = (len(signs) == 3) and (len({s for s in signs}) == 1) and (signs[0] != 0)

    return dict(n=n, ev_lordo=ev_lordo, ev_netto=ev_netto, mirror=mirror,
                r_net_mean=r_net_mean, usd_net_mean=usd_net_mean, atr_net_mean=atr_net_mean,
                sign_agree=sign_agree)


def bh_thresholds(pvalues: list[float], q: float) -> list[float]:
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    thr = [0.0] * m
    for rank, idx in enumerate(order, start=1):
        thr[idx] = q * rank / m
    return thr


def fmt_ci(ci: tuple[float, float]) -> str:
    return f"[{ci[0]:+.4f}, {ci[1]:+.4f}]"


def pf(ok: bool) -> str:
    return "SI" if ok else "NO"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    t0 = time.time()
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    print(f"barre {len(bars)}, caricate in {time.time()-t0:.0f}s")
    bn, bs = cfg["backtest"]["bootstrap_n"], cfg["backtest"]["bootstrap_seed"]

    print("ATR(14) del giorno precedente ...")
    t1 = time.time()
    atr_map = previous_day_atr(bars, cfg)
    print(f"  {len(atr_map)} giorni con ATR precedente noto, {time.time()-t1:.0f}s")

    print("deriva trailing (252 sessioni) RTH e overnight ...")
    t1 = time.time()
    drift_rth = segment_drift(bars, "rth", window=252)
    drift_overnight = segment_drift(bars, "overnight", window=252)
    print(f"  {time.time()-t1:.0f}s")

    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[int, dict] = {}
    stats: dict[int, list[dict]] = {}

    def finish_candidate(cid: int, res: dict, drift_series: pd.Series | None) -> None:
        name, label, order, null_kind = CANDIDATE_META[cid]
        rows = []
        for geom in order:
            sub = res["df"][res["df"]["geom"] == geom]
            sub_m = res["df_mirror"][res["df_mirror"]["geom"] == geom]
            assert len(sub) > 0, f"candidato {cid} ({name}): geometria {geom} senza eventi"
            st = compute_stats(sub, sub_m, cfg, null_kind, drift_series, bn, bs)
            rows.append(dict(candidate=cid, name=name, label=label, geom=geom) | st)
        stats[cid] = rows
        results[cid] = res
        # salvataggio parziale (sicurezza per run lunghi): una riga per test di questo candidato
        part = pd.DataFrame([_flatten(r) for r in rows])
        part.to_parquet(SCREEN_DIR / f"v2_partial_{name}.parquet", index=False)
        print(f"  candidato {cid} ({label}): {len(order)} geometrie misurate, salvate in v2_partial_{name}.parquet")

    print("candidato 1 (ORB15) ...")
    t1 = time.time()
    res = run_orb(bars, cfg, atr_map)
    print(f"  giorni {res['n_days_seen']} (validi {res['n_days_valid']}, con evento {res['n_days_with_event']}), "
          f"eventi {len(res['ev_df'])}, {time.time()-t1:.0f}s")
    assert_no_vault(res["ev_df"], cfg)
    finish_candidate(1, res, None)

    print("candidato 2 (gap) ...")
    t1 = time.time()
    res = run_gap(bars, cfg, atr_map)
    print(f"  giorni {res['n_days_seen']} (validi {res['n_days_valid']}, con evento {res['n_days_with_event']}), "
          f"eventi {len(res['ev_df'])}, {time.time()-t1:.0f}s")
    assert_no_vault(res["ev_df"], cfg)
    finish_candidate(2, res, None)

    print("candidato 3 (prima ora) ...")
    t1 = time.time()
    res = run_firsthour(bars, cfg, atr_map)
    print(f"  giorni {res['n_days_seen']} (validi {res['n_days_valid']}, con evento {res['n_days_with_event']}), "
          f"eventi {len(res['ev_df'])}, {time.time()-t1:.0f}s")
    assert_no_vault(res["ev_df"], cfg)
    finish_candidate(3, res, None)

    print("candidato 4 (prosecuzione VA) ...")
    t1 = time.time()
    res = run_vabreak(bars, cfg, atr_map)
    print(f"  giorni {res['n_days_seen']} (validi {res['n_days_valid']}, con evento {res['n_days_with_event']}), "
          f"eventi {len(res['ev_df'])}, {time.time()-t1:.0f}s")
    assert_no_vault(res["ev_df"], cfg)
    finish_candidate(4, res, None)

    print("candidato 5 (VWAP) ...")
    t1 = time.time()
    res = run_vwap(bars, cfg, atr_map)
    print(f"  giorni {res['n_days_seen']} (validi {res['n_days_valid']}, con evento {res['n_days_with_event']}), "
          f"eventi {len(res['ev_df'])}, {time.time()-t1:.0f}s")
    assert_no_vault(res["ev_df"], cfg)
    finish_candidate(5, res, None)

    print("candidato 6 (overnight) ...")
    t1 = time.time()
    res = run_overnight(bars, cfg, atr_map)
    print(f"  giorni {res['n_days_seen']} (validi {res['n_days_valid']}, scartati confine {res['n_dropped_boundary']}), "
          f"eventi {len(res['ev_df'])}, {time.time()-t1:.0f}s")
    assert_no_vault(res["ev_df"], cfg)
    assert (pd.to_datetime(res["ev_df"]["next_open_ts"]).dt.date < BOUNDARY).all(), \
        "un evento overnight scartato per il confine di periodo e' comunque entrato nella tabella"
    finish_candidate(6, res, drift_overnight)

    print("candidato 7 (ultima ora) ...")
    t1 = time.time()
    res = run_lasthour(bars, cfg, atr_map)
    print(f"  giorni {res['n_days_seen']} (validi {res['n_days_valid']}, con evento {res['n_days_with_event']}), "
          f"eventi {len(res['ev_df'])}, {time.time()-t1:.0f}s")
    assert_no_vault(res["ev_df"], cfg)
    finish_candidate(7, res, drift_rth)

    print("candidato 8 (apertura fuori VA) ...")
    t1 = time.time()
    res = run_prevva(bars, cfg, atr_map)
    print(f"  giorni {res['n_days_seen']} (validi {res['n_days_valid']}, con evento {res['n_days_with_event']}), "
          f"eventi {len(res['ev_df'])}, {time.time()-t1:.0f}s")
    assert_no_vault(res["ev_df"], cfg)
    finish_candidate(8, res, None)

    print("candidato 0 (setup value-area originale + 5 strati rr) ...")
    t1 = time.time()
    day_rth_cache = build_day_rth_cache(bars, cfg, PERIOD_START, PERIOD_END)
    res0 = run_candidate0(cfg, atr_map, day_rth_cache)
    print(f"  eventi nel periodo {len(res0['ev_df']) + res0['n_zero_denom']} "
          f"(scartati per r_unit=0: {res0['n_zero_denom']}; etichettati {len(res0['df'])}, "
          f"scartati senza giorno RTH noto {res0['n_skipped_no_day']}), quintili {res0['n_bins']}, "
          f"{time.time()-t1:.0f}s")
    assert res0["n_bins"] == 5, f"quintili di rr degeneri: attesi 5 strati, ottenuti {res0['n_bins']}"
    assert_no_vault(res0["ev_df"], cfg)
    stats[0] = []
    order0 = ["complessiva"] + [f"rr_Q{i+1}" for i in range(res0["n_bins"])]
    for geom in order0:
        if geom == "complessiva":
            sub, sub_m = res0["df"], res0["df_mirror"]
        else:
            q = geom.split("_")[1]
            sub = res0["df"][res0["df"]["rr_quintile"] == q]
            sub_m = res0["df_mirror"][res0["df_mirror"]["rr_quintile"] == q]
        assert len(sub) > 0, f"candidato 0: strato {geom} senza eventi"
        st = compute_stats(sub, sub_m, cfg, "zero", None, bn, bs)
        stats[0].append(dict(candidate=0, name="value_area", label=CANDIDATE_META[0][1], geom=geom) | st)
    part0 = pd.DataFrame([_flatten(r) for r in stats[0]])
    part0.to_parquet(SCREEN_DIR / "v2_partial_value_area.parquet", index=False)
    results[0] = res0
    print(f"  candidato 0: {len(order0)} righe misurate, salvate in v2_partial_value_area.parquet")

    # -----------------------------------------------------------------------------------------------
    # Famiglia BH unica sui 58 test (ordine: candidati 1..8 poi 0, spec §2)
    # -----------------------------------------------------------------------------------------------
    all_rows: list[dict] = []
    for cid in (1, 2, 3, 4, 5, 6, 7, 8, 0):
        all_rows.extend(stats[cid])
    assert len(all_rows) == 58, f"attesi 58 test, trovati {len(all_rows)}"

    pvalues = [r["ev_lordo"]["p_one_sided"] for r in all_rows]
    discoveries = benjamini_hochberg(pvalues, Q_BH)
    thresholds = bh_thresholds(pvalues, Q_BH)
    for r, disc, thr in zip(all_rows, discoveries, thresholds):
        r["bh_threshold"] = thr
        r["bh_discovery"] = disc
        r["exploratory"] = (r["candidate"] == 0 and r["geom"] != "complessiva")
        r["P"] = bool(disc and r["ev_lordo"]["point"] > 0)
        r["N"] = bool(r["n"] >= 500)
        if r["P"]:
            r["E"] = bool(r["ev_netto"]["ci"][0] > 0)
            r["S"] = bool(r["mirror"]["drift"] > 0 and abs(r["mirror"]["micro"]) < abs(r["mirror"]["drift"]))
        else:
            r["E"] = r["S"] = None

    # -----------------------------------------------------------------------------------------------
    # Matrice di sovrapposizione: copiata letteralmente da reports/screen_batch2.md (spec §2, gia'
    # misurata li'; non ricalcolata qui)
    # -----------------------------------------------------------------------------------------------
    overlap_text = _extract_overlap_section(Path(cfg["backtest"]["reports_dir"]) / "screen_batch2.md")

    # -----------------------------------------------------------------------------------------------
    # data/screen/v2_results.parquet — una riga per test, tutti i numeri
    # -----------------------------------------------------------------------------------------------
    results_df = pd.DataFrame([_flatten(r) for r in all_rows])
    results_df.to_parquet(SCREEN_DIR / "v2_results.parquet", index=False)
    print(f"scritto {SCREEN_DIR / 'v2_results.parquet'} ({len(results_df)} righe)")

    # -----------------------------------------------------------------------------------------------
    # Report
    # -----------------------------------------------------------------------------------------------
    md = render_report(cfg, all_rows, bn, bs, overlap_text, results)
    out_dir = Path(cfg["backtest"]["reports_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "screen_v2.md"
    out.write_text(md, encoding="utf-8")
    print(f"scritto {out} in {time.time()-t0:.0f}s totali")
    n_disc = sum(1 for r in all_rows if r["bh_discovery"])
    n_p = sum(1 for r in all_rows if r["P"])
    print(f"{n_disc} scoperte BH su 58 test; {n_p} soddisfano P (scoperta + segno positivo)")
    return 0


def _flatten(r: dict) -> dict:
    el, en, mi = r["ev_lordo"], r["ev_netto"], r["mirror"]
    return dict(
        candidate=r["candidate"], name=r["name"], geom=r["geom"], n=r["n"],
        ev_lordo_point=el["point"], ev_lordo_ci_lo=el["ci"][0], ev_lordo_ci_hi=el["ci"][1],
        ev_lordo_p=el["p_one_sided"],
        ev_netto_point=en["point"], ev_netto_ci_lo=en["ci"][0], ev_netto_ci_hi=en["ci"][1],
        micro=mi["micro"], micro_ci_lo=mi["ci_micro"][0], micro_ci_hi=mi["ci_micro"][1],
        drift=mi["drift"], drift_ci_lo=mi["ci_drift"][0], drift_ci_hi=mi["ci_drift"][1],
        r_net_mean=r["r_net_mean"], usd_net_mean=r["usd_net_mean"], atr_net_mean=r["atr_net_mean"],
        sign_agree=r["sign_agree"],
        bh_threshold=r.get("bh_threshold"), bh_discovery=r.get("bh_discovery"),
        exploratory=r.get("exploratory"), P=r.get("P"), E=r.get("E"), S=r.get("S"), N=r.get("N"),
    )


def _extract_overlap_section(path: Path) -> list[str]:
    if not path.exists():
        return ["*(reports/screen_batch2.md non trovato: matrice non copiata)*"]
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("## Matrice di sovrapposizione")), None)
    if start is None:
        return ["*(sezione 'Matrice di sovrapposizione' non trovata in screen_batch2.md)*"]
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


# ---------------------------------------------------------------------------
# Rendering del report (italiano)
# ---------------------------------------------------------------------------

CANDIDATE_DESC = {
    1: "Rottura dell'opening range di 15 minuti (candidato 1). 8 geometrie (2 stop x 4 target). Nullo 0 "
       "(simmetrico).",
    2: "|gap RTH| >= 2 punti; F (chiusura del gap) e P (prosecuzione), speculari, 3 k ciascuna (candidato 2). "
       "6 geometrie. Nullo 0 (simmetrico). **Condivide il 98,1% dei suoi eventi con la famiglia R del "
       "candidato 8** (vedi matrice di sovrapposizione sotto): non sono due prove indipendenti.",
    3: "FHH/FHL sulle 60 barre 1m 09:30-10:29:59 ET, rottura dalle 10:30 (candidato 3). 8 geometrie (2 stop x "
       "4 target). Nullo 0 (simmetrico).",
    4: "Prima transizione INSIDE->BROKEN per (tipo di VA x lato), evento alla rottura indipendentemente dal "
       "rientro (candidato 4). 8 geometrie (2 stop x 4 target). Nullo 0 (simmetrico).",
    5: "Ritorno alla media, segnale a 2 sigma dal VWAP di sessione dalle 10:00 ET (candidato 5). 6 geometrie "
       "(2 target x 3 stop in ATR). Nullo 0 (simmetrico).",
    6: "Long alla chiusura RTH, uscita all'apertura RTH successiva, nessuna condizione (candidato 6). 4 "
       "geometrie (2 stop x 2 target in ATR). **Nullo con deriva** (identita' di Wald, mu-hat trailing 252 "
       "sessioni del segmento overnight): unico candidato interamente long, il nullo a zero sarebbe banale da "
       "battere su un indice in salita nel training.",
    7: "Alle 15:00 ET, nella direzione della sessione rispetto all'apertura RTH (candidato 7). 4 geometrie (2 "
       "stop x 2 target in ATR). **Nullo con deriva** (identita' di Wald, mu-hat trailing 252 sessioni del "
       "segmento RTH): il lato del trade e' correlato all'andamento della sessione, quindi il nullo a zero "
       "non e' neutro.",
    8: "Apertura RTH fuori dalla value area (70%) della sessione precedente; famiglie R (ritorno) e C "
       "(continuazione) (candidato 8). 8 geometrie (2 famiglie x 4 k). Nullo 0 (simmetrico). **La famiglia R "
       "condivide il 98,1% dei suoi eventi con il candidato 2 (gap)**: vedi matrice di sovrapposizione sotto.",
    0: "Setup value-area originale (rientro nella value area dopo la rottura), `data/events/events.parquet`. "
       "Una sola geometria (gia' fissata dal detector) + 5 strati di rr (quintili calcolati sugli eventi del "
       "training). Nullo 0 (simmetrico). Un evento (20170410-DEV-short-0940) ha `entry_price == stop_price` "
       "(r_unit = 0, artefatto del detector originale, non una scelta di geometria): scartato prima dei "
       "quintili, stessa convenzione «salta se |entry_ref - stop| <= 0» gia' usata dai candidati 1-8. "
       "**Gli strati di rr sono esplorativi**: nascono dall'aver guardato il training e non possono "
       "autorizzare nulla da soli, anche se il BH li segna come scoperta.",
}


def render_candidate_table(rows: list[dict]) -> list[str]:
    L = ["| geometria | n | EV_lordo | CI 95% | p | soglia BH | scoperta | EV_netto | CI 95% | segno R/$/ATR "
         "concorde | micro | deriva | P | E | S | N |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        el, en, mi = r["ev_lordo"], r["ev_netto"], r["mirror"]
        excl = " *(esplorativo)*" if r.get("exploratory") else ""
        e_str = pf(r["E"]) if r["E"] is not None else "—"
        s_str = pf(r["S"]) if r["S"] is not None else "—"
        L.append(
            f"| {r['geom']}{excl} | {r['n']} | {el['point']:+.4f} | {fmt_ci(el['ci'])} | "
            f"{el['p_one_sided']:.4f} | {r['bh_threshold']:.4f} | {pf(r['bh_discovery'])} | "
            f"{en['point']:+.4f} | {fmt_ci(en['ci'])} | {pf(r['sign_agree'])} | "
            f"{mi['micro']:+.4f} {fmt_ci(mi['ci_micro'])} | {mi['drift']:+.4f} {fmt_ci(mi['ci_drift'])} | "
            f"{pf(r['P'])} | {e_str} | {s_str} | {pf(r['N'])} |"
        )
    return L


def render_outcome_tree(cid: int, rows: list[dict]) -> list[str]:
    """Albero degli esiti (spec §3), applicato verbatim geometria per geometria, poi aggregato per
    candidato: nessuna scoperta P -> chiuso; P si' E no -> reale non tradabile; P si' E si' S si' ->
    candidato proposto (solo se e' anche il migliore dell'intera famiglia, deciso a valle); P si' E si' S
    no -> microstruttura simmetrica, registrato non proposto."""
    real_rows = [r for r in rows if not r.get("exploratory")]
    p_rows = [r for r in real_rows if r["P"]]
    if not p_rows:
        return ["**Nessuna geometria supera P (scoperta BH + segno positivo)** → per questo candidato il "
                "filone si chiude qui: nessuna geometria autorizza nulla."]
    L = [f"**{len(p_rows)} geometria/e superano P** su {len(real_rows)} non esplorative:"]
    for r in p_rows:
        el, en = r["ev_lordo"], r["ev_netto"]
        if not r["E"]:
            L.append(f"- `{r['geom']}`: P sì, E no → «effetto reale non tradabile a questi costi» "
                      f"(EV_lordo {el['point']:+.4f} {fmt_ci(el['ci'])}, EV_netto {en['point']:+.4f} "
                      f"{fmt_ci(en['ci'])} include 0). Si registra, non si apre nulla.")
        elif r["S"]:
            L.append(f"- `{r['geom']}`: P sì, E sì, S sì → effetto direzionale (non microstruttura); "
                      f"EV_netto {en['point']:+.4f} {fmt_ci(en['ci'])}, segno R/$/ATR "
                      f"{'concorde' if r['sign_agree'] else 'NON concorde'}. Candidato al singolo test di "
                      "replica OOS (§4), soggetto al confronto con tutti gli altri candidati P/E/S.")
        else:
            L.append(f"- `{r['geom']}`: P sì, E sì, S no → effetto simmetrico di microstruttura "
                      f"(i costi lo mangiano per costruzione); EV_netto {en['point']:+.4f} "
                      f"{fmt_ci(en['ci'])}. Si registra come tale, non si propone.")
    return L


def render_report(cfg: dict, all_rows: list[dict], bn: int, bs: int, overlap_lines: list[str],
                   results: dict) -> str:
    L: list[str] = []
    L.append("# Screening v2 — rifacimento integrale con lo strumento corretto")
    L.append("")
    L.append(f"Generato {dt.datetime.now():%Y-%m-%d %H:%M} · config `{config_hash()}` · commit `{git_commit()}`")
    L.append("")
    L.append("Pre-registrazione: `docs/superpowers/specs/2026-09-23-screening-v2-rifacimento.md`. Periodo di "
              f"screening: {PERIOD_START} → {PERIOD_END} (anni di training del progetto). L'OOS di lavoro "
              "(2023-10-02 → 2026-03-19) e la cassaforte (2026-03-20 → 2026-09-19) non sono stati toccati. "
              "Statistica primaria: `EV_lordo = media(R_lordo - nullo)`, R_lordo mark-to-market (target a "
              "trade-through di 1 tick, stop al tocco, time-stop 15:55 ET — apertura RTH successiva per il "
              "solo candidato 6 — nessun costo), CI a blocchi per giorno "
              f"({bn:,} ricampionamenti, seed {bs}), p a **una coda**. Nullo 0 per i candidati simmetrici "
              "(1-5, 8, 0); nullo con deriva (identita' di Wald, mu-hat trailing 252 sessioni) per i "
              "candidati direzionali (6, 7). Co-primaria: `EV_netto = media(R_netto)` dopo commissioni "
              "($2,50/lato) e slippage (1 tick/lato su ingresso e uscite a mercato). Specchio obbligatorio "
              "per ogni geometria (stesso ingresso, lato opposto, stesse distanze). Robustezza di unita': "
              "segno del netto in R, in $ per contratto e in unita' ATR, tutti e tre concordi. "
              "**Molteplicita': Benjamini-Hochberg, q = 0,10, sull'intera famiglia di 58 test** (non per "
              "lotto).")
    L.append("")

    for cid in (1, 2, 3, 4, 5, 6, 7, 8, 0):
        name, label, order, null_kind = CANDIDATE_META[cid]
        rows = [r for r in all_rows if r["candidate"] == cid]
        L.append(f"## Candidato {cid} — {label}")
        L.append("")
        L.append(CANDIDATE_DESC[cid])
        L.append("")
        L.extend(render_candidate_table(rows))
        L.append("")
        L.append("### Esito (albero pre-registrato, spec §3)")
        L.append("")
        L.extend(render_outcome_tree(cid, rows))
        L.append("")

    # --- Sintesi: tutti i 58 test, ordinati per p ---------------------------------------------------
    L.append("## Sintesi — tutti i 58 test, ordinati per p (BH q = 0,10 sull'intera famiglia)")
    L.append("")
    L.append("| candidato | geometria | n | p | soglia BH | scoperta | EV_lordo | EV_netto | P | E | S | N |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    ordered = sorted(all_rows, key=lambda r: r["ev_lordo"]["p_one_sided"])
    for r in ordered:
        el, en = r["ev_lordo"], r["ev_netto"]
        excl = " *(espl.)*" if r.get("exploratory") else ""
        e_str = pf(r["E"]) if r["E"] is not None else "—"
        s_str = pf(r["S"]) if r["S"] is not None else "—"
        L.append(f"| {CANDIDATE_META[r['candidate']][1]} | {r['geom']}{excl} | {r['n']} | "
                  f"{el['p_one_sided']:.4f} | {r['bh_threshold']:.4f} | {pf(r['bh_discovery'])} | "
                  f"{el['point']:+.4f} | {en['point']:+.4f} | {pf(r['P'])} | {e_str} | {s_str} | "
                  f"{pf(r['N'])} |")
    L.append("")
    n_disc = sum(1 for r in all_rows if r["bh_discovery"])
    n_p = sum(1 for r in all_rows if r["P"])
    L.append(f"**{n_disc} scoperta/e BH su 58 test** al livello q = {Q_BH:.2f}; **{n_p} soddisfano anche P** "
              "(scoperta con segno positivo — identico a scoperta, dato che il test e' a una coda solo "
              "positiva).")
    L.append("")

    # --- Esito complessivo del filone (albero, spec §3) ---------------------------------------------
    L.append("## Esito complessivo del filone")
    L.append("")
    real_p = [r for r in all_rows if r["P"] and not r.get("exploratory")]
    if not real_p:
        L.append("**Nessuna scoperta P su tutta la famiglia (esclusi gli strati esplorativi del candidato "
                  "0)** → il filone screening si **chiude**; la conclusione e' quella gia' scritta in §4 "
                  "della spec `docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`.")
        expl_p = [r for r in all_rows if r["P"] and r.get("exploratory")]
        if expl_p:
            names = ", ".join(f"{r['name']}/{r['geom']}" for r in expl_p)
            L.append("")
            L.append(f"Nota: {len(expl_p)} strato/i esplorativo/i del candidato 0 supererebbero P da soli "
                      f"({names}) ma sono dichiarati esplorativi (spec v2 §2) e **non possono autorizzare "
                      "nulla**: nascono dall'aver guardato il training.")
    else:
        pes = [r for r in real_p if r["E"] and r["S"]]
        pe_not_s = [r for r in real_p if r["E"] and not r["S"]]
        p_not_e = [r for r in real_p if not r["E"]]
        if pes:
            best = max(pes, key=lambda r: r["ev_netto"]["point"])
            L.append(f"**{len(pes)} geometria/e passano P, E e S.** Per la regola pre-registrata (spec §3), "
                      f"**un solo candidato — quello con EV_netto più alto — è proposto all'utente per "
                      f"l'unico test di replica sull'OOS vergine (disegno di §4)**: "
                      f"**{CANDIDATE_META[best['candidate']][1]} / {best['geom']}** "
                      f"(EV_netto {best['ev_netto']['point']:+.4f} {fmt_ci(best['ev_netto']['ci'])}, "
                      f"EV_lordo {best['ev_lordo']['point']:+.4f} {fmt_ci(best['ev_lordo']['ci'])}, "
                      f"n = {best['n']}, segno R/$/ATR {'concorde' if best['sign_agree'] else 'NON concorde'}). "
                      "**Nessuna esecuzione OOS senza approvazione esplicita dell'utente.**")
        if pe_not_s:
            names = ", ".join(f"{CANDIDATE_META[r['candidate']][1]}/{r['geom']}" for r in pe_not_s)
            L.append(f"- {len(pe_not_s)} geometria/e P+E ma non S (microstruttura simmetrica, non "
                      f"direzionale): {names}. Registrate come tali, non proposte.")
        if p_not_e:
            names = ", ".join(f"{CANDIDATE_META[r['candidate']][1]}/{r['geom']}" for r in p_not_e)
            L.append(f"- {len(p_not_e)} geometria/e P ma non E («effetto reale non tradabile a questi "
                      f"costi»): {names}. Si registrano, non si apre nulla; ridiscutibili solo se cambiano i "
                      "costi di esecuzione.")
    L.append("")

    # --- Matrice di sovrapposizione, copiata da screen_batch2.md ------------------------------------
    L.append("## Matrice di sovrapposizione fra i setup (copiata da `reports/screen_batch2.md`)")
    L.append("")
    L.append("Citata per intero perche' rilevante alle righe gap (candidato 2) e prevva/R (candidato 8), che "
              "condividono il 98,1% degli eventi (spec v2 §0.3): non sono due prove indipendenti, anche se "
              "contano separatamente nella famiglia BH.")
    L.append("")
    L.extend(overlap_lines)
    L.append("")

    # --- Come leggere --------------------------------------------------------------------------------
    L.append("## Come leggere questa tabella")
    L.append("")
    L.append("`EV_lordo` è la media per evento di `R_lordo - nullo` (nullo 0 per i simmetrici, nullo con "
              "deriva per overnight e ultima ora), con CI a blocchi per giorno; `p` è a una coda (solo "
              "positivo). `soglia BH` è la soglia assegnata al rango di quel test nell'ordinamento crescente "
              "dei p-value dell'intera famiglia di 58 (non alla sua posizione naturale nella tabella): una "
              "geometria è **scoperta** se `p` ≤ soglia BH. `EV_netto` è la media di `R_netto` dopo costi "
              "(commissione + slippage), criterio E: CI 95% che esclude 0 ed è positiva. `micro` e `deriva` "
              "sono il test dello specchio: `micro = (EV_orig+EV_specchio)/2`, `deriva = "
              "(EV_orig-EV_specchio)/2`; criterio S: deriva positiva e |micro| < |deriva| (effetto "
              "direzionale, non microstruttura). Il segno R/$/ATR concorde è il criterio di robustezza di "
              "unità: la scoperta è valida solo se il segno del netto è lo stesso in tutte e tre le unità. "
              "P/E/S/N sono i quattro criteri della spec §3: solo P**+**E**+**S insieme, sulla geometria con "
              "EV_netto più alto fra tutte quelle che li passano, autorizzano la proposta di un test di "
              "replica sull'OOS vergine — mai eseguito senza approvazione esplicita dell'utente. Gli strati "
              "di rr del candidato 0 sono **esplorativi**: anche se il BH li segna come scoperta, non possono "
              "autorizzare nulla da soli (nascono dall'aver guardato il training). «—» in E/S significa che "
              "il criterio non è stato valutato perché la geometria non supera P.")
    L.append("")

    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
