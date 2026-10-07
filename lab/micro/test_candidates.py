"""Test minimo: ogni fn gira su core.load('discovery', warmup) e restituisce i numeri dichiarati."""
import numpy as np
from lab import core
from lab.micro.candidates import CANDIDATES


def run():
    for c in CANDIDATES:
        bars, daily = core.load("discovery", warmup_days=c["warmup_days"])
        t = c["fn"](bars, daily)
        assert list(t.columns) == ["session", "entry_ts", "exit_ts", "side", "gross_pts"], t.columns
        assert (t["entry_ts"] <= t["exit_ts"]).all() and t["side"].isin([1, -1]).all()
        ok = t["session"].isin(daily.index[daily["in_phase"]])
        t = t[ok]
        d = c["discovery"]
        if c["kind"] == "regularity":
            st = core.day_block_bootstrap(t["gross_pts"].to_numpy(), t["session"].to_numpy(), n_boot=10000)
            print(c["id"], st)
            assert st["n"] == d["n"] and abs(st["mean"] - d["mean_gross"]) < 1e-3
        else:
            net = t["gross_pts"].to_numpy() - core.COST_RT_POINTS
            st = core.day_block_bootstrap(net, t["session"].to_numpy(), n_boot=4000)
            print(c["id"], st)
            assert st["n"] == d["n"] and abs(st["mean"] - d["mean_net"]) < 1e-3
    print("OK")


if __name__ == "__main__":
    run()
