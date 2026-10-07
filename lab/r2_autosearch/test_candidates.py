"""Test di riproduzione di r2_autosearch: la pipeline reale deve ridare i numeri del REPORT.
Eseguire: .venv/Scripts/python.exe -m lab.r2_autosearch.test_candidates"""
import numpy as np

from lab.r2_autosearch import common as cm
from lab.r2_autosearch import s01_autosearch as s
from lab.r2_autosearch.candidates import CANDIDATES
from lab.r2_autosearch.s04_look import evaluate


def test_all():
    assert CANDIDATES == []
    s._setup()
    st, top, _ = s.run_pipeline(s._G["P"]["G"])
    assert st["n_rules"] == 480181, st
    assert abs(st["S1_max_t_search"] - 4.1828) < 1e-3
    assert st["S2_n_survivors"] == 1
    assert abs(st["S3_max_t_sel"] - 2.1289) < 1e-3
    # un placebo a caso deve essere riproducibile (seme fisso)
    st0, _, _ = s.run_pipeline(s.placebo_Y("sign", 0))
    assert np.isfinite(st0["S1_max_t_search"])
    r = evaluate(cm.panel(), 690, 120, 1, ("r60>0.50", "gap>0.50", "pos_night>=0.75"))
    assert r["n_selection"] == 94 and abs(r["mean_selection"] - 3.426) < 1e-2
    print("ok", st)


if __name__ == "__main__":
    test_all()
