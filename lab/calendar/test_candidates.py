"""Test minimo: ogni fn gira sul discovery e restituisce i numeri dichiarati.
Uso: python -m lab.calendar.test_candidates"""
import numpy as np
import pandas as pd

from lab import core
from lab.calendar.candidates import CANDIDATES


def main():
    for c in CANDIDATES:
        bars, daily = core.load("discovery", warmup_days=c["warmup_days"])
        tr = c["fn"](bars, daily)
        assert list(tr.columns[:5]) == ["session", "entry_ts", "exit_ts", "side", "gross_pts"], tr.columns
        assert (tr["entry_ts"] < tr["exit_ts"]).all()
        inph = set(daily.index[daily["in_phase"]])
        tr = tr[tr["session"].isin(inph)]
        net = tr["gross_pts"].to_numpy() - core.COST_RT_POINTS
        st = core.day_block_bootstrap(net, tr["session"].to_numpy())
        yr = core.yearly(net, tr["session"])
        d = c["discovery"]
        print(c["id"], {k: round(v, 4) if isinstance(v, float) else v for k, v in st.items()},
              "anni+", f"{int((yr['mean'] > 0).sum())}/{len(yr)}", "drop20", round(core.drop_top(net, 20), 3))
        assert st["n"] == d["n"], (st["n"], d["n"])
        assert abs(st["mean"] - d["mean_net"]) < 1e-3, (st["mean"], d["mean_net"])
        assert abs(st["lo"] - d["lo"]) < 1e-3 and abs(st["hi"] - d["hi"]) < 1e-3
        assert f"{int((yr['mean'] > 0).sum())}/{len(yr)}" == d["years_pos"]
    print("OK")


if __name__ == "__main__":
    main()
