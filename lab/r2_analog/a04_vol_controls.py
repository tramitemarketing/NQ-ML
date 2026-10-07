"""A04: controlli sul risultato di A03 (gli analoghi migliorano la previsione della vol del pomeriggio).
Domanda: e' la traiettoria, o solo cose note che il benchmark lineare di A03 non conteneva?
Benchmark esteso (dichiarato prima di guardare): benchmark A03 + rendimento della mattina CON SEGNO (effetto leva),
  notte con segno, ieri con segno, mlrv^2, mlrv*eff, log(s5 * prezzo / tick) (vol in tick: discretezza).
Confronti (q = errore quadratico del benchmark esteso - errore del modello aumentato):
  (i)   + vpred, dpred degli analoghi (W in {90,150}, rep in {ctx, shape, dtw}, K=25)
  (ii)  solo vpred / solo dpred
  (iii) analoghi nello spazio delle feature SCALARI del benchmark esteso (z-score con media/sd delle 750 sessioni
        precedenti): se fanno lo stesso, e' non-linearita' nelle feature, non 'forma della traiettoria'."""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_analog import common as C

bars, daily, M = C.setup_discovery()
ok = M["ok"]; sess = M["sess"].to_numpy()


def score(lrv, bench, aug, tid, desc, **extra):
    m = ok & M["in_phase"] & np.isfinite(aug) & np.isfinite(bench) & np.isfinite(lrv)
    q = (lrv - bench) ** 2 - (lrv - aug) ** 2
    st = core.day_block_bootstrap(q[m], sess[m], n_boot=2000)
    sst = ((lrv[m] - lrv[m].mean()) ** 2).sum()
    st["r2_bench"] = float(1 - ((lrv[m] - bench[m]) ** 2).sum() / sst)
    st["r2_aug"] = float(1 - ((lrv[m] - aug[m]) ** 2).sum() / sst)
    yrs = pd.Series(q[m]).groupby(M["year"][m]).mean()
    st["years_pos"] = f"{int((yrs > 0).sum())}/{len(yrs)}"
    st["yearly"] = {int(k): round(float(v), 4) for k, v in yrs.items()}
    st.update(extra)
    print(tid, C.fmt(st), "r2", round(st["r2_bench"], 4), round(st["r2_aug"], 4), flush=True)
    C.rec(tid, desc, st)
    return st


def scalar_neighbors(X, K=100):
    """Analoghi nello spazio delle feature scalari, z-score con la biblioteca di ciascun giorno."""
    n = len(X); NN = np.full((n, K), -1); idx = np.where(ok & np.isfinite(X).all(1))[0]
    for j, i in enumerate(idx):
        if j < C.LIB_MIN:
            continue
        lib = idx[max(0, j - C.LIB_WIN):j]
        mu = X[lib].mean(0); sd = X[lib].std(0) + 1e-12
        d = (((X[lib] - mu) / sd - (X[i] - mu) / sd) ** 2).sum(1)
        NN[i] = lib[np.argsort(d, kind="stable")[:K]]
    return NN


for W in (90, 150):
    o = C.outcome(M, W); lrv, y = o["lrv"], o["y"]
    Xb0 = C.vol_bench_X(M, W); Xe = C.vol_bench_X(M, W, extended=True)
    b0 = C.roll_pred(lrv, Xb0, ok); be = C.roll_pred(lrv, Xe, ok)
    score(lrv, b0, be, f"a04_W{W}_ext_vs_base", f"W={W}: benchmark esteso contro benchmark A03")
    for rep in ("ctx", "shape", "dtw"):
        NN = C.neighbors(C.distance_matrix(C.features(M, W, rep), rep), ok, 100)
        vp = C.agg(NN, 25, lrv); dp = np.log(C.agg(NN, 25, y, "std"))
        sel = ok & np.isfinite(vp)
        score(lrv, be, C.roll_pred(lrv, np.column_stack([Xe, vp, dp]), sel), f"a04_W{W}_{rep}_both",
              f"W={W} rep={rep} K=25: esteso + vpred + dpred degli analoghi")
        score(lrv, be, C.roll_pred(lrv, np.column_stack([Xe, vp]), sel), f"a04_W{W}_{rep}_vp",
              f"W={W} rep={rep} K=25: esteso + solo vpred")
        score(lrv, be, C.roll_pred(lrv, np.column_stack([Xe, dp]), sel), f"a04_W{W}_{rep}_dp",
              f"W={W} rep={rep} K=25: esteso + solo dpred (dispersione del futuro degli analoghi)")
    NS = scalar_neighbors(Xe)
    vps = C.agg(NS, 25, lrv); dps = np.log(C.agg(NS, 25, y, "std"))
    score(lrv, be, C.roll_pred(lrv, np.column_stack([Xe, vps, dps]), ok & np.isfinite(vps)), f"a04_W{W}_scalarNN",
          f"W={W}: esteso + analoghi nello spazio delle feature scalari (controllo non-linearita')")
