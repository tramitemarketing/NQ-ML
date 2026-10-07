"""Controlli sui due possibili candidati 'regolarita''.
(a) V1: il range notturno aggiunge informazione oltre al range RTH di ieri? (regressione, CI a blocchi)
(b) P2b: sensibilita' del predittore e della finestra dopo la pausa; placebo con segno casuale."""
import numpy as np, pandas as pd
import statsmodels.api as sm
from lab import core
from lab.cross_session.build_cache import get
from lab.cross_session.common import evaluate, fmt, FAMILY
from lab.cross_session.series import segments

t = get(); S = segments(t); m = t["valid"] & t["in_phase"]; atr = t.atr20
ratio = lambda r: r / r.shift(1).rolling(20, min_periods=10).mean()
on_r = ratio(t.on_hi - t.on_lo); rth_r = ratio(t.range_rth)
d = pd.concat({"y": np.log(rth_r), "on": np.log(on_r), "prev": np.log(rth_r.shift(1)), "prevon": np.log(on_r.shift(1))}, axis=1)[m].replace([np.inf, -np.inf], np.nan).dropna()
fit = sm.OLS(d["y"], sm.add_constant(d[["on", "prev", "prevon"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
print(fit.summary().tables[1])
core.record(FAMILY, "V1c_partial_regression", "log(range RTH/media20) ~ log(range notte/media20) + log(range RTH ieri) + log(range notte ieri), HAC",
            "discovery", {"n": int(len(d)), "coef_on": float(fit.params["on"]), "t_on": float(fit.tvalues["on"]),
                          "coef_prev": float(fit.params["prev"]), "t_prev": float(fit.tvalues["prev"]), "r2": float(fit.rsquared)})
def run(tid, desc, side, tgt):
    r = evaluate(tid, desc, side * tgt, side, tgt, atr, m); print(fmt(tid, r)); return r
after = t.sig_s17 - t.ent_s1615
run("P4_m15_to_after_halt", "sign(15:45-16:00) su 16:30-17:00", np.sign(t.sig_s16 - t.ent_s1545), after)
run("P4b_rth_to_after_halt", "sign(RTH 09:30-16:00) su 16:30-17:00", np.sign(S["R_sig"]), after)
run("P4c_1500_1615_to_after_halt", "sign(15:00-16:15) su 16:30-17:00", np.sign(t.sig_s1615 - t.ent_s15), after)
run("P4d_first15post_to_after_halt", "sign(16:00-16:15) su 16:30-17:00", np.sign(t.sig_s1615 - t.ent_s16), after)
rng = np.random.default_rng(7)
rs = pd.Series(rng.choice([-1.0, 1.0], len(t)), index=t.index)
run("P4e_placebo_random_after_halt", "placebo: segno casuale su 16:30-17:00", rs, after)
