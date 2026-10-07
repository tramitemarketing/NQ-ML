"""Test primari pre-dichiarati: LGB su y30 vs baseline (sempre long, Ridge 3 feature, Ridge tutte)."""
import numpy as np, pandas as pd, json
from lab import core
from lab.ml.common import dataset, walk_forward, fit_lgb, fit_ridge, evaluate, CACHE
from lab.ml.features import FEATURES

ds = dataset()
preds = {}
# B0: sempre long negli stessi istanti (pred costante +1 -> tutti i trade long; soglia: |pred| sempre >= quantile)
p0 = pd.Series(1.0, index=ds.index)
evaluate(ds, p0, "ml_B0_long_h30", "Baseline: sempre long a ogni istante 10:00-15:30, uscita 30m (beta)", h=30)
# B1: ridge 3 feature
p1, i1 = walk_forward(ds, fit_ridge, "y30", feats=["r_sess", "r_on", "r30"])
preds["B1"] = p1
evaluate(ds, p1, "ml_B1_ridge3_h30", "Baseline: Ridge (r_sess, r_on, r30) walk-forward, R1, h30", h=30,
         extra=dict(coef={y: v["coef"] for y, v in i1.items()}))
# B2: ridge tutte
p2, i2 = walk_forward(ds, fit_ridge, "y30")
preds["B2"] = p2
evaluate(ds, p2, "ml_B2_ridgeall_h30", "Baseline: Ridge 40 feature walk-forward, R1, h30", h=30)
# M1: LGB
p3, i3 = walk_forward(ds, fit_lgb, "y30")
preds["M1"] = p3
print({y: (v["cfg"], v["n_trees"], round(v["inner_ic"], 4)) for y, v in i3.items()})
evaluate(ds, p3, "ml_M1_lgb_h30", "PRIMARIO: LightGBM 40 feature walk-forward, target y30, R1 p90, h30", h=30,
         extra=dict(tuning={y: dict(cfg=v["cfg"], n=v["n_trees"], inner_ic=v["inner_ic"]) for y, v in i3.items()}))
pd.DataFrame(preds).to_parquet(CACHE / "preds_h30.parquet")
