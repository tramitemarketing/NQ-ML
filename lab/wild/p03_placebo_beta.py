"""PLACEBO, batteria E: quanto e' largo il buco del criterio 2 (beta) del PROTOCOLLO?

Motivo (dichiarato dopo p02): nella batteria D il 13 % dei placebo long multi-sessione passa TUTTI e
quattro i criteri. Meccanismo sospettato: il criterio 2 chiede solo «EV netto al netto del beta > 0»,
non che sia significativo; un sottoinsieme di giorni scelto a caso ha media sopra quella di tutti i
giorni con probabilita' ~1/2, quindi il criterio 2 filtra solo meta' dei falsi positivi da beta.
Qui: 500 regole a caso (300 long, 100 short, 100 lato-hash) su finestre c2c1 / c2o / c2c5, giorni
scelti con hash e probabilita' casuale 0,2-0,9. Oltre ai 4 criteri, calcolo la correzione proposta:
p unilaterale del bootstrap sul rendimento NETTO MENO BETA (p_badj) < 0,05.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from lab import core
from lab.wild import common as C
from lab.wild.p01_placebo import h64


def main():
    _, daily = core.load("discovery")
    dv = daily[daily["valid"] & daily["in_phase"]]
    sess = dv.index; dates = [d.strftime("%Y%m%d") for d in sess]
    rc = dv["rth_close"].to_numpy(); ro = dv["rth_open"].to_numpy()
    win = {"c2c1": (np.r_[rc[1:], np.nan] - rc, 1), "c2o": (np.r_[ro[1:], np.nan] - rc, 1),
           "c2c5": (np.r_[rc[5:], [np.nan] * 5] - rc, 5)}
    prepared = []
    for r in range(500):
        rng = np.random.default_rng(30_000 + r)
        wname = list(win)[rng.integers(0, 3)]
        ret, step = win[wname]
        dmean = np.nanmean(ret)
        pday = rng.uniform(0.2, 0.9)
        side_s = "long" if r < 300 else ("short" if r < 400 else "hash")
        idx, nxt = [], -1
        for i in range(len(sess)):
            if (h64(dates[i], "E", r) % 10 ** 6) / 10 ** 6 < pday and i >= nxt and np.isfinite(ret[i]):
                idx.append(i); nxt = i + step
        idx = np.array(idx)
        SD = (np.ones(len(idx)) if side_s == "long" else -np.ones(len(idx)) if side_s == "short"
              else np.array([1.0 if h64(dates[i], "Es", r) % 2 else -1.0 for i in idx]))
        t = pd.DataFrame(dict(session=sess[idx], side=SD, gross=SD * ret[idx], beta=SD * dmean))
        prepared.append((f"placebo_E{r:03d}_{wname}_{side_s}",
                         f"PLACEBO multi-sessione casuale (seme {30_000 + r}): finestra {wname}, giorni da "
                         f"hash con prob {pday:.2f}, lato={side_s}; misura anche p sul netto meno beta", t, side_s))

    def boot(t):
        net = t["gross"].to_numpy() - core.COST_RT_POINTS
        return (core.day_block_bootstrap(net, t["session"].to_numpy()),
                core.day_block_bootstrap(net - t["beta"].to_numpy(), t["session"].to_numpy()))

    res = Parallel(n_jobs=24)(delayed(boot)(t) for _, _, t, _ in prepared)
    rows = []
    for (tid, desc, t, sname), (st, sb) in zip(prepared, res):
        net = t["gross"].to_numpy() - core.COST_RT_POINTS
        beta = t["beta"].to_numpy()
        yr = core.yearly(net, t["session"]); ypos = int((yr["mean"] > 0).sum())
        d20 = core.drop_top(net, 20); badj = float(np.mean(net - beta))
        st = dict(st)
        st.update(gross=float(t["gross"].mean()), mean_beta=float(beta.mean()), beta_adj=badj,
                  years_pos=f"{ypos}/{len(yr)}", ypos=ypos, drop20=d20, p_badj=sb["p_pos"],
                  c1=bool(st["p_pos"] < 0.05), c1_bonf=bool(st["p_pos"] < 0.05 / C.K_BONF), c2=bool(badj > 0),
                  c3=bool(ypos >= C.YEARS_NEEDED), c4=bool(d20 > 0))
        st["pass_all"] = bool(st["c1"] and st["c2"] and st["c3"] and st["c4"])
        st["pass_all_bonf"] = bool(st["c1_bonf"] and st["c2"] and st["c3"] and st["c4"])
        st["pass_fixed"] = bool(st["c1"] and sb["p_pos"] < 0.05 and st["c3"] and st["c4"])
        st["pass_fixed_bonf"] = bool(st["c1_bonf"] and sb["p_pos"] < 0.05 / C.K_BONF and st["c3"] and st["c4"])
        C.rec(tid, desc, st, side_scheme=sname, battery="E")
        rows.append(dict(test_id=tid, side=sname, win=tid.split("_")[2], **{k: st[k] for k in (
            "n", "mean", "p_pos", "p_badj", "mean_beta", "beta_adj", "ypos", "drop20", "c1", "c1_bonf",
            "c2", "c3", "c4", "pass_all", "pass_all_bonf", "pass_fixed", "pass_fixed_bonf")}))
    df = pd.DataFrame(rows)
    df.to_csv(C.__file__.replace("common.py", "placebo_results_beta.csv"), index=False)
    pd.set_option("display.width", 200)
    agg = df.groupby(["side", "win"]).agg(N=("n", "size"), mean_net=("mean", "mean"), beta=("mean_beta", "mean"),
                                          p05=("c1", "mean"), p01=("p_pos", lambda s: (s < 0.01).mean()),
                                          c2=("c2", "mean"), ALL4=("pass_all", "mean"),
                                          ALL4_bonf=("pass_all_bonf", "mean"), FIX=("pass_fixed", "mean"),
                                          FIX_bonf=("pass_fixed_bonf", "mean"))
    print(agg.round(3).to_string())
    print(df.groupby("side")[["c1", "pass_all", "pass_all_bonf", "pass_fixed", "pass_fixed_bonf"]].mean().round(3))
    print("hist p_badj (long):", np.histogram(df[df.side == "long"].p_badj, bins=10, range=(0, 1))[0])


if __name__ == "__main__":
    main()
