import datetime as dt

import numpy as np
import pandas as pd
import pytest

from nqml.report.criteria_1c import evaluate_1c, render_1c

T0 = dt.date(2026, 3, 2)


def _pred(n, seed, p_fn, tick=False):
    rng = np.random.default_rng(seed)
    days = [T0 + dt.timedelta(days=i // 5) for i in range(n)]
    rr = np.exp(rng.normal(np.log(1.9), 0.4, size=n))
    prw = 1 / (1 + rr)
    y = (rng.uniform(size=n) < prw).astype(int)
    p_l2 = prw
    p = p_fn(prw, y, rng)
    return pd.DataFrame({"event_id": [f"e{i}" for i in range(n)], "session_date": days, "fold": [i % 5 for i in range(n)],
                         "label": y, "rr_ratio": rr, "p_rw": prw, "p_l2": p_l2, "p": p,
                         "p_context": prw, "ev_r": 0.2, "take_A": True, "realized_R": rng.normal(size=n), "pnl_usd": 0.0,
                         "entry_ts": pd.Timestamp("2026-03-02 14:00", tz="UTC"), "exit_ts": pd.Timestamp("2026-03-02 15:00", tz="UTC")})


def _sampled(pred, every=2):
    d = sorted(set(pred["session_date"]))[::every]
    return pd.DataFrame({"session_date": d, "month": ["2026-03"] * len(d), "n_valid_in_month": len(d), "n_selected_in_month": len(d)})


def test_p1_fail_when_model_equals_prior_and_s1_not_read():
    a = _pred(2000, 0, lambda prw, y, rng: prw)
    b = a.copy(); b["p"] = np.clip(a["p"] + rng_noise(2000, 1), 0.01, 0.99)
    a1 = a.copy()
    res = evaluate_1c(a, b, a1, _sampled(a), n_boot=300, seed=0)
    assert res["verdict_p1"] == "FAIL" and res["verdict_s1"] == "non letto"
    assert res["p1_95"]["ci"][0] <= 0 <= res["p1_95"]["ci"][1]


def rng_noise(n, seed):
    return np.random.default_rng(seed).normal(0, 0.02, size=n)


def test_p1_confirmed_when_model_knows_the_labels_and_s1_read():
    def sharp(prw, y, rng):
        return np.clip(0.5 * prw + 0.5 * y + rng.normal(0, 0.02, size=len(y)), 0.01, 0.99)
    a = _pred(2000, 2, sharp)
    sampled = _sampled(a)
    in_s = pd.to_datetime(a["session_date"]).dt.date.isin(set(sampled["session_date"])).to_numpy()
    better = np.clip(0.3 * a["p_rw"] + 0.7 * a["label"], 0.01, 0.99)
    b = a.copy(); b["p"] = np.where(in_s, better, a["p"])                              # B meglio SOLO su S, identica ad A fuori
    a1 = a.copy(); a1["p"] = np.clip(a["p"] + rng_noise(2000, 3), 0.01, 0.99)
    res = evaluate_1c(a, b, a1, sampled, n_boot=300, seed=0)
    assert res["verdict_p1"] == "confermato" and res["g1"]["ci"][1] < 0
    assert res["verdict_s1"] in ("candidato", "confermato") and res["s1_95"]["ci"][1] < 0
    assert res["n_all"] == 2000 and res["n_s"] + res["n_non_s"] == 2000


def test_g2_invalidates_s1_when_b_moves_on_non_sampled_days():
    def sharp(prw, y, rng):
        return np.clip(0.5 * prw + 0.5 * y + rng.normal(0, 0.02, size=len(y)), 0.01, 0.99)
    a = _pred(2000, 4, sharp)
    a1 = a.copy(); a1["p"] = np.clip(a["p"] + rng_noise(2000, 5), 0.01, 0.99)
    b = a.copy(); b["p"] = np.clip(a["p"] + 0.2, 0.01, 0.99)                         # B diversa OVUNQUE, anche fuori S
    res = evaluate_1c(a, b, a1, _sampled(a), n_boot=300, seed=0)
    assert res["verdict_p1"] == "confermato" and res["verdict_s1"] == "invalido" and res["g2"]["passed"] is False


def test_render_1c_contains_table_and_verdicts():
    a = _pred(600, 6, lambda prw, y, rng: prw); b = a.copy(); a1 = a.copy()
    res = evaluate_1c(a, b, a1, _sampled(a), n_boot=100, seed=0)
    md = render_1c(res, shuffle_a=[0.5] * 5, shuffle_b=[0.5] * 5,
                    shuffle_fixed_a=[0.25] * 5, shuffle_fixed_b=[0.26] * 5)
    assert "| G1" in md and "| P1" in md and "| S1" in md and "| G2" in md and res["verdict_p1"] in md
    assert "offset fisso" in md and "0.25" in md and "0.26" in md


def test_g2_esito_names_the_actual_p1_verdict():
    from nqml.report.criteria_1c import _g2_esito
    assert _g2_esito("non letto", "FAIL") == "S1 non letto (P1 FAIL)"
    assert _g2_esito("non letto", "invalido") == "S1 non letto (P1 invalido)"
    assert _g2_esito("invalido", "candidato") == "S1 invalido" and _g2_esito("candidato", "candidato") == "S1 valido"
