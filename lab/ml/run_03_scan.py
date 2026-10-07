"""Scan univariato: IC di ciascuna feature con y30 (2012-2018, stesso campione del WF) + importanza M1 finale.
Ogni feature e' un test guardato: registrata singolarmente."""
import numpy as np, pandas as pd
from lab import core
from lab.ml.common import dataset, ic_boot
from lab.ml.features import FEATURES
ds = dataset()
ev = ds[(pd.DatetimeIndex(ds.session).year >= 2012) & np.isfinite(ds.y30)]
rows = []
for f in FEATURES:
    r = ic_boot(ev[f], ev.y30, ev.session, n_boot=1000)
    # anche con y30 de-mediato per slot (toglie effetti orari di media)
    yd = ev.y30 - ev.groupby("slot").y30.transform("mean")
    r2 = ic_boot(ev[f], yd, ev.session, n_boot=300)
    ypy = {int(y): round(float(pd.Series(g[f].to_numpy()).corr(pd.Series(g.y30.to_numpy()), method="spearman")), 4)
           for y, g in ev.groupby(pd.DatetimeIndex(ev.session).year)}
    core.record("ml", f"ml_scan_{f}", f"Scan univariato: IC Spearman di {f} con y30, 2012-2018", "discovery",
                dict(r, ic_demeaned_slot=r2["ic"], ic_year=ypy, n=r["ic_n"]))
    rows.append((f, r["ic"], r["ic_lo"], r["ic_hi"], r["ic_p_two"], r2["ic"], sum(v > 0 for v in ypy.values())))
t = pd.DataFrame(rows, columns=["f", "ic", "lo", "hi", "p", "ic_dm", "yrs_pos"]).sort_values("p")
print(t.to_string(index=False, float_format=lambda x: f"{x:+.4f}"))
