"""Sensibilita' del candidato ml_rank30: finestra della mediana (1000, 6000) e seme del modello (11, 23, 42)."""
import numpy as np, pandas as pd
from lab import core
from lab.ml.common import dataset, walk_forward, fit_lgb, CACHE
ds = dataset().sort_values(["session", "slot"])
def reg(p, window, name, desc):
    d = ds[["session", "y30"]].copy(); d["p"] = p.reindex(d.index)
    d = d[np.isfinite(d.p)]
    med = d.p.shift(1).rolling(window, min_periods=min(2000, window)).median()
    ok = np.isfinite(med) & np.isfinite(d.y30)
    g = (np.sign(d.p - med) * d.y30)[ok]
    st = core.day_block_bootstrap(g.to_numpy(), d.session[ok].to_numpy(), n_boot=4000)
    yr = core.yearly(g.to_numpy(), d.session[ok])
    st["years_pos"] = f"{int((yr['mean']>0).sum())}/{len(yr)}"
    core.record("ml", name, desc, "discovery", st)
    print(f"[{name}] n={st['n']} {st['mean']:+.4f} [{st['lo']:+.4f};{st['hi']:+.4f}] p2={st['p_two']:.4f} anni {st['years_pos']}")
p = pd.read_parquet(CACHE / "preds_h30.parquet")["M1"]
for w in (1000, 6000):
    reg(p, w, f"ml_SENS_rank30_win{w}", f"Sensibilita' ml_rank30: finestra mediana {w} (unita' vol)")
for seed in (11, 23, 42):
    ps, _ = walk_forward(dataset(), fit_lgb, "y30", objective=dict(seed=seed))
    reg(ps, 3000, f"ml_SENS_rank30_seed{seed}", f"Sensibilita' ml_rank30: seme LGB {seed} (unita' vol)")
