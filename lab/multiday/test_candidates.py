"""Test minimo: le fn dei candidati girano su core.load("discovery") e restituiscono i numeri dichiarati.
Replica le misure del controller: netto = gross - 0,75, filtro in_phase, bootstrap a blocchi per giorno
d'ingresso, anni, senza i 20 migliori, e EV al netto del beta (side x giorni tenuti x deriva media giornaliera
in punti della fase). Uso: .venv/Scripts/python.exe -m lab.multiday.test_candidates [--record]"""
import sys

import numpy as np
import pandas as pd

from lab import core
import lab.multiday.common as C
from lab.multiday import candidates as cand
from lab.multiday.common import build_daily


def measure(c, bars, daily):
    tr = c["fn"](bars, daily)
    inph = daily.index[daily["in_phase"]]
    tr = tr[tr["session"].isin(inph)].copy()
    for col in ("session", "entry_ts", "exit_ts", "side", "gross_pts"):
        assert col in tr.columns
    assert (tr["entry_ts"] < tr["exit_ts"]).all()
    assert tr["gross_pts"].notna().all()
    net = tr["gross_pts"].to_numpy() - core.COST_RT_POINTS
    st = core.day_block_bootstrap(net, tr["session"].to_numpy())
    d = build_daily(bars, daily)
    drift = d.loc[d["in_phase"], "dP"].mean()
    badj = net - tr["side"].to_numpy() * tr["hold_days"].to_numpy() * drift
    sb = core.day_block_bootstrap(badj, tr["session"].to_numpy())
    y = core.yearly(net, tr["session"])
    yb = core.yearly(badj, tr["session"])
    return tr, dict(n=st["n"], mean_net=st["mean"], lo=st["lo"], hi=st["hi"], p_pos=st["p_pos"],
                    years_pos=f"{int((y['mean'] > 0).sum())}/{len(y)}", beta_adj=sb["mean"], beta_lo=sb["lo"],
                    beta_p_pos=sb["p_pos"], beta_years_pos=f"{int((yb['mean'] > 0).sum())}/{len(yb)}",
                    drop20=core.drop_top(net, 20), drift_pts_day=drift), y.assign(beta_adj=yb["mean"])


if __name__ == "__main__":
    bars, daily = core.load("discovery", warmup_days=15)
    C.REV = 3
    for c in cand.CANDIDATES:
        tr, s, y = measure(c, bars, daily)
        print(c["id"], {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()})
        print(y.round(2).to_string())
        print("long:", round(tr.loc[tr.side > 0, "gross_pts"].mean() - 0.75, 2), "short:",
              round(tr.loc[tr.side < 0, "gross_pts"].mean() - 0.75, 2), "giorni medi:", round(tr["hold_days"].mean(), 2))
        dec = c["discovery"]
        if True:
            assert abs(dec["mean_net"] - s["mean_net"]) < 0.01 and dec["n"] == s["n"] and dec["years_pos"] == s["years_pos"], (dec, s)
            print("  -> numeri dichiarati verificati")
        if "--record" in sys.argv:
            C.rec(f"CAND_{c['id']}", "candidato congelato, misura come il controller (tutto il discovery)", s)
