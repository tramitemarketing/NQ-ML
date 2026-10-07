"""Test del muro per i candidati 5 (VWAP), 6 (overnight), 7 (ultima ora) e 8 (apertura fuori VA di ieri)
dello screening, con il controllo di molteplicita' Benjamini-Hochberg (pre-registrazione
`docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`). Aritmetico: nessun modello viene
addestrato. Solo gli anni di training (2016-09-20 -> 2023-09-30); OOS di lavoro e cassaforte non vengono
toccati. I quattro candidati sono eseguiti insieme, in un'unica passata: nessuno e' ri-eseguito dopo aver
visto gli altri. Salva anche gli eventi dei candidati 1-8 in `data/screen/` e produce la matrice di
sovrapposizione (spec §2), necessaria (ma non sufficiente da sola) per la fase ibrida futura (§3, non
eseguita qui).
Uso: .venv\\Scripts\\python scripts\\24_screen_batch2.py
Precondizione: scripts/20_screen_orb.py e scripts/21_screen_batch.py gia' eseguiti (servono i loro
data/screen/events_*.parquet per la matrice di sovrapposizione)."""
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
from nqml.screen import lasthour, overnight, prevva, vwap
from nqml.screen.atr import previous_day_atr
from nqml.screen.fdr import benjamini_hochberg, bootstrap_p
from nqml.screen.overlap import overlap_matrix
from nqml.screen.persist import save_events
from nqml.screen.wall import event_descriptives, fmt_ci, g_per_day, g_stat, geometry_descriptives, wall_test

PERIOD_START = dt.date(2016, 9, 20)
PERIOD_END = dt.date(2023, 9, 30)
BOUNDARY = dt.date(2023, 10, 1)
Q_BH = 0.10
ALPHA_CI = 0.05

VWAP_GEOM_ORDER = [f"{t}_{s}" for t in ("TVWAP", "TMID") for s in ("A1.0", "A1.5", "A2.0")]
OVERNIGHT_GEOM_ORDER = [f"{s}_{t}" for s in ("S1.0", "S2.0") for t in ("T1.0", "T2.0")]
LASTHOUR_GEOM_ORDER = [f"{s}_{t}" for s in ("S0.5", "S1.0") for t in ("T0.5", "T1.0")]
PREVVA_GEOM_ORDER = [f"{fam}_{k}" for fam in ("R", "C") for k in ("K0.25", "K0.5", "K0.75", "K1.0")]

ATTESA = {"vwap": 0.20, "overnight": 0.30, "lasthour": 0.15, "prevva": 0.20}
CANDIDATE_LABEL = {"vwap": "Candidato 5 — VWAP", "overnight": "Candidato 6 — Overnight",
                    "lasthour": "Candidato 7 — Ultima ora", "prevva": "Candidato 8 — Apertura fuori VA"}


# ---------------------------------------------------------------------------
# Eventi + label per candidato (indipendenti l'uno dall'altro)
# ---------------------------------------------------------------------------

def run_vwap(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
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
        evs = vwap.vwap_events(day_rth, sd, cfg, atr_map.get(sd))
        if not evs:
            continue
        n_days_with_event += 1
        raw_events.extend(evs)
        for ev in evs:
            for g in vwap.geometries(ev, cfg):
                lab = label_event(g, day_rth, cfg)
                records.append(g | {k: v for k, v in lab.items() if k != "event_id"})
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records))


def run_lasthour(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
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
        ev = lasthour.lasthour_event(day_rth, sd, cfg, atr_map.get(sd))
        if ev is None:
            continue
        n_days_with_event += 1
        raw_events.append(ev)
        for g in lasthour.geometries(ev, cfg):
            lab = label_event(g, day_rth, cfg)
            records.append(g | {k: v for k, v in lab.items() if k != "event_id"})
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records))


def run_prevva(bars: pd.DataFrame, cfg: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = n_days_with_event = 0
    raw_events: list[dict] = []
    records: list[dict] = []
    prev_day_rth: pd.DataFrame | None = None
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
                            lab = label_event(g, day_rth, cfg)
                            records.append(g | {k: v for k, v in lab.items() if k != "event_id"})
        if sd > PERIOD_END:
            break
        if valid:
            prev_day_rth = day_rth
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_days_with_event=n_days_with_event,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records))


def run_overnight(bars: pd.DataFrame, cfg: dict, atr_map: dict) -> dict:
    min_rth = cfg["sessions"]["min_rth_bars"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    n_days_seen = n_days_valid = 0
    n_dropped_boundary = 0
    raw_events: list[dict] = []
    records: list[dict] = []
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
                        lab = overnight.label_overnight_event(g, span, cfg)
                        records.append(g | {k: v for k, v in lab.items() if k != "event_id"})
        prev_sd, prev_rth, prev_full, prev_valid = sd, day_rth, day, valid
        if prev_sd > PERIOD_END:
            break
    return dict(n_days_seen=n_days_seen, n_days_valid=n_days_valid, n_dropped_boundary=n_dropped_boundary,
                ev_df=pd.DataFrame(raw_events), df=pd.DataFrame(records))


# ---------------------------------------------------------------------------
# Tabella del muro con BH (comune ai quattro candidati)
# ---------------------------------------------------------------------------

def geometry_row_bh(geom: str, sub: pd.DataFrame, bn: int, bs: int) -> dict:
    n = len(sub)
    if n == 0:
        return dict(geom=geom, n=0, freq=float("nan"), prior=float("nan"), g=float("nan"),
                    ci95=(float("nan"), float("nan")), p=float("nan"), ev_no_cost=float("nan"), mean_r=float("nan"))
    wt = wall_test(sub, bn, bs, [ALPHA_CI])
    per_day = g_per_day(sub)
    p = bootstrap_p(per_day, g_stat, bn, bs)
    desc = geometry_descriptives(sub)
    return dict(geom=geom, n=n, freq=wt["freq"], prior=wt["prior"], g=wt["g"], ci95=wt["ci"][ALPHA_CI], p=p,
                ev_no_cost=desc["ev_no_cost"], mean_r=desc["mean_r"])


def bh_thresholds(pvalues: list[float], q: float) -> list[float]:
    """Soglia q*i/m di ciascun test, i = suo rango nell'ordinamento crescente dei p-value (non la sua
    posizione nell'elenco originale)."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    thr = [0.0] * m
    for rank, idx in enumerate(order, start=1):
        thr[idx] = q * rank / m
    return thr


def render_geom_table_bh(rows: list[dict], discoveries: list[bool], thresholds: list[float]) -> list[str]:
    L = ["| geometria | n | freq | prior medio | g | CI 95% | p (bootstrap) | soglia BH | scoperta | "
         "EV senza costi | R medio dopo costi |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r, disc, thr in zip(rows, discoveries, thresholds):
        if r["n"] == 0:
            L.append(f"| {r['geom']} | 0 | — | — | — | — | — | {thr:.4f} | NO | — | — |")
            continue
        L.append(f"| {r['geom']} | {r['n']} | {r['freq']:.3f} | {r['prior']:.3f} | {r['g']:+.4f} | "
                  f"{fmt_ci(r['ci95'])} | {r['p']:.4f} | {thr:.4f} | {'SI' if disc else 'NO'} | "
                  f"{r['ev_no_cost']:+.4f} R | {r['mean_r']:+.4f} R |")
    return L


def render_outcome_bh(name: str, rows: list[dict], discoveries: list[bool]) -> list[str]:
    discovered = [(r, d) for r, d in zip(rows, discoveries) if d and r["n"] > 0]
    if not discovered:
        return [f"**Nessuna geometria di {name} e' una scoperta BH** → candidato **chiuso**, nessun modello addestrato."]
    best = max((r for r, _ in discovered), key=lambda r: r["g"])
    names = ", ".join(r["geom"] for r, _ in discovered)
    return [f"**{len(discovered)} geometria/e scoperta/e dal BH** ({names}) → candidato: la geometria con g piu' "
            f"alto e' **{best['geom']}** (g = {best['g']:+.4f} {fmt_ci(best['ci95'])} CI 95%, p = {best['p']:.4f}, "
            f"n = {best['n']}). Autorizza una milestone pre-registrata il cui verdetto e' sull'OOS vergine "
            "2023-10 → 2026-03, mai toccato: la scoperta e' un candidato, non un risultato."]


def prepare_save(ev_df: pd.DataFrame, extra: dict[str, pd.Series] | None = None) -> pd.DataFrame:
    out = ev_df.copy()
    if extra:
        for col, series in extra.items():
            out[col] = series
    return out


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

    print("candidato 5 (VWAP) ...")
    t1 = time.time()
    vwap_res = run_vwap(bars, cfg, atr_map)
    print(f"  giorni {vwap_res['n_days_seen']} (validi {vwap_res['n_days_valid']}, con evento {vwap_res['n_days_with_event']}), "
          f"eventi {len(vwap_res['ev_df'])}, {time.time()-t1:.0f}s")

    print("candidato 6 (overnight) ...")
    t1 = time.time()
    on_res = run_overnight(bars, cfg, atr_map)
    print(f"  giorni {on_res['n_days_seen']} (validi {on_res['n_days_valid']}, scartati per confine periodo "
          f"{on_res['n_dropped_boundary']}), eventi {len(on_res['ev_df'])}, {time.time()-t1:.0f}s")

    print("candidato 7 (ultima ora) ...")
    t1 = time.time()
    lh_res = run_lasthour(bars, cfg, atr_map)
    print(f"  giorni {lh_res['n_days_seen']} (validi {lh_res['n_days_valid']}, con evento {lh_res['n_days_with_event']}), "
          f"eventi {len(lh_res['ev_df'])}, {time.time()-t1:.0f}s")

    print("candidato 8 (apertura fuori VA) ...")
    t1 = time.time()
    pv_res = run_prevva(bars, cfg)
    print(f"  giorni {pv_res['n_days_seen']} (validi {pv_res['n_days_valid']}, con evento {pv_res['n_days_with_event']}), "
          f"eventi {len(pv_res['ev_df'])}, {time.time()-t1:.0f}s")

    # --- guardie di periodo (spec §1) e cassaforte, come nei lotti precedenti ------------------------
    results = {"vwap": vwap_res, "overnight": on_res, "lasthour": lh_res, "prevva": pv_res}
    for name, res in results.items():
        ev_df = res["ev_df"]
        assert len(ev_df) > 0, f"nessun evento nel periodo di screening ({name})"
        assert (pd.to_datetime(ev_df["session_date"]) < pd.Timestamp("2023-10-01")).all(), \
            f"evento oltre il periodo di screening (>= 2023-10-01): violazione del periodo pre-registrato ({name})"
        assert_no_vault(ev_df, cfg)
    # candidato 6: l'USCITA (non l'entrata) puo' cadere oltre il confine; e' per questo che quegli eventi
    # sono stati scartati a monte (run_overnight), non troncati. Guardia esplicita qui:
    assert (pd.to_datetime(on_res["ev_df"]["next_open_ts"]).dt.date < BOUNDARY).all(), \
        "un evento overnight scartato per il confine di periodo e' comunque entrato nella tabella"

    # --- apply_costs -----------------------------------------------------------------------------
    dfs = {name: apply_costs(res["df"], cfg["costs"]["slippage_ticks_per_side"], cfg["costs"]["commission_per_side_usd"], cfg)
           for name, res in results.items()}

    # --- tabella del muro per geometria, poi BH sull'intera famiglia di 22 test --------------------
    geom_orders = {"vwap": VWAP_GEOM_ORDER, "overnight": OVERNIGHT_GEOM_ORDER,
                   "lasthour": LASTHOUR_GEOM_ORDER, "prevva": PREVVA_GEOM_ORDER}
    all_rows: list[dict] = []
    row_candidate: list[str] = []
    for name, order in geom_orders.items():
        df = dfs[name]
        for geom in order:
            sub = df[df["geom"] == geom]
            row = geometry_row_bh(geom, sub, bn, bs)
            all_rows.append(row)
            row_candidate.append(name)

    assert len(all_rows) == 22, f"attesi 22 test nel lotto, trovati {len(all_rows)}"
    assert all(r["n"] > 0 for r in all_rows), "una geometria del lotto non ha eventi: la molteplicita' dichiarata (22) non e' rispettata"

    pvalues = [r["p"] for r in all_rows]
    discoveries = benjamini_hochberg(pvalues, Q_BH)
    thresholds = bh_thresholds(pvalues, Q_BH)

    rows_by_candidate: dict[str, list[dict]] = {name: [] for name in geom_orders}
    disc_by_candidate: dict[str, list[bool]] = {name: [] for name in geom_orders}
    thr_by_candidate: dict[str, list[float]] = {name: [] for name in geom_orders}
    for name, row, disc, thr in zip(row_candidate, all_rows, discoveries, thresholds):
        rows_by_candidate[name].append(row)
        disc_by_candidate[name].append(disc)
        thr_by_candidate[name].append(thr)

    # --- salvataggio eventi 5-8 (spec §2, per la fase ibrida futura) --------------------------------
    save_events(vwap_res["ev_df"], "vwap", cfg)
    save_events(on_res["ev_df"], "overnight", cfg)
    save_events(lh_res["ev_df"], "lasthour", cfg)
    pv_save = prepare_save(pv_res["ev_df"], {"va_width": pv_res["ev_df"]["w"]})
    save_events(pv_save, "prevva", cfg)

    # --- matrice di sovrapposizione (spec §2): candidati 1-8, letti da data/screen/ ------------------
    screen_dir = Path(cfg["data"]["raw_dir"]).parent / "screen"
    all_names = ["orb15", "gap", "firsthour", "vabreak", "vwap", "overnight", "lasthour", "prevva"]
    missing = [n for n in all_names if not (screen_dir / f"events_{n}.parquet").exists()]
    if missing:
        raise SystemExit(f"mancano gli eventi salvati di {missing}: eseguire prima scripts/20_screen_orb.py "
                          "e scripts/21_screen_batch.py")
    all_events = {n: pd.read_parquet(screen_dir / f"events_{n}.parquet") for n in all_names}
    ov = overlap_matrix(all_events)

    # --- report -----------------------------------------------------------------------------------
    L: list[str] = []
    L.append("# Test del muro — candidati 5, 6, 7, 8 (VWAP, overnight, ultima ora, apertura fuori VA) — "
             "Benjamini-Hochberg")
    L.append("")
    L.append(f"Generato {dt.datetime.now():%Y-%m-%d %H:%M} · config `{config_hash()}` · commit `{git_commit()}`")
    L.append("")
    L.append("Pre-registrazione: `docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`. "
              f"Periodo di screening: {PERIOD_START} → {PERIOD_END} (anni di training del progetto). "
              "L'OOS di lavoro (2023-10-02 → 2026-03-19) e la cassaforte (2026-03-20 → 2026-09-19) non sono "
              "stati toccati. Eseguiti insieme, in un'unica passata: nessuno dei quattro e' stato ri-eseguito "
              "dopo aver visto gli altri. **Controllo di molteplicita': Benjamini-Hochberg, q = 0,10, sui 22 "
              "test di questo lotto** (6 VWAP + 4 overnight + 4 ultima ora + 8 apertura fuori VA), non "
              "retroattivo sulle righe S1-S4 (Bonferroni, gia' chiuse). p-value bootstrap a due code, "
              f"{bn:,} ricampionamenti, seed {bs}, con correzione (k+1)/(B+1). Una geometria che non e' una "
              "scoperta BH non e' un candidato, qualunque sia la sua CI 95%.")
    L.append("")

    sections = [
        ("vwap", "Candidato 5 — Ritorno alla media sul VWAP",
         "Evento: dalle 10:00 ET, la prima barra 1m che chiude a piu' di 2σ dal VWAP di sessione (pesato per "
         "volume dall'apertura) genera un ritorno alla media (short se sopra, long se sotto). Sei geometrie "
         "(2 target x 3 stop in ATR del giorno precedente)."),
        ("overnight", "Candidato 6 — Tenuta overnight",
         "Evento: long alla chiusura RTH, uscita all'apertura RTH successiva; nessuna condizione, un evento "
         "ogni giorno valido. Quattro geometrie (2 stop x 2 target in ATR del giorno precedente). Unica "
         "deroga del lotto: il time stop non e' alle 15:55 ma all'apertura RTH successiva (nella definizione "
         "del setup, non un parametro)."),
        ("lasthour", "Candidato 7 — Momentum dell'ultima ora",
         "Evento: alle 15:00 ET, nella direzione della sessione rispetto all'apertura RTH; un evento ogni "
         "giorno (salvo sessione esattamente flat). Quattro geometrie (2 stop x 2 target in ATR del giorno "
         "precedente)."),
        ("prevva", "Candidato 8 — Apertura fuori dalla value area di ieri",
         "Evento: se l'apertura RTH di oggi e' fuori dalla value area (70%) della sessione RTH precedente, "
         "un evento per famiglia (R ritorno, C continuazione) alla prima barra RTH. Otto geometrie (2 "
         "famiglie x 4 multipli della larghezza della VA precedente; vedi nota nel modulo "
         "`nqml/screen/prevva.py` sulla lettura del testo della spec)."),
    ]
    for name, title, desc in sections:
        res = results[name]
        L.append(f"## {title}")
        L.append("")
        L.append(f"{desc} Attesa dichiarata: {ATTESA[name]:.0%} di almeno una scoperta BH.")
        L.append("")
        ev_df = res["ev_df"]
        if name == "overnight":
            L.append(f"- giorni d'ingresso nel periodo: {res['n_days_seen']}")
            L.append(f"- giorni d'ingresso validi (uscita nel periodo e non oltre il confine): {res['n_days_valid']}")
            L.append(f"- eventi scartati per il confine di periodo (uscita >= {BOUNDARY}, non troncati): {res['n_dropped_boundary']}")
            L.append(f"- eventi totali: {len(ev_df)}")
        else:
            ed = event_descriptives(ev_df, PERIOD_START, PERIOD_END)
            L.append(f"- giorni nel periodo: {res['n_days_seen']}")
            L.append(f"- giorni con ≥ {cfg['sessions']['min_rth_bars']} barre RTH: {res['n_days_valid']}")
            L.append(f"- giorni con almeno un evento: {res['n_days_with_event']}")
            L.append(f"- eventi totali: {ed['n']} (long {ed['n_long']}, short {ed['n_short']}; quota long {ed['share_long']:.1%})")
            L.append(f"- eventi per anno: {ed['events_per_year']:.1f}")
        L.append("")
        n_geom = len(geom_orders[name])
        L.append(f"### Test del muro ({n_geom} geometrie)")
        L.append("")
        L.extend(render_geom_table_bh(rows_by_candidate[name], disc_by_candidate[name], thr_by_candidate[name]))
        L.append("")
        L.append("### Esito")
        L.append("")
        L.extend(render_outcome_bh(name, rows_by_candidate[name], disc_by_candidate[name]))
        L.append("")

    # --- Sintesi: tutti i 22 test -----------------------------------------------------------------
    L.append("## Sintesi — i 22 test del lotto 5-8 (BH q = 0,10)")
    L.append("")
    L.append("| candidato | geometria | n | g | p | soglia BH | scoperta |")
    L.append("|---|---|---|---|---|---|---|")
    for name, row, disc, thr in zip(row_candidate, all_rows, discoveries, thresholds):
        g_str = f"{row['g']:+.4f}" if row["n"] > 0 else "—"
        p_str = f"{row['p']:.4f}" if row["n"] > 0 else "—"
        L.append(f"| {CANDIDATE_LABEL[name]} | {row['geom']} | {row['n']} | {g_str} | {p_str} | {thr:.4f} | "
                  f"{'SI' if disc else 'NO'} |")
    L.append("")
    n_disc = sum(discoveries)
    L.append(f"**{n_disc} scoperta/e su 22 test** al livello BH q = {Q_BH:.2f}.")
    L.append("")

    # --- Matrice di sovrapposizione (spec §2) -------------------------------------------------------
    L.append("## Matrice di sovrapposizione fra i setup (candidati 1-8)")
    L.append("")
    L.append("Per ogni coppia ORDINATA (riga, colonna): quota degli eventi della riga che hanno un evento "
              "della colonna nello stesso giorno, stesso lato, entro 15 minuti (`signal_ts`). Descrittiva: "
              "nessun criterio, non decide nulla da sola — serve solo a sapere se un ibrido futuro "
              "aggiungerebbe informazione o conterebbe due volte la stessa operazione (spec §2).")
    L.append("")
    header = "| da \\\\ a | " + " | ".join(all_names) + " |"
    L.append(header)
    L.append("|---|" + "---|" * len(all_names))
    for i in all_names:
        cells = []
        for j in all_names:
            v = ov.loc[i, j]
            cells.append("—" if pd.isna(v) else f"{v:.1%}")
        L.append(f"| {i} | " + " | ".join(cells) + " |")
    L.append("")

    L.append("## Come leggere questa tabella")
    L.append("")
    L.append("`g` è lo scarto tra la frequenza osservata (target prima dello stop) e il prior di passeggiata "
              "aleatoria `1/(1+rr)`. Il controllo di molteplicita' e' Benjamini-Hochberg (q = 0,10) sui 22 "
              "test di questo lotto: una geometria e' una **scoperta** se il suo p-value e' minore o uguale "
              "alla soglia BH assegnata al suo rango nell'ordinamento crescente dei p-value dell'intero "
              "lotto (non alla sua posizione naturale nella tabella). Una scoperta autorizza una milestone "
              "pre-registrata, il cui verdetto e' sull'OOS vergine, non su questi anni: e' un candidato, non "
              "un risultato. «EV senza costi» ed «R medio dopo costi» sono descrittivi: entrano nella lettura "
              "ma non nel criterio. Nessun filtro e' stato applicato: questo e' il setup nudo di ciascun "
              "candidato.")
    L.append("")

    md = "\n".join(L)
    out_dir = Path(cfg["backtest"]["reports_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "screen_batch2.md"
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"scritto {out} in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
