"""Test del muro per i candidati 2 (gap), 3 (prima ora) e 4 (prosecuzione VA) dello screening
(pre-registrazione `docs/superpowers/specs/2026-09-22-screening-candidati-2-3-4.md`). Aritmetico: nessun
modello viene addestrato. Solo gli anni di training (2016-09-20 -> 2023-09-30); OOS di lavoro e cassaforte del
filone value-area non vengono toccati. I tre candidati sono eseguiti insieme, in un'unica passata: nessuno dei
tre e' ri-eseguito dopo aver visto gli altri. Le 8 righe dell'ORB15 (candidato 1, gia' registrato come S1 in
`screening_looks.md`) sono copiate da `reports/screen_orb15.md`, non ricalcolate.
Uso: .venv\\Scripts\\python scripts\\21_screen_batch.py"""
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
from nqml.labels.labeler import apply_costs, label_event
from nqml.model.walkforward import assert_no_vault
from nqml.screen import firsthour, gap, vabreak
from nqml.screen.persist import save_events
from nqml.screen.wall import event_descriptives, fmt_ci, geometry_row, pf

PERIOD_START = dt.date(2016, 9, 20)
PERIOD_END = dt.date(2023, 9, 30)
# Molteplicita' aggiornata del filone (spec candidati-2-3-4, "Molteplicita', aggiornata prima di eseguire"):
# 8 (ORB15) + 6 (gap) + 8 (prima ora) + 8 (prosecuzione VA) = 30 test.
ALPHA_M1 = 0.05
ALPHA_M2 = 0.05 / 30
M3_MIN_N = 500

GAP_GEOM_ORDER = [f"{fam}_k{k}" for fam in ("F", "P") for k in ("0.5", "1", "2")]
FH_GEOM_ORDER = [f"{s}_{t}" for s in ("S1", "S2") for t in ("T0.5", "T1", "T1.5", "T2")]
VA_GEOM_ORDER = [f"{s}_{t}" for s in ("S1", "S2") for t in ("T0.25", "T0.5", "T0.75", "T1.0")]

ATTESA = {"gap": 0.15, "firsthour": 0.15, "vabreak": 0.25}  # attese dichiarate, spec candidati-2-3-4


# ---------------------------------------------------------------------------
# Eventi + label per candidato (indipendenti l'uno dall'altro)
# ---------------------------------------------------------------------------

def run_gap(bars: pd.DataFrame, cfg: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events: list[dict] = []
    records: list[dict] = []
    prev_close: float | None = None
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
                        lab = label_event(g, day_rth, cfg)
                        records.append(g | {k: v for k, v in lab.items() if k != "event_id"})
        if len(day_rth) > 0:
            prev_close = float(day_rth["close"].iloc[-1])
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records))


def run_firsthour(bars: pd.DataFrame, cfg: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events: list[dict] = []
    records: list[dict] = []
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
                lab = label_event(g, day_rth, cfg)
                records.append(g | {k: v for k, v in lab.items() if k != "event_id"})
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records))


def run_vabreak(bars: pd.DataFrame, cfg: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events: list[dict] = []
    records: list[dict] = []
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
                lab = label_event(g, day_rth, cfg)
                records.append(g | {k: v for k, v in lab.items() if k != "event_id"})
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records))


# ---------------------------------------------------------------------------
# Tabella del muro comune ai tre candidati
# ---------------------------------------------------------------------------

def finalize(cfg: dict, ev_df: pd.DataFrame, df: pd.DataFrame, geom_order: list[str], bn: int, bs: int) -> dict:
    assert len(ev_df) > 0, "nessun evento nel periodo di screening"
    assert (pd.to_datetime(ev_df["session_date"]) < pd.Timestamp("2023-10-01")).all(), \
        "evento oltre il periodo di screening (>= 2023-10-01): violazione del periodo pre-registrato"
    assert_no_vault(ev_df, cfg)

    df = apply_costs(df, cfg["costs"]["slippage_ticks_per_side"], cfg["costs"]["commission_per_side_usd"], cfg)
    rows, best_m1, best_m2 = [], None, None
    for geom in geom_order:
        sub = df[df["geom"] == geom]
        row = geometry_row(geom, sub, bn, bs, ALPHA_M1, ALPHA_M2, M3_MIN_N)
        rows.append(row)
        if row["n"] == 0:
            continue
        if row["m1"] and (best_m1 is None or row["g"] > best_m1["g"]):
            best_m1 = row
        if row["m2"] and (best_m2 is None or row["g"] > best_m2["g"]):
            best_m2 = row
    advancing = best_m2 if best_m2 is not None else best_m1
    return dict(rows=rows, best_m1=best_m1, best_m2=best_m2, advancing=advancing)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_geom_table(rows: list[dict]) -> list[str]:
    L = ["| geometria | n | freq | prior medio | g | CI 95% | CI 99,83% | M1 | M2 | M3 | EV senza costi | R medio dopo costi |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["n"] == 0:
            L.append(f"| {r['geom']} | 0 | — | — | — | — | — | FAIL | FAIL | FAIL | — | — |")
            continue
        L.append(f"| {r['geom']} | {r['n']} | {r['freq']:.3f} | {r['prior']:.3f} | {r['g']:+.4f} | "
                  f"{fmt_ci(r['ci95'])} | {fmt_ci(r['ci_m2'])} | {pf(r['m1'])} | {pf(r['m2'])} | {pf(r['m3'])} | "
                  f"{r['ev_no_cost']:+.4f} R | {r['mean_r']:+.4f} R |")
    return L


def render_outcome(res: dict) -> list[str]:
    best_m1, best_m2, advancing = res["best_m1"], res["best_m2"], res["advancing"]
    if advancing is None:
        return ["**Nessuna geometria passa M1** → candidato **chiuso**, nessun modello addestrato."]
    if best_m2 is not None:
        return [f"**Almeno una geometria passa M2** → milestone completa pre-registrata sulla geometria con g "
                f"più alto: **{advancing['geom']}** (g = {advancing['g']:+.4f} {fmt_ci(advancing['ci_m2'])} "
                f"CI 99,83%, n = {advancing['n']}), verdetto sull'OOS vergine 2023-10 → 2026-03."]
    return [f"**Passa M1 ma non M2** → «segnale debole»: si annota, non si apre nulla. Geometria con g più alto: "
            f"**{advancing['geom']}** (g = {advancing['g']:+.4f} {fmt_ci(advancing['ci95'])} CI 95%, "
            f"n = {advancing['n']}); può rientrare in un disegno futuro solo se pre-registrato esplicitamente "
            "come replica, con soglia M2."]


ORB15_ROW_RE = re.compile(r"^\| (S[12]_T[0-9.]+) \|")


def load_orb15_rows(path: Path) -> list[str]:
    """Copia letterale delle 8 righe della tabella gia' registrata (screening_looks.md riga S1): non
    ricalcolata qui. Ritorna le righe di tabella markdown gia' pronte, con l'etichetta di colonna CI
    rinominata per allinearsi alla tabella dei nuovi candidati (stesso numero, la 99,4% dell'epoca dell'ORB15,
    Bonferroni su 8 geometrie, non su 30: e' un test gia' chiuso, non viene ricalcolato a soglia diversa)."""
    text = path.read_text(encoding="utf-8")
    return [line for line in text.splitlines() if ORB15_ROW_RE.match(line)]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    t0 = time.time()
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    print(f"barre {len(bars)}, caricate in {time.time()-t0:.0f}s")
    bn, bs = cfg["backtest"]["bootstrap_n"], cfg["backtest"]["bootstrap_seed"]

    print("candidato 2 (gap) ...")
    t1 = time.time()
    gap_res = run_gap(bars, cfg)
    print(f"  giorni {gap_res['n_days_seen']} (validi {gap_res['n_days_valid']}, con evento {gap_res['n_days_with_event']}), "
          f"eventi {len(gap_res['ev_df'])}, {time.time()-t1:.0f}s")
    gap_final = finalize(cfg, gap_res["ev_df"], gap_res["df"], GAP_GEOM_ORDER, bn, bs)
    # L'evento gap grezzo non ha un "side" proprio: genera sempre una geometria F (chiusura, verso la
    # direzione opposta al gap) e una P (prosecuzione, nella direzione del gap), speculari (vedi
    # nqml/screen/gap.py::geometries). Per la matrice di sovrapposizione (colonna "side" richiesta) si
    # salvano le due famiglie come righe separate, stessa costruzione dei lati di prevva.py.
    gap_save_base = gap_res["ev_df"].rename(columns={"open_ts": "signal_ts"})
    u_p = np.where(gap_save_base["gap"] > 0, 1.0, -1.0)
    side_p = np.where(u_p > 0, "long", "short")
    side_f = np.where(u_p > 0, "short", "long")
    gap_save = pd.concat([
        gap_save_base.assign(family="F", side=side_f, event_id=gap_save_base["event_id"] + "_F"),
        gap_save_base.assign(family="P", side=side_p, event_id=gap_save_base["event_id"] + "_P"),
    ], ignore_index=True)
    save_events(gap_save, "gap", cfg)

    print("candidato 3 (prima ora) ...")
    t1 = time.time()
    fh_res = run_firsthour(bars, cfg)
    print(f"  giorni {fh_res['n_days_seen']} (validi {fh_res['n_days_valid']}, con evento {fh_res['n_days_with_event']}), "
          f"eventi {len(fh_res['ev_df'])}, {time.time()-t1:.0f}s")
    fh_final = finalize(cfg, fh_res["ev_df"], fh_res["df"], FH_GEOM_ORDER, bn, bs)
    save_events(fh_res["ev_df"].rename(columns={"break_ts": "signal_ts"}), "firsthour", cfg)

    print("candidato 4 (prosecuzione VA) ...")
    t1 = time.time()
    va_res = run_vabreak(bars, cfg)
    print(f"  giorni {va_res['n_days_seen']} (validi {va_res['n_days_valid']}, con evento {va_res['n_days_with_event']}), "
          f"eventi {len(va_res['ev_df'])}, {time.time()-t1:.0f}s")
    va_final = finalize(cfg, va_res["ev_df"], va_res["df"], VA_GEOM_ORDER, bn, bs)
    va_save = va_res["ev_df"].rename(columns={"break_ts": "signal_ts"})
    va_save["va_width"] = va_save["w"]
    va_save["poc_dist"] = (va_save["entry_ref_price"] - va_save["poc"]).abs()
    save_events(va_save, "vabreak", cfg)

    orb15_rows = load_orb15_rows(Path(cfg["backtest"]["reports_dir"]) / "screen_orb15.md")
    assert len(orb15_rows) == 8, f"attese 8 righe ORB15 gia' registrate, trovate {len(orb15_rows)}"

    # --- report -----------------------------------------------------------
    L: list[str] = []
    L.append("# Test del muro — candidati 2, 3, 4 (gap, prima ora, prosecuzione value area)")
    L.append("")
    L.append(f"Generato {dt.datetime.now():%Y-%m-%d %H:%M} · config `{config_hash()}` · commit `{git_commit()}`")
    L.append("")
    L.append("Pre-registrazione: `docs/superpowers/specs/2026-09-22-screening-candidati-2-3-4.md`. "
              f"Periodo di screening: {PERIOD_START} → {PERIOD_END} (anni di training del progetto). "
              "L'OOS di lavoro (2023-10-02 → 2026-03-19) e la cassaforte (2026-03-20 → 2026-09-19) non sono stati "
              "toccati. Eseguiti insieme, in un'unica passata: nessuno dei tre e' stato ri-eseguito dopo aver visto "
              "gli altri. Molteplicita' del filone: 8 (ORB15, gia' chiuso) + 6 (gap) + 8 (prima ora) + 8 "
              "(prosecuzione VA) = 30 test. M1: CI 95% esclude 0 ed e' positiva. M2: CI 99,83% (Bonferroni 0,05/30) "
              "esclude 0 ed e' positiva. M3: n ≥ 500. In ogni candidato una sola geometria puo' avanzare.")
    L.append("")

    # --- Candidato 2: Gap --------------------------------------------------
    L.append("## Candidato 2 — Gap di apertura (S2)")
    L.append("")
    L.append("Evento: |gap RTH| ≥ 2 punti (apertura RTH − chiusura RTH del giorno precedente). Due famiglie "
              "speculari, tre geometrie ciascuna: F (chiusura del gap, verso la chiusura precedente) e P "
              "(prosecuzione, nella direzione del gap), k ∈ {0,5; 1; 2}. Al massimo un evento per giorno. "
              f"Attesa dichiarata: {ATTESA['gap']:.0%} di passare M2.")
    L.append("")
    ev_df = gap_res["ev_df"]
    n_ev = len(ev_df)
    n_up = int((ev_df["gap"] > 0).sum())
    period_years = (PERIOD_END - PERIOD_START).days / 365.25
    L.append(f"- giorni nel periodo: {gap_res['n_days_seen']}")
    L.append(f"- giorni con ≥ {cfg['sessions']['min_rth_bars']} barre RTH e chiusura precedente nota: {gap_res['n_days_valid']}")
    L.append(f"- giorni con un gap ≥ 2 punti: {gap_res['n_days_with_event']}")
    L.append(f"- eventi totali: {n_ev} (gap in su {n_up}, gap in giù {n_ev - n_up}; quota in su {n_up/n_ev:.1%})")
    L.append(f"- eventi per anno: {n_ev/period_years:.1f}")
    L.append("")
    L.append("### Test del muro (6 geometrie)")
    L.append("")
    L.extend(render_geom_table(gap_final["rows"]))
    L.append("")
    L.append("### Esito")
    L.append("")
    L.extend(render_outcome(gap_final))
    L.append("")

    # --- Candidato 3: prima ora ---------------------------------------------
    L.append("## Candidato 3 — Estremi della prima ora (S3)")
    L.append("")
    L.append("Evento: FHH/FHL sulle 60 barre 1m dalle 09:30 alle 10:29:59 ET; dalle 10:30 la prima barra che "
              "chiude oltre l'estremo genera l'evento (al massimo uno per lato al giorno). Otto geometrie "
              "(2 stop × 4 target), stessa struttura dell'ORB15 su una finestra di un'ora. "
              f"Attesa dichiarata: {ATTESA['firsthour']:.0%} di passare M2.")
    L.append("")
    ev_df = fh_res["ev_df"]
    ed = event_descriptives(ev_df, PERIOD_START, PERIOD_END)
    L.append(f"- giorni nel periodo: {fh_res['n_days_seen']}")
    L.append(f"- giorni con ≥ {cfg['sessions']['min_rth_bars']} barre RTH: {fh_res['n_days_valid']}")
    L.append(f"- giorni con almeno un evento: {fh_res['n_days_with_event']}")
    L.append(f"- eventi totali: {ed['n']} (long {ed['n_long']}, short {ed['n_short']}; quota long {ed['share_long']:.1%})")
    L.append(f"- eventi per anno: {ed['events_per_year']:.1f}")
    L.append("")
    L.append("### Test del muro (8 geometrie)")
    L.append("")
    L.extend(render_geom_table(fh_final["rows"]))
    L.append("")
    L.append("### Esito")
    L.append("")
    L.extend(render_outcome(fh_final))
    L.append("")

    # --- Candidato 4: prosecuzione VA ---------------------------------------
    L.append("## Candidato 4 — Prosecuzione della value area (S4)")
    L.append("")
    L.append("Evento: prima transizione INSIDE → BROKEN per (tipo di value area ON/DEV × lato di rottura) per "
              "giorno — prima chiusura di barra 5m oltre il bordo della value area, indipendentemente da cio' "
              "che accade dopo. Guida le stesse barre 5m e lo stesso codice di value area di "
              "nqml/detector/run_day.py (ON fissa, DEV ricalcolata a ogni chiusura 5m) senza usare "
              "`SetupDetector`, che emette solo al rientro: gli eventi gia' calcolati in "
              "`data/events/events.parquet` conterrebbero percio' solo le rotture poi rientrate, una selezione "
              "che favorirebbe artificialmente il rientro. Otto geometrie (2 stop × 4 target su k della "
              f"larghezza della value area alla rottura). Attesa dichiarata: {ATTESA['vabreak']:.0%} di passare M2.")
    L.append("")
    ev_df = va_res["ev_df"]
    ed = event_descriptives(ev_df, PERIOD_START, PERIOD_END)
    n_on = int((ev_df["va_type"] == "ON").sum())
    n_dev = int((ev_df["va_type"] == "DEV").sum())
    L.append(f"- giorni nel periodo: {va_res['n_days_seen']}")
    L.append(f"- giorni con ≥ {cfg['sessions']['min_rth_bars']} barre RTH: {va_res['n_days_valid']}")
    L.append(f"- giorni con almeno un evento: {va_res['n_days_with_event']}")
    L.append(f"- eventi totali: {ed['n']} (ON {n_on}, DEV {n_dev}; long {ed['n_long']}, short {ed['n_short']}, "
              f"quota long {ed['share_long']:.1%})")
    L.append(f"- eventi per anno: {ed['events_per_year']:.1f}")
    L.append("")
    L.append("### Test del muro (8 geometrie)")
    L.append("")
    L.extend(render_geom_table(va_final["rows"]))
    L.append("")
    L.append("### Esito")
    L.append("")
    L.extend(render_outcome(va_final))
    L.append("")

    # --- Sintesi: tutti i 30 test -------------------------------------------
    L.append("## Sintesi — tutti i 30 test del filone screening")
    L.append("")
    L.append("Le 8 righe ORB15 sono copiate letteralmente da `reports/screen_orb15.md` (candidato 1, S1, gia' "
              "chiuso e registrato: CI al 99,4%, Bonferroni sulle sue 8 geometrie soltanto, non ricalcolate a "
              "99,83%). Le altre 22 righe usano la soglia M2 aggiornata di questo documento (99,83%, Bonferroni "
              "sui 30 test del filone).")
    L.append("")
    L.append("| candidato | geometria | n | g | M1 | M2 | M3 | nota |")
    L.append("|---|---|---|---|---|---|---|---|")
    for line in orb15_rows:
        cells = [c.strip() for c in line.strip("|").split("|")]
        geom, n, g, m1, m2, m3 = cells[0], cells[1], cells[4], cells[7], cells[8], cells[9]
        L.append(f"| ORB15 (candidato 1) | {geom} | {n} | {g} | {m1} | {m2} | {m3} | già registrato (S1, CI 99,4%) |")
    for label, res in (("Gap (candidato 2)", gap_final), ("Prima ora (candidato 3)", fh_final), ("Prosecuzione VA (candidato 4)", va_final)):
        for r in res["rows"]:
            g_str = f"{r['g']:+.4f}" if r["n"] > 0 else "—"
            L.append(f"| {label} | {r['geom']} | {r['n']} | {g_str} | {pf(r['m1'])} | {pf(r['m2'])} | {pf(r['m3'])} | |")
    L.append("")
    L.append("## Come leggere questa tabella")
    L.append("")
    L.append("`g` è lo scarto tra la frequenza osservata (target prima dello stop) e il prior di passeggiata "
              "aleatoria `1/(1+rr)`: se `g` non è positivo con CI che esclude 0, nessuna geometria — e quindi "
              "nessun modello — può rendere profittevole quella coppia stop/target. «EV senza costi» ed «R medio "
              "dopo costi» sono descrittivi: entrano nella lettura ma non nel criterio del muro, che è solo su "
              "`g`. Nessun filtro (volume, volatilità, giorno della settimana, notizie) è stato applicato: questo "
              "è il setup nudo di ciascun candidato.")
    L.append("")

    md = "\n".join(L)
    out_dir = Path(cfg["backtest"]["reports_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "screen_roundup.md"
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"scritto {out} in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
