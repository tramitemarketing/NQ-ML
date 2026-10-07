"""PASSO 1 — B2 e' un doppione di un candidato gia' schermato?

Solo definizioni ed eventi: **nessun rendimento viene calcolato o letto in questo script**.

Per ogni candidato gia' schermato si misurano due quote, in entrambe le direzioni:
  - STESSO LATO:  quota di eventi di A che hanno un evento di B stesso giorno, stesso lato, entro 15 minuti;
  - LATO OPPOSTO: idem, dopo aver rovesciato il lato di B.
La finestra e la definizione sono quelle gia' in uso nel progetto (`nqml.screen.overlap.overlap_share`,
spec candidati-5-8 §2). Si riportano entrambe le direzioni perche' la sovrapposizione non e' simmetrica:
B2 ha molti piu' eventi (entra a ogni barra 5m in cui una macchina e' BROKEN), quindi «quanti B2 sono
coperti da X» e «quanti X sono coperti da B2» rispondono a domande diverse.

Uso: .venv\\Scripts\\python scripts\\33_passo1_doppione.py
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from nqml.config import config_hash, git_commit, load_config
from nqml.data.bars import five_min_bin, load_bars, resample_5m, rth_bars, sessions_iter
from nqml.detector.events import Bar5m
from nqml.detector.run_day import entry_allowed
from nqml.detector.state_machine import SetupDetector
from nqml.profile.sessions import on_mask
from nqml.profile.volume_profile import VolumeProfile
from nqml.screen import firsthour, gap, lasthour, orb, prevva, vabreak, vwap
from nqml.screen.atr import previous_day_atr
from nqml.screen.overlap import overlap_share

START, END = dt.date(2016, 9, 20), dt.date(2023, 10, 1)      # stesso periodo dello screening V2


def flip(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["side"] = d["side"].map({"long": "short", "short": "long"})
    return d


def b2_events(bars, cfg) -> pd.DataFrame:
    """Ogni barra 5m in cui almeno una macchina e' BROKEN: lato = quello della macchina (fade verso la
    value area), ingresso all'open della barra 5m successiva. Include le rotture mai rientrate."""
    tick, pct = cfg["instrument"]["tick_size"], cfg["detector"]["value_area_pct"]
    max_min, last_entry = cfg["detector"]["max_excursion_minutes"], cfg["detector"]["last_entry"]
    ro, rc, oo = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"], cfg["sessions"]["on_open"]
    rows = []
    for sd, day in sessions_iter(bars):
        if not (START <= sd < END):
            continue
        rth = rth_bars(day, ro, rc)
        if len(rth) < cfg["sessions"]["min_rth_bars"]:
            continue
        on = VolumeProfile(tick); on.add_bars(day.loc[on_mask(day.index, oo, ro)])
        on_va = on.value_area(pct)
        b5 = resample_5m(rth); groups = {ts: g for ts, g in rth.groupby(five_min_bin(rth.index))}
        ms = [SetupDetector(vt, s, max_min, tick) for vt in ("ON", "DEV") for s in ("long", "short")]
        dev = VolumeProfile(tick); rr = list(b5.itertuples())
        for i, r in enumerate(rr):
            dev.add_bars(groups[r.Index]); dva = dev.value_area(pct)
            bar = Bar5m(r.Index, r.open, r.high, r.low, r.close, r.volume)
            for m in ms:
                m.on_bar(bar, on_va if m.va_type == "ON" else dva)
            if i + 1 >= len(rr) or not entry_allowed(rr[i + 1].Index, last_entry):
                continue
            for m in ms:
                if m.state == "BROKEN":
                    rows.append(dict(session_date=sd, side=m.side, signal_ts=rr[i + 1].Index,
                                     va_type=m.va_type, first_bar_of_break=(m._bars_outside == 1)))
    return pd.DataFrame(rows)


def candidate_events(bars, cfg, atr_map) -> dict[str, pd.DataFrame]:
    ro, rc = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    min_rth = cfg["sessions"]["min_rth_bars"]
    acc: dict[str, list] = {k: [] for k in ("orb15", "gap", "firsthour", "vabreak", "vwap", "lasthour", "prevva")}
    prev_close = None; prev_rth = None
    for sd, day in sessions_iter(bars):
        if sd >= END:
            break
        rth = rth_bars(day, ro, rc).drop(columns=["session_date"])
        if START <= sd < END and len(rth) >= min_rth:
            a = atr_map.get(sd)
            for ev in orb.orb_events(rth, sd, cfg):
                acc["orb15"].append(ev)
            e = gap.gap_event(rth, sd, prev_close, cfg)
            if e is not None:
                acc["gap"].append(e)
            for ev in firsthour.firsthour_events(rth, sd, cfg):
                acc["firsthour"].append(ev)
            for ev in vabreak.vabreak_events(day, sd, cfg):
                acc["vabreak"].append(ev)
            for ev in vwap.vwap_events(rth, sd, cfg, a):
                acc["vwap"].append(ev)
            e = lasthour.lasthour_event(rth, sd, cfg, a)
            if e is not None:
                acc["lasthour"].append(e)
            va_p = prevva.prev_day_value_area(prev_rth, cfg) if prev_rth is not None else None
            for ev in prevva.prevva_events(rth, sd, cfg, va_p):
                acc["prevva"].append(ev)
        if len(rth) > 0:
            prev_close = float(rth["close"].iloc[-1]); prev_rth = rth
    out = {}
    for k, v in acc.items():
        d = pd.DataFrame(v)
        if len(d) and "signal_ts" not in d.columns:
            d["signal_ts"] = d["entry_ts"]        # l'istante confrontabile e' quello d'ingresso
        if len(d) and "side" not in d.columns:
            # `gap` non ha un lato a livello di evento: lo scelgono le sue 6 geometrie (3 chiusura del
            # gap, 3 prosecuzione). Gli si assegna il lato FADE (chiusura del gap), che e' l'analogo di
            # B2; il lato prosecuzione e' il suo opposto ed e' coperto dalla colonna «lato opposto».
            assert k == "gap", f"candidato {k} senza lato e senza regola dichiarata"
            d["side"] = np.where(d["gap"] > 0, "short", "long")
        out[k] = d
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    atr_map = previous_day_atr(bars, cfg)
    t0 = time.time()
    b2 = b2_events(bars, cfg)
    b2["signal_ts"] = pd.DatetimeIndex(b2["signal_ts"])
    print(f"B2: {len(b2)} eventi ({b2['first_bar_of_break'].sum()} alla prima barra della rottura) "
          f"su {b2['session_date'].nunique()} giorni ({time.time()-t0:.0f}s)", flush=True)
    cands = candidate_events(bars, cfg, atr_map)
    L = [f"PASSO 1 — doppione — config {config_hash('config.yaml')} commit {git_commit()}",
         f"periodo {START} -> {END}; NESSUN rendimento calcolato in questo script.",
         f"B2: {len(b2)} eventi, {int(b2['first_bar_of_break'].sum())} alla prima barra della rottura, "
         f"{b2['session_date'].nunique()} giorni.",
         "",
         f"{'candidato':<12}{'n eventi':>10}{'B2 coperti':>12}{'B2 coperti':>12}{'cand. coperti':>15}{'cand. coperti':>15}",
         f"{'':<12}{'':>10}{'stesso lato':>12}{'lato opp.':>12}{'stesso lato':>15}{'lato opp.':>15}"]
    for name, d in cands.items():
        if len(d) == 0:
            L.append(f"{name:<12}{0:>10}"); continue
        d = d.copy(); d["signal_ts"] = pd.DatetimeIndex(d["signal_ts"])
        a1 = overlap_share(b2, d); a2 = overlap_share(b2, flip(d))
        b1 = overlap_share(d, b2); b2s = overlap_share(d, flip(b2))
        L.append(f"{name:<12}{len(d):>10}{a1:>11.1%}{a2:>12.1%}{b1:>14.1%}{b2s:>15.1%}")
        print(L[-1], flush=True)
    # confronto mirato: solo gli eventi B2 alla PRIMA barra della rottura, contro vabreak
    first = b2[b2["first_bar_of_break"]].copy()
    vb = cands["vabreak"].copy(); vb["signal_ts"] = pd.DatetimeIndex(vb["signal_ts"])
    L += ["", "Confronto mirato B2-prima-barra vs vabreak (candidato 4):",
          f"  B2 alla prima barra della rottura: {len(first)} eventi",
          f"  di questi, coperti da vabreak STESSO lato:  {overlap_share(first, vb):.1%}",
          f"  di questi, coperti da vabreak LATO OPPOSTO: {overlap_share(first, flip(vb)):.1%}",
          f"  eventi vabreak coperti da B2-prima-barra STESSO lato:  {overlap_share(vb, first):.1%}",
          f"  eventi vabreak coperti da B2-prima-barra LATO OPPOSTO: {overlap_share(vb, flip(first)):.1%}"]
    print("\n".join(L[-6:]), flush=True)
    Path("data/ext").mkdir(parents=True, exist_ok=True)
    Path("data/ext/passo1_doppione.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\nscritto data/ext/passo1_doppione.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
