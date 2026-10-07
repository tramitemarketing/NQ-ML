"""Mappa esplorativa della superficie EV su (stop, target) per il setup value-area.

**Esplorativa e dichiarata tale**: nessuna pretesa confermativa, nessuna geometria «avanza», nessun criterio.
Serve a rispondere a una domanda di fisica, non di trading: sotto martingala l'EV e' zero per QUALUNQUE coppia
stop/target (optional stopping), quindi una mappa della superficie mostra dove il mercato devia dalla
martingala — se in una regione sistematica o in modo sparso.

Due pannelli: 2016-09-20 -> 2023-09-30 (training, gia' guardato molte volte) e 2010-06-07 -> 2016-09-19
(estensione). L'OOS 2023-10 -> 2026-03 e la cassaforte NON vengono letti.

Geometrie: stop e target in multipli di ATR(14, 5m) del giorno precedente, griglia 7x7 = 49 celle.
Convenzioni gia' pre-registrate: target riempito solo su trade-through di 1 tick, stop al prezzo di stop,
uscita a tempo alla chiusura delle 15:55. EV in unita' di ATR (invariante di scala).

Trucco numerico: le 49 geometrie di un evento condividono il percorso. Si calcolano una volta i massimi e
minimi CORRENTI (monotoni) e si usa una ricerca binaria per trovare quando ciascuna barriera e' toccata.

Uso: .venv\\Scripts\\python scripts\\27_mappa_geometrie.py
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


def event_grid(path_high: np.ndarray, path_low: np.ndarray, close_last: float,
               entry: float, u: int, atr: float, tick: float) -> np.ndarray:
    """EV in unita' di ATR per ciascuna delle 49 celle, per un singolo evento.

    `path_high`/`path_low`: massimi/minimi CORRENTI (cumulati) del percorso dopo l'ingresso, in punti
    firmati rispetto all'ingresso e nella direzione del trade: fav[k] = miglior escursione a favore fino a k,
    avv[k] = peggiore escursione contraria fino a k. Entrambi monotoni non decrescenti -> searchsorted.
    """
    fav = u * (path_high - entry) if u > 0 else u * (path_low - entry)
    avv = u * (entry - path_low) if u > 0 else u * (entry - path_high)
    fav = np.maximum.accumulate(fav)
    avv = np.maximum.accumulate(avv)
    n = len(fav)
    out = np.empty((len(MULT), len(MULT)))
    t_pts = MULT * atr + tick          # trade-through di 1 tick
    s_pts = MULT * atr
    k_t = np.searchsorted(fav, t_pts, side="left")     # primo minuto in cui il target e' superato
    k_s = np.searchsorted(avv, s_pts, side="left")     # primo minuto in cui lo stop e' toccato
    pnl_time = u * (close_last - entry)
    for i, s in enumerate(s_pts):                       # riga = stop
        ks = k_s[i]
        for j, t in enumerate(t_pts):                   # colonna = target
            kt = k_t[j]
            if kt >= n and ks >= n:
                pnl = pnl_time
            elif kt < ks:
                pnl = MULT[j] * atr                     # target: si esce al livello, non al trade-through
            elif ks < kt:
                pnl = -s
            else:                                       # stesso minuto: convenzione conservativa = stop
                pnl = -s
            out[i, j] = pnl / atr
    return out


def run_panel(name: str, lo: dt.date, hi: dt.date, bars: pd.DataFrame, cfg: dict) -> tuple[np.ndarray, np.ndarray, int]:
    tick = cfg["instrument"]["tick_size"]
    ev_path = Path("data/ext/events_ext.parquet") if name == "2010-2016" else Path(cfg["data"]["events_dir"]) / "events.parquet"
    events = pd.read_parquet(ev_path)
    events["session_date"] = pd.to_datetime(events["session_date"]).dt.date
    events = events[(events["session_date"] >= lo) & (events["session_date"] < hi)]
    atr_map = previous_day_atr(bars, cfg)
    ts_stop = time_stop_minute(cfg)          # minuto NY dell'uscita a tempo, come nel labeler
    days = {}
    for sd, day in sessions_iter(bars):
        if lo <= sd < hi:
            r = rth_bars(day, cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"])
            days[sd] = r.loc[ny_minutes(r.index) <= ts_stop]   # tagliato una volta per giornata
    acc = np.zeros((len(MULT), len(MULT))); cnt = 0
    per_day: dict[dt.date, list[np.ndarray]] = {}
    t0 = time.time()
    for i, r in enumerate(events.to_dict("records")):
        sd = r["session_date"]
        rth = days.get(sd); atr = atr_map.get(sd)
        if rth is None or atr is None or not np.isfinite(atr) or atr <= 0:
            continue
        ets = pd.Timestamp(r["entry_ts"])
        path = rth.loc[rth.index >= ets]
        if len(path) == 0:
            continue
        u = 1 if r["side"] == "long" else -1
        g = event_grid(path["high"].to_numpy(), path["low"].to_numpy(), float(path["close"].iloc[-1]),
                       float(r["entry_price"]), u, float(atr), tick)
        acc += g; cnt += 1
        per_day.setdefault(sd, []).append(g)
        if (i + 1) % 4000 == 0:
            print(f"  {name}: {i+1}/{len(events)} ({time.time()-t0:.0f}s)", flush=True)
    mean = acc / max(cnt, 1)
    # CI a blocchi per giorno, 2000 ricampionamenti
    day_sums = np.array([np.sum(v, axis=0) for v in per_day.values()])
    day_ns = np.array([len(v) for v in per_day.values()])
    rng = np.random.default_rng(0); B = 2000
    idx = rng.integers(0, len(day_ns), (B, len(day_ns)))
    boots = day_sums[idx].sum(axis=1) / day_ns[idx].sum(axis=1)[:, None, None]
    lo_ci = np.percentile(boots, 2.5, axis=0); hi_ci = np.percentile(boots, 97.5, axis=0)
    sig = np.where(lo_ci > 0, 1, np.where(hi_ci < 0, -1, 0))
    print(f"{name}: {cnt} eventi, {len(per_day)} giorni ({time.time()-t0:.0f}s)", flush=True)
    return mean, sig, cnt


def show(name: str, mean: np.ndarray, sig: np.ndarray, n: int) -> str:
    L = [f"\n=== {name} — EV medio in unita' di ATR, per cella (n {n}) ===",
         "righe = stop (x ATR), colonne = target (x ATR); * = CI 95% esclude lo zero",
         "        " + "".join(f"{m:>9}" for m in MULT)]
    for i, s in enumerate(MULT):
        cells = "".join(f"{mean[i,j]:>+8.3f}{'*' if sig[i,j] else ' '}" for j in range(len(MULT)))
        L.append(f"s={s:<5} {cells}")
    return "\n".join(L)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    out = Path("data/ext"); out.mkdir(parents=True, exist_ok=True)
    txt = [f"Mappa esplorativa delle geometrie — config {config_hash('config.yaml')} commit {git_commit()}",
           "ESPLORATIVA: nessuna pretesa confermativa, nessuna geometria avanza, nessun criterio applicato."]
    res = {}
    for name, (lo, hi) in PANELS.items():
        mean, sig, n = run_panel(name, lo, hi, bars, cfg)
        res[name] = (mean, sig, n)
        s = show(name, mean, sig, n)
        print(s, flush=True); txt.append(s)
        np.save(out / f"mappa_{name}.npy", mean)
    if len(res) == 2:
        d = res["2016-2023"][0] - res["2010-2016"][0]
        s = "\n=== DIFFERENZA (2016-2023 meno 2010-2016), in ATR ===\n" + \
            "        " + "".join(f"{m:>9}" for m in MULT) + "\n" + \
            "\n".join(f"s={MULT[i]:<5} " + "".join(f"{d[i,j]:>+9.3f}" for j in range(len(MULT))) for i in range(len(MULT)))
        print(s, flush=True); txt.append(s)
    (out / "mappa_geometrie.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
    print(f"\nscritto data/ext/mappa_geometrie.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
