"""Test di riproduzione della famiglia r4_macro. Non ci sono candidati (CANDIDATES vuota): il test verifica
(1) che la lista sia vuota e importabile dal controller, (2) che l'osservazione d40 riproduca i numeri di
discovery registrati (R1_L40: +4,39 bp p 0,053 contando come 0 i giorni con d40=0; qui, senza quei giorni, +4,45 bp p 0,060, 8/9 anni) e l'IC a 20 g (-0,213).
Uso: .venv/Scripts/python.exe -m lab.r4_macro.test_candidates"""
import numpy as np

from lab import core
from lab.r4_macro import candidates as cand
from lab.r4_macro import common as C

if __name__ == "__main__":
    assert cand.CANDIDATES == []
    bars, daily = core.load("discovery")
    ob = cand.observation_d40_daily(bars, daily)
    assert (ob["entry_ts"] < ob["exit_ts"]).all()
    g = ob.set_index("session")["gross_bp"]
    st = core.day_block_bootstrap(g.to_numpy(), g.index.to_numpy())
    yy = g.groupby(g.index.year).mean()
    print("osservazione d40 giornaliera (bp):", round(st["mean"], 2), [round(st["lo"], 2), round(st["hi"], 2)],
          "p", st["p_two"], "anni+", int((yy > 0).sum()), "/", len(yy))
    assert abs(st["mean"] - 4.45) < 0.05 and abs(st["p_two"] - 0.060) < 0.01 and int((yy > 0).sum()) == 8
    d = C.build(bars, daily)
    k = C.ext_known(d.index)["DGS10"]
    d40 = (k - k.shift(40)).reindex(d.index)
    y20, _ = C.fwd(d, 20)
    ic = C.ic_test(d40, y20, n_boot=500)["ic"]
    print("IC d40 -> NQ 20g:", round(ic, 3))
    assert abs(ic - (-0.213)) < 0.005
    print("OK")
