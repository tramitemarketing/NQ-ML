"""Lotto 4: il regime di alta volatilita' (GHLZ e BDLM: l'effetto e' piu' forte quando la volatilita'
e' alta / i dealer sono corti gamma). Griglia di sensibilita' dichiarata PRIMA di guardarla:
lookback vol L in {10, 20, 60} x soglia = quantile q in {0,5; 0,67} della vol L delle 250 sessioni
precedenti, per tre predittori (rin = 09:30->15:30, rbd = chiusura ieri->15:30, r1 = chiusura ieri->10:00).
Piu' H31b (efficienza con soglia relativa) e controllo senza 2018.
"""
import numpy as np
import pandas as pd

from lab import core
from lab.intraday_momentum.common import build, ret, trade, evaluate, rec

bars, daily = core.load("discovery")
M = build(bars, daily)
ok = M["ok"]
S = M["sess"]
one = pd.Series(1, index=S)
d = trade(M, one, 930, 960)
DL = d[d.in_phase]["gross_pts"]

r1m = M["adj_close"].diff(axis=1) / M["close"]
rv = r1m.std(axis=1).where(ok)
preds = {"rin": ret(M, 570, 930), "rbd": ret(M, "pc", 930), "r1": ret(M, "pc", 600)}


def regime(L, q):
    v = rv.rolling(L, min_periods=int(L * 0.75)).mean().shift(1)
    thr = v.rolling(250, min_periods=120).quantile(q)
    return v > thr, thr.notna()


for L in (10, 20, 60):
    for q in (0.5, 0.67):
        hi, has = regime(L, q)
        for nm, x in preds.items():
            if (L, q, nm) == (20, 0.5, "rin"):
                continue  # gia' registrato come H12_rin_hivol
            rec(f"H12g_{nm}_L{L}_q{q}", f"segno({nm}) -> 15:30-16:00 solo vol{L} > quantile {q} delle 250 sessioni prima",
                evaluate(trade(M, np.sign(x), 930, 960, hi), DL))

# senza 2018 per la versione base
hi, has = regime(20, 0.5)
tr = trade(M, np.sign(preds["rin"]), 930, 960, hi)
rec("H12_rin_hivol_no2018", "H12_rin_hivol escluso 2018 (controllo di concentrazione)",
    evaluate(tr[pd.DatetimeIndex(tr.session).year < 2018], DL))

# H31b efficienza con soglia relativa (quantile 0,7 delle 250 sessioni precedenti)
c = M["adj_close"].loc[:, 570:929]
eff = ((c[929] - M["adj_open"][570]).abs() / c.diff(axis=1).abs().sum(axis=1)).where(ok)
thr = eff.rolling(250, min_periods=120).quantile(0.7).shift(1)
rec("H31b_eff_q70", "segno(rin) -> ultima mezz'ora solo se efficienza del percorso > q70 delle 250 sessioni prima",
    evaluate(trade(M, np.sign(preds["rin"]), 930, 960, eff > thr), DL))
