"""A01: previsione per analoghi (Lorenz) — griglia dichiarata in common.py: W x rappresentazione x K.
Per ogni configurazione: IC direzionale (pred vs y del pomeriggio), sign_mean, percentile contro 200 placebo
(K giorni a caso della stessa biblioteca); volatilita': corr(vpred, lrv) e corr parziale dato il log RV
della mattina (stessa finestra), contro placebo. Tutto registrato."""
import numpy as np
import pandas as pd

from lab.r2_analog import common as C

bars, daily, M = C.setup_discovery()
ok = M["ok"]
sess = M["sess"].to_numpy()
rng = np.random.default_rng(12345)
N_PL = 200
rows = []


def partial_corr(a, b, z):
    Z = np.column_stack([np.ones(len(z)), z])
    ra = a - Z @ np.linalg.lstsq(Z, a, rcond=None)[0]
    rb = b - Z @ np.linalg.lstsq(Z, b, rcond=None)[0]
    return float(np.corrcoef(ra, rb)[0, 1])


# placebo: neighbors casuali una volta per ripetizione (kmax 100), riusati per tutte le W/rep
PL = [C.random_neighbors(ok, 100, rng) for _ in range(N_PL)]

for W in C.WINDOWS:
    o = C.outcome(M, W)
    y, lrv = o["y"], o["lrv"]
    k = W // 5
    mlrv = np.log((M["r5"][:, :k] ** 2).sum(1) / k / M["s5"] ** 2)   # vol della mattina (nota alla decisione)
    for rep in C.REPS:
        X = C.features(M, W, rep)
        D = C.distance_matrix(X, rep)
        NN = C.neighbors(D, ok, 100)
        base = ok & M["in_phase"] & (NN[:, 0] >= 0) & np.isfinite(y)
        for K in C.KS:
            pred = C.agg(NN, K, y)
            st = C.ic_stats(pred, y, sess, base)
            m = base & np.isfinite(pred)
            pl_ic = []; pl_sg = []; pl_v = []; pl_vp = []
            for P in PL:
                pp = C.agg(P, K, y)
                pl_ic.append(np.corrcoef(pp[m], y[m])[0, 1])
                pl_sg.append(np.mean(np.sign(pp[m]) * y[m]))
                vp = C.agg(P, K, lrv)
                pl_v.append(np.corrcoef(vp[m], lrv[m])[0, 1])
                pl_vp.append(partial_corr(vp[m], lrv[m], mlrv[m]))
            pl_ic = np.array(pl_ic); pl_sg = np.array(pl_sg)
            st["plac_pct"] = float((pl_ic < st["ic"]).mean())
            st["plac_ic_mean"] = float(pl_ic.mean()); st["plac_ic_sd"] = float(pl_ic.std())
            st["plac_sign_pct"] = float((pl_sg < st["sign_mean"]).mean())
            vpred = C.agg(NN, K, lrv)
            st["vol_corr"] = float(np.corrcoef(vpred[m], lrv[m])[0, 1])
            st["vol_pcorr"] = partial_corr(vpred[m], lrv[m], mlrv[m])
            st["vol_corr_plac_pct"] = float((np.array(pl_v) < st["vol_corr"]).mean())
            st["vol_pcorr_plac_pct"] = float((np.array(pl_vp) < st["vol_pcorr"]).mean())
            st["vol_pcorr_plac_mean"] = float(np.mean(pl_vp))
            tid = f"a01_W{W}_{rep}_K{K}"
            C.rec(tid, f"analoghi: mattina 09:30+{W}m rep={rep} K={K}; IC direzionale pomeriggio (y vol-unit) "
                       f"e vol (lrv) vs 200 placebo casuali", st)
            rows.append(dict(W=W, rep=rep, K=K, n=st["n"], ic=st["ic"], lo=st["lo"], hi=st["hi"], p_two=st["p_two"],
                             plac=st["plac_pct"], sign=st["sign_mean"], sign_pl=st["plac_sign_pct"], yrs=st["years_pos"],
                             vcorr=st["vol_corr"], vpc=st["vol_pcorr"], vpc_pl=st["vol_pcorr_plac_pct"],
                             vpc_plm=st["vol_pcorr_plac_mean"]))
            print(rows[-1], flush=True)

df = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print(df.round(4).to_string())
df.to_csv(__file__.replace(".py", ".csv"), index=False)
