import datetime as dt

import numpy as np
import pandas as pd
import pytest

from nqml.report.compare import decision_overlap, evaluate_paired_criteria, paired_brier_ci, paired_frame, paired_mean_r, render_comparison

T = lambda s: pd.Timestamp(f"2026-03-10 {s}", tz="UTC")


def _pred(p, take, r, ids=("a", "b", "c", "d")):
    days = [dt.date(2026, 3, 10), dt.date(2026, 3, 10), dt.date(2026, 3, 11), dt.date(2026, 3, 11)]
    return pd.DataFrame({"event_id": list(ids), "session_date": days, "fold": [0, 0, 1, 1], "label": [1, 0, 1, 0],
                         "entry_ts": [T("14:10"), T("15:00"), T("14:10") + pd.Timedelta(days=1), T("15:00") + pd.Timedelta(days=1)],
                         "exit_ts": [T("14:30"), T("15:20"), T("14:30") + pd.Timedelta(days=1), T("15:20") + pd.Timedelta(days=1)],
                         "p": p, "p_context": p, "p_rw": [0.5, 0.5, 0.5, 0.5], "ev_r": [0.2, 0.2, 0.2, 0.2],
                         "take_A": take, "realized_R": r, "pnl_usd": [x * 100 for x in r]})


def test_paired_frame_requires_same_events():
    a, b = _pred([0.5] * 4, [True] * 4, [1.0, -1.0, 1.0, -1.0]), _pred([0.9, 0.1, 0.9, 0.1], [True, False, True, False], [1.0, 0.0, 1.0, 0.0])
    pf = paired_frame(a, b)
    assert len(pf) == 4 and {"p_a", "p_b", "take_A_a", "take_A_b", "realized_R_a", "realized_R_b"} <= set(pf.columns)
    with pytest.raises(ValueError):
        paired_frame(a, b.iloc[:3])


def test_paired_frame_requires_identical_labels_and_unique_ids():
    a = _pred([0.5] * 4, [True] * 4, [1.0, -1.0, 1.0, -1.0])
    b = _pred([0.5] * 4, [True] * 4, [1.0, -1.0, 1.0, -1.0])
    b.loc[b["event_id"] == "c", "label"] = 1 - b.loc[b["event_id"] == "c", "label"]      # una label ribaltata
    with pytest.raises(ValueError, match="label"):
        paired_frame(a, b)
    dup = pd.concat([a, a.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicati"):
        paired_frame(dup, a)


def test_paired_brier_ci_point_and_direction():
    a, b = _pred([0.5] * 4, [True] * 4, [1.0, -1.0, 1.0, -1.0]), _pred([0.9, 0.1, 0.9, 0.1], [True, False, True, False], [1.0, 0.0, 1.0, 0.0])
    pf = paired_frame(a, b)
    out = paired_brier_ci(pf, "p_b", "p_a", n_boot=500, seed=0)
    assert abs(out["point"] - (0.01 - 0.25)) < 1e-12 and out["ci"][1] < 0          # b e' meglio: differenza negativa
    same = paired_brier_ci(pf, "p_a", "p_a", n_boot=100, seed=0)
    assert same["point"] == 0.0 and same["ci"] == (0.0, 0.0)


def test_paired_mean_r_and_overlap():
    a, b = _pred([0.5] * 4, [True] * 4, [1.0, -1.0, 1.0, -1.0]), _pred([0.9, 0.1, 0.9, 0.1], [True, False, True, False], [1.0, 0.0, 1.0, 0.0])
    pf = paired_frame(a, b)
    days = [dt.date(2026, 3, 10), dt.date(2026, 3, 11)]
    mr = paired_mean_r(pf, days, n_boot=200, seed=0)
    assert mr["n_a"] == 4 and mr["n_b"] == 2 and abs(mr["point"] - (1.0 - 0.0)) < 1e-12
    ov = decision_overlap(pf)
    assert ov == {"jaccard": 0.5, "only_a": 2, "only_b": 0, "both": 2}


def test_paired_criteria_and_render():
    cmp = dict(brier_b_vs_a={"point": -0.01, "ci": (-0.02, -0.001)}, brier_b_vs_rw={"point": -0.01, "ci": (-0.02, -0.001)},
               mean_r={"point": 0.1, "ci": (0.02, 0.2), "n_a": 400, "n_b": 300}, overlap={"jaccard": 0.7, "only_a": 50, "only_b": 30, "both": 250},
               by_fold=[{"fold": 0, "auc_a": 0.75, "auc_b": 0.78, "auc_rw": 0.75, "brier_a": 0.18, "brier_b": 0.17, "brier_rw": 0.18}])
    crit = evaluate_paired_criteria(cmp, fraction=0.45, n_A_b=300)
    assert [c["passed"] for c in crit] == [True, True, True, True]
    assert not evaluate_paired_criteria({**cmp, "mean_r": {"point": 0.1, "ci": (-0.02, 0.2), "n_a": 400, "n_b": 300}}, 0.45, 300)[2]["passed"]
    assert not evaluate_paired_criteria(cmp, 0.45, 134)[3]["passed"]              # 300*0.45 = 135
    cmp["criteria"] = crit
    md = render_comparison(cmp, "1a_S", "1b")
    assert "Confronto appaiato 1b − 1a_S" in md and "PASS" in md and "Jaccard" in md


def test_render_comparison_prints_optional_context_and_rw_keys_when_present():
    cmp = dict(brier_b_vs_a={"point": -0.01, "ci": (-0.02, -0.001)}, brier_b_vs_rw={"point": -0.01, "ci": (-0.02, -0.001)},
               brier_a_vs_rw={"point": 0.0105, "ci": (0.0045, 0.0166)},
               brier_b_vs_context={"point": 0.0086, "ci": (0.0031, 0.0143)},
               brier_a_vs_context={"point": 0.0054, "ci": (0.0000, 0.0107)},
               mean_r={"point": 0.1, "ci": (0.02, 0.2), "n_a": 400, "n_b": 300}, overlap={"jaccard": 0.7, "only_a": 50, "only_b": 30, "both": 250},
               by_fold=[{"fold": 0, "auc_a": 0.75, "auc_b": 0.78, "auc_rw": 0.75, "brier_a": 0.18, "brier_b": 0.17, "brier_rw": 0.18}])
    md = render_comparison(cmp, "1a_S", "1b")
    assert "1a_S − prior geometrico" in md and "+0.0105" in md
    assert "1b − solo-contesto" in md and "+0.0086" in md
    assert "1a_S − solo-contesto" in md and "+0.0054" in md


def test_render_comparison_omits_optional_keys_when_absent():
    cmp = dict(brier_b_vs_a={"point": -0.01, "ci": (-0.02, -0.001)}, brier_b_vs_rw={"point": -0.01, "ci": (-0.02, -0.001)},
               mean_r={"point": 0.1, "ci": (0.02, 0.2), "n_a": 400, "n_b": 300}, overlap={"jaccard": 0.7, "only_a": 50, "only_b": 30, "both": 250},
               by_fold=[{"fold": 0, "auc_a": 0.75, "auc_b": 0.78, "auc_rw": 0.75, "brier_a": 0.18, "brier_b": 0.17, "brier_rw": 0.18}])
    md = render_comparison(cmp, "1a_S", "1b")
    assert "solo-contesto" not in md
