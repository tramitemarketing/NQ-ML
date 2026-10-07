"""r3_adaptive B — le 106 meta-procedure del piano (s00): ricerca 2011-07..2015-12, verifica 2016-18,
benchmark 'miglior regola fissa', placebo 'segno per giorno' (300) dell'intera pipeline."""
import itertools
import multiprocessing as mp

import numpy as np
import pandas as pd

from lab import core
from lab.r3_adaptive import common as c

TOPK = list(itertools.product(["month", "week"], [1, 3, 6, 12], [1, 5, 20], ["mean", "t"], [False, True]))
HEDGE = list(itertools.product([0.05, 0.2, 1.0], [0, 63]))
REGIME = ["ac1", "vr", "er", "D"]


def config_names():
    n = [f"topk_{f}_L{L}_k{k}_{s}_{'filt' if fl else 'all'}" for f, L, k, s, fl in TOPK]
    n += [f"hedge_eta{e}_hl{h}" for e, h in HEDGE]
    n += [f"regime_{r}" for r in REGIME]
    return n


def setup():
    P = c.discovery_panel()
    SIDE, GR, meta = c.library(P)
    sess = P["sessions"]
    pids = {f: c.period_ids(sess, f) for f in ("month", "week")}
    reg = c.regime_stats(P["G"], P["F"])
    regsig = {k: v > c.causal_median(v) for k, v in reg.items()}      # True -> trend
    regok = {k: np.isfinite(c.causal_median(v)) & np.isfinite(v) for k, v in reg.items()}
    fol = meta["dir"].to_numpy() == "follow"
    return dict(P=P, SIDE=SIDE, GR=GR, meta=meta, sess=sess, pids=pids, regsig=regsig, regok=regok, fol=fol)


def run_configs(S, sign_day=None):
    """(n_s, n_config) P&L netto giornaliero."""
    gross, net, traded = c.gross_net(S["SIDE"], S["GR"], sign_day)
    out = []
    for f, L, k, s, fl in TOPK:
        pos = c.topk_positions(net, traded, S["pids"][f], L, k, s, fl)
        out.append(c.portfolio(net, traded, pos))
    for e, h in HEDGE:
        W = c.hedge_weights(net, traded, S["P"]["atr"], e, h)
        out.append(c.hedge_pnl(net, traded, W))
    fol = S["fol"]
    # spread D giornaliero (lordo) e sua media delle 20 sessioni precedenti
    with np.errstate(invalid="ignore", divide="ignore"):
        gf = (gross * traded)[:, fol].sum(1) / traded[:, fol].sum(1)
        gd = (gross * traded)[:, ~fol].sum(1) / traded[:, ~fol].sum(1)
    D = np.nan_to_num(gf - gd)
    Dp = pd.Series(D).shift(1).rolling(20, min_periods=20).mean().to_numpy()
    trend_pos = np.broadcast_to(fol[None, :], net.shape)
    fade_pos = ~trend_pos
    pnl_tr = c.portfolio(net, traded, trend_pos)
    pnl_mr = c.portfolio(net, traded, fade_pos)
    for r in REGIME:
        if r == "D":
            sig, ok = Dp > 0, np.isfinite(Dp)
        else:
            sig, ok = S["regsig"][r], S["regok"][r]
        out.append(np.where(ok, np.where(sig, pnl_tr, pnl_mr), np.nan))
    return np.column_stack(out), net, traded


def tstat(x):
    x = x[np.isfinite(x)]
    return x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 else np.nan


def pipeline_stats(S, pnl, net, traded):
    sess = S["sess"]
    ms = (sess >= c.SEARCH[0]) & (sess <= c.SEARCH[1])
    mc = (sess >= c.CHECK[0]) & (sess <= c.CHECK[1])
    ts = np.array([tstat(pnl[ms, j]) for j in range(pnl.shape[1])])
    tc = np.array([tstat(pnl[mc, j]) for j in range(pnl.shape[1])])
    win = int(np.nanargmax(ts))
    # regole fisse
    nm = np.where(traded, net, np.nan)
    fs = np.array([tstat(nm[ms, j]) for j in range(nm.shape[1])])
    fc = np.array([tstat(nm[mc, j]) for j in range(nm.shape[1])])
    fw = int(np.nanargmax(fs))
    return dict(S1=np.nanmax(ts), S3=tc[win], win=win, S3_mean=np.nanmean(pnl[mc, win]), S4=np.nanmean(tc),
                n_pos_check=int((tc > 1.645).sum()), fixed_S1=fs[fw], fixed_S3=fc[fw], fixed_win=fw,
                meta_minus_fixed=tc[win] - fc[fw]), ts, tc, fs, fc


_S = None


def _init():
    global _S
    _S = setup()


def _placebo(rep):
    rng = np.random.default_rng(1000 + rep)
    s = rng.choice([-1.0, 1.0], size=len(_S["sess"]))
    pnl, net, traded = run_configs(_S, s)
    st, *_ = pipeline_stats(_S, pnl, net, traded)
    st["rep"] = rep
    return st


if __name__ == "__main__":
    S = setup()
    names = config_names()
    pnl, net, traded = run_configs(S)
    st, ts, tc, fs, fc = pipeline_stats(S, pnl, net, traded)
    sess = S["sess"]
    mc = (sess >= c.CHECK[0]) & (sess <= c.CHECK[1]); ms = (sess >= c.SEARCH[0]) & (sess <= c.SEARCH[1])
    tab = pd.DataFrame(dict(config=names, t_search=ts, t_check=tc,
                            mean_search=np.nanmean(pnl[ms], 0), mean_check=np.nanmean(pnl[mc], 0),
                            days_search=np.isfinite(pnl[ms]).sum(0), days_check=np.isfinite(pnl[mc]).sum(0)))
    c.CACHE.mkdir(exist_ok=True)
    tab.to_csv(c.CACHE / "meta_real.csv", index=False)
    np.save(c.CACHE / "meta_real_pnl.npy", pnl)
    pd.set_option("display.width", 220)
    print(tab.sort_values("t_search", ascending=False).head(15).round(3).to_string())
    print(tab.sort_values("t_check", ascending=False).head(8).round(3).to_string())
    print("real pipeline:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in st.items()})
    print("winner:", names[st["win"]], " fixed winner:", S["meta"].rule[st["fixed_win"]])
    with mp.Pool(30, initializer=_init) as pool:
        pl = pd.DataFrame(pool.map(_placebo, range(300)))
    pl.to_csv(c.CACHE / "meta_placebo.csv", index=False)
    summ = {}
    for k in ["S1", "S3", "S3_mean", "S4", "n_pos_check", "fixed_S1", "fixed_S3", "meta_minus_fixed"]:
        x = pl[k].to_numpy()
        summ[k] = dict(real=st[k], med=np.median(x), q05=np.quantile(x, .05), q95=np.quantile(x, .95), p=(x >= st[k]).mean())
    summ = pd.DataFrame(summ).T
    print(summ.round(3).to_string())
    for i, n in enumerate(names):
        core.record(c.FAM, f"B_{n}", f"meta-procedura {n}: t netto in ricerca 2011-07..2015 / verifica 2016-18",
                    "discovery", {"n": int(tab.days_search[i] + tab.days_check[i]), "mean": float(tab.mean_check[i])},
                    t_search=float(ts[i]), t_check=float(tc[i]), mean_search=float(tab.mean_search[i]), kind="meta_config")
    core.record(c.FAM, "B_pipeline_summary", "pipeline meta: vincitrice in ricerca -> verifica, contro 300 placebo segno-per-giorno",
                "discovery", {"n": 300, "p_pos": float(summ.loc["S3", "p"])},
                winner=names[st["win"]], fixed_winner=S["meta"].rule[st["fixed_win"]],
                **{f"{k}_real": float(summ.loc[k, "real"]) for k in summ.index},
                **{f"{k}_p": float(summ.loc[k, "p"]) for k in summ.index})
