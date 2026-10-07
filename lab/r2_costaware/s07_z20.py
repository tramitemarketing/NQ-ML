"""Batteria 6 (POST HOC, dichiarato): la scomposizione di B5 mostra che la regolarita' sta nella componente z_20d.
Qui: (a) sensibilita' della regolarita' z_20d centrata (finestra 1000/6000, mattina/pomeriggio, h=60/120 invece di close);
(b) la regola di costo applicata a z_20d centrato (Z20C), h=close, m in {0,1,1.5,2}, con controlli."""
import hashlib

import numpy as np
import pandas as pd

from lab import core
from lab.r2_costaware.common import load_panel, rule_trades, evaluate, rec, fmt, ycol

ds = load_panel()


def centered(sig, win=3000):
    med = ds[sig].shift(1).rolling(win, min_periods=min(1000, win)).median()
    return ds[sig] - med


def reg(c, h="close", slots=None, tag=""):
    d = ds.assign(c=c)
    y = ycol(h)
    ok = np.isfinite(d["c"]) & np.isfinite(d[y]) & (d["c"] != 0)
    if slots is not None:
        ok &= d["slot"].isin(slots)
    d = d[ok]
    d["q"] = np.sign(d["c"]) * d[y]
    day = d.groupby("session")["q"].mean()
    st = core.day_block_bootstrap(day.to_numpy(), day.index.values)
    yr = core.yearly(day.to_numpy(), day.index)
    yp = f"{int((yr['mean']>0).sum())}/{len(yr)}"
    rec(f"B6a_z20c_{tag}", f"Regolarita' z_20d centrato, media giornaliera, {tag}", st, years_pos=yp,
        years={int(k): round(float(v), 4) for k, v in yr["mean"].items()}, long_share=float((d["c"] > 0).mean()))
    print(f"z20c {tag:12s} n={st['n']} {st['mean']:+.4f} [{st['lo']:+.4f};{st['hi']:+.4f}] p2={st['p_two']:.4f} yrs={yp}",
          yr["mean"].round(3).to_dict(), "L", round(float((d['c'] > 0).mean()), 2))


for w in [1000, 6000]:
    reg(centered("z_20d", w), tag=f"win{w}")
reg(centered("z_20d"), slots=list(range(600, 751, 30)), tag="am")
reg(centered("z_20d"), slots=list(range(780, 931, 30)), tag="pm")
reg(centered("z_20d"), slots=[600], tag="only1000")
for h in [60, 120]:
    reg(centered("z_20d"), h=h, tag=f"h{h}")
# versione grezza (non centrata) per confronto con il beta
reg(ds["z_20d"], tag="raw")

ds["Z20C"] = centered("z_20d")
for m in [0.0, 1.0, 1.5, 2.0]:
    t = rule_trades(ds, "Z20C", "close", m)
    s = evaluate(t)
    rec(f"B6b_Z20C_close_m{m}", f"Regola di costo su z_20d centrato, h=close, m={m} (post hoc)", s)
    print(f"RULE Z20C m={m}: {fmt(s)}\n   {s['years']}")
    if m == 1.0:
        hs = np.array([1 if int(hashlib.md5(str(d)[:10].encode()).hexdigest(), 16) % 2 else -1 for d in t["session"]])
        tr = t.copy(); tr["gross_pts"] = tr["gross_pts"] * tr["side"] * hs; tr["gross_vol"] *= tr["side"] * hs; tr["side"] = hs
        s2 = evaluate(tr)
        rec("B6b_Z20C_close_m1_randside", "Stessi trade Z20C close m=1 con lato casuale", s2)
        print(f"   lato casuale: {fmt(s2)}")
