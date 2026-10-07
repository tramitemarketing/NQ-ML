"""TEST B (look-ahead nel placebo) e TEST C (segnale senza barriere).

SOSPETTO DA VERIFICARE (revisione esterna, e ha ragione di porlo): il placebo di `30_placebo_ingressi.py`
prende il LATO del trade vero, che e' deciso al trigger. Un ingresso placebo piazzato PRIMA del trigger
usa quindi il lato prima del movimento che ha generato il trigger: e' condizionato sul futuro. In piu' il
campione placebo e' condizionato su «quell'escursione ha poi prodotto un rientro» — sopravvivenza.

B1  — si divide il placebo +/-60 minuti in PRIMA e DOPO il trigger, e si misura il drift di ciascuno.
B2  — placebo CORRETTO: si rigioca la macchina a stati del detector bar per bar; a ogni barra 5m in cui
      almeno una macchina e' in stato BROKEN (il prezzo e' uscito dalla value area su quel lato e non e'
      ancora rientrato) il LATO e' noto causalmente, con i soli dati fino a quell'istante. Si entra
      all'open della barra 5m successiva, stessa convenzione del detector. Include anche le rotture che
      NON sono mai rientrate: niente sopravvivenza.
C   — rendimenti a ORIZZONTE FISSO (5, 15, 30, 60 minuti e chiusura) nella direzione del trade, in unita'
      di ATR. Nessuno stop, nessun target, nessuna convenzione di riempimento: se il setup ha un segnale,
      deve vedersi qui.

Tutto su training 2016-2023 ed estensione 2010-2016. OOS e cassaforte non toccati. Seme fisso.

Uso: .venv\\Scripts\\python scripts\\32_test_b_c_placebo.py
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
from nqml.profile.sessions import _hm, ny_minutes, on_mask
from nqml.profile.volume_profile import VolumeProfile
from nqml.screen.atr import previous_day_atr

MULT = np.array([0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
PANELS = {"2010-2016": (dt.date(2010, 6, 7), dt.date(2016, 9, 20)),
          "2016-2023": (dt.date(2016, 9, 20), dt.date(2023, 10, 1))}
N = len(MULT)
HOR = [5, 15, 30, 60]


def grid(h, l, close_last, entry, u, atr, tick):
    """Le 49 celle, convenzioni invariate (stop vince i pareggi, target su trade-through di 1 tick)."""
    fav = np.maximum.accumulate(u * (h - entry) if u > 0 else u * (l - entry))
    avv = np.maximum.accumulate(u * (entry - l) if u > 0 else u * (entry - h))
    n = len(fav)
    t_pts, s_pts = MULT * atr + tick, MULT * atr
    k_t = np.searchsorted(fav, t_pts, side="left")
    k_s = np.searchsorted(avv, s_pts, side="left")
    pnl_time = u * (close_last - entry)
    out = np.empty((N, N))
    for i in range(N):
        ks = k_s[i]
        for j in range(N):
            kt = k_t[j]
            out[i, j] = pnl_time if (kt >= n and ks >= n) else (MULT[j] * atr if kt < ks else -s_pts[i])
    return out / atr


def horizons(close_arr, k0, entry, u, atr):
    """Rendimenti a orizzonte fisso in ATR: 5/15/30/60 minuti dopo l'ingresso, e alla chiusura."""
    n = len(close_arr)
    out = []
    for hmin in HOR:
        k = k0 + hmin
        out.append(u * (float(close_arr[min(k, n - 1)]) - entry) / atr)
    out.append(u * (float(close_arr[-1]) - entry) / atr)
    return np.array(out)


def broken_states(day_bars1m, cfg):
    """Rigioca la macchina a stati come `run_day`, e per ogni indice di barra 5m restituisce i lati con
    una macchina in stato BROKEN **dopo** l'aggiornamento di quella barra (informazione disponibile a
    quell'istante, nessun dato futuro)."""
    tick, pct = cfg["instrument"]["tick_size"], cfg["detector"]["value_area_pct"]
    max_min = cfg["detector"]["max_excursion_minutes"]
    rth_open, rth_close, on_open = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"], cfg["sessions"]["on_open"]
    on = VolumeProfile(tick)
    on.add_bars(day_bars1m.loc[on_mask(day_bars1m.index, on_open, rth_open)])
    on_va = on.value_area(pct)
    rth = rth_bars(day_bars1m, rth_open, rth_close)
    if len(rth) < cfg["sessions"]["min_rth_bars"]:
        return None, None
    bars5 = resample_5m(rth)
    groups = {ts: g for ts, g in rth.groupby(five_min_bin(rth.index))}
    machines = [SetupDetector(vt, sd, max_min, tick) for vt in ("ON", "DEV") for sd in ("long", "short")]
    dev = VolumeProfile(tick)
    rows = list(bars5.itertuples())
    states: list[set[str]] = []
    for r in rows:
        dev.add_bars(groups[r.Index])
        dev_va = dev.value_area(pct)
        bar = Bar5m(r.Index, r.open, r.high, r.low, r.close, r.volume)
        for m in machines:
            m.on_bar(bar, on_va if m.va_type == "ON" else dev_va)
        states.append({m.side for m in machines if m.state == "BROKEN"})
    return rows, states


def run_panel(name, lo, hi, bars, cfg):
    tick = cfg["instrument"]["tick_size"]
    last_entry = cfg["detector"]["last_entry"]
    ev_path = Path("data/ext/events_ext.parquet") if name == "2010-2016" else Path(cfg["data"]["events_dir"]) / "events.parquet"
    events = pd.read_parquet(ev_path)
    events["session_date"] = pd.to_datetime(events["session_date"]).dt.date
    events = events[(events["session_date"] >= lo) & (events["session_date"] < hi)]
    ev_by_day: dict[dt.date, list[dict]] = {}
    for r in events.to_dict("records"):
        ev_by_day.setdefault(r["session_date"], []).append(r)
    atr_map = previous_day_atr(bars, cfg)
    ts_stop = time_stop_minute(cfg)
    rng = np.random.default_rng(2026)

    # accumulatori: per ciascun gruppo, drift per cella (giorno->lista) e orizzonti (giorno->lista)
    groups_d: dict[str, dict] = {k: {} for k in ("setup", "b1_prima", "b1_dopo", "b2")}
    groups_h: dict[str, dict] = {k: {} for k in ("setup", "b1_prima", "b1_dopo", "b2")}
    t0 = time.time()
    for sd, day in sessions_iter(bars):
        if not (lo <= sd < hi):
            continue
        atr = atr_map.get(sd)
        if atr is None or not np.isfinite(atr) or atr <= 0:
            continue
        rth_full = rth_bars(day, cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"])
        rth = rth_full.loc[ny_minutes(rth_full.index) <= ts_stop]
        if len(rth) == 0:
            continue
        h1, l1, c1 = rth["high"].to_numpy(), rth["low"].to_numpy(), rth["close"].to_numpy()
        c_last = float(c1[-1])
        mins = ny_minutes(rth.index)

        def add(group, k0, u, e):
            go = grid(h1[k0:], l1[k0:], c_last, e, u, float(atr), tick)
            gm = grid(h1[k0:], l1[k0:], c_last, e, -u, float(atr), tick)
            groups_d[group].setdefault(sd, []).append((go - gm) / 2.0)
            groups_h[group].setdefault(sd, []).append(horizons(c1, k0, e, u, float(atr)))

        # --- setup vero, e B1 (placebo +/-60 diviso prima/dopo il trigger) ---
        for r in ev_by_day.get(sd, []):
            k_real = int(rth.index.get_indexer([pd.Timestamp(r["entry_ts"])], method="nearest")[0])
            if k_real < 0 or k_real >= len(rth):
                continue
            u = 1 if r["side"] == "long" else -1
            add("setup", k_real, u, float(r["entry_price"]))
            elig = np.flatnonzero(mins <= _hm(last_entry))
            for lab, sel in (("b1_prima", elig[(elig < k_real) & (elig >= k_real - 60)]),
                             ("b1_dopo", elig[(elig > k_real) & (elig <= k_real + 60)])):
                if len(sel) == 0:
                    continue
                for k0 in rng.choice(sel, size=min(3, len(sel)), replace=False):
                    add(lab, int(k0), u, float(rth["open"].to_numpy()[k0]))

        # --- B2: placebo causale, lato dalla macchina a stati, tutte le rotture (anche mai rientrate) ---
        rows5, states = broken_states(day, cfg)
        if rows5 is None:
            continue
        cand = []
        for i, st in enumerate(states):
            if not st or i + 1 >= len(rows5) or not entry_allowed(rows5[i + 1].Index, last_entry):
                continue
            for side in st:
                cand.append((rows5[i + 1].Index, float(rows5[i + 1].open), 1 if side == "long" else -1))
        if cand:
            n_take = min(len(cand), max(1, 3 * len(ev_by_day.get(sd, []))) if ev_by_day.get(sd) else 3)
            for idx in rng.choice(len(cand), size=n_take, replace=False):
                ts, e, u = cand[idx]
                k0 = int(rth.index.get_indexer([ts], method="nearest")[0])
                if 0 <= k0 < len(rth):
                    add("b2", k0, u, e)
    res = {}
    for g in groups_d:
        dd, hh = groups_d[g], groups_h[g]
        n = sum(len(v) for v in dd.values())
        if n == 0:
            continue
        drift = np.sum([np.sum(v, axis=0) for v in dd.values()], axis=0) / n
        hor = np.sum([np.sum(v, axis=0) for v in hh.values()], axis=0) / n
        # CI a blocchi per giorno sugli orizzonti
        ds = np.array([np.sum(v, axis=0) for v in hh.values()]); dn = np.array([len(v) for v in hh.values()])
        r2 = np.random.default_rng(0)
        idx = r2.integers(0, len(dn), (4000, len(dn)))
        boots = ds[idx].sum(axis=1) / dn[idx].sum(axis=1)[:, None]
        res[g] = dict(n=n, drift=drift, hor=hor,
                      hlo=np.percentile(boots, 2.5, axis=0), hhi=np.percentile(boots, 97.5, axis=0))
    print(f"{name}: " + " | ".join(f"{g} n={res[g]['n']}" for g in res) + f" ({time.time()-t0:.0f}s)", flush=True)
    return res


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    out = Path("data/ext"); out.mkdir(parents=True, exist_ok=True)
    L = [f"TEST B e C — config {config_hash('config.yaml')} commit {git_commit()}"]
    labels = {"setup": "SETUP (ingressi veri)", "b1_prima": "B1 PRIMA del trigger",
              "b1_dopo": "B1 DOPO il trigger", "b2": "B2 placebo causale (lato da macchina a stati)"}
    for name, (lo, hi) in PANELS.items():
        R = run_panel(name, lo, hi, bars, cfg)
        L.append(f"\n=== {name} — DRIFT medio sulle 49 celle (unita' ATR) ===")
        for g, lab in labels.items():
            if g in R:
                L.append(f"  {lab:<46} n {R[g]['n']:>6}   drift medio {R[g]['drift'].mean():+.4f}")
        if "setup" in R:
            for g in ("b1_prima", "b1_dopo", "b2"):
                if g in R:
                    L.append(f"  differenza setup - {g:<12}: {R['setup']['drift'].mean() - R[g]['drift'].mean():+.4f}")
        L.append(f"\n=== {name} — TEST C: rendimenti a orizzonte fisso in ATR (CI 95% a blocchi per giorno) ===")
        L.append(f"  {'gruppo':<46}" + "".join(f"{str(h)+'m':>22}" for h in HOR) + f"{'close':>22}")
        for g, lab in labels.items():
            if g not in R:
                continue
            cells = "".join(f"{R[g]['hor'][k]:>+8.4f} [{R[g]['hlo'][k]:+.3f},{R[g]['hhi'][k]:+.3f}]"
                            for k in range(len(HOR) + 1))
            L.append(f"  {lab:<46}" + cells)
        print("\n".join(L[-14:]), flush=True)
    (out / "test_b_c.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\nscritto data/ext/test_b_c.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
