"""Controllo rimbalzo bid-ask: stessa regolarita' con ingresso 1 minuto dopo (close barra t) e con la previsione M1 h30."""
import numpy as np, pandas as pd
from lab import core
from lab.ml.common import dataset, CACHE, ic_boot
ds = dataset()
p = pd.read_parquet(CACHE / "preds_h30.parquet")["M1"]
d = ds[["session", "slot", "y30", "y30_d1"]].copy(); d["p"] = p
d = d[np.isfinite(d.p)].sort_values(["session", "slot"])
med = d.p.shift(1).rolling(3000, min_periods=2000).median()
side = np.sign(d.p - med)
sel = np.isfinite(med) & (pd.DatetimeIndex(d.session).year >= 2013)
for col in ("y30", "y30_d1"):
    g = (side * d[col])[sel]
    st = core.day_block_bootstrap(g.to_numpy(), d.session[sel].to_numpy(), n_boot=4000)
    ic = ic_boot(d.p[sel], d[col][sel], d.session[sel], n_boot=1000)
    print(col, {k: round(v, 4) for k, v in st.items() if isinstance(v, float)}, "IC", round(ic["ic"], 4), round(ic["ic_lo"], 4), round(ic["ic_hi"], 4))
    core.record("ml", f"ml_REG_M1_h30_bounce_{col}", f"Controllo rimbalzo: regolarita' M1 h30 tutti gli slot, esito {col} (d1 = ingresso 1 minuto dopo), unita' di vol", "discovery", dict(st, **ic))
