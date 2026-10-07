"""Variazioni della regola di trading sulle previsioni WF gia' calcolate (h30, h60) + LGB media di 5 semi."""
import numpy as np, pandas as pd
from lab.ml.common import dataset, walk_forward, fit_lgb, evaluate, CACHE, LGB_BASE
import lab.ml.common as C
ds = dataset()
p30 = pd.read_parquet(CACHE / "preds_h30.parquet")["M1"]
p60 = pd.read_parquet(CACHE / "preds_hor.parquet")["M1_60"]
for h, p in ((30, p30), (60, p60)):
    for q in (0.95, 0.98):
        evaluate(ds, p, f"ml_M1_h{h}_q{int(q*100)}", f"LGB WF y{h}, regola R1 con quantile {q}", h=h, q=q)
    for c in (1.0, 2.0):
        evaluate(ds, p, f"ml_M1_h{h}_R2c{c:g}", f"LGB WF y{h}, regola R2: opera se |pred|*sig1m*sqrt(h) > {c}x costo", h=h, q=c, side_mode="cost")
