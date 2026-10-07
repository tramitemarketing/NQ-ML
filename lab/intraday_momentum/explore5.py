"""Lotto 5: controlli sul miglior filone (segno di 09:30->15:30 in regime di alta vol, L20 q0,67).
- anno per anno, senza 2018, placebo (segno di IERI sugli stessi giorni), quantili piu' alti,
- finestra del predittore (10:00/12:00/14:00 -> 15:30), uscita 16:15, ingresso 15:45,
- soglia di magnitudine aggiuntiva.
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


def drift(t0, t1):
    d = trade(M, one, t0, t1)
    return d[d.in_phase]["gross_pts"]


DL = drift(930, 960)
r1m = M["adj_close"].diff(axis=1) / M["close"]
rv = r1m.std(axis=1).where(ok)
v20 = rv.rolling(20, min_periods=15).mean().shift(1)


def hi_q(q):
    return v20 > v20.rolling(250, min_periods=120).quantile(q)


rin = ret(M, 570, 930)
HI = hi_q(0.67)
base = trade(M, np.sign(rin), 930, 960, HI)
st = evaluate(base, DL)
print("yearly base:", st["yearly"])
rec("C01_base_no2018", "base (rin, vol20>q67) escluso 2018",
    evaluate(base[pd.DatetimeIndex(base.session).year < 2018], DL))
rec("C01_base_2010_2014", "base solo 2010-2014",
    evaluate(base[pd.DatetimeIndex(base.session).year <= 2014], DL))
rec("C01_base_2015_2018", "base solo 2015-2018",
    evaluate(base[pd.DatetimeIndex(base.session).year >= 2015], DL))
y_prev = rin.where(ok).ffill().shift(1)
rec("C02_placebo_yday_sign", "placebo: segno del rin di IERI, stessi giorni ad alta vol",
    evaluate(trade(M, np.sign(y_prev), 930, 960, HI), DL))
rec("C02_placebo_long", "placebo: sempre long negli stessi giorni ad alta vol",
    evaluate(trade(M, one, 930, 960, HI), DL))
for q in (0.75, 0.8, 0.9):
    rec(f"C03_rin_q{q}", f"segno(rin) -> ultima mezz'ora, vol20 > quantile {q}",
        evaluate(trade(M, np.sign(rin), 930, 960, hi_q(q)), DL))
for t0 in (600, 720, 840):
    rec(f"C04_pred_from{t0}", f"segno({t0//60}:{t0%60:02d}->15:30) -> ultima mezz'ora, vol20>q67",
        evaluate(trade(M, np.sign(ret(M, t0, 930)), 930, 960, HI), DL))
rec("C05_entry1545", "segno(09:30->15:45) -> 15:45-16:00, vol20>q67",
    evaluate(trade(M, np.sign(ret(M, 570, 945)), 945, 960, HI), drift(945, 960)))
rec("C05_entry1500", "segno(09:30->15:00) -> 15:00-16:00, vol20>q67",
    evaluate(trade(M, np.sign(ret(M, 570, 900)), 900, 960, HI), drift(900, 960)))
# uscita 16:15
post = bars[(bars.ny_min >= 960) & (bars.ny_min <= 974)].pivot_table(index="session", columns="ny_min", values="adj_close", aggfunc="first").reindex(S)
x1615 = post.ffill(axis=1)[974]
e = M["adj_open"][930]
s = np.sign(rin)
mask = ok & s.ne(0) & x1615.notna() & HI.fillna(False)
tr = pd.DataFrame({"session": S[mask.to_numpy()], "side": s[mask].astype(int).to_numpy(),
                   "gross_pts": ((x1615 - e) * s)[mask].to_numpy(), "raw_px": M["close"][930][mask].to_numpy(),
                   "in_phase": M["in_phase"][mask].to_numpy()})
rec("C05_exit1615", "segno(rin) -> 15:30-16:15, vol20>q67", evaluate(tr, ((x1615 - e)[ok & M["in_phase"]]).dropna()))
# magnitudine aggiuntiva
sg = rin.where(ok).rolling(60, min_periods=40).std().shift(1)
for k in (0.5, 1.0):
    rec(f"C06_mag{k}", f"segno(rin) -> ultima mezz'ora, vol20>q67 e |rin|>{k} sigma60",
        evaluate(trade(M, np.sign(rin).where(rin.abs() > k * sg, 0), 930, 960, HI), DL))
