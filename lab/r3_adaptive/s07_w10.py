"""r3_adaptive G — DIAGNOSTICA POST-HOC di s06 (dichiarata tale): la sola persistenza netta e' a 10 sessioni
(IC +0,037, 0/300 placebo). Domande: (a) e' persistenza di REGIME o solo differenze statiche fra regole?
(IC dopo aver tolto a ogni regola la sua media dell'intero periodo: diagnostica in-sample, non tradabile);
(b) quanto vale in punti: lordo e netto di top-k (k 1/5/20) e del long-short top20-bottom20 ogni 10 sessioni;
(c) ricerca contro verifica, anni. Placebo segno-per-giorno (300) per il P&L."""
import numpy as np
import pandas as pd
from scipy.stats import rankdata

from lab import core
from lab.r3_adaptive import common as c
from lab.r3_adaptive.s06_scale_brevi import ic_blocks


def ic_series(g, i0, wp, wf):
    cs = np.vstack([np.zeros((1, g.shape[1])), np.cumsum(g, 0)])
    st = np.arange(max(i0, wp), len(g) - wf + 1, wf)
    past = (cs[st] - cs[st - wp]) / wp; fut = (cs[st + wf] - cs[st]) / wf
    rp = rankdata(past, axis=1); rf = rankdata(fut, axis=1)
    rp -= rp.mean(1, keepdims=True); rf -= rf.mean(1, keepdims=True)
    return (rp * rf).sum(1) / np.sqrt((rp ** 2).sum(1) * (rf ** 2).sum(1)), st, past


def topk_block(net, traded, i0, w, k, bottom=False):
    """ogni w sessioni sceglie le k regole con miglior (peggior) netto nelle w precedenti; P&L giornaliero."""
    n_s, N = net.shape
    cs = np.vstack([np.zeros((1, N)), np.cumsum(net, 0)])
    pos = np.zeros((n_s, N), bool)
    for s0 in range(max(i0, w), n_s, w):
        sc = (cs[s0] - cs[s0 - w])
        idx = np.argsort(sc)[:k] if bottom else np.argsort(-sc)[:k]
        pos[s0:s0 + w, idx] = True
    return c.portfolio(net, traded, pos), pos


if __name__ == "__main__":
    P = c.discovery_panel()
    SIDE, GR, meta = c.library(P)
    sess = P["sessions"]
    i0 = int(np.searchsorted(sess, c.SEARCH[0]))
    gross, net, traded = c.gross_net(SIDE, GR)
    # (a) statico contro regime
    gd = gross - gross[i0:].mean(0, keepdims=True)
    ic, st, _ = ic_series(gross, i0, 10, 10)
    icd, _, _ = ic_series(gd, i0, 10, 10)
    print(f"IC 10->10 {ic.mean():+.4f}; dopo aver tolto la media di ogni regola {icd.mean():+.4f}")
    sd = sess[st]
    print("IC per anno:", core.yearly(ic, sd)["mean"].round(3).to_dict())
    print("ricerca", ic[sd <= c.SEARCH[1]].mean().round(4), "verifica", ic[sd >= c.CHECK[0]].mean().round(4))
    core.record(c.FAM, "G_ic10_demeaned", "POST-HOC: IC 10->10 dopo aver tolto la media per regola (statico vs regime)", "discovery",
                {"n": len(ic), "mean": float(icd.mean())}, ic_raw=float(ic.mean()), kind="posthoc")
    # IC per sottoinsiemi di regole: solo stessa (T,h)? solo follow?
    fol = meta["dir"].to_numpy() == "follow"
    icf, _, _ = ic_series(gross[:, fol], i0, 10, 10)
    print(f"IC 10->10 solo follow {icf.mean():+.4f}")
    # (b) P&L
    rng = np.random.default_rng(99)
    signs = [rng.choice([-1.0, 1.0], size=len(sess)) for _ in range(300)]
    mall = np.arange(len(sess)) >= i0
    for k in (1, 5, 20):
        y, _ = topk_block(net, traded, i0, 10, k)
        yg = y + c.COST
        stn = core.day_block_bootstrap(y[mall], sess[mall].values)
        stg = core.day_block_bootstrap(yg[mall], sess[mall].values)
        pl = np.array([np.nanmean(topk_block(c.gross_net(SIDE, GR, s)[1], traded, i0, 10, k)[0][mall]) for s in signs[:100]]) + c.COST
        yr = core.yearly(yg[mall], sess[mall])
        print(f"top{k} ogni 10: lordo {stg['mean']:+.3f} [{stg['lo']:+.3f};{stg['hi']:+.3f}] p_pos {stg['p_pos']:.3f} placebo p {(pl>=stg['mean']).mean():.2f} | "
              f"netto {stn['mean']:+.3f} | anni+ lordo {(yr['mean']>0).sum()}/8 | senza top20 lordo {core.drop_top(yg[mall]):+.3f}")
        core.record(c.FAM, f"G_top{k}_w10", f"POST-HOC: top-{k} regole delle 10 sessioni precedenti, tenute 10 sessioni (netto)",
                    "discovery", stn, gross_mean=stg["mean"], gross_p=stg["p_pos"], placebo_p_gross=float((pl >= stg["mean"]).mean()),
                    years_pos_gross=f"{(yr['mean']>0).sum()}/8", kind="posthoc")
    # long-short: top20 - bottom20 (lordo, come misura di regolarita')
    yt, _ = topk_block(net, traded, i0, 10, 20)
    yb, _ = topk_block(net, traded, i0, 10, 20, bottom=True)
    ls = (yt - yb)[mall]
    st2 = core.day_block_bootstrap(ls, sess[mall].values)
    yr = core.yearly(ls, sess[mall])
    print(f"top20 - bottom20 lordo: {st2['mean']:+.3f} [{st2['lo']:+.3f};{st2['hi']:+.3f}] p2 {st2['p_two']:.3f} anni+ {(yr['mean']>0).sum()}/8",
          yr["mean"].round(2).to_dict())
    core.record(c.FAM, "G_ls20_w10", "POST-HOC: spread lordo top20 - bottom20 (10 sessioni -> 10 sessioni)", "discovery", st2,
                years_pos=f"{(yr['mean']>0).sum()}/8", kind="posthoc_regularity")
