"""Test di riproduzione: ogni fn gira su core.load("discovery") e restituisce i numeri dichiarati.
Uso: .venv/Scripts/python.exe -m lab.r2_footprints.test_candidates"""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_footprints.candidates import CANDIDATES

COLS = ["session", "entry_ts", "exit_ts", "side", "gross_pts"]

if __name__ == "__main__":
    for c in CANDIDATES:
        bars, daily = core.load("discovery", warmup_days=c["warmup_days"])
        t = c["fn"](bars, daily)
        assert list(t.columns) == COLS, t.columns
        t = t[t["session"].isin(daily.index[daily["in_phase"]])]
        assert (pd.DatetimeIndex(t["exit_ts"]) > pd.DatetimeIndex(t["entry_ts"])).all()
        g = t["gross_pts"].to_numpy()
        st = core.day_block_bootstrap(g, t["session"].to_numpy())
        y = core.yearly(g, t["session"])
        yp = f"{int((y['mean'] > 0).sum())}/{len(y)}"
        d20 = core.drop_top(g, 20)
        core.record("r2_footprints", f"REPRO_{c['id']}", f"test di riproduzione del candidato {c['id']} su discovery",
                    "discovery", st, years_pos=yp, drop20=d20, yearly=y["mean"].round(4).to_dict())
        print(c["id"], {k: round(v, 5) if isinstance(v, float) else v for k, v in st.items()}, yp, "drop20", round(d20, 4))
        print(y["mean"].round(4).to_dict())
        dd = c["discovery"]
        if dd.get("mean_gross") is not None:
            assert abs(st["mean"] - dd["mean_gross"]) < 1e-3, (st["mean"], dd["mean_gross"])
            assert st["n"] == dd["n"], (st["n"], dd["n"])
            print("  OK: riproduce i numeri dichiarati")
