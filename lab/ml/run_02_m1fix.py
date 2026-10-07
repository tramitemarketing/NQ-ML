"""M1 rifatto dopo bug: l'IC di validazione interna era NaN (indici disallineati) -> sceglieva sempre la prima config."""
import numpy as np, pandas as pd
from lab.ml.common import dataset, walk_forward, fit_lgb, evaluate, CACHE
ds = dataset()
p3, i3 = walk_forward(ds, fit_lgb, "y30")
print({y: (v["cfg"], v["n_trees"], round(v["inner_ic"], 4)) for y, v in i3.items()})
evaluate(ds, p3, "ml_M1b_lgb_h30", "PRIMARIO (bug tuning corretto): LightGBM 40 feature WF, y30, R1 p90, h30", h=30,
         extra=dict(tuning={y: dict(cfg=v["cfg"], n=v["n_trees"], inner_ic=v["inner_ic"]) for y, v in i3.items()}))
pr = pd.read_parquet(CACHE / "preds_h30.parquet"); pr["M1"] = p3; pr.to_parquet(CACHE / "preds_h30.parquet")
