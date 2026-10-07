"""B6 - fasce OCO di B2 condizionate al regime previsto dalla regolarita' confermata del giro 1
(range notturno -> range RTH): onr = range 18:00-09:29 / media dei 20 range notturni precedenti;
regime basso/alto = sotto il terzile inferiore / sopra il terzile superiore delle 250 sessioni
precedenti (causale). Ipotesi dichiarata: nei giorni previsti calmi la fornitura di liquidita' soffre
meno di trend (selezione avversa minore). Griglia: finestra {mid, rth} x k {1, 2} x uscita {t30, tg1t30}
x regime {low, high}."""
import numpy as np
import pandas as pd

from lab.r2_execution.common import load, compare, summarize, xi_after
from lab.micro.candidates import overnight_range

D, B = load(warmup_days=300)
U, Dn = overnight_range(D)
onr = pd.Series(U - Dn)
ratio = onr / onr.rolling(20, min_periods=15).mean().shift(1)
q_lo = ratio.rolling(250, min_periods=120).quantile(1 / 3).shift(1)
q_hi = ratio.rolling(250, min_periods=120).quantile(2 / 3).shift(1)
reg = np.full(len(ratio), 0)
reg[(ratio < q_lo).to_numpy()] = -1
reg[(ratio > q_hi).to_numpy()] = 1
reg_bar = reg[D.scode]

m = D.m
ok = (m % 15 == 14) & np.isfinite(D.sig60) & (D.sig60 > 0)
WIN = {"mid": (749, 900), "rth": (584, 900)}
for wn, (lo, hi) in WIN.items():
    for rn, rv in (("low", -1), ("high", 1)):
        s = np.nonzero(ok & (m >= lo) & (m < hi) & (reg_bar == rv))[0]
        sW = D.sig60[s] * np.sqrt(15)
        for k in (1, 2):
            for ex, tg in (("t30", None), ("tg1t30", 1.0)):
                t = compare(D, B, s, 1, xi_after(D, s, 30), k * sW, 15,
                            tgt=None if tg is None else tg * sW, oco=True)
                summarize(t, f"B6_{wn}_{rn}_k{k}_{ex}", f"OCO fasce k={k}, finestra {wn}, regime notte {rn}, uscita {ex}")
