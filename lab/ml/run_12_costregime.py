"""Il costo fisso (0,75 pt) pesa diversamente a seconda della volatilita' in punti. Descrittivo: trade R1 p90
divisi per costo in unita' di vol (0,75/(sig1m*sqrt h)), terzili fissi a priori: <0,03, 0,03-0,06, >0,06."""
import numpy as np, pandas as pd
from lab import core
from lab.ml.common import dataset, CACHE, trade_rule
ds = dataset()
pe = pd.read_parquet(CACHE / "preds_ens.parquet")["E1"]
p30 = pd.read_parquet(CACHE / "preds_h30.parquet")["M1"]
for h, p, nm in ((30, p30, "M1"), (60, pe, "E1")):
    t = trade_rule(ds, p, h=h, q=0.9)
    t["cv"] = 0.75 / (t.sig1m * np.sqrt(h))
    t["b"] = pd.cut(t.cv, [0, 0.03, 0.06, 10], labels=["<0.03", "0.03-0.06", ">0.06"])
    res = {}
    for b, g in t.groupby("b"):
        st = core.day_block_bootstrap(g.net.to_numpy(), g.session.to_numpy(), n_boot=3000)
        sv = core.day_block_bootstrap(g.gross_v.to_numpy(), g.session.to_numpy(), n_boot=3000)
        yrs = sorted(set(pd.DatetimeIndex(g.session).year))
        res[str(b)] = dict(n=st["n"], net=round(st["mean"], 3), lo=round(st["lo"], 3), hi=round(st["hi"], 3),
                           gross_v=round(sv["mean"], 4), gv_lo=round(sv["lo"], 4), gv_hi=round(sv["hi"], 4), years=f"{yrs[0]}-{yrs[-1]}")
        print(nm, h, b, res[str(b)])
    core.record("ml", f"ml_diag_costregime_{nm}_h{h}", f"R1 p90 {nm} h{h} diviso per costo in unita' di vol (<0,03 / 0,03-0,06 / >0,06)", "discovery",
                dict(n=len(t), by_cost=res))
