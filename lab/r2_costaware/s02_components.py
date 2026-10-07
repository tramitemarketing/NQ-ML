"""Batteria 1: il vantaggio in unita' di vol regge a orizzonti lunghi? Per ogni componente e composito,
rendimento firmato (segno del segnale, fissato a priori) in unita' di vol a h = 30, 60, 120, close.
Tutte le righe (sovrapposte), bootstrap per giorno. Anche in punti lordi e la correlazione di rango."""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_costaware.common import load_panel, ycol, ptscol, rec

ds = load_panel()
yrs = pd.DatetimeIndex(ds["session"]).year
for sig in ["z_ml", "z_day", "z_20d", "z_surp", "COMP2", "COMP3"]:
    for h in [30, 60, 120, "close"]:
        x = ds[sig].to_numpy(float)
        y = ds[ycol(h)].to_numpy(float)
        p = ds[ptscol(h)].to_numpy(float)
        ok = np.isfinite(x) & np.isfinite(y) & (x != 0)
        s = np.sign(x[ok])
        st = core.day_block_bootstrap(s * y[ok], ds["session"].values[ok], n_boot=4000)
        stp = core.day_block_bootstrap(s * p[ok], ds["session"].values[ok], n_boot=4000)
        ic = pd.Series(x[ok]).corr(pd.Series(y[ok]), method="spearman")
        yr = core.yearly(s * y[ok], ds["session"].values[ok])
        ypos = f"{int((yr['mean'] > 0).sum())}/{len(yr)}"
        rec(f"B1_{sig}_h{h}", f"Batteria 1: segno({sig}) -> rendimento firmato a h={h}, unita' vol (tutte le righe)",
            st, ic=float(ic), mean_pts=stp["mean"], lo_pts=stp["lo"], hi_pts=stp["hi"], years_pos=ypos,
            years={int(k): round(float(v), 4) for k, v in yr["mean"].items()})
        print(f"{sig:6s} h={str(h):5s} n={st['n']:6d} vol={st['mean']:+.4f} [{st['lo']:+.4f};{st['hi']:+.4f}] "
              f"p2={st['p_two']:.4f} ic={ic:+.4f} pts={stp['mean']:+.3f} [{stp['lo']:+.2f};{stp['hi']:+.2f}] yrs={ypos}")
