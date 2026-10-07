"""B5 - terza esecuzione, dichiarata: LIMITE POI MERCATO (se il limite non e' eseguito entro N minuti si
entra a mercato all'open successivo + 1 tick: nessun trade perso). Piu' la calibrazione dell'ibrido
"ingresso aggressivo + uscita a target con limite" (chase con N=0) sui placebo.
Griglia dichiarata: placebo RTH (seme 11, come B0) H30: hybrid N0 con target {0.5, 1}*sig60*sqrt15,
chase off {0, 2t, s5h} N5; segnali del giro 1 con lordo positivo (sorpresa, hivol last30, fade rottura
notte, turnaround): chase off {0, s5h} N5. Solo studio: i bocciati del giro 1 non sono ripresentabili."""
import numpy as np
import pandas as pd

from lab.r2_execution.common import load, compare, summarize, xi_after
from lab.micro.candidates import surprise_cont_signals, overnight_range, _on_break_events
from lab.intraday_momentum.candidates import hivol_last30
from lab.calendar.candidates import turnaround_tue_am

D, B = load(warmup_days=300)
n = len(D.c)
idx_ts = pd.DatetimeIndex(pd.to_datetime(D.ts, utc=True))

# placebo identico a B0 (rth, p=1/30, seme 11)
r = np.random.default_rng(11)
ok = (D.m >= 585) & (D.m < 900) & np.isfinite(D.sig60) & (D.sig60 > 0)
s = np.nonzero(ok & (r.random(n) < 1 / 30))[0]
sd = np.where(r.random(len(s)) < 0.5, 1, -1)
xi = xi_after(D, s, 30)
sW = D.sig60[s] * np.sqrt(15)
for m in (0.5, 1.0):
    t = compare(D, B, s, sd, xi, 0.0, 0, tgt=m * sW, chase=True)
    summarize(t, f"B5_placebo_hybrid_tg{m}", f"placebo RTH H30: ingresso aggressivo, target {m}*sW a limite (costo 0,5 sui target)")
s5 = 0.5 * D.sig60[s] * np.sqrt(5)
for on, off in (("0", 0.0), ("2t", 0.5), ("s5h", s5)):
    t = compare(D, B, s, sd, xi, off, 5, chase=True)
    summarize(t, f"B5_placebo_chase_off{on}_N5", f"placebo RTH H30: limite off={on} poi mercato dopo 5m")


def from_trades(tr, exit_is_bar_start):
    e = idx_ts.get_indexer(pd.DatetimeIndex(tr["entry_ts"]))
    x = idx_ts.get_indexer(pd.DatetimeIndex(tr["exit_ts"])) if exit_is_bar_start else \
        idx_ts.searchsorted(pd.DatetimeIndex(tr["exit_ts"])) - 1
    ok = (e > 0) & (x > e)
    sig = e[ok] - 1
    k = D.scode[sig] == D.scode[e[ok]]
    return sig[k], tr["side"].to_numpy()[ok][k], x[ok][k]


sigs = {}
a, b_ = surprise_cont_signals(D)
sigs["surprise"] = (a, b_, xi_after(D, a, 30))
U, Dn = overnight_range(D)
ei, es = _on_break_events(D.h, D.l, D.c, D.m, D.scode, U, Dn, 575, 720)
sigs["onbreakfade"] = (ei, es, xi_after(D, ei, 120))
sigs["last30_hivol"] = from_trades(hivol_last30(D.bars, D.daily), False)
sigs["turnaround"] = from_trades(turnaround_tue_am(D.bars, D.daily), False)
for nm, (sg, side, x) in sigs.items():
    s5 = np.nan_to_num(0.5 * D.sig60[sg] * np.sqrt(5), nan=1.0)
    for on, off in (("0", 0.0), ("s5h", s5)):
        t = compare(D, B, sg, side, x, off, 5, chase=True)
        summarize(t, f"B5_{nm}_chase_off{on}_N5", f"giro1 {nm}: limite off={on} poi mercato dopo 5m")
