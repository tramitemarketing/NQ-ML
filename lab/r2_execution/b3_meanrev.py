"""B3 - mean reversion dove il limite e' naturale (fade: compri piu' in basso).
Predittori (solo passato, alla chiusura della barra i, griglia ogni 5 minuti):
  r30   = (c_i - c_{i-30}) / (sig60 * sqrt30)
  dev60 = (c_i - media dei close i-59..i) / (sig60 * sqrt30)
Segnale: |x| > z, lato = -segno(x). Griglia dichiarata: finestra {mid 12:30-15:00, rth 09:45-15:00},
z {1, 2}, off {0, 0.5*sig60*sqrt5}, uscita a tempo H {30, 60}; attesa N 15; niente target/stop.
(La regolarita' vol_midday_variance_ratio del giro 1 dice VR<1 a mezzogiorno: se c'e' un posto dove un
fade passivo funziona, e' li'.)"""
import numpy as np
import pandas as pd

from lab.r2_execution.common import load, compare, summarize, xi_after

D, B = load()
c, m, n = D.c, D.m, len(D.c)
sg = D.sig60 * np.sqrt(30)
i = np.arange(n)
p30 = np.clip(i - 30, 0, None)
r30 = np.where(D.scode[p30] == D.scode, (c - c[p30]) / sg, np.nan)
ma = pd.Series(c).rolling(60).mean().to_numpy()
p60 = np.clip(i - 59, 0, None)
dev = np.where(D.scode[p60] == D.scode, (c - ma) / sg, np.nan)
grid5 = (m % 5 == 4)
WIN = {"mid": (749, 900), "rth": (584, 900)}
s5 = 0.5 * D.sig60 * np.sqrt(5)
for wn, (lo, hi) in WIN.items():
    for pn, x in (("r30", r30), ("dev60", dev)):
        for z in (1, 2):
            sel = grid5 & (m >= lo) & (m < hi) & np.isfinite(x) & (np.abs(x) > z)
            s = np.nonzero(sel)[0]
            side = -np.sign(x[s]).astype(int)
            for H in (30, 60):
                xi = xi_after(D, s, H)
                for on, off in (("0", 0.0), ("s5h", s5[s])):
                    t = compare(D, B, s, side, xi, off, 15)
                    summarize(t, f"B3_{wn}_{pn}_z{z}_H{H}_off{on}",
                              f"fade {pn}>{z} finestra {wn}, uscita {H}m, limite off={on}, attesa 15m")
