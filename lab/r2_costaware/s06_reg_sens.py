"""Batteria 5: sensibilita' della regolarita' centrata COMP2 -> chiusura (unita' vol, media giornaliera).
Griglia dichiarata qui prima di guardare: finestra della mediana {1000, 3000, 6000}; per slot (mattina 10:00-12:30,
pomeriggio 13:00-15:30); componenti singole centrate allo stesso modo."""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_costaware.common import load_panel, rec

ds = load_panel()


def reg(sig, win=3000, slots=None, tag=""):
    med = ds[sig].shift(1).rolling(win, min_periods=min(1000, win)).median()
    d = ds.assign(c=ds[sig] - med)
    ok = np.isfinite(d["c"]) & np.isfinite(d["y_close"]) & (d["c"] != 0)
    if slots is not None:
        ok &= d["slot"].isin(slots)
    d = d[ok]
    d["q"] = np.sign(d["c"]) * d["y_close"]
    day = d.groupby("session")["q"].mean()
    st = core.day_block_bootstrap(day.to_numpy(), day.index.values)
    yr = core.yearly(day.to_numpy(), day.index)
    yp = f"{int((yr['mean']>0).sum())}/{len(yr)}"
    rec(f"B5_{sig}_c{win}{tag}", f"Regolarita' centrata segno({sig}-mediana {win})*y_close, media giornaliera {tag}", st,
        years_pos=yp, years={int(k): round(float(v), 4) for k, v in yr["mean"].items()})
    print(f"{sig:6s} win={win} {tag:5s} n={st['n']} {st['mean']:+.4f} [{st['lo']:+.4f};{st['hi']:+.4f}] p2={st['p_two']:.4f} yrs={yp}",
          yr["mean"].round(3).to_dict())


for w in [1000, 6000]:
    reg("COMP2", w)
reg("COMP2", 3000, slots=list(range(600, 751, 30)), tag="am")
reg("COMP2", 3000, slots=list(range(780, 931, 30)), tag="pm")
for sig in ["z_day", "z_20d"]:
    reg(sig, 3000)
