"""Addestra e salva i modelli del candidato ml_rank30: un modello walk-forward per ciascun anno 2012-2018
(addestrato su sessioni < 1 gennaio Y meno 5 di embargo) e il modello finale su TUTTO il discovery
(usato per le sessioni dal 2019). Stessa procedura di tuning di run_02 (validazione interna = ultimo anno)."""
import json
import numpy as np, pandas as pd
from lab.ml.common import dataset, fit_lgb, HERE
from lab.ml.features import FEATURES
MODELS = HERE / "models"
SEEDS = (7, 11, 23, 42, 99)   # media di 5 semi: la scelta del seme spostava l'effetto da 0,013 a 0,028 (run_13)

def main():
    MODELS.mkdir(exist_ok=True)
    ds = dataset()
    sess = np.sort(ds["session"].unique())
    meta = {}
    for Y in list(range(2012, 2019)) + [2019]:
        first = np.datetime64(f"{Y}-01-01")
        cut = sess[max(0, np.searchsorted(sess, first) - 5)] if Y <= 2018 else np.datetime64("2100-01-01")
        tr = ds[ds["session"] < cut]
        for seed in SEEDS:
            m, inf = fit_lgb(tr, ycol="y30", objective=dict(seed=seed))
            tag = str(Y) if Y <= 2018 else "final"
            name = f"lgb_y30_{tag}_s{seed}.txt"
            m.m.save_model(str(MODELS / name))
            meta[name] = dict(train_last_session=str(pd.Timestamp(tr["session"].max()).date()), n_rows=int(len(tr)), **inf)
            print(name, meta[name])
    json.dump(dict(features=FEATURES, models=meta), open(MODELS / "meta.json", "w"), indent=1)

if __name__ == "__main__":
    main()
