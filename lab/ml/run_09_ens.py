"""Varianti di modello su h60: media di 5 semi LGB, LGB+Ridge (media dei ranghi), classificazione del segno."""
import numpy as np, pandas as pd
from functools import partial
import lab.ml.common as C
from lab.ml.common import dataset, walk_forward, fit_lgb, fit_ridge, evaluate, CACHE
ds = dataset()
out = {}
ps = []
for seed in (7, 11, 23, 42, 99):
    p, _ = walk_forward(ds, fit_lgb, "y60", objective=dict(seed=seed))
    ps.append(p)
pe = sum(ps) / len(ps)
out["E1"] = pe
evaluate(ds, pe, "ml_E1_lgb5seeds_h60", "LGB WF y60, media di 5 semi, R1 p90", h=60)
pr, _ = walk_forward(ds, fit_ridge, "y60")
out["R60"] = pr
evaluate(ds, pr, "ml_B2_ridgeall_h60", "Ridge 40 feature WF y60, R1 p90", h=60)
# media dei ranghi per anno (rango calcolato dentro ogni anno di test = solo previsioni dell'anno: causale? NO -> uso z-score con scala del passato)
# per restare causali: standardizzo ciascuna previsione con media/sd delle 3000 previsioni precedenti
def zpast(p):
    s = p.dropna()
    idx = C.dataset().loc[s.index].sort_values(["session", "slot"]).index
    s = s.loc[idx]
    z = (s - s.shift(1).rolling(3000, min_periods=1000).mean()) / s.shift(1).rolling(3000, min_periods=1000).std()
    return z.reindex(p.index)
pz = zpast(pe) + zpast(pr)
out["E2"] = pz
evaluate(ds, pz, "ml_E2_lgb5+ridge_h60", "Ensemble: z-score causale (3000 prec.) di LGB5semi + Ridge, y60, R1 p90", h=60)
# classificazione del segno
ds2 = ds.copy(); ds2["s60"] = (ds2["y60"] > 0).astype(float); ds2.loc[~np.isfinite(ds2.y60), "s60"] = np.nan
pc, _ = walk_forward(ds2, fit_lgb, "s60", objective=dict(objective="binary"), clip=10)
pc = pc - 0.5
out["E4"] = pc
evaluate(ds, pc, "ml_E4_lgbclass_h60", "LGB classificazione segno y60 (prob-0,5), R1 p90", h=60)
pd.DataFrame(out).to_parquet(CACHE / "preds_ens.parquet")
