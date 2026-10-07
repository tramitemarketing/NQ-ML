"""Approfondimento del grappolo 'fine RTH -> 16:00-17:00' (B1/B2_lasthour_to_post, V10b).
Unita' primaria qui: ATR20 (il grappolo e' emerso in ATR; in punti gli anni recenti dominano)."""
import numpy as np, pandas as pd
from lab import core
from lab.cross_session.build_cache import get
from lab.cross_session.common import evaluate, fmt
from lab.cross_session.series import segments

t = get(); S = segments(t); m = t["valid"] & t["in_phase"]; atr = t.atr20
def run(tid, desc, side, tgt, yrs=False):
    r = evaluate(tid, desc, side * tgt, side, tgt, atr, m); print(fmt(tid, r))
    if yrs:
        g = ((side * tgt) / atr)[m & side.notna() & tgt.notna() & (side != 0)]
        print("   ATR per anno:", core.yearly(g.to_numpy(), g.index)["mean"].round(4).to_dict())
    return r
post_all = t.sig_s17 - t.ent_s16
post_15 = t.ent_s1615 - t.ent_s16         # 16:00 -> 16:15 (prima della pausa; ingresso 16:30 se ent_s1615 cade dopo la pausa)
post_after = t.sig_s17 - t.ent_s1615      # 16:30 circa -> 17:00
preds = {"h1": t.sig_s16 - t.ent_s15, "m30": t.sig_s16 - t.ent_s1530, "m15": t.sig_s16 - t.ent_s1545,
         "rth": S["R_sig"]}
for k, p in preds.items():
    run(f"P1_{k}_to_post", f"sign({k} fino alle 16:00) su 16:00-17:00", np.sign(p), post_all, yrs=(k == "h1"))
run("P2_h1_to_post_first15", "sign(15:00-16:00) su 16:00-16:15", np.sign(preds["h1"]), post_15)
run("P2b_h1_to_post_after_halt", "sign(15:00-16:00) su 16:30-17:00", np.sign(preds["h1"]), post_after)
cpos = (t.sig_s16 - t.rth_lo) / t.range_rth
for thr in (0.7, 0.8, 0.9):
    sd = pd.Series(np.where(cpos > thr, 1.0, np.where(cpos < 1 - thr, -1.0, np.nan)), index=t.index)
    run(f"P3_closepos{int(thr*100)}_to_post", f"chiusura RTH oltre {thr:.0%} del range (long) / sotto {1-thr:.0%} (short) -> 16:00-17:00", sd, post_all, yrs=(thr == 0.8))
