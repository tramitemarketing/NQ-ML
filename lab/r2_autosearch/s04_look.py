"""r2_autosearch — sguardo di trasparenza (NON selezione di candidati: il piano esclude candidati perche'
la pipeline non si distingue dal caso). Controlli completi sull'intero discovery per:
  a) la regola n.1 della ricerca (t_ricerca massimo su 480.181);
  b) l'unica «sopravvissuta» della selezione (t_sel > 1,645);
  c) la deriva incondizionata long 09:45 -> chiusura (per leggere l'eccesso di S5 nelle celle del mattino).
"""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_autosearch import common as cm

RULES = [
    ("top1_search", 660, "close", 1, ("r_5d<=0.50", "vol60_rel<=0.50", "pos_today<=0.50")),
    ("lone_survivor", 690, 120, 1, ("r60>0.50", "gap>0.50", "pos_night>=0.75")),
    ("uncond_0945_close_long", 585, "close", 1, ()),
]


def evaluate(P, T, h, side, conds):
    k, m = cm.TIMES.index(T), cm.HORIZONS.index(h)
    w = cm.rule_mask(P, T, conds) if conds else np.ones(len(P["sessions"]), bool)
    g = P["G"][:, k, m]
    w &= np.isfinite(g)
    days = P["sessions"][w]
    gross = side * g[w]
    net = gross - cm.COST
    beta = side * np.nanmean(g)                    # deriva media della stessa finestra, tutte le sessioni
    bs = core.day_block_bootstrap(net, days.values)
    bb = core.day_block_bootstrap(net - beta, days.values)
    yr = core.yearly(net, days)
    per = {"search": days <= pd.Timestamp("2015-12-31"), "selection": days >= pd.Timestamp("2016-01-01")}
    return dict(bs=bs, beta=float(beta), p_net_minus_beta=bb["p_pos"], mean_net_minus_beta=bb["mean"],
                drop20=core.drop_top(net, 20), years_pos=f"{int((yr['mean'] > 0).sum())}/{len(yr)}",
                yearly={int(y): round(v, 2) for y, v in yr["mean"].items()},
                **{f"mean_{a}": float(net[b].mean()) for a, b in per.items()},
                **{f"n_{a}": int(b.sum()) for a, b in per.items()})


if __name__ == "__main__":
    P = cm.panel()
    for name, T, h, side, conds in RULES:
        r = evaluate(P, T, h, side, conds)
        print(name, T, h, side, conds)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != "bs"})
        print({k: round(v, 4) if isinstance(v, float) else v for k, v in r["bs"].items()})
        core.record(cm.FAM, f"look_{name}", f"sguardo di trasparenza sull'intero discovery: T={T} h={h} "
                    f"lato={side} {' & '.join(conds) or 'incondizionata'}", "discovery", r["bs"],
                    kind="look", **{k: v for k, v in r.items() if k != "bs"})
