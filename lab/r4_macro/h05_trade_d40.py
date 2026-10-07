"""Versioni negoziabili del segnale d40_10y (dichiarate prima di eseguire):
 T1 long/short: posizione = -segno(d40_DGS10) noto all'apertura, tenuta finche' il segno non cambia
    (un trade per sequenza, ingresso/uscita all'apertura RTH), punti adj, netto 0,75.
 T2 solo long quando d40<0 (tassi scesi), flat altrimenti.
 T3 solo short quando d40>0.
 T4 regolarita' giornaliera: -segno(d40) x rendimento % open->open del giorno dopo (in bp).
 Controlli: beta (deriva media open->open del discovery x giorni x lato; e beta_component del controller),
 anni, senza i 20 migliori, bootstrap per trade (come il controller) e a blocchi mensili."""
import numpy as np
import pandas as pd
from lab import core
from lab.controller import beta_component
from lab.r4_macro import common as C


def runs(d, pos):
    rows = []; cur = 0.0; start = None
    s = list(pos.index); v = pos.to_numpy()
    for t, x in zip(s, v):
        if x != cur:
            if cur != 0:
                rows.append((start, t, cur))
            cur, start = x, t
    if cur != 0 and start != s[-1]:
        rows.append((start, s[-1], cur))
    tr = pd.DataFrame(rows, columns=["session", "exit_session", "side"])
    tr["entry_ts"] = d.loc[tr["session"], "O_ts"].to_numpy()
    tr["exit_ts"] = d.loc[tr["exit_session"], "O_ts"].to_numpy()
    tr["gross_pts"] = tr["side"] * (d.loc[tr["exit_session"], "O"].to_numpy() - d.loc[tr["session"], "O"].to_numpy())
    tr["hold"] = [pos.index.get_loc(b) - pos.index.get_loc(a) for a, b in zip(tr["session"], tr["exit_session"])]
    tr["side"] = tr["side"].astype(int)
    return tr


def evaluate(tid, desc, d, bars, tr, drift):
    net = tr["gross_pts"].to_numpy() - core.COST_RT_POINTS
    st = core.day_block_bootstrap(net, tr["session"].to_numpy())
    badj = net - tr["side"].to_numpy() * tr["hold"].to_numpy() * drift
    sb = core.day_block_bootstrap(badj, tr["session"].to_numpy())
    bc = beta_component(bars, tr)
    sc = core.day_block_bootstrap(net - bc, tr["session"].to_numpy())
    y = core.yearly(net, tr["session"]); yb = core.yearly(net - bc, tr["session"])
    out = dict(n=st["n"], mean_net=st["mean"], lo=st["lo"], hi=st["hi"], p_pos=st["p_pos"],
               years_pos=f"{int((y['mean'] > 0).sum())}/{len(y)}", beta_adj=sb["mean"], beta_p=sb["p_pos"],
               ctrl_beta_adj=sc["mean"], ctrl_beta_lo=sc["lo"], ctrl_beta_p=sc["p_pos"],
               ctrl_beta_years=f"{int((yb['mean'] > 0).sum())}/{len(yb)}", drop20=core.drop_top(net, 20),
               mean_hold=float(tr["hold"].mean()), frac_long=float((tr["side"] > 0).mean()))
    core.record(C.FAM, tid, desc, "discovery", out)
    print(tid, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()})
    print("   anni netto:", y["mean"].round(1).to_dict())
    print("   anni netto-beta ctrl:", yb["mean"].round(1).to_dict())
    return out


if __name__ == "__main__":
    d, bars, daily = C.load()
    k = C.ext_known(d.index)["DGS10"]
    d["d40"] = (k - k.shift(40)).reindex(d.index)
    d = d[d["O"].notna()]
    drift = (d["O"].diff()).mean()
    print("deriva media open->open (punti):", round(drift, 3))
    s = -np.sign(d["d40"]).fillna(0.0)
    evaluate("T1_d40_ls", "long/short -segno(d40_10y), run fino al cambio di segno, open RTH", d, bars, runs(d, s), drift)
    evaluate("T2_d40_long", "long se d40_10y<0, flat altrimenti", d, bars, runs(d, s.clip(lower=0)), drift)
    evaluate("T3_d40_short", "short se d40_10y>0, flat altrimenti", d, bars, runs(d, s.clip(upper=0)), drift)
    r1 = (d["O"].shift(-1) - d["O"]) / d["Oraw"] * 1e4
    g = (s * r1).dropna()
    st = core.day_block_bootstrap(g.to_numpy(), g.index.to_numpy())
    stm = core.day_block_bootstrap(g.to_numpy(), C.month_key(g.index))
    yy = g.groupby(g.index.year).mean()
    out = dict(**st, p_two_month=stm["p_two"], lo_m=stm["lo"], hi_m=stm["hi"], years_pos=f"{int((yy>0).sum())}/{len(yy)}",
               excess_vs_long=float(g.mean() - r1.mean()))
    core.record(C.FAM, "T4_d40_daily_bp", "regolarita': -segno(d40_10y) x rend. open->open 1g in bp", "discovery", out)
    print("T4", {k2: (round(v, 4) if isinstance(v, float) else v) for k2, v in out.items()}, yy.round(2).to_dict())
