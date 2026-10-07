"""IC per istante di decisione (fra giorni allo stesso slot: nessun uso di info successive).
Nota: la scomposizione fra-giorni/dentro-giorno di run_07 e' INVALIDA (la media giornaliera delle previsioni
include previsioni fatte piu' tardi, che conoscono i rendimenti delle ore precedenti = esiti degli slot precedenti)."""
import numpy as np, pandas as pd
from lab import core
from lab.ml.common import dataset, ic_boot, CACHE
ds = dataset()
yrs = pd.DatetimeIndex(ds.session).year
core.record("ml", "ml_note_decomp_invalid", "NOTA: la scomposizione fra-giorni (IC +0,15) di ml_diag_decomp_* e' contaminata da look-ahead "
            "(media giornaliera delle previsioni include slot successivi che vedono gli esiti degli slot precedenti). Ritirata.", "discovery", {"n": 0})
p30 = pd.read_parquet(CACHE / "preds_h30.parquet")["M1"]
p60 = pd.read_parquet(CACHE / "preds_hor.parquet")["M1_60"]
for h, p in ((30, p30), (60, p60)):
    res = {}
    for s, e in ds[(yrs >= 2012) & np.isfinite(ds[f"y{h}"])].groupby("slot"):
        r = ic_boot(p[e.index], e[f"y{h}"], e.session, n_boot=1000)
        res[int(s)] = (round(r["ic"], 4), round(r["ic_lo"], 4), round(r["ic_hi"], 4))
    for k, v in res.items():
        print(h, f"{k//60}:{k%60:02d}", v)
    core.record("ml", f"ml_diag_slot_h{h}", f"IC M1 h{h} per slot (descrittivo, 12 numeri)", "discovery", dict(n=len(res), ic_by_slot=res))
