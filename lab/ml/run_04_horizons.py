"""M1 (stesso disegno) su altri orizzonti: 15m, 60m, chiusura RTH. Stessa regola R1."""
import numpy as np, pandas as pd
from lab.ml.common import dataset, walk_forward, fit_lgb, fit_ridge, evaluate, CACHE
ds = dataset()
out = {}
for h in (15, 60, "_close"):
    p, i = walk_forward(ds, fit_lgb, f"y{h}")
    out[f"M1_{h}"] = p
    evaluate(ds, p, f"ml_M1_lgb_h{h}", f"LightGBM 40 feature WF, target y{h}, R1 p90, uscita h={h}", h=h,
             extra=dict(tuning={y: dict(cfg=v["cfg"], n=v["n_trees"], inner_ic=v["inner_ic"]) for y, v in i.items()}))
    evaluate(ds, pd.Series(1.0, index=ds.index), f"ml_B0_long_h{h}", f"Baseline sempre long, uscita h={h}", h=h)
pd.DataFrame(out).to_parquet(CACHE / "preds_hor.parquet")
