"""r3_adaptive A — la performance recente di una regola predice quella del mese dopo? (regolarita', piano s00)

IC_m = Spearman fra le N regole: lordo medio giornaliero nelle 21*L sessioni prima del mese m contro lordo
medio nel mese m. Mesi da 2011-07 a 2018-12 (lookback completo per ogni L). Nulli: 'segno per giorno'
(500) e 'libreria a lato casuale' (200). Anche per famiglia: spread D (follow - fade) passato -> futuro.
"""
import numpy as np
import pandas as pd
from scipy.stats import rankdata

from lab import core
from lab.r3_adaptive import common as c

LS = [1, 3, 6, 12]


def month_stats(gross, pid, starts, st_ok, L, cols=None):
    g = gross if cols is None else gross[:, cols]
    N = g.shape[1]
    cs = np.vstack([np.zeros((1, N)), np.cumsum(g, 0)])
    w = 21 * L
    ends = np.r_[starts[1:], len(g)]
    past = (cs[st_ok] - cs[st_ok - w]) / w
    e = ends[np.searchsorted(starts, st_ok)]
    fut = (cs[e] - cs[st_ok]) / (e - st_ok)[:, None]
    rp = rankdata(past, axis=1); rf = rankdata(fut, axis=1)
    rp -= rp.mean(1, keepdims=True); rf -= rf.mean(1, keepdims=True)
    ic = (rp * rf).sum(1) / np.sqrt((rp ** 2).sum(1) * (rf ** 2).sum(1))
    return ic, past, fut


def all_stats(gross, sess, pid, meta):
    starts = np.r_[0, np.flatnonzero(np.diff(pid)) + 1]
    st_ok = starts[sess[starts] >= c.SEARCH[0]]
    fol = np.flatnonzero(meta["dir"].to_numpy() == "follow")
    out = {}
    for L in LS:
        ic, past, fut = month_stats(gross, pid, starts, st_ok, L)
        out[f"ic_L{L}"] = ic.mean()
        out[f"ic_L{L}_search"] = ic[sess[st_ok] <= c.SEARCH[1]].mean()
        out[f"ic_L{L}_check"] = ic[sess[st_ok] >= c.CHECK[0]].mean()
        icf, _, _ = month_stats(gross, pid, starts, st_ok, L, cols=fol)
        out[f"icfollow_L{L}"] = icf.mean()
        # famiglia: D = media follow - media fade (lordo)
        Dp = past[:, fol].mean(1) - past[:, ~np.isin(np.arange(gross.shape[1]), fol)].mean(1)
        Df = fut[:, fol].mean(1) - fut[:, ~np.isin(np.arange(gross.shape[1]), fol)].mean(1)
        out[f"famcorr_L{L}"] = np.corrcoef(Dp, Df)[0, 1]
        if L == 3:
            out["_ic_series"] = ic
            out["_months"] = sess[st_ok]
    return out


if __name__ == "__main__":
    P = c.discovery_panel()
    SIDE, GR, meta = c.library(P)
    sess = P["sessions"]
    pid = c.period_ids(sess, "month")
    gross, net, traded = c.gross_net(SIDE, GR)
    real = all_stats(gross, sess, pid, meta)
    rng = np.random.default_rng(12345)
    rows = []
    for rep in range(500):
        s = rng.choice([-1.0, 1.0], size=len(sess))
        g, _, _ = c.gross_net(SIDE, GR, s)
        o = all_stats(g, sess, pid, meta); o["null"] = "sign"; rows.append(o)
    for rep in range(200):
        rs = rng.choice([-1.0, 1.0], size=SIDE.shape) * (SIDE != 0)
        g = rs * GR
        o = all_stats(g, sess, pid, meta); o["null"] = "randside"; rows.append(o)
    pl = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])
    c.CACHE.mkdir(exist_ok=True)
    pl.to_csv(c.CACHE / "persist_placebo.csv", index=False)
    keys = [k for k in real if not k.startswith("_")]
    res = []
    for k in keys:
        d = dict(stat=k, real=real[k])
        for nl in ("sign", "randside"):
            x = pl.loc[pl.null == nl, k].to_numpy()
            d[f"{nl}_med"] = np.median(x); d[f"{nl}_q95"] = np.quantile(x, 0.95)
            d[f"{nl}_p"] = (x >= real[k]).mean()
            d[f"{nl}_p2"] = (np.abs(x - np.median(x)) >= abs(real[k] - np.median(x))).mean()
        res.append(d)
    res = pd.DataFrame(res)
    pd.set_option("display.width", 200)
    print(res.round(4).to_string())
    # bootstrap a blocchi di mesi della serie IC (L=3), come controllo
    ic = real["_ic_series"]; months = real["_months"]
    st = core.day_block_bootstrap(ic, np.arange(len(ic)) // 6)   # blocchi di 6 mesi (overlap L=3)
    print("IC L3 serie:", {k: round(v, 4) if isinstance(v, float) else v for k, v in st.items()})
    print(core.yearly(ic, months).round(3).T.to_string())
    for _, r in res.iterrows():
        core.record(c.FAM, f"A_persist_{r['stat']}", f"persistenza delle regole: {r['stat']} (reale contro 500 placebo segno e 200 lato-casuale)",
                    "discovery", {"n": int(len(ic)), "mean": float(r["real"]), "p_pos": float(r["sign_p"])},
                    p_sign=float(r["sign_p"]), p_randside=float(r["randside_p"]), sign_med=float(r["sign_med"]),
                    randside_med=float(r["randside_med"]), kind="regularity_meta")
