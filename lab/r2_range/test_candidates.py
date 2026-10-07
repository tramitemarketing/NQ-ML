"""Test di riproduzione: le fn dei candidati, girate su core.load("discovery") SENZA cache, restituiscono i numeri
dichiarati in CANDIDATES[...]["discovery"] (tolleranza sul bootstrap)."""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_range.candidates import CANDIDATES

REQ = ["session", "entry_ts", "exit_ts", "side", "gross_pts"]


def main():
    bars, daily = core.load("discovery")
    for c in CANDIDATES:
        t = c["fn"](bars.copy(), daily.copy())
        assert list(t.columns[:5]) == REQ, t.columns
        t = t[pd.to_datetime(t["session"]).isin(daily.index[daily["in_phase"]])]
        assert (pd.DatetimeIndex(t["entry_ts"]) < pd.DatetimeIndex(t["exit_ts"])).all()
        assert t["session"].is_unique, "piu' di un trade per sessione"
        g = t["gross_pts"].to_numpy(float)
        d = c["discovery"]
        if c["kind"] == "tradeable":
            st = core.day_block_bootstrap(g - core.COST_RT_POINTS, t["session"].values)
            yr = core.yearly(g - core.COST_RT_POINTS, t["session"])
            print(c["id"], st, "anni+", int((yr["mean"] > 0).sum()), "/", len(yr), "drop20", core.drop_top(g - 0.75, 20))
            assert st["n"] == d["n"], (st["n"], d["n"])
            assert abs(st["mean"] - d["mean_net"]) < 1e-3
            assert abs(core.drop_top(g - 0.75, 20) - d["drop20"]) < 1e-3
        else:
            st = core.day_block_bootstrap(g, t["session"].values)
            print(c["id"], st)
            assert st["n"] == d["n"]
            assert abs(st["mean"] - d["mean_gross"]) < 1e-3
            assert st["p_two"] < 0.01
    print("OK")


if __name__ == "__main__":
    main()
