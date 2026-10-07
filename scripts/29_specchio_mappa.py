"""Decomposizione a specchio della mappa delle geometrie.

La mappa (27) e' negativa quasi ovunque in entrambi i pannelli, e il diagnostico dei pareggi (28) ha
escluso che sia la nostra convenzione a produrla. Restano due spiegazioni, e lo specchio le separa.

Per ogni evento si valuta la stessa griglia due volte:
  - ORIGINALE: nella direzione del segnale;
  - SPECCHIO: stesso istante, stesso prezzo d'ingresso, **direzione opposta**, stesse distanze in ATR.

Poi, per cella:
  micro = (orig + specchio) / 2   -> componente che colpisce entrambe le direzioni: costo/artefatto
  drift = (orig - specchio) / 2   -> componente direzionale: il mercato si muove contro (o a favore)

Sotto martingala entrambe valgono zero. Un `micro` negativo e piatto e' un costo per trade; un `drift`
negativo dice che il setup entra dalla parte sbagliata.

CI a blocchi per giorno, appaiate (originale e specchio vengono dagli stessi eventi e dagli stessi giorni).
Esplorativo, stessi due pannelli, nessuna pretesa confermativa.

Uso: .venv\\Scripts\\python scripts\\29_specchio_mappa.py
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
from nqml.labels.labeler import time_stop_minute
from nqml.profile.sessions import ny_minutes
from nqml.screen.atr import previous_day_atr

MULT = np.array([0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
PANELS = {"2010-2016": (dt.date(2010, 6, 7), dt.date(2016, 9, 20)),
          "2016-2023": (dt.date(2016, 9, 20), dt.date(2023, 10, 1))}
N = len(MULT)


def grid(path_high, path_low, close_last, entry, u, atr, tick):
    """EV in ATR per le 49 celle, convenzione di 27 (stop vince i pareggi, target su trade-through)."""
    fav = np.maximum.accumulate(u * (path_high - entry) if u > 0 else u * (path_low - entry))
    avv = np.maximum.accumulate(u * (entry - path_low) if u > 0 else u * (entry - path_high))
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
            if kt >= n and ks >= n:
                out[i, j] = pnl_time
            elif kt < ks:
                out[i, j] = MULT[j] * atr
            else:
                out[i, j] = -s_pts[i]
    return out / atr


def ci_from_days(per_day: dict, B: int = 4000, seed: int = 0):
    day_sums = np.array([np.sum(v, axis=0) for v in per_day.values()])
    day_ns = np.array([len(v) for v in per_day.values()])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(day_ns), (B, len(day_ns)))
    boots = day_sums[idx].sum(axis=1) / day_ns[idx].sum(axis=1)[:, None, None]
    return np.percentile(boots, 2.5, axis=0), np.percentile(boots, 97.5, axis=0)


def run_panel(name, lo, hi, bars, cfg):
    tick = cfg["instrument"]["tick_size"]
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
    pdm: dict = {}; pdd: dict = {}; pdo: dict = {}
    cnt = 0; t0 = time.time()
    for r in events.to_dict("records"):
        sd = r["session_date"]
        rth = days.get(sd); atr = atr_map.get(sd)
        if rth is None or atr is None or not np.isfinite(atr) or atr <= 0:
            continue
        path = rth.loc[rth.index >= pd.Timestamp(r["entry_ts"])]
        if len(path) == 0:
            continue
        h, l, c = path["high"].to_numpy(), path["low"].to_numpy(), float(path["close"].iloc[-1])
        e = float(r["entry_price"]); u = 1 if r["side"] == "long" else -1
        o = grid(h, l, c, e, u, float(atr), tick)
        m = grid(h, l, c, e, -u, float(atr), tick)
        pdo.setdefault(sd, []).append(o)
        pdm.setdefault(sd, []).append((o + m) / 2.0)      # micro
        pdd.setdefault(sd, []).append((o - m) / 2.0)      # drift
        cnt += 1
    res = {}
    for key, store in (("orig", pdo), ("micro", pdm), ("drift", pdd)):
        mean = np.sum([np.sum(v, axis=0) for v in store.values()], axis=0) / cnt
        lo_ci, hi_ci = ci_from_days(store)
        res[key] = (mean, lo_ci, hi_ci)
    print(f"{name}: {cnt} eventi, {len(pdo)} giorni ({time.time()-t0:.0f}s)", flush=True)
    res["n"] = cnt
    return res


def table(title, mean, lo_ci, hi_ci):
    L = [title, "        " + "".join(f"{x:>9}" for x in MULT)]
    for i in range(N):
        cells = "".join(f"{mean[i,j]:>+8.3f}" + ("*" if (lo_ci[i, j] > 0 or hi_ci[i, j] < 0) else " ")
                        for j in range(N))
        L.append(f"s={MULT[i]:<5} {cells}")
    return "\n".join(L)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    out = Path("data/ext"); out.mkdir(parents=True, exist_ok=True)
    txt = [f"Specchio della mappa — config {config_hash('config.yaml')} commit {git_commit()}",
           "ESPLORATIVO. micro=(orig+specchio)/2 (costo, colpisce entrambe le direzioni); "
           "drift=(orig-specchio)/2 (direzionale). * = CI 95% a blocchi per giorno esclude lo zero."]
    for name, (lo, hi) in PANELS.items():
        R = run_panel(name, lo, hi, bars, cfg)
        for key, label in (("orig", "ORIGINALE (= mappa di 27)"), ("micro", "MICRO — costo per trade"),
                           ("drift", "DRIFT — componente direzionale")):
            mean, lo_ci, hi_ci = R[key]
            b = table(f"\n=== {name} — {label} (n {R['n']}) ===", mean, lo_ci, hi_ci)
            print(b, flush=True); txt.append(b)
        mi = R["micro"][0]; dr = R["drift"][0]
        s = (f"\nsintesi {name}: micro medio {mi.mean():+.4f} (dev.st fra celle {mi.std():.4f}) | "
             f"drift medio {dr.mean():+.4f} (dev.st fra celle {dr.std():.4f})")
        print(s, flush=True); txt.append(s)
    (out / "specchio_mappa.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
    print("\nscritto data/ext/specchio_mappa.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
