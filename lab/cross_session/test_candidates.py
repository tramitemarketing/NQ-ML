"""Test minimo: ogni candidato gira sul discovery e riproduce i numeri dichiarati (non registra nulla)."""
import numpy as np, pandas as pd
from lab import core
from lab.cross_session.candidates import CANDIDATES

def main():
    for c in CANDIDATES:
        bars, daily = core.load("discovery", warmup_days=c["warmup_days"])
        df = c["fn"](bars, daily)
        assert set(["session", "entry_ts", "exit_ts", "side", "gross_pts"]) <= set(df.columns)
        assert (df["exit_ts"] > df["entry_ts"]).all()
        ph = daily.index[daily["in_phase"]]
        df = df[df["session"].isin(ph)]
        v = df["gross_pts"].to_numpy(); d = df["session"].to_numpy()
        st = core.day_block_bootstrap(v, d)
        stn = core.day_block_bootstrap(v - core.COST_RT_POINTS, d)
        yr = core.yearly(v, d)
        print(c["id"], "n", st["n"], "gross %.4f [%.4f; %.4f] p_two %.4f" % (st["mean"], st["lo"], st["hi"], st["p_two"]),
              "| net %.3f p_pos %.3f" % (stn["mean"], stn["p_pos"]), "| anni lordo+ %d/%d" % ((yr["mean"] > 0).sum(), len(yr)),
              "| drop20 lordo %.4f" % core.drop_top(v, 20))
        dc = c["discovery"]
        assert dc["n"] == st["n"], (dc["n"], st["n"])

if __name__ == "__main__":
    main()
