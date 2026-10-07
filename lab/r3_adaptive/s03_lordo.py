"""r3_adaptive C — DIAGNOSTICA POST-HOC (dichiarata tale, scritta dopo aver visto che in s02 tutte le 106
meta-procedure sono negative al netto gia' in ricerca). Domanda: c'e' almeno un vantaggio LORDO di selezione?
Le configurazioni con molte regole pagano 0,75 per regola senza compensare le posizioni opposte: al netto
sono condannate per costruzione. Qui: stesse 106 configurazioni, stessa scelta online (punteggi sul NETTO,
come nel piano), ma misurate sul LORDO medio per contratto; contro 300 placebo segno-per-giorno.
Unita': punti lordi per 1 contratto. Test unilaterale (selezione migliore del caso)."""
import multiprocessing as mp

import numpy as np
import pandas as pd

from lab import core
from lab.r3_adaptive import common as c
from lab.r3_adaptive import s02_meta as m


def gross_configs(S, sign_day=None):
    pnl_net, net, traded = m.run_configs(S, sign_day)
    # lordo = netto + costo per contratto (ogni giorno operato il portafoglio paga 0,75 per contratto)
    return pnl_net + c.COST, net, traded


def stats(S, g):
    sess = S["sess"]
    ms = (sess >= c.SEARCH[0]) & (sess <= c.SEARCH[1]); mc = (sess >= c.CHECK[0]) & (sess <= c.CHECK[1])
    ts = np.array([m.tstat(g[ms, j]) for j in range(g.shape[1])])
    tc = np.array([m.tstat(g[mc, j]) for j in range(g.shape[1])])
    tall = np.array([m.tstat(g[ms | mc, j]) for j in range(g.shape[1])])
    return dict(mean_t_all=np.nanmean(tall), max_t_all=np.nanmax(tall), n_t2=int((tall > 2).sum()),
                S1=np.nanmax(ts), S3=tc[int(np.nanargmax(ts))], S4=np.nanmean(tc)), ts, tc, tall


_S = None


def _init():
    global _S
    _S = m.setup()


def _pl(rep):
    rng = np.random.default_rng(1000 + rep)          # stessi semi di s02
    s = rng.choice([-1.0, 1.0], size=len(_S["sess"]))
    g, *_ = gross_configs(_S, s)
    return stats(_S, g)[0]


if __name__ == "__main__":
    S = m.setup()
    names = m.config_names()
    g, net, traded = gross_configs(S)
    st, ts, tc, tall = stats(S, g)
    sess = S["sess"]; mall = (sess >= c.SEARCH[0])
    tab = pd.DataFrame(dict(config=names, gross_all=np.nanmean(g[mall], 0), t_all=tall, t_search=ts, t_check=tc))
    tab.to_csv(c.CACHE / "meta_gross_real.csv", index=False)
    pd.set_option("display.width", 220)
    print(tab.sort_values("t_all", ascending=False).head(12).round(3).to_string())
    print(tab.iloc[96:].round(3).to_string())
    with mp.Pool(30, initializer=_init) as pool:
        pl = pd.DataFrame(pool.map(_pl, range(300)))
    pl.to_csv(c.CACHE / "meta_gross_placebo.csv", index=False)
    rows = {}
    for k in st:
        x = pl[k].to_numpy()
        rows[k] = dict(real=st[k], med=np.median(x), q95=np.quantile(x, .95), p=(x >= st[k]).mean())
    rows = pd.DataFrame(rows).T
    print(rows.round(3).to_string())
    core.record(c.FAM, "C_gross_pipeline", "POST-HOC: vantaggio lordo delle 106 meta-procedure contro 300 placebo segno-per-giorno",
                "discovery", {"n": 300, "p_pos": float(rows.loc["mean_t_all", "p"])},
                **{f"{k}_real": float(rows.loc[k, "real"]) for k in rows.index},
                **{f"{k}_p": float(rows.loc[k, "p"]) for k in rows.index}, kind="posthoc")
    for i, n in enumerate(names):
        core.record(c.FAM, f"C_gross_{n}", f"POST-HOC lordo della meta-procedura {n} (2011-07..2018)", "discovery",
                    {"n": int(np.isfinite(g[mall, i]).sum()), "mean": float(tab.gross_all[i])},
                    t_all=float(tall[i]), t_search=float(ts[i]), t_check=float(tc[i]), kind="posthoc")
