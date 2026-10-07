"""Lotto 2: varianti (soglie, regimi, finestre diverse, periodicita').

Soglie in unita' di sigma: sigma = deviazione standard del predittore sulle 60 sessioni valide
PRECEDENTI (solo passato). Volatilita' realizzata RTH = std dei rendimenti a 1m 09:30-16:00.
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


def past_sigma(x, n=60):
    x = x.where(ok)
    return x.rolling(n, min_periods=40).std().shift(1)


rin = ret(M, 570, 930)
rbd = ret(M, "pc", 930)
DL = drift(930, 960)

# --- soglie
for nm, x in [("rin", rin), ("rbd", rbd)]:
    sg = past_sigma(x)
    for k in (0.5, 1.0, 1.5, 2.0):
        side = np.sign(x).where(x.abs() > k * sg, 0)
        rec(f"H10_{nm}_thr{k}", f"segno({nm}) -> 15:30-16:00 solo se |{nm}|>{k} sigma60 passata",
            evaluate(trade(M, side, 930, 960), DL))

# --- regime di volatilita' (vol realizzata RTH di ieri e media 20 giorni, solo passato)
c = M["adj_close"]
r1m = c.diff(axis=1) / M["close"]
rv = r1m.std(axis=1).where(ok)
rv20 = rv.rolling(20, min_periods=15).mean().shift(1)
rv_med = rv20.rolling(250, min_periods=120).median()
hi = rv20 > rv_med
rec("H12_rin_hivol", "segno(rin) -> ultima mezz'ora, solo regime vol20 > mediana 250g",
    evaluate(trade(M, np.sign(rin), 930, 960, hi), DL))
rec("H12_rin_lovol", "segno(rin) -> ultima mezz'ora, solo regime vol20 <= mediana 250g",
    evaluate(trade(M, np.sign(rin), 930, 960, ~hi & rv_med.notna()), DL))
# vol del giorno stesso fino alle 15:30 (nota prima dell'ingresso)
rv_today = r1m.loc[:, 571:929].std(axis=1)
hi_t = rv_today > rv20
rec("H12_rin_hivol_today", "segno(rin) -> ultima mezz'ora, solo se vol 09:30-15:30 oggi > vol20",
    evaluate(trade(M, np.sign(rin), 930, 960, hi_t), DL))

# --- volume della prima mezz'ora rispetto alla media 20g
v = M["volume"]
v1 = v.loc[:, 570:599].sum(axis=1).where(ok)
v1m = v1.rolling(20, min_periods=15).mean().shift(1)
rec("H13_ghlz_hivolume", "GHLZ r1 -> ultima mezz'ora solo se volume 09:30-10:00 > media 20g",
    evaluate(trade(M, np.sign(ret(M, "pc", 600)), 930, 960, v1 > v1m), DL))
vday = v.loc[:, 570:929].sum(axis=1).where(ok)
vdm = vday.rolling(20, min_periods=15).mean().shift(1)
rec("H13_rin_hivolume", "segno(rin) -> ultima mezz'ora solo se volume 09:30-15:30 > media 20g",
    evaluate(trade(M, np.sign(rin), 930, 960, vday > vdm), DL))

# --- finestre diverse (piu' lunghe = costi relativamente minori)
rec("H14_lasthour", "segno(chiusura ieri->15:00) -> 15:00-16:00",
    evaluate(trade(M, np.sign(ret(M, "pc", 900)), 900, 960), drift(900, 960)))
rec("H14_lasthour_intra", "segno(09:30->15:00) -> 15:00-16:00",
    evaluate(trade(M, np.sign(ret(M, 570, 900)), 900, 960), drift(900, 960)))
rec("H15_after14", "segno(09:30->14:00) -> 14:00-16:00",
    evaluate(trade(M, np.sign(ret(M, 570, 840)), 840, 960), drift(840, 960)))
rec("H15_after14_pc", "segno(chiusura ieri->14:00) -> 14:00-16:00",
    evaluate(trade(M, np.sign(ret(M, "pc", 840)), 840, 960), drift(840, 960)))
rec("H16_penult", "segno(09:30->15:00) -> 15:00-15:30 (penultima mezz'ora)",
    evaluate(trade(M, np.sign(ret(M, 570, 900)), 900, 930), drift(900, 930)))
rec("H17_morning_mom", "segno(09:30-10:00) -> 10:00-10:30",
    evaluate(trade(M, np.sign(ret(M, 570, 600)), 600, 630), drift(600, 630)))
rec("H17_morning_rev", "-segno(09:30-10:00) -> 10:00-10:30 (reversal della mattina)",
    evaluate(trade(M, -np.sign(ret(M, 570, 600)), 600, 630), drift(600, 630)))
rec("H17_morning_mom_close", "segno(09:30-10:00) -> 10:00-16:00",
    evaluate(trade(M, np.sign(ret(M, 570, 600)), 600, 960), drift(600, 960)))
rec("H18_lunch_mom", "segno(09:30->12:00) -> 12:00-13:30 (pausa pranzo)",
    evaluate(trade(M, np.sign(ret(M, 570, 720)), 720, 810), drift(720, 810)))
rec("H18_lunch_rev", "-segno(09:30->12:00) -> 12:00-13:30",
    evaluate(trade(M, -np.sign(ret(M, 570, 720)), 720, 810), drift(720, 810)))
rec("H18_afternoon_mom", "segno(09:30->12:00) -> 12:00-16:00",
    evaluate(trade(M, np.sign(ret(M, 570, 720)), 720, 960), drift(720, 960)))

# --- periodicita' HKS: ultima mezz'ora di ieri -> ultima mezz'ora di oggi
yl = ret(M, 930, 960).where(ok)
yl_prev = yl.ffill().shift(1)
rec("H19_hks_last30", "segno(15:30-16:00 di ieri) -> 15:30-16:00 di oggi",
    evaluate(trade(M, np.sign(yl_prev), 930, 960), DL))

# --- ultimi 10 minuti (imbalance MOC pubblicate dalle 15:50)
rec("H20_last10", "segno(09:30->15:50) -> 15:50-16:00",
    evaluate(trade(M, np.sign(ret(M, 570, 950)), 950, 960), drift(950, 960)))
rec("H20_last10_pc", "segno(chiusura ieri->15:50) -> 15:50-16:00",
    evaluate(trade(M, np.sign(ret(M, "pc", 950)), 950, 960), drift(950, 960)))

# --- gamma: giorni con movimento piccolo -> reversal (dealer long gamma)
sg = past_sigma(rin)
small = rin.abs() < 0.5 * sg
rec("H24_gamma_small_rev", "-segno(rin) -> ultima mezz'ora, solo |rin|<0,5 sigma60",
    evaluate(trade(M, -np.sign(rin), 930, 960, small), DL))

# --- giorno della settimana / scadenza opzioni (terzo venerdi')
dow = pd.Series(S.dayofweek, index=S)
for d in range(5):
    rec(f"H22_rin_dow{d}", f"segno(rin) -> ultima mezz'ora solo dow={d}",
        evaluate(trade(M, np.sign(rin), 930, 960, dow == d), DL))
opex = pd.Series((S.dayofweek == 4) & (S.day >= 15) & (S.day <= 21), index=S)
rec("H23_rin_opex", "segno(rin) -> ultima mezz'ora solo terzo venerdi' del mese",
    evaluate(trade(M, np.sign(rin), 930, 960, opex), DL))
