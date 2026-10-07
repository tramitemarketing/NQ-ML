"""r2_autosearch — riepilogo reale vs placebo dai CSV di s01 (la prima esecuzione di s01 si e' fermata
per un errore di nome di argomento DOPO aver registrato lotti e selezione e salvato i placebo: qui si
completano le righe di riepilogo senza rifare nulla). La pipeline reale e' deterministica e viene ricalcolata."""
import json

import numpy as np
import pandas as pd

from lab import core
from lab.r2_autosearch import common as cm
from lab.r2_autosearch import s01_autosearch as s

STATS = ("S1_max_t_search", "S2_n_survivors", "S3_max_t_sel", "S4_mean_t_sel", "S5_n_t_gt3_search")


def summary(record=True):
    s._setup()
    st, top, _ = s.run_pipeline(s._G["P"]["G"])
    summ = {}
    for null in ("sign", "block"):
        df = pd.read_csv(cm.CACHE / f"placebo_{null}.csv")
        d = {}
        for k in STATS:
            d[k] = dict(real=st[k], p=float((df[k] >= st[k]).mean()), q05=float(df[k].quantile(0.05)),
                        q50=float(df[k].median()), q95=float(df[k].quantile(0.95)), max=float(df[k].max()))
        d["n_rules_mean"] = float(df["n_rules"].mean())
        summ[null] = d
        if record:
            core.record(cm.FAM, f"placebo_{null}", f"pipeline intera ripetuta su {len(df)} placebo ({null})",
                        "discovery", {"n": len(df)}, kind="placebo_summary", summary=d)
    if record:
        core.record(cm.FAM, "real_pipeline", "pipeline reale: statistiche S1..S5", "discovery",
                    {"n": st["n_rules"]}, kind="real_summary", **st)
    return st, summ


if __name__ == "__main__":
    st, summ = summary()
    print(st)
    print(json.dumps(summ, indent=1))
