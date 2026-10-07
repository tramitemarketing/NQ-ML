"""Binario 'regolarita'': il modello ordina i rendimenti futuri? Lato = segno di (pred - mediana delle 3000
previsioni precedenti) -> ~50/50 long/short, niente beta. Misura LORDA (nessun costo)."""
import numpy as np, pandas as pd
from lab import core
from lab.ml.common import dataset, CACHE
ds = dataset()
pe = pd.read_parquet(CACHE / "preds_ens.parquet")
p30 = pd.read_parquet(CACHE / "preds_h30.parquet")["M1"]
def reg(p, h, name, desc, q=None):
    d = ds[["session", "slot", "sig1m", f"pts{h}", f"y{h}"]].copy(); d["p"] = p
    d = d[np.isfinite(d.p)].sort_values(["session", "slot"])
    med = d.p.shift(1).rolling(3000, min_periods=2000).median()
    c = d.p - med
    sel = np.isfinite(med) & np.isfinite(d[f"pts{h}"]) & (pd.DatetimeIndex(d.session).year >= 2013)
    if q is not None:
        thr = c.abs().shift(1).rolling(3000, min_periods=2000).quantile(q)
        sel &= c.abs() >= thr
    t = d[sel]; side = np.sign(c[sel])
    g = side * t[f"pts{h}"]; gv = side * t[f"y{h}"]
    st = core.day_block_bootstrap(g.to_numpy(), t.session.to_numpy())
    sv = core.day_block_bootstrap(gv.to_numpy(), t.session.to_numpy(), n_boot=4000)
    yr = core.yearly(g.to_numpy(), t.session); yv = core.yearly(gv.to_numpy(), t.session)
    res = dict(st, unit="punti NQ LORDI per trade", mean_v=sv["mean"], lo_v=sv["lo"], hi_v=sv["hi"], p_two_v=sv["p_two"],
               long_share=float((side > 0).mean()), years_pos=f"{int((yr['mean']>0).sum())}/{len(yr)}",
               years_pos_v=f"{int((yv['mean']>0).sum())}/{len(yv)}", yearly={int(k): round(v, 3) for k, v in yr["mean"].items()},
               yearly_v={int(k): round(v, 4) for k, v in yv["mean"].items()})
    core.record("ml", name, desc, "discovery", res)
    print(f"[{name}] n={st['n']} lordo {st['mean']:+.3f} [{st['lo']:+.3f};{st['hi']:+.3f}] p2={st['p_two']:.4f} | vol {sv['mean']:+.4f} "
          f"[{sv['lo']:+.4f};{sv['hi']:+.4f}] p2={sv['p_two']:.4f} | long {res['long_share']:.2f} | anni {res['years_pos']} / vol {res['years_pos_v']}")
    print("   ", res["yearly"], res["yearly_v"])
reg(pe["E1"], 60, "ml_REG_E1_h60_all", "Regolarita': LGB5semi y60, tutti gli slot, lato=segno(pred-mediana passata), lordo")
reg(pe["E1"], 60, "ml_REG_E1_h60_q80", "Regolarita': LGB5semi y60, |pred-mediana| >= p80 passato, lordo", q=0.8)
reg(p30, 30, "ml_REG_M1_h30_all", "Regolarita': LGB y30, tutti gli slot, lato=segno(pred-mediana passata), lordo")
