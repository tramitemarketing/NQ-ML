"""H06: verifica onesta di H05B (SKEW/VVIX -> code nei 20 giorni) e H05C: le finestre a 20 giorni si sovrappongono,
quindi il bootstrap per giorno e' troppo ottimista. Qui: (1) campioni NON sovrapposti (un giorno ogni 20, 20 fasi),
(2) bootstrap a blocchi mobili di 60 sessioni, (3) OLS con errori HAC(20) e controlli (rank VXN, rank HAR, rank VRP).
Piu' la stessa domanda a 5 giorni e per la coda destra (placebo di simmetria)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from lab import core
from lab.r4_implied import common as C


def mbb_p(v: np.ndarray, block=60, n_boot=5000, seed=0):
    v = v[np.isfinite(v)]
    n = len(v)
    point = v.mean()
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(n_boot, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_boot, -1)[:, :n]
    dist = v[idx].mean(1)
    c = dist - point
    return float(point), float(np.percentile(dist, 2.5)), float(np.percentile(dist, 97.5)), max(float((np.abs(c) >= abs(point)).mean()), 1 / n_boot)


def main():
    f = C.load_features()
    rth_pct = (f["rth_close"] - f["rth_open"]) / f["raw_open"] * 100
    sd = np.sqrt(np.exp(f["har"]))
    ranks = {c: C.prank(f[c]) for c in ["skew_s", "vvix_s", "vxn_s", "vrp_har_s", "har"]}
    for side_nm, tail in (("left", rth_pct < -2 * sd), ("right", rth_pct > 2 * sd)):
        tail = tail.astype(float).where(sd.notna())
        for h in (5, 20):
            fut = pd.concat([tail.shift(-j) for j in range(1, h + 1)], axis=1).mean(axis=1)
            for sig in ("skew_s", "vvix_s"):
                rs = ranks[sig]
                v = ((rs - 0.5) * (fut - fut.mean())).dropna()
                mean, lo, hi, p = mbb_p(v.to_numpy(), block=60)
                # non sovrapposti: media sulle h fasi dei p-value? riporto la fase 0 e la media delle stime
                est = [v.iloc[k::h].mean() for k in range(h)]
                d = pd.DataFrame({"y": fut, "r": rs, "rv": ranks["vxn_s"], "rh": ranks["har"], "rp": ranks["vrp_har_s"]}).dropna()
                res = sm.OLS(d["y"], sm.add_constant(d[["r", "rv", "rh", "rp"]])).fit(cov_type="HAC", cov_kwds={"maxlags": h})
                tid = f"H06_{sig}_{side_nm}_tail{h}_mbb"
                core.record(C.FAM, tid, f"(rank {sig}-0.5)*(quota giorni coda {side_nm} >2 sigma HAR nei {h} successivi); bootstrap a blocchi 60 + OLS HAC con controlli",
                            "discovery", {"n": int(len(v)), "mean": mean, "lo": lo, "hi": hi, "p_two": p,
                                          "nonoverlap_min": float(min(est)), "nonoverlap_max": float(max(est)),
                                          "ols_coef": float(res.params["r"]), "ols_t": float(res.tvalues["r"]),
                                          "ols_t_vxn": float(res.tvalues["rv"]), "ols_t_har": float(res.tvalues["rh"])})
                print(f"{tid:36s} mean={mean:+.5f} [{lo:+.5f};{hi:+.5f}] p_mbb={p:.4f} | OLS t(sig)={res.tvalues['r']:+.2f} "
                      f"t(vxn)={res.tvalues['rv']:+.2f} t(har)={res.tvalues['rh']:+.2f} t(vrp)={res.tvalues['rp']:+.2f}")
    # yearly of the skew left 20 effect (simple conditional rates)
    tail = (rth_pct < -2 * sd).astype(float).where(sd.notna())
    fut = pd.concat([tail.shift(-j) for j in range(1, 21)], axis=1).mean(axis=1)
    rs = ranks["skew_s"]
    d = pd.DataFrame({"fut": fut, "hi": rs >= 0.8, "lo": rs <= 0.2, "y": f.index.year}).dropna()
    print(d.groupby("y").apply(lambda x: pd.Series({"hi": x.loc[x.hi, "fut"].mean(), "lo": x.loc[x.lo, "fut"].mean(), "all": x.fut.mean()})))


if __name__ == "__main__":
    main()
