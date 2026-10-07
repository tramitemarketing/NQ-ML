"""TEST A — micro sulla diagonale e variance ratio.

Sulla diagonale (s = t = d) il trade originale e il suo specchio condividono quasi gli stessi livelli, e
il PnL dovrebbe essere opposto evento per evento => micro = 0. Le uniche eccezioni sono MECCANICHE e
identificabili a priori. Con E = prezzo d'ingresso, u = +1 per il long:

  long  : stop a E-d      (scatta se low  <= E-d)         target a E+d (scatta se high >= E+d+tick)
  short : stop a E+d      (scatta se high >= E+d)         target a E-d (scatta se low  <= E-d-tick)

Quindi lo STOP di un lato scatta **un tick prima** del TARGET dell'altro: e' l'asimmetria del
trade-through, dichiarata da sempre nelle convenzioni, e NON e' la stessa cosa dell'ambiguita' di barra.
Definiti i primi istanti di attraversamento:
  a  = primo k con high >= E+d          (stop dello short)
  a' = primo k con high >= E+d+tick     (target del long)
  b  = primo k con low  <= E-d          (stop del long)
  b' = primo k con low  <= E-d-tick     (target dello short)
vale sempre a <= a' e b <= b'.

Le categorie esaustive di un evento sono:
  (0) ENTRAMBI A TEMPO      -> i due PnL sono opposti per costruzione   -> contributo a micro = 0 ESATTO
  (1) UNO VINCE, UNO PERDE  -> +d e -d                                  -> contributo a micro = 0 ESATTO
  (2) ENTRAMBI PERDONO      -> -d e -d                                  -> contributo -d       (meccanico)
  (3) UNO A TEMPO, L'ALTRO RISOLVE -> misto                             -> contributo != 0     (meccanico)
  (4) ENTRAMBI VINCONO      -> impossibile (si dimostra: b' >= b > a' >= a contraddice b' < a)

**Il test non circolare**: le categorie (0) e (1) devono contribuire ESATTAMENTE zero. Se non lo fanno,
c'e' un'asimmetria nel motore e tutto il resto e' sospeso. Le categorie (2) e (3) sono attese e si
quantificano; si riporta anche la previsione semplificata «-d x quota ambigua di barra» per mostrare di
quanto sia incompleta.

Si rifa' tutto anche con la convenzione OPPOSTA (il target vince i pareggi di barra), come richiesto.

In coda: variance ratio dei rendimenti a 1 minuto a 5/15/30/60 minuti sulle stesse sessioni (VR > 1 =
momentum; VR = 1 = passeggiata aleatoria).

Uso: .venv\\Scripts\\python scripts\\31_test_a_diagonale.py
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
CAT = ["0_entrambi_a_tempo", "1_uno_vince_uno_perde", "2_entrambi_perdono", "3_uno_a_tempo", "4_entrambi_vincono"]


def diagonale(h, l, close_last, entry, u, atr, tick, stop_vince: bool):
    """Per le 7 celle diagonali: (micro, categoria, quota ambigua di barra) evento per evento."""
    hi_fav = np.maximum.accumulate(u * (h - entry))       # escursione in su nella direzione del long
    lo_fav = np.maximum.accumulate(u * (entry - l))       # escursione in giu'
    n = len(h)
    d = MULT * atr
    a = np.searchsorted(hi_fav, d, side="left")           # stop dello short
    a1 = np.searchsorted(hi_fav, d + tick, side="left")   # target del long
    b = np.searchsorted(lo_fav, d, side="left")           # stop del long
    b1 = np.searchsorted(lo_fav, d + tick, side="left")   # target dello short
    t_pnl = u * (close_last - entry)
    micro = np.empty(N); cat = np.empty(N, dtype=int); amb = np.zeros(N)
    for j in range(N):
        aj, a1j, bj, b1j, dj = a[j], a1[j], b[j], b1[j], d[j]
        # long: target se a1 < b, stop se b <= a1 (o b < a1 se vince il target), tempo se entrambi fuori
        if a1j >= n and bj >= n:
            pl, rl = t_pnl, "t"
        elif a1j < bj or (not stop_vince and a1j == bj and a1j < n):
            pl, rl = +dj, "w"
        else:
            pl, rl = -dj, "s"
        # short: target se b1 < a, stop se a <= b1
        if b1j >= n and aj >= n:
            ps, rs = -t_pnl, "t"
        elif b1j < aj or (not stop_vince and b1j == aj and b1j < n):
            ps, rs = +dj, "w"
        else:
            ps, rs = -dj, "s"
        micro[j] = (pl + ps) / 2.0 / atr
        pair = {rl, rs}
        if rl == "t" and rs == "t":
            cat[j] = 0
        elif pair == {"w", "s"}:
            cat[j] = 1
        elif rl == "s" and rs == "s":
            cat[j] = 2
        elif "t" in pair:
            cat[j] = 3
        else:
            cat[j] = 4
        amb[j] = 1.0 if (min(a1j, bj) == min(b1j, aj) and min(a1j, bj) < n) else 0.0
    return micro, cat, amb


def run_panel(name, lo, hi, bars, cfg, stop_vince: bool):
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
    tot = np.zeros(N); per_cat = np.zeros((5, N)); n_cat = np.zeros((5, N)); amb_tot = np.zeros(N); cnt = 0
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
        m, c, ab = diagonale(path["high"].to_numpy(), path["low"].to_numpy(), float(path["close"].iloc[-1]),
                             float(r["entry_price"]), u, float(atr), tick, stop_vince)
        tot += m; amb_tot += ab; cnt += 1
        for j in range(N):
            per_cat[c[j], j] += m[j]; n_cat[c[j], j] += 1
    print(f"{name} [{'stop' if stop_vince else 'target'} vince]: {cnt} eventi ({time.time()-t0:.0f}s)", flush=True)
    return dict(n=cnt, micro=tot / cnt, per_cat=per_cat / cnt, quota=n_cat / cnt, amb=amb_tot / cnt)


def variance_ratio(bars, cfg, lo, hi, horizons=(5, 15, 30, 60)):
    """VR(q) = Var(r_q) / (q * Var(r_1)) su rendimenti logaritmici a 1 minuto, non sovrapposti,
    calcolati DENTRO ogni sessione RTH (nessun salto overnight)."""
    r1_all: list[np.ndarray] = []
    rq_all: dict[int, list[np.ndarray]] = {q: [] for q in horizons}
    for sd, day in sessions_iter(bars):
        if not (lo <= sd < hi):
            continue
        r = rth_bars(day, cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"])
        c = r["close"].to_numpy(dtype=float)
        if len(c) < 120:
            continue
        lp = np.log(c)
        r1_all.append(np.diff(lp))
        for q in horizons:
            idx = np.arange(0, len(lp) - 1, q)
            rq_all[q].append(np.diff(lp[::q]))
    r1 = np.concatenate(r1_all)
    v1 = r1.var(ddof=1)
    out = {}
    for q in horizons:
        rq = np.concatenate(rq_all[q])
        out[q] = (rq.var(ddof=1) / (q * v1), len(rq))
    return out, len(r1)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    bars = load_bars(Path(cfg["data"]["raw_dir"]))
    out = Path("data/ext"); out.mkdir(parents=True, exist_ok=True)
    L = [f"TEST A — config {config_hash('config.yaml')} commit {git_commit()}"]
    for name, (lo, hi) in PANELS.items():
        for stop_vince in (True, False):
            R = run_panel(name, lo, hi, bars, cfg, stop_vince)
            conv = "STOP vince i pareggi (convenzione in uso)" if stop_vince else "TARGET vince i pareggi"
            L.append(f"\n=== {name} — DIAGONALE s=t, {conv} (n {R['n']}) ===")
            L.append("        " + "".join(f"{x:>10}" for x in MULT))
            L.append("micro   " + "".join(f"{R['micro'][j]:>+10.5f}" for j in range(N)))
            for k, lab in enumerate(CAT):
                L.append(f"c{k} EV   " + "".join(f"{R['per_cat'][k, j]:>+10.5f}" for j in range(N)) + f"   {lab}")
            for k, lab in enumerate(CAT):
                L.append(f"c{k} %    " + "".join(f"{R['quota'][k, j]:>9.2%} " for j in range(N)) + f"   {lab}")
            resid = R["per_cat"][0] + R["per_cat"][1]
            L.append("RESIDUO " + "".join(f"{resid[j]:>+10.2e}" for j in range(N)) +
                     "   <- categorie 0+1: DEVE essere 0 esatto")
            pred = -MULT * R["amb"]
            L.append("prev.sempl " + "".join(f"{pred[j]:>+9.5f}" for j in range(N)) +
                     "   <- -d x quota ambigua di barra (previsione incompleta)")
            L.append("quota amb " + "".join(f"{R['amb'][j]:>9.2%} " for j in range(N)))
            print("\n".join(L[-14:]), flush=True)
    for name, (lo, hi) in PANELS.items():
        vr, n1 = variance_ratio(bars, cfg, lo, hi)
        s = f"\n=== {name} — VARIANCE RATIO (rendimenti log 1m intra-sessione, n {n1}) ===\n" + \
            "\n".join(f"  VR({q:>2}m) = {v:.4f}   (n blocchi {nq})" for q, (v, nq) in vr.items())
        print(s, flush=True); L.append(s)
    (out / "test_a.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\nscritto data/ext/test_a.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
