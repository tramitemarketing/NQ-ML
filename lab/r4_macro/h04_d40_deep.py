"""Approfondimento del segnale 'tassi a 10 anni saliti nelle ultime ~8 settimane -> NQ piu' debole nel mese dopo'.
(a) regressione congiunta f20 ~ d40_10y + nq_mom40 + nq_mom20 (z-score, bootstrap mensile sui coefficienti);
(b) griglia piccola di lookback (20,30,40,60,80) x orizzonte (10,20,40) per vedere se e' una superficie liscia;
(c) le altre serie sullo stesso lookback (3 mesi, pendenza, dollaro) per capire cosa conta."""
import numpy as np
import pandas as pd
from lab import core
from lab.r4_macro import common as C

if __name__ == "__main__":
    d, bars, daily = C.load()
    k = C.ext_known(d.index)
    for L in (20, 30, 40, 60, 80):
        for c in ("DGS10", "DGS3MO", "T10Y2Y"):
            d[f"d{L}_{c}"] = (k[c] - k[c].shift(L)).reindex(d.index)
        d[f"r{L}_USD"] = np.log(k["USD"]).diff(L).reindex(d.index)
    cc = d["rth_close"]
    d["nq_mom40"] = (cc.shift(1) - cc.shift(41)) / d["Craw"].shift(41)
    y20, _ = C.fwd(d, 20)
    X = d[["d40_DGS10", "nq_mom40", "nq_mom20"]]
    m = pd.concat([X, y20.rename("y")], axis=1).dropna()
    Z = (m - m.mean()) / m.std()
    A = np.column_stack([np.ones(len(Z)), Z[X.columns].to_numpy()])
    beta = np.linalg.lstsq(A, Z["y"].to_numpy(), rcond=None)[0]
    mk = C.month_key(m.index); um = np.unique(mk); rng = np.random.default_rng(0)
    groups = [np.where(mk == u)[0] for u in um]
    bs = []
    for _ in range(2000):
        ii = np.concatenate([groups[j] for j in rng.integers(0, len(groups), len(groups))])
        bs.append(np.linalg.lstsq(A[ii], Z["y"].to_numpy()[ii], rcond=None)[0])
    bs = np.array(bs)
    out = {}
    for j, nm in enumerate(["const"] + list(X.columns)):
        lo, hi = np.percentile(bs[:, j], [2.5, 97.5])
        p = float(min(1, 2 * min((bs[:, j] - beta[j] + beta[j] <= 0).mean(), (bs[:, j] >= 0).mean())))
        out[nm] = dict(b=round(float(beta[j]), 3), lo=round(float(lo), 3), hi=round(float(hi), 3))
    print("regressione congiunta (z):", out)
    core.record(C.FAM, "H21_joint_reg_d40_mom", "OLS z-score NQ20g ~ d40_10y + mom40 NQ + mom20 NQ, bootstrap mensile", "discovery",
                dict(n=len(m), **{f"b_{k2}": v["b"] for k2, v in out.items()}, **{f"lo_{k2}": v["lo"] for k2, v in out.items()},
                     **{f"hi_{k2}": v["hi"] for k2, v in out.items()}))
    # (b) griglia
    rows = []
    for L in (20, 30, 40, 60, 80):
        for h in (10, 20, 40):
            y, _ = C.fwd(d, h)
            st = C.ic_test(d[f"d{L}_DGS10"], y, n_boot=2000)
            core.record(C.FAM, f"H22_grid_d{L}_f{h}", f"griglia IC d{L}_10y -> NQ {h}g", "discovery", st)
            rows.append((L, h, round(st["ic"], 3), round(st["p_two"], 3), st["years_pos"]))
    print(pd.DataFrame(rows, columns=["L", "h", "ic", "p", "yrs+"]).pivot(index="L", columns="h", values="ic"))
    print(pd.DataFrame(rows, columns=["L", "h", "ic", "p", "yrs+"]).to_string())
    # (c) altre serie a 40g
    for c in ("d40_DGS3MO", "d40_T10Y2Y", "r40_USD"):
        st = C.ic_test(d[c], y20, n_boot=2000)
        core.record(C.FAM, f"H23_{c}_f20", f"IC {c} -> NQ 20g", "discovery", st)
        print(c, round(st["ic"], 3), [round(st["lo"], 3), round(st["hi"], 3)], st["p_two"], st["years_pos"])
