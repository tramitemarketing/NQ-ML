"""Modello giornaliero: una decisione alle 10:00, uscita alle 15:59 (close RTH). Meno trade, costo relativo minore.
D1 LGB WF (target y_close alle 10:00), D2 segno di r_20d, D3 segno di r_5d (D2/D3 POST HOC: suggeriti dallo scan)."""
import numpy as np, pandas as pd
from lab.ml.common import dataset, walk_forward, fit_lgb, fit_ridge, evaluate, CACHE
ds = dataset()
d10 = ds[ds.slot == 600].copy()
p, i = walk_forward(d10, fit_lgb, "y_close")
print({y: (v["cfg"], v["n_trees"], round(v["inner_ic"], 4)) for y, v in i.items()})
kw = dict(h="_close", window=250, min_hist=150)
evaluate(d10, p, "ml_D1_lgb_10to16_all", "Giornaliero: LGB WF alle 10:00 -> close RTH, opera ogni giorno col segno", q=0.0, **kw)
evaluate(d10, p, "ml_D1_lgb_10to16_top50", "Giornaliero: LGB WF alle 10:00 -> close RTH, opera se |pred| >= mediana delle 250 precedenti", q=0.5, **kw)
pr, _ = walk_forward(d10, fit_ridge, "y_close")
evaluate(d10, pr, "ml_D1_ridge_10to16_all", "Giornaliero: Ridge 40 feature WF alle 10:00 -> close, segno ogni giorno", q=0.0, **kw)
evaluate(d10, d10["r_20d"], "ml_D2_r20d_sign", "POST HOC dallo scan: segno di r_20d alle 10:00 -> close RTH, ogni giorno", q=0.0, **kw)
evaluate(d10, d10["r_5d"], "ml_D3_r5d_sign", "POST HOC dallo scan: segno di r_5d alle 10:00 -> close RTH, ogni giorno", q=0.0, **kw)
evaluate(d10, pd.Series(1.0, index=d10.index), "ml_D0_long_10to16", "Baseline: sempre long 10:00 -> close RTH", q=0.0, **kw)
pd.DataFrame({"D1": p, "D1r": pr}).to_parquet(CACHE / "preds_daily.parquet")
