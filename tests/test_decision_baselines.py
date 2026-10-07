import numpy as np
import pandas as pd
import pytest

from nqml.config import load_config
from nqml.model.baselines import apply_c_opt, fit_c_opt, rule_list
from nqml.model.decision import costs_in_r, ev_r, take

CFG = load_config("config.yaml")


def test_costs_in_r_default_and_override():
    # stop 20 pt: (2*2.5 + 2*0.25*20) / (20*20) = 15/400
    assert abs(costs_in_r(20.0, CFG) - 15 / 400) < 1e-12
    assert abs(costs_in_r(20.0, CFG, slippage_ticks=2, commission=5.0) - (10 + 20) / 400) < 1e-12
    arr = costs_in_r(np.array([20.0, 40.0]), CFG)
    assert arr.shape == (2,) and abs(arr[1] - 15 / 800) < 1e-12


def test_ev_and_take():
    # p=0.4, rr=2, costi 0.05 -> 0.8 - 0.6 - 0.05 = 0.15 > 0.1 -> take
    assert abs(ev_r(0.4, 2.0, 0.05) - 0.15) < 1e-12 and take(0.15, 0.1)
    ev = ev_r(np.array([0.4, 0.3]), np.array([2.0, 2.0]), 0.05)
    assert list(take(ev, 0.1)) == [True, False]


def _df():
    return pd.DataFrame({
        "vol_slope_excursion": [-0.1, -0.1, 0.1, np.nan, -0.3, -0.3],
        "vol_reentry_bar":     [1.5,  0.5, 1.5, 1.5,    2.0,  2.0],
        "realized_R":          [1.0, -1.0, 1.0, 1.0,   -1.0, -1.0],
    })


RULES_1A = [{"feature": "vol_slope_excursion", "op": "<", "value": 0.0, "values": [-0.2, 0.0]},
            {"feature": "vol_reentry_bar", "op": ">", "value": 1.0, "values": [1.0]}]


def test_rule_list_literal_and_nan():
    assert list(rule_list(_df(), RULES_1A)) == [True, False, False, False, True, True]


def test_rule_list_three_rules_with_delta():
    df = _df().assign(delta_excursion=[0.2, 0.2, 0.2, 0.2, -0.1, np.nan])
    rules = RULES_1A + [{"feature": "delta_excursion", "op": ">", "value": 0.0, "values": [0.0]}]
    assert list(rule_list(df, rules)) == [True, False, False, False, False, False]


def test_rule_list_rejects_unknown_operator():
    rules = [{"feature": "vol_slope_excursion", "op": ">=", "value": 0.0, "values": [0.0]}]
    with pytest.raises(ValueError):
        rule_list(_df(), rules)


def test_fit_c_opt_picks_best_mean_r_with_min_trades():
    cfg = {"baselines": {"rules_by_version": {"1a": RULES_1A}, "c_opt_min_trades": 1}}
    rules = fit_c_opt(_df(), cfg, "1a")
    # max -0.2: righe 4,5 (R media -1); max 0.0: righe 0,4,5 (R media -1/3) -> vince 0.0
    assert [r["value"] for r in rules] == [0.0, 1.0]
    assert list(apply_c_opt(_df(), rules)) == list(rule_list(_df(), RULES_1A))


def test_fit_c_opt_falls_back_to_default_when_too_few_trades():
    cfg = {"baselines": {"rules_by_version": {"1a": RULES_1A}, "c_opt_min_trades": 50}}
    assert [r["value"] for r in fit_c_opt(_df(), cfg, "1a")] == [0.0, 1.0]
