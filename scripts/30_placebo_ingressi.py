"""Controllo placebo: la superficie `micro` della mappa dipende dal setup, o e' una proprieta' di
qualunque ingresso in quelle giornate?

`29_specchio_mappa.py` mostra che la mappa negativa e' quasi tutta componente **micro** — colpisce
identicamente il trade e il suo specchio. Due spiegazioni restano in piedi:

  (a) PROPRIETA' DELL'ISTANTE: il setup entra in momenti di volatilita' elevata rispetto all'ATR del
      giorno prima, quindi le barriere tarate su quell'ATR sono troppo strette e lo stop largo viene
      colpito piu' spesso di quanto preveda un cammino aleatorio;
  (b) PROPRIETA' DELLO STRUMENTO: NQ ha code piu' grasse di un moto browniano a qualunque ora, e la
      superficie si vedrebbe uguale entrando a caso.

Il controllo: per ogni evento si estraggono `K` istanti d'ingresso **a caso** nella stessa sessione
(stessa finestra oraria ammessa, stesso lato, stesse distanze in ATR del giorno prima) e si ricostruisce
la stessa mappa. Se la superficie placebo e' uguale, la risposta e' (b) e il setup non c'entra nulla.

Esplorativo, stessi due pannelli, nessuna pretesa confermativa. Seme fisso.

Uso: .venv\\Scripts\\python scripts\\30_placebo_ingressi.py
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from nqml.config import config_hash, git_commit, load_config
from nqml.data.bars import load_bars, rth_bars, sessions_iter
from nqml.detector.run_day import entry_allowed
from nqml.labels.labeler import time_stop_minute
from nqml.profile.sessions import _hm, ny_minutes
from nqml.screen.atr import previous_day_atr

MULT = np.array([0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
PANELS = {"2010-2016": (dt.date(2010, 6, 7), dt.date(2016, 9, 20)),
          "2016-2023": (dt.date(2016, 9, 20), dt.date(2023, 10, 1))}
N = len(MULT)
K = 3           # ingressi placebo per evento reale


def grid(h, l, close_last, entry, u, atr, tick):
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


def ci_from_days(per_day: dict, B: int = 4000, seed: int = 0):
    ds = np.array([np.sum(v, axis=0) for v in per_day.values()])
    dn = np.array([len(v) for v in per_day.values()])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(dn), (B, len(dn)))
    boots = ds[idx].sum(axis=1) / dn[idx].sum(axis=1)[:, None, None]
    return np.percentile(boots, 2.5, axis=0), np.percentile(boots, 97.5, axis=0)


def run_panel(name, lo, hi, bars, cfg, mode: str = "uniform", window_min: int = 60):
    """mode='uniform': istante a caso in tutta la finestra d'ingresso ammessa.
    mode='locale': istante a caso entro +/- `window_min` minuti dall'ingresso vero, escluso l'ingresso
    stesso. Serve a togliere il confondente del tempo rimasto: la deriva contraria cresce con le ore che
    restano, quindi un placebo a inizio giornata non e' confrontabile con un ingresso vero delle 13."""
    tick = cfg["instrument"]["tick_size"]
    last_entry = cfg["detector"].get("last_entry", "15:30")
    ev_path = Path("data/ext/events_ext.parquet") if name == "2010-2016" else Path(cfg["data"]["events_dir"]) / "events.parquet"
    events = pd.read_parquet(ev_path)
    events["session_date"] = pd.to_datetime(events["session_date"]).dt.date
    events = events[(events["session_date"] >= lo) & (events["session_date"] < hi)]
    atr_map = previous_day_atr(bars, cfg)
    ts_stop = time_stop_minute(cfg)
    days = {}
    for sd, day in sessions_iter(bars):
        if lo <= sd < hi:
            r = rth_bars(day, cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"])
            days[sd] = r.loc[ny_minutes(r.index) <= ts_stop]
    rng = np.random.default_rng(12345)
    pdm: dict = {}          # micro placebo
    pdd: dict = {}          # drift placebo
    mins_used: list[int] = []; mins_real: list[int] = []
    cnt = 0; t0 = time.time()
    for r in events.to_dict("records"):
        sd = r["session_date"]
        rth = days.get(sd); atr = atr_map.get(sd)
        if rth is None or atr is None or not np.isfinite(atr) or atr <= 0:
            continue
        mins = ny_minutes(rth.index)
        elig = np.flatnonzero(mins <= _hm(last_entry))
        if mode == "locale":
            k_real = int(rth.index.get_indexer([pd.Timestamp(r["entry_ts"])], method="nearest")[0])
            elig = elig[(np.abs(elig - k_real) <= window_min) & (elig != k_real)]
        if len(elig) < 2:
            continue
        u = 1 if r["side"] == "long" else -1
        h_all, l_all, o_all = rth["high"].to_numpy(), rth["low"].to_numpy(), rth["open"].to_numpy()
        c_last = float(rth["close"].iloc[-1])
        mins_real.append(int(mins[int(rth.index.get_indexer([pd.Timestamp(r["entry_ts"])], method="nearest")[0])]))
        for k0 in rng.choice(elig, size=min(K, len(elig)), replace=False):
            mins_used.append(int(mins[k0]))
            e = float(o_all[k0])                      # open della barra scelta: stessa convenzione del detector
            h, l = h_all[k0:], l_all[k0:]
            g_o = grid(h, l, c_last, e, u, float(atr), tick)
            g_m = grid(h, l, c_last, e, -u, float(atr), tick)
            pdm.setdefault(sd, []).append((g_o + g_m) / 2.0)
            pdd.setdefault(sd, []).append((g_o - g_m) / 2.0)
            cnt += 1
    res = {"n": cnt, "min_medio": float(np.mean(mins_used)), "min_medio_reale": float(np.mean(mins_real))}
    for key, store in (("micro", pdm), ("drift", pdd)):
        mean = np.sum([np.sum(v, axis=0) for v in store.values()], axis=0) / cnt
        res[key] = (mean,) + ci_from_days(store)
    print(f"{name} [{mode}]: {cnt} ingressi placebo, {len(pdm)} giorni, minuto NY medio "
          f"{res['min_medio']:.0f} vs {res['min_medio_reale']:.0f} reale ({time.time()-t0:.0f}s)", flush=True)
    return res


def table(title, mean, lo_ci, hi_ci):
    L = [title, "        " + "".join(f"{x:>9}" for x in MULT)]
    for i in range(N):
        L.append(f"s={MULT[i]:<5} " + "".join(
            f"{mean[i,j]:>+8.3f}" + ("*" if (lo_ci[i, j] > 0 or hi_ci[i, j] < 0) else " ") for j in range(N)))
    return "\n".join(L)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    out = Path("data/ext"); out.mkdir(parents=True, exist_ok=True)
    txt = [f"Placebo ingressi — config {config_hash('config.yaml')} commit {git_commit()}",
           f"ESPLORATIVO. {K} ingressi casuali per evento reale, stessa sessione, stesso lato, stesse "
           "distanze in ATR. Confronto con le superfici di 29."]
    for name, (lo, hi) in PANELS.items():
        for mode in ("uniform", "locale"):
            R = run_panel(name, lo, hi, bars, cfg, mode=mode)
            for key, label in (("micro", "MICRO placebo"), ("drift", "DRIFT placebo")):
                b = table(f"\n=== {name} [{mode}] — {label} (n {R['n']}, minuto NY medio "
                          f"{R['min_medio']:.0f} vs {R['min_medio_reale']:.0f} reale) ===", *R[key])
                print(b, flush=True); txt.append(b)
            s = (f"\nsintesi placebo {name} [{mode}]: micro medio {R['micro'][0].mean():+.4f} | "
                 f"drift medio {R['drift'][0].mean():+.4f}")
            print(s, flush=True); txt.append(s)
    (out / "placebo_ingressi.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
    print("\nscritto data/ext/placebo_ingressi.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
