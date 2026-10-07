"""Riproduzione della famiglia r5_amd: CANDIDATES vuota e P0 con i numeri registrati (n 458, netto -0,26, 1/9).
Uso: .venv/Scripts/python.exe -m lab.r5_amd.test_candidates"""
import numpy as np

from lab import core
from lab.r5_amd import candidates as cand

if __name__ == "__main__":
    assert cand.CANDIDATES == []
    bars, daily = core.load("discovery")
    t = cand.observation_p0(bars, daily)
    assert (t["entry_ts"] <= t["exit_ts"]).all()   # stop nella barra di riempimento: stessa barra
    net = t["gross_pts"].to_numpy() - core.COST_RT_POINTS
    st = core.day_block_bootstrap(net, t["session"].values)
    yr = core.yearly(net, t["session"])
    print("P0:", st["n"], round(st["mean"], 2), "anni+", int((yr["mean"] > 0).sum()))
    assert st["n"] == 458 and abs(st["mean"] - (-0.26)) < 0.01 and int((yr["mean"] > 0).sum()) == 1
    print("OK")
