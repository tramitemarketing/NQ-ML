"""Test minimo: ogni fn gira su core.load('discovery') e restituisce i numeri dichiarati."""
import numpy as np
import pandas as pd

from lab import core
from lab.intraday_momentum.candidates import CANDIDATES


def main():
    for c in CANDIDATES:
        bars, daily = core.load("discovery", warmup_days=c["warmup_days"])
        tr = c["fn"](bars, daily)
        need = {"session", "entry_ts", "exit_ts", "side", "gross_pts"}
        assert need <= set(tr.columns), tr.columns
        assert (tr["entry_ts"] < tr["exit_ts"]).all()
        assert set(tr["side"].unique()) <= {-1, 1}
        inph = daily.index[daily["in_phase"]]
        tr = tr[pd.DatetimeIndex(tr["session"]).isin(inph)]
        d = c["discovery"]
        if c["kind"] == "tradeable":
            v = tr["gross_pts"].to_numpy() - core.COST_RT_POINTS
            st = core.day_block_bootstrap(v, tr["session"].to_numpy())
            y = core.yearly(v, tr["session"])
            yp = f"{int((y['mean'] > 0).sum())}/{len(y)}"
            print(c["id"], st, yp, "drop20", core.drop_top(v, 20))
            assert st["n"] == d["n"] and abs(st["mean"] - d["mean_net"]) < 0.01 and yp == d["years_pos"]
        else:
            v = tr["gross_pts"].to_numpy()
            st = core.day_block_bootstrap(v, tr["session"].to_numpy())
            print(c["id"], st)
            assert st["n"] == d["n"] and abs(st["mean"] - d["mean_gross"]) < 0.01
            m = pd.DatetimeIndex(tr["session"]).year < 2018
            print("  senza 2018: lordo", v[m].mean())
    print("OK")


if __name__ == "__main__":
    main()
