"""Diagnostico: quanta parte della mappa delle geometrie e' prodotta dalla nostra convenzione di
pareggio, e non dal mercato.

Quando stop e target cadono **nella stessa barra da 1 minuto**, l'OHLC non dice quale sia stato toccato
prima. `nqml.screen.wall2.r_gross` risolve sempre a favore dello stop (convenzione conservativa, gia'
dichiarata). Questa scelta e' prudente per un singolo backtest, ma su una mappa di geometrie introduce
una distorsione **crescente al restringersi delle barriere**: piu' le barriere sono strette, piu' spesso
sono entrambe dentro la stessa barra, e piu' spesso la convenzione decide al posto dei dati.

Per ogni cella (stop, target) si calcolano tre cose:
  1. la frazione di eventi ambigui (stop e target nella stessa barra);
  2. la mappa PESSIMISTA (stop vince i pareggi) = quella di 27_mappa_geometrie.py;
  3. la mappa OTTIMISTA (target vince i pareggi).

Il vero EV, qualunque sia, sta **fra le due**: sono limiti, non stime. Se lo zero sta dentro la forchetta,
quella cella non dice nulla sul mercato.

Esplorativo, stessi due pannelli di 27, nessuna pretesa confermativa.

Uso: .venv\\Scripts\\python scripts\\28_ambiguita_stessa_barra.py
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


def event_grids(path_high: np.ndarray, path_low: np.ndarray, close_last: float,
                entry: float, u: int, atr: float, tick: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(pessimista, ottimista, ambiguo) in unita' di ATR per le 49 celle di un evento."""
    fav = np.maximum.accumulate(u * (path_high - entry) if u > 0 else u * (path_low - entry))
    avv = np.maximum.accumulate(u * (entry - path_low) if u > 0 else u * (entry - path_high))
    n = len(fav)
    t_pts, s_pts = MULT * atr + tick, MULT * atr          # trade-through di 1 tick sul target
    k_t = np.searchsorted(fav, t_pts, side="left")
    k_s = np.searchsorted(avv, s_pts, side="left")
    pnl_time = u * (close_last - entry)
    pess = np.empty((N, N)); opt = np.empty((N, N)); amb = np.zeros((N, N))
    for i in range(N):
        ks = k_s[i]
        for j in range(N):
            kt = k_t[j]
            if kt >= n and ks >= n:
                pess[i, j] = opt[i, j] = pnl_time
            elif kt < ks:
                pess[i, j] = opt[i, j] = MULT[j] * atr
            elif ks < kt:
                pess[i, j] = opt[i, j] = -s_pts[i]
            else:                                          # stessa barra: decide la convenzione
                pess[i, j] = -s_pts[i]
                opt[i, j] = MULT[j] * atr
                amb[i, j] = 1.0
    return pess / atr, opt / atr, amb


def ci_from_days(per_day: dict, B: int = 2000, seed: int = 0):
    day_sums = np.array([np.sum(v, axis=0) for v in per_day.values()])
    day_ns = np.array([len(v) for v in per_day.values()])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(day_ns), (B, len(day_ns)))
    boots = day_sums[idx].sum(axis=1) / day_ns[idx].sum(axis=1)[:, None, None]
    return np.percentile(boots, 2.5, axis=0), np.percentile(boots, 97.5, axis=0)


def run_panel(name: str, lo: dt.date, hi: dt.date, bars: pd.DataFrame, cfg: dict):
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
    acc_p = np.zeros((N, N)); acc_o = np.zeros((N, N)); acc_a = np.zeros((N, N)); cnt = 0
    pd_p: dict = {}; pd_o: dict = {}
    t0 = time.time()
    for r in events.to_dict("records"):
        sd = r["session_date"]
        rth = days.get(sd); atr = atr_map.get(sd)
        if rth is None or atr is None or not np.isfinite(atr) or atr <= 0:
            continue
        path = rth.loc[rth.index >= pd.Timestamp(r["entry_ts"])]
        if len(path) == 0:
            continue
        u = 1 if r["side"] == "long" else -1
        p, o, a = event_grids(path["high"].to_numpy(), path["low"].to_numpy(),
                              float(path["close"].iloc[-1]), float(r["entry_price"]), u, float(atr), tick)
        acc_p += p; acc_o += o; acc_a += a; cnt += 1
        pd_p.setdefault(sd, []).append(p); pd_o.setdefault(sd, []).append(o)
    lo_p, hi_p = ci_from_days(pd_p)
    lo_o, hi_o = ci_from_days(pd_o)
    print(f"{name}: {cnt} eventi, {len(pd_p)} giorni ({time.time()-t0:.0f}s)", flush=True)
    return dict(n=cnt, pess=acc_p / cnt, opt=acc_o / cnt, amb=acc_a / cnt,
                lo_p=lo_p, hi_p=hi_p, lo_o=lo_o, hi_o=hi_o)


def table(title: str, m: np.ndarray, fmt: str = "{:>+8.3f}", mark=None) -> str:
    L = [title, "        " + "".join(f"{x:>9}" for x in MULT)]
    for i in range(N):
        cells = "".join(fmt.format(m[i, j]) + (mark(i, j) if mark else " ") for j in range(N))
        L.append(f"s={MULT[i]:<5} {cells}")
    return "\n".join(L)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    out = Path("data/ext"); out.mkdir(parents=True, exist_ok=True)
    txt = [f"Ambiguita' stessa barra — config {config_hash('config.yaml')} commit {git_commit()}",
           "ESPLORATIVO. La mappa di 27 e' la colonna PESSIMISTA. Il vero EV sta fra pessimista e ottimista."]
    for name, (lo, hi) in PANELS.items():
        R = run_panel(name, lo, hi, bars, cfg)
        blocks = [
            table(f"\n=== {name} — frazione di eventi AMBIGUI (stop e target nella stessa barra), n {R['n']} ===",
                  R["amb"], "{:>8.1%}"),
            table(f"\n=== {name} — PESSIMISTA (stop vince i pareggi) = mappa di 27 ===", R["pess"],
                  mark=lambda i, j, R=R: "*" if (R["lo_p"][i, j] > 0 or R["hi_p"][i, j] < 0) else " "),
            table(f"\n=== {name} — OTTIMISTA (target vince i pareggi) ===", R["opt"],
                  mark=lambda i, j, R=R: "*" if (R["lo_o"][i, j] > 0 or R["hi_o"][i, j] < 0) else " "),
        ]
        # verdetto per cella: lo zero sta dentro la forchetta pessimista-ottimista?
        dentro = (R["pess"] <= 0) & (R["opt"] >= 0)
        blocks.append(table(f"\n=== {name} — lo ZERO sta nella forchetta? (1 = si', la cella non dice nulla) ===",
                            dentro.astype(float), "{:>8.0f}"))
        blocks.append(f"celle in cui lo zero e' nella forchetta: {int(dentro.sum())}/{N*N}")
        for b in blocks:
            print(b, flush=True); txt.append(b)
    (out / "ambiguita_stessa_barra.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
    print("\nscritto data/ext/ambiguita_stessa_barra.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
