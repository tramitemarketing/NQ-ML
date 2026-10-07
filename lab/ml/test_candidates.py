"""Test minimo: ogni candidato gira su core.load('discovery') e restituisce i numeri dichiarati."""
import sys
import numpy as np, pandas as pd
from lab import core
from lab.ml.candidates import CANDIDATES

def stats(t):
    g = t["gross_pts"].to_numpy(); gp = t["gross_points"].to_numpy(); days = t["session"].to_numpy()
    st = core.day_block_bootstrap(g, days)
    sp = core.day_block_bootstrap(gp, days)
    net = core.day_block_bootstrap(gp - core.COST_RT_POINTS, days)
    yr = core.yearly(g, t["session"]); yp = core.yearly(gp, t["session"])
    return dict(n=st["n"], mean_gross=round(st["mean"], 4), lo=round(st["lo"], 4), hi=round(st["hi"], 4),
                p_two=round(st["p_two"], 4), years_pos=f"{int((yr['mean'] > 0).sum())}/{len(yr)}",
                mean_gross_points=round(sp["mean"], 4), lo_points=round(sp["lo"], 4), hi_points=round(sp["hi"], 4),
                p_two_points=round(sp["p_two"], 4), mean_net_points=round(net["mean"], 4),
                long_share=round(float((t["side"] > 0).mean()), 3), drop_top20=round(core.drop_top(g, 20), 4),
                years_pos_points=f"{int((yp['mean'] > 0).sum())}/{len(yp)}",
                yearly={int(k): round(float(v), 4) for k, v in yr["mean"].items()},
                yearly_points={int(k): round(float(v), 3) for k, v in yp["mean"].items()})

def main(record=False):
    bars, daily = core.load("discovery", warmup_days=400)
    ok = True
    for c in CANDIDATES:
        t = c["fn"](bars, daily)
        assert {"session", "entry_ts", "exit_ts", "side", "gross_pts"} <= set(t.columns)
        assert t["entry_ts"].dt.tz is not None and (t["exit_ts"] > t["entry_ts"]).all()
        # l'ingresso deve cadere in RTH 10:00-15:30 NY
        ny = t["entry_ts"].dt.tz_convert("America/New_York")
        assert ((ny.dt.hour * 60 + ny.dt.minute) >= 600).all() and ((ny.dt.hour * 60 + ny.dt.minute) <= 930).all()
        s = stats(t)
        print(c["id"], s)
        for k, v in c["discovery"].items():
            if v is not None and s.get(k) != v:
                print("  DIVERSO:", k, v, "vs", s.get(k)); ok = False
        if record:
            core.record("ml", f"CANDIDATO_{c['id']}", "Numeri discovery restituiti da fn (candidato congelato): " + c["description"],
                        "discovery", s)
    print("OK" if ok else "NUMERI DIVERSI")
    return ok

if __name__ == "__main__":
    sys.exit(0 if main(record="--record" in sys.argv) else 1)
