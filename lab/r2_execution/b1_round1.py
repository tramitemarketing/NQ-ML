"""B1 - segnali del giro 1 (ricostruiti importando le funzioni congelate, NON modificate), eseguiti
AGG vs PAS sugli stessi segnali. Serve a misurare la selezione avversa su segnali veri; i candidati
bocciati del giro 1 NON possono essere ripresentati (servono solo come materiale di studio).
Griglia dichiarata prima: off in {0, 2 tick, 0.5*sig60*sqrt5}, N in {5, 15} (+ N = orizzonte intero
per i segnali giornalieri)."""
import numpy as np
import pandas as pd

from lab.r2_execution.common import load, compare, summarize, xi_after
from lab.micro.candidates import surprise_cont_signals, overnight_range, _on_break_events
from lab.intraday_momentum.candidates import hivol_last30, rin_last30_all
from lab.calendar.candidates import turnaround_tue_am
from lab.cross_session.candidates import rth_direction_continues_after_halt

D, B = load(warmup_days=300)
idx_ts = pd.DatetimeIndex(pd.to_datetime(D.ts, utc=True))


def from_trades(tr, exit_is_bar_start=True):
    e = idx_ts.get_indexer(pd.DatetimeIndex(tr["entry_ts"]))
    ok = e > 0
    x_ts = pd.DatetimeIndex(tr["exit_ts"])
    if exit_is_bar_start:
        x = idx_ts.get_indexer(x_ts)
    else:
        x = idx_ts.searchsorted(x_ts) - 1          # ultima barra che inizia prima di exit_ts
    ok &= x > e
    sig = e[ok] - 1
    ok2 = D.scode[sig] == D.scode[e[ok]]
    return sig[ok2], tr["side"].to_numpy()[ok][ok2], x[ok][ok2]


def grid(name, sig, side, xi, H_full=None):
    s5 = 0.5 * D.sig60[sig] * np.sqrt(5)
    s5 = np.where(np.isfinite(s5), s5, 1.0)
    Ns = [5, 15] + ([H_full] if H_full else [])
    for oname, off in [("0", 0.0), ("2t", 0.5), ("s5h", s5)]:
        for N in Ns:
            t = compare(D, B, sig, side, xi, off, N)
            summarize(t, f"B1_{name}_off{oname}_N{N}", f"giro1 {name}: AGG vs PAS limite off={oname} attesa {N}m")


bars, daily = D.bars, D.daily
# 1) fade della prima rottura del range notturno (micro, bocciato) - H 120
U, Dn = overnight_range(D)
ei, es = _on_break_events(D.h, D.l, D.c, D.m, D.scode, U, Dn, 575, 720)
grid("onbreakfade", ei, es, xi_after(D, ei, 120), H_full=60)
# 2) sorpresa a 15 minuti, continuazione 30 m (micro, regolarita' bocciata) - non sovrapposto
s, sd = surprise_cont_signals(D)
grid("surprise", s, sd, xi_after(D, s, 30))
# 3) momentum ultima mezz'ora (tutti i giorni e alta vol)
for nm, fn in [("last30_all", rin_last30_all), ("last30_hivol", hivol_last30)]:
    sg, sd, xi = from_trades(fn(bars, daily), exit_is_bar_start=False)
    grid(nm, sg, sd, xi, H_full=30)
# 4) turnaround tuesday
sg, sd, xi = from_trades(turnaround_tue_am(bars, daily), exit_is_bar_start=False)
grid("turnaround", sg, sd, xi, H_full=150)
# 5) RTH -> sera
sg, sd, xi = from_trades(rth_direction_continues_after_halt(bars, daily), exit_is_bar_start=True)
grid("rth2eve", sg, sd, xi, H_full=30)
