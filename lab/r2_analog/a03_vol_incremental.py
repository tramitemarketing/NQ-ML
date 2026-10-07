"""A03: gli analoghi aggiungono informazione sulla volatilita' del pomeriggio OLTRE un benchmark lineare?
Benchmark (dichiarato prima): OLS mobile (500 sessioni valide precedenti, min 250) di lrv su
  mlrv (log RV mattina / s5^2), mlrv_last30 (ultimi 30 minuti della mattina), log(night^2 + 0,01),
  log(RV di ieri /78 / s5^2), efficienza della mattina |net|/sum|r5|.
Modello aumentato: + vpred (media lrv dei K analoghi) + dpred (log dev.std di y degli analoghi).
q_t = (lrv - bench)^2 - (lrv - aug)^2 (>0 = gli analoghi migliorano la previsione fuori campione).
Griglia: W in {60,90,150} x rep in REPS x K in {25, 50}. Placebo: analoghi casuali (20 ripetizioni) per W."""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_analog import common as C

bars, daily, M = C.setup_discovery()
ok = M["ok"]; sess = M["sess"].to_numpy()


def roll_pred(y, X, ok, win=500, minp=250):
    Xv = np.column_stack([np.ones(len(X)), X])
    good = ok & np.isfinite(Xv).all(1) & np.isfinite(y)
    out = np.full(len(y), np.nan)
    idx = np.where(good)[0]
    for j, t in enumerate(idx):
        if j < minp:
            continue
        lib = idx[max(0, j - win):j]
        b, *_ = np.linalg.lstsq(Xv[lib], y[lib], rcond=None)
        out[t] = Xv[t] @ b
    return out


def bench_X(W):
    k = W // 5
    r = M["r5"]; s2 = M["s5"] ** 2
    mlrv = np.log((r[:, :k] ** 2).sum(1) / k / s2)
    m30 = np.log((r[:, k - 6:k] ** 2).sum(1) / 6 / s2 + 1e-6)
    nig = np.log(M["night"] ** 2 + 0.01)
    rvd = (r ** 2).sum(1)
    prev = np.full(len(rvd), np.nan); last = np.nan
    for i in range(len(rvd)):        # ultima sessione VALIDA precedente
        prev[i] = last
        if M["ok"][i]:
            last = rvd[i]
    yv = np.log(prev / 78 / s2)
    eff = np.abs(np.log(M["P5"][:, k] / M["P5"][:, 0])) / np.abs(r[:, :k]).sum(1)
    return np.column_stack([mlrv, m30, nig, yv, eff])


rows = []
rng = np.random.default_rng(99)
for W in C.WINDOWS:
    o = C.outcome(M, W); lrv, y = o["lrv"], o["y"]
    Xb = bench_X(W)
    bench = roll_pred(lrv, Xb, ok)
    PL = [C.random_neighbors(ok, 50, rng) for _ in range(20)]
    for rep in C.REPS:
        NN = C.neighbors(C.distance_matrix(C.features(M, W, rep), rep), ok, 100)
        for K in (25, 50):
            vp = C.agg(NN, K, lrv); dp = np.log(C.agg(NN, K, y, "std"))
            aug = roll_pred(lrv, np.column_stack([Xb, vp, dp]), ok & np.isfinite(vp))
            m = ok & M["in_phase"] & np.isfinite(aug) & np.isfinite(bench)
            q = (lrv - bench) ** 2 - (lrv - aug) ** 2
            st = core.day_block_bootstrap(q[m], sess[m], n_boot=2000)
            sst = ((lrv[m] - lrv[m].mean()) ** 2).sum()
            st["r2_bench"] = float(1 - ((lrv[m] - bench[m]) ** 2).sum() / sst)
            st["r2_aug"] = float(1 - ((lrv[m] - aug[m]) ** 2).sum() / sst)
            yrs = pd.Series(q[m]).groupby(M["year"][m]).mean()
            st["years_pos"] = f"{int((yrs > 0).sum())}/{len(yrs)}"
            plq = []
            for P in PL:
                vpp = C.agg(P, K, lrv); dpp = np.log(C.agg(P, K, y, "std"))
                ap = roll_pred(lrv, np.column_stack([Xb, vpp, dpp]), ok & np.isfinite(vpp))
                mm = m & np.isfinite(ap)
                plq.append(np.mean(((lrv - bench) ** 2 - (lrv - ap) ** 2)[mm]))
            st["plac_q_mean"] = float(np.mean(plq)); st["plac_q_max"] = float(np.max(plq))
            C.rec(f"a03_W{W}_{rep}_K{K}", f"vol pomeriggio: benchmark lineare + analoghi (rep={rep}, K={K}, W={W}); "
                  "q = miglioramento errore quadratico fuori campione", st)
            rows.append(dict(W=W, rep=rep, K=K, mean=st["mean"], lo=st["lo"], hi=st["hi"], p=st["p_two"],
                             r2b=st["r2_bench"], r2a=st["r2_aug"], yrs=st["years_pos"], plm=st["plac_q_mean"],
                             plmax=st["plac_q_max"]))
            print(rows[-1], flush=True)
print(pd.DataFrame(rows).round(4).to_string())
