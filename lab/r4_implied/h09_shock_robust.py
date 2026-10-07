"""H09: stress del contro-shock (H08_shock_k1.5_oo5, selezionato: i numeri sono condizionati alla scelta).
- griglia k x orizzonte; lato long (dopo ribassi) e short (dopo rialzi) separati;
- sigma implicita contro sigma HAR (l'implicita serve davvero?) e contro soglia fissa in % (1,5 * media);
- bootstrap per CLUSTER di eventi (eventi a meno di h sessioni l'uno dall'altro stanno nello stesso cluster);
- anni, senza i 20 migliori, unita' % del grezzo, beta (deriva media dello stesso orizzonte)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.r4_implied import common as C


def cluster_ids(dates_idx: np.ndarray, gap: int) -> np.ndarray:
    cid = np.zeros(len(dates_idx), int)
    for i in range(1, len(dates_idx)):
        cid[i] = cid[i - 1] + (1 if dates_idx[i] - dates_idx[i - 1] >= gap else 0)
    return cid


def main():
    f = C.load_features()
    o = f["rth_open"]
    pos_i = np.arange(len(f))
    rprev = (f["rth_close"] - f["rth_open"]).shift(1)
    rprev_pct = rprev / f["raw_open"].shift(1) * 100
    sig_imp_pct = (f["VXN"] / np.sqrt(252)).shift(1)                   # % (VXN di S-2 noto il giorno dello shock)
    sig_har_pct = np.sqrt(np.exp(f["har"])).shift(1)                   # sigma RTH prevista per S-1 (%)
    sig_fix = pd.Series(np.nanmean(sig_imp_pct), index=f.index)        # soglia fissa (media del campione: diagnostica)
    rows = []

    def run(tag, sig, k, h, which="both", unit="pts"):
        sd = pd.Series(0.0, index=f.index)
        if which in ("both", "long"):
            sd[rprev_pct < -k * sig] = 1.0
        if which in ("both", "short"):
            sd[rprev_pct > k * sig] = -1.0
        mv = o.shift(-h) - o
        if unit == "pct":
            mv = mv / f["raw_open"] * 100
        m = (sd != 0) & mv.notna()
        gross = (sd * mv)[m]
        net = gross - (core.COST_RT_POINTS if unit == "pts" else 0.0)
        beta = sd[m] * mv.mean()
        ii = pos_i[m.to_numpy()]
        cid = cluster_ids(ii, h)
        st_c = core.day_block_bootstrap(net.to_numpy(), cid)             # bootstrap per cluster
        st_cb = core.day_block_bootstrap((net - beta).to_numpy(), cid)
        tid = f"H09_{tag}_k{k}_h{h}_{which}_{unit}"
        st = C.rec(tid, f"contro-shock {tag} k={k} h={h} lato={which} unita'={unit}; bootstrap per cluster in p_cluster",
                   net.to_numpy(), net.index.values, n_clusters=int(cid.max() + 1), p_cluster_two=st_c["p_two"],
                   lo_cluster=st_c["lo"], hi_cluster=st_c["hi"], beta_adj_mean=st_cb["mean"], p_beta_cluster_pos=st_cb["p_pos"],
                   long_share=float((sd[m] > 0).mean()))
        print(C.fmt(tid, st), f"| cl={cid.max()+1} p_cl={st_c['p_two']:.4f} netto-beta={st_cb['mean']:+.2f} p_b={st_cb['p_pos']:.4f}")
        rows.append((tid, st["mean"], st_c["p_two"]))
        return st

    for k in (1.0, 1.25, 1.5, 1.75, 2.0):
        for h in (1, 3, 5, 10):
            run("imp", sig_imp_pct, k, h)
    for which in ("long", "short"):
        run("imp", sig_imp_pct, 1.5, 5, which)
    run("imp", sig_imp_pct, 1.5, 5, "both", "pct")
    for k in (1.5, 2.0, 2.5):
        run("har", sig_har_pct, k, 5)
    run("fix", sig_fix, 1.5, 5)
    # anni per il caso selezionato
    sd = pd.Series(0.0, index=f.index)
    sd[rprev_pct < -1.5 * sig_imp_pct] = 1.0
    sd[rprev_pct > 1.5 * sig_imp_pct] = -1.0
    mv = o.shift(-5) - o
    m = (sd != 0) & mv.notna()
    net = (sd * mv)[m] - core.COST_RT_POINTS
    print(pd.DataFrame({"net": net, "side": sd[m]}).groupby([net.index.year, "side"])["net"].agg(["mean", "count"]))


if __name__ == "__main__":
    main()
