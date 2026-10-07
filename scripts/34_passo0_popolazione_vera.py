"""PASSO 0 — il lordo a 60 minuti sulla popolazione VERA del §1.

Il TEST C aveva misurato B2 su un proxy, non sulla popolazione che si intende testare
(`32_test_b_c_placebo.py` riga 171: sottocampione di `3 x eventi_value_area_del_giorno`, prima barra della
rottura inclusa, ponderazione correlata al carattere della giornata). Qui si scompone un passo alla volta.

Quattro popolazioni, stessi trigger e stessa uscita (tempo fisso 60 minuti, lordo in unita' di ATR):

  A = PROXY          sottocampione `3 x eventi del giorno`, prima barra INCLUSA  (la regola di 32)
  B = TUTTI          tutti i candidati del giorno, prima barra INCLUSA           (tolta la ponderazione)
  C = §1             tutti i candidati del giorno, prima barra ESCLUSA           (la popolazione vera)
  D = SOLO PRIMA     solo le prime barre di ogni rottura                         (la parte tolta da B a C)

B e' la media di C e D pesata per numerosita': e' un controllo di coerenza aritmetica.
A viene rifatto con TRE semi diversi, per distinguere «estrazione fortunata» da «regola di campionamento».

Entrambi i periodi: training 2016-09-20 -> 2023-09-30 ed estensione 2010-06-07 -> 2016-09-19.
CI 95 % a blocchi per giorno, 10.000 ricampionamenti, seme 0. OOS e cassaforte NON toccati.

Uso: .venv\\Scripts\\python scripts\\34_passo0_popolazione_vera.py
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
from nqml.labels.labeler import time_stop_minute
from nqml.profile.sessions import ny_minutes, on_mask
from nqml.profile.volume_profile import VolumeProfile
from nqml.screen.atr import previous_day_atr

PANELS = {"2010-2016": (dt.date(2010, 6, 7), dt.date(2016, 9, 20)),
          "2016-2023": (dt.date(2016, 9, 20), dt.date(2023, 10, 1))}
HORIZON = 60          # minuti, uscita unica pre-registrata
PROXY_SEEDS = (1, 2, 3)


def day_candidates(day, cfg, ts_stop):
    """Per una sessione: (rth 1m troncato al time stop, lista di candidati B2).

    Ogni candidato e' (indice 1m d'ingresso, prezzo d'ingresso, u, prima_barra_della_rottura).
    Replica esattamente il ciclo di `run_day`, e legge lo stato DOPO l'aggiornamento della barra: solo
    dati fino a quell'istante."""
    tick, pct = cfg["instrument"]["tick_size"], cfg["detector"]["value_area_pct"]
    max_min, last_entry = cfg["detector"]["max_excursion_minutes"], cfg["detector"]["last_entry"]
    ro, rc, oo = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"], cfg["sessions"]["on_open"]
    rth_full = rth_bars(day, ro, rc)
    if len(rth_full) < cfg["sessions"]["min_rth_bars"]:
        return None, []
    rth = rth_full.loc[ny_minutes(rth_full.index) <= ts_stop]
    if len(rth) == 0:
        return None, []
    on = VolumeProfile(tick); on.add_bars(day.loc[on_mask(day.index, oo, ro)])
    on_va = on.value_area(pct)
    b5 = resample_5m(rth_full); groups = {ts: g for ts, g in rth_full.groupby(five_min_bin(rth_full.index))}
    ms = [SetupDetector(vt, s, max_min, tick) for vt in ("ON", "DEV") for s in ("long", "short")]
    dev = VolumeProfile(tick); rows = list(b5.itertuples())
    cand = []
    for i, r in enumerate(rows):
        dev.add_bars(groups[r.Index]); dva = dev.value_area(pct)
        bar = Bar5m(r.Index, r.open, r.high, r.low, r.close, r.volume)
        for m in ms:
            m.on_bar(bar, on_va if m.va_type == "ON" else dva)
        if i + 1 >= len(rows) or not entry_allowed(rows[i + 1].Index, last_entry):
            continue
        k0 = int(rth.index.get_indexer([rows[i + 1].Index], method="nearest")[0])
        if k0 < 0 or k0 >= len(rth):
            continue
        for m in ms:
            if m.state == "BROKEN":
                cand.append((k0, float(rows[i + 1].open), 1 if m.side == "long" else -1,
                             m._bars_outside == 1))
    return rth, cand


def ci(per_day: dict, n_boot: int = 10000, seed: int = 0):
    """Media per evento e CI 95 % a blocchi per giorno (ricampiona giornate intere)."""
    if not per_day:
        return float("nan"), (float("nan"), float("nan")), 0, 0
    sums = np.array([sum(v) for v in per_day.values()], dtype=float)
    ns = np.array([len(v) for v in per_day.values()], dtype=float)
    point = sums.sum() / ns.sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ns), (n_boot, len(ns)))
    boots = sums[idx].sum(axis=1) / ns[idx].sum(axis=1)
    return point, (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))), int(ns.sum()), len(ns)


def run_panel(name, lo, hi, bars, cfg):
    ev = pd.read_parquet(Path("data/ext/events_ext.parquet") if name == "2010-2016"
                         else Path(cfg["data"]["events_dir"]) / "events.parquet")
    ev["session_date"] = pd.to_datetime(ev["session_date"]).dt.date
    n_real = ev[(ev["session_date"] >= lo) & (ev["session_date"] < hi)].groupby("session_date").size().to_dict()
    atr_map = previous_day_atr(bars, cfg)
    ts_stop = time_stop_minute(cfg)
    pd_all = {k: {} for k in ("B", "C", "D")}
    pd_proxy = {s: {} for s in PROXY_SEEDS}
    rngs = {s: np.random.default_rng(s) for s in PROXY_SEEDS}
    t0 = time.time(); n_days = 0
    for sd, day in sessions_iter(bars):
        if not (lo <= sd < hi):
            continue
        atr = atr_map.get(sd)
        if atr is None or not np.isfinite(atr) or atr <= 0:
            continue
        rth, cand = day_candidates(day, cfg, ts_stop)
        if rth is None or not cand:
            continue
        n_days += 1
        c1 = rth["close"].to_numpy(dtype=float); n1 = len(c1)

        def ret(k0, e, u):
            return u * (c1[min(k0 + HORIZON, n1 - 1)] - e) / float(atr)

        vals = [ret(k0, e, u) for k0, e, u, _ in cand]
        first = [f for _, _, _, f in cand]
        pd_all["B"].setdefault(sd, []).extend(vals)
        for v, f in zip(vals, first):
            pd_all["D" if f else "C"].setdefault(sd, []).append(v)
        # A: la regola del proxy, con tre semi indipendenti
        k = n_real.get(sd, 0)
        n_take = min(len(cand), 3 * k if k else 3)
        for s in PROXY_SEEDS:
            pick = rngs[s].choice(len(cand), size=n_take, replace=False)
            pd_proxy[s].setdefault(sd, []).extend(vals[j] for j in pick)
    out = {k: ci(v) for k, v in pd_all.items()}
    out |= {f"A_seed{s}": ci(v) for s, v in pd_proxy.items()}
    print(f"{name}: {n_days} giorni ({time.time()-t0:.0f}s)", flush=True)
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    lab = {"B": "B  TUTTI, prima barra INCLUSA", "C": "C  §1: TUTTI, prima barra ESCLUSA",
           "D": "D  SOLO le prime barre (parte tolta)"}
    L = [f"PASSO 0 — config {config_hash('config.yaml')} commit {git_commit()}",
         f"lordo a {HORIZON} minuti, unita' di ATR, CI 95 % a blocchi per giorno (10.000, seme 0)",
         "proxy di riferimento misurato al TEST C: +0,1486 (2016-2023) e +0,1531 (2010-2016)"]
    res = {}
    for name, (lo, hi) in PANELS.items():
        R = run_panel(name, lo, hi, bars, cfg)
        res[name] = R
        L.append(f"\n=== {name} ===")
        for s in PROXY_SEEDS:
            p, c, n, d = R[f"A_seed{s}"]
            L.append(f"  A  PROXY (3 x eventi del giorno), seme {s:<2}   {p:>+8.4f} [{c[0]:+.4f}; {c[1]:+.4f}]  n {n:>7}  giorni {d}")
        for k in ("B", "C", "D"):
            p, c, n, d = R[k]
            L.append(f"  {lab[k]:<40} {p:>+8.4f} [{c[0]:+.4f}; {c[1]:+.4f}]  n {n:>7}  giorni {d}")
        pb, _, nb, _ = R["B"]; pc, _, nc, _ = R["C"]; pdd, _, nd_, _ = R["D"]
        check = (pc * nc + pdd * nd_) / (nc + nd_)
        L.append(f"  controllo aritmetico: (C*n_C + D*n_D)/(n_C+n_D) = {check:+.6f} contro B = {pb:+.6f}")
        print("\n".join(L[-8:]), flush=True)
    # verdetto sulla regola +/-30 % / <= 0, applicata al training
    pc_tr = res["2016-2023"]["C"][0]; pc_ext = res["2010-2016"]["C"][0]
    banda = (0.1486 * 0.7, 0.1486 * 1.3)
    L += ["", "=== VERDETTO PRE-REGISTRATO ===",
          f"  §1 training  {pc_tr:+.4f}   banda +/-30 % del proxy: [{banda[0]:+.4f}; {banda[1]:+.4f}]",
          f"  §1 estensione {pc_ext:+.4f}",
          f"  dentro la banda: {'SI' if banda[0] <= pc_tr <= banda[1] else 'NO'}",
          f"  training <= 0: {'SI -> FILONE CHIUSO, ES non si compra' if pc_tr <= 0 else 'NO'}",
          f"  periodi concordi di segno: {'SI' if np.sign(pc_tr) == np.sign(pc_ext) else 'NO -> CI SI FERMA'}"]
    print("\n".join(L[-7:]), flush=True)
    Path("data/ext").mkdir(parents=True, exist_ok=True)
    Path("data/ext/passo0.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\nscritto data/ext/passo0.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
