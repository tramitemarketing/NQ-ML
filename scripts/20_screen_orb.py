"""Test del muro per il candidato ORB15 (pre-registrazione `docs/superpowers/specs/2026-09-22-screening-nuovi-setup.md`).
Aritmetico: nessun modello viene addestrato. Solo gli anni di training (2016-09-20 -> 2023-09-30); OOS di lavoro e
cassaforte del filone value-area non vengono toccati. Riusa il labeler esistente (nqml/labels/labeler.py), non ne
scrive uno secondo.
Uso: .venv\\Scripts\\python scripts\\20_screen_orb.py"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

import pandas as pd

from nqml.config import config_hash, git_commit, load_config
from nqml.data.bars import load_bars, rth_bars, sessions_iter
from nqml.labels.labeler import apply_costs, label_event
from nqml.model.walkforward import assert_no_vault
from nqml.screen.orb import geometries, orb_events
from nqml.screen.persist import save_events
from nqml.screen.wall import event_descriptives, fmt_ci, geometry_row, pf

PERIOD_START = dt.date(2016, 9, 20)
PERIOD_END = dt.date(2023, 9, 30)
GEOM_ORDER = [f"{s}_{t}" for s in ("S1", "S2") for t in ("T0.5", "T1", "T1.5", "T2")]
ALPHA_M1, ALPHA_M2, M3_MIN_N = 0.05, 0.05 / 8, 500  # Bonferroni per 8 geometrie (spec §3)

_fmt_ci, _pf = fmt_ci, pf


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    t0 = time.time()
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    print(f"barre {len(bars)}, caricate in {time.time()-t0:.0f}s")

    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]

    n_days_seen = n_days_valid_rth = n_days_with_event = 0
    raw_events: list[dict] = []
    records: list[dict] = []
    for i, (sd, day) in enumerate(sessions_iter(bars)):
        if sd < PERIOD_START:
            continue
        if sd > PERIOD_END:
            break
        n_days_seen += 1
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        if len(day_rth) < min_rth:
            continue
        n_days_valid_rth += 1
        evs = orb_events(day_rth, sd, cfg, minutes=15)
        if not evs:
            continue
        n_days_with_event += 1
        raw_events.extend(evs)
        for ev in evs:
            for g in geometries(ev, cfg):
                lab = label_event(g, day_rth, cfg)
                records.append(g | {k: v for k, v in lab.items() if k != "event_id"})
        if i % 250 == 0:
            print(f"  {sd}  eventi finora {len(raw_events)}, righe evento x geometria finora {len(records)}")

    print(f"giorni nel periodo {n_days_seen} (RTH validi {n_days_valid_rth}, con almeno un evento ORB {n_days_with_event}), "
          f"eventi {len(raw_events)}, righe evento x geometria {len(records)}, {time.time()-t0:.0f}s")

    ev_df = pd.DataFrame(raw_events)
    assert len(ev_df) > 0, "nessun evento ORB nel periodo di screening"
    # Guardia del periodo (spec §1): solo gli anni di training, nessun evento nell'OOS di lavoro o nella cassaforte.
    assert (pd.to_datetime(ev_df["session_date"]) < pd.Timestamp("2023-10-01")).all(), \
        "evento oltre il periodo di screening (>= 2023-10-01): violazione del periodo pre-registrato"
    assert_no_vault(ev_df, cfg)

    save_events(ev_df.rename(columns={"break_ts": "signal_ts"}), "orb15", cfg)

    df = pd.DataFrame(records)
    df = apply_costs(df, cfg["costs"]["slippage_ticks_per_side"], cfg["costs"]["commission_per_side_usd"], cfg)

    bn, bs = cfg["backtest"]["bootstrap_n"], cfg["backtest"]["bootstrap_seed"]
    rows = []
    best_m1 = best_m2 = None
    for geom in GEOM_ORDER:
        sub = df[df["geom"] == geom]
        row = geometry_row(geom, sub, bn, bs, ALPHA_M1, ALPHA_M2, M3_MIN_N)
        row["ci994"] = row.pop("ci_m2")  # nome storico di questo report (Bonferroni 0,05/8)
        rows.append(row)
        if row["n"] == 0:
            continue
        if row["m1"] and (best_m1 is None or row["g"] > best_m1["g"]):
            best_m1 = row
        if row["m2"] and (best_m2 is None or row["g"] > best_m2["g"]):
            best_m2 = row

    if best_m2 is not None:
        advancing = best_m2
    elif best_m1 is not None:
        advancing = best_m1
    else:
        advancing = None

    ed = event_descriptives(ev_df, PERIOD_START, PERIOD_END)
    n_long, n_short, n_ev, events_per_year = ed["n_long"], ed["n_short"], ed["n"], ed["events_per_year"]

    # --- report ---------------------------------------------------------
    L: list[str] = []
    L.append("# Test del muro — ORB15 (Opening Range Breakout, 15 minuti)")
    L.append("")
    L.append(f"Generato {dt.datetime.now():%Y-%m-%d %H:%M} · config `{config_hash()}` · commit `{git_commit()}`")
    L.append("")
    L.append("Pre-registrazione: `docs/superpowers/specs/2026-09-22-screening-nuovi-setup.md` (§2). "
              f"Periodo di screening: {PERIOD_START} → {PERIOD_END} (anni di training del progetto). "
              "L'OOS di lavoro (2023-10-02 → 2026-03-19) e la cassaforte (2026-03-20 → 2026-09-19) non sono stati toccati.")
    L.append("")
    L.append("## Eventi")
    L.append("")
    L.append(f"- giorni nel periodo: {n_days_seen}")
    L.append(f"- giorni con ≥ {min_rth} barre RTH: {n_days_valid_rth}")
    L.append(f"- giorni con almeno un evento ORB: {n_days_with_event}")
    L.append(f"- eventi totali: {n_ev} (long {n_long}, short {n_short}; quota long {n_long/n_ev:.1%})")
    L.append(f"- eventi per anno: {events_per_year:.1f}")
    L.append("")
    L.append("## Test del muro (8 geometrie)")
    L.append("")
    L.append("g = media per evento di (label − prior geometrico); CI da bootstrap a blocchi per giorno, "
              f"{bn:,} ricampionamenti, seed {bs}. M1: CI 95% esclude 0 ed è positiva. "
              "M2: CI 99,4% (Bonferroni 0,05/8) esclude 0 ed è positiva. M3: n ≥ 500.")
    L.append("")
    L.append("| geometria | n | freq | prior medio | g | CI 95% | CI 99,4% | M1 | M2 | M3 | EV senza costi | R medio dopo costi |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        if r["n"] == 0:
            L.append(f"| {r['geom']} | 0 | — | — | — | — | — | FAIL | FAIL | FAIL | — | — |")
            continue
        L.append(f"| {r['geom']} | {r['n']} | {r['freq']:.3f} | {r['prior']:.3f} | {r['g']:+.4f} | "
                  f"{_fmt_ci(r['ci95'])} | {_fmt_ci(r['ci994'])} | {_pf(r['m1'])} | {_pf(r['m2'])} | {_pf(r['m3'])} | "
                  f"{r['ev_no_cost']:+.4f} R | {r['mean_r']:+.4f} R |")
    L.append("")
    L.append("## Esito (albero pre-registrato, spec §3)")
    L.append("")
    if advancing is None:
        L.append("**Nessuna geometria passa M1** → filone ORB15 **chiuso**; si passa al candidato successivo dell'elenco "
                  "(gap di apertura, estremi della prima ora, prosecuzione della value area). Nessun modello viene addestrato.")
    elif best_m2 is not None:
        L.append(f"**Almeno una geometria passa M2** → milestone completa pre-registrata sulla geometria con g più alto: "
                  f"**{advancing['geom']}** (g = {advancing['g']:+.4f} {_fmt_ci(advancing['ci994'])} CI 99,4%, n = {advancing['n']}).")
    else:
        L.append("**Almeno una geometria passa M1 ma nessuna M2** → «segnale debole»: si può aprire una milestone completa "
                  f"sulla geometria con g più alto, **{advancing['geom']}** (g = {advancing['g']:+.4f} {_fmt_ci(advancing['ci95'])} CI 95%, "
                  f"n = {advancing['n']}), dichiarando che è stata scelta fra 8; il verdetto sarà sull'OOS vergine, non su questi anni.")
    L.append("")
    L.append("In ogni caso una sola geometria avanza; le altre restano descrittive e non possono essere ripescate in seguito "
              "senza una nuova pre-registrazione.")
    L.append("")
    L.append("## Come leggere questa tabella")
    L.append("")
    L.append("`g` è lo scarto tra la frequenza osservata (target prima dello stop) e il prior di passeggiata aleatoria "
              "`1/(1+rr)`: se `g` non è positivo con CI che esclude 0, nessuna geometria — e quindi nessun modello — può "
              "rendere profittevole quella coppia stop/target, perché sotto passeggiata aleatoria il valore atteso è "
              "identicamente zero per qualunque rr. «EV senza costi» ed «R medio dopo costi» sono descrittivi (§1): "
              "entrano nella lettura ma non nel criterio del muro, che è solo su `g`. Nessun filtro (volume, volatilità, "
              "giorno della settimana) è stato applicato: questo è il setup nudo.")
    L.append("")

    md = "\n".join(L)
    out_dir = Path(cfg["backtest"]["reports_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "screen_orb15.md"
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"scritto {out} in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
