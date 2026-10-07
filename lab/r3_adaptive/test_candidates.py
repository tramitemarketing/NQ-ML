"""Test di riproduzione di r3_adaptive: la pipeline reale deve ridare i numeri del REPORT.
Eseguire: .venv/Scripts/python.exe -m lab.r3_adaptive.test_candidates"""
import numpy as np

from lab.r3_adaptive import common as c
from lab.r3_adaptive import s01_persistenza as a
from lab.r3_adaptive import s02_meta as m
from lab.r3_adaptive.candidates import CANDIDATES
from lab.r3_adaptive.s06_scale_brevi import ic_blocks


def test_all():
    assert CANDIDATES == []
    S = m.setup()
    assert S["SIDE"].shape == (2121, 374)
    gross, _, _ = c.gross_net(S["SIDE"], S["GR"])
    st = a.all_stats(gross, S["sess"], S["pids"]["month"], S["meta"])
    assert abs(st["ic_L3"] - 0.0219) < 5e-4, st["ic_L3"]
    pnl, net, traded = m.run_configs(S)
    ps, ts, tc, *_ = m.pipeline_stats(S, pnl, net, traded)
    assert m.config_names()[ps["win"]] == "hedge_eta1.0_hl0"
    assert abs(ps["S1"] + 0.660) < 5e-3 and abs(ps["S3"] + 0.220) < 5e-3, ps
    assert (ts < 0).all()
    i0 = int(np.searchsorted(S["sess"], c.SEARCH[0]))
    ic10, _ = ic_blocks(gross, i0, 10, 10)
    assert abs(ic10 - 0.0371) < 5e-4, ic10
    print("ok", round(st["ic_L3"], 4), round(ps["S1"], 3), round(ps["S3"], 3), round(ic10, 4))


if __name__ == "__main__":
    test_all()
