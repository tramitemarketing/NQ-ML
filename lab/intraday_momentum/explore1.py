"""Lotto 1: repliche della letteratura su NQ (discovery).

H01 GHLZ: segno(r chiusura ieri -> 10:00) -> ultima mezz'ora 15:30-16:00.
H02 GHLZ: segno(r 15:00-15:30, la dodicesima mezz'ora) -> ultima mezz'ora.
H03 GHLZ: entrambi i predittori concordi -> ultima mezz'ora (altrimenti niente).
H04 BDLM: segno(r chiusura ieri -> 15:30) -> ultima mezz'ora.
H05 Deriva passiva dell'ultima mezz'ora (sempre long): riferimento per il beta.
H06 LPS: segno(overnight, chiusura ieri -> 09:30) -> intraday 09:30-16:00.
H07 LPS rovesciato (tug of war): -segno(overnight) -> intraday.
H08 BDLM intraday puro: segno(r 09:30 -> 15:30) -> ultima mezz'ora.
H09 BDLM overnight puro: segno(overnight) -> ultima mezz'ora.
"""
import numpy as np
import pandas as pd

from lab import core
from lab.intraday_momentum.common import build, ret, trade, evaluate, rec, hm

bars, daily = core.load("discovery")
M = build(bars, daily)
T930, T1000, T1500, T1530, T1600 = 570, 600, 900, 930, 960
one = pd.Series(1, index=M["sess"])
drift_last = trade(M, one, T1530, T1600)
drift_last = drift_last[drift_last.in_phase]["gross_pts"]
drift_day = trade(M, one, T930, T1600)
drift_day = drift_day[drift_day.in_phase]["gross_pts"]

r1 = ret(M, "pc", T1000)
r12 = ret(M, T1500, T1530)
rbd = ret(M, "pc", T1530)
ron = ret(M, "pc", T930)
rin = ret(M, T930, T1530)

rec("H01_ghlz_r1", "GHLZ: segno(chiusura ieri->10:00) -> 15:30-16:00", evaluate(trade(M, np.sign(r1), T1530, T1600), drift_last))
rec("H02_ghlz_r12", "GHLZ: segno(15:00-15:30) -> 15:30-16:00", evaluate(trade(M, np.sign(r12), T1530, T1600), drift_last))
agree = np.sign(r1).where(np.sign(r1) == np.sign(r12), 0)
rec("H03_ghlz_both", "GHLZ: r1 e r12 concordi -> 15:30-16:00", evaluate(trade(M, agree, T1530, T1600), drift_last))
rec("H04_bdlm", "BDLM: segno(chiusura ieri->15:30) -> 15:30-16:00", evaluate(trade(M, np.sign(rbd), T1530, T1600), drift_last))
rec("H05_drift_last30", "Deriva passiva: sempre long 15:30-16:00", evaluate(trade(M, one, T1530, T1600), drift_last))
rec("H06_lps_on_mom", "LPS: segno(overnight) -> 09:30-16:00", evaluate(trade(M, np.sign(ron), T930, T1600), drift_day))
rec("H07_lps_on_rev", "LPS rovesciato: -segno(overnight) -> 09:30-16:00", evaluate(trade(M, -np.sign(ron), T930, T1600), drift_day))
rec("H08_bdlm_intra", "segno(09:30->15:30) -> 15:30-16:00", evaluate(trade(M, np.sign(rin), T1530, T1600), drift_last))
rec("H09_bdlm_overnight", "segno(overnight chiusura ieri->09:30) -> 15:30-16:00", evaluate(trade(M, np.sign(ron), T1530, T1600), drift_last))

# regressione lorda (predittivita' pura, in rendimenti relativi) per le repliche
y = ret(M, T1530, T1600)
ok = M["ok"] & M["in_phase"]
import statsmodels.api as sm
for name, x in [("r1", r1), ("r12", r12), ("rbd", rbd), ("ron", ron), ("rin", rin)]:
    d = pd.DataFrame({"y": y, "x": x})[ok].dropna()
    res = sm.OLS(d.y, sm.add_constant(d.x)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    print(f"OLS y_last30 ~ {name}: beta={res.params['x']:+.4f} t={res.tvalues['x']:+.2f} R2={res.rsquared*100:.2f}%")
    core.record("intraday_momentum", f"R01_ols_last30_{name}", f"OLS HAC(5) rendimento 15:30-16:00 su {name}", "discovery",
                {"n": int(len(d)), "beta": float(res.params['x']), "t": float(res.tvalues['x']), "r2": float(res.rsquared)})
