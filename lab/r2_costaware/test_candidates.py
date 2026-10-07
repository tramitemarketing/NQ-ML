"""Test minimo: le fn dei candidati girano sul discovery e restituiscono i numeri dichiarati.
Uso: .venv/Scripts/python.exe -m lab.r2_costaware.test_candidates"""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_costaware.candidates import CANDIDATES

COLS = {"session", "entry_ts", "exit_ts", "side", "gross_pts"}

if __name__ == "__main__":
    bars, daily = core.load("discovery", warmup_days=0)
    for c in CANDIDATES:
        t = c["fn"](bars.copy(), daily.copy())
        assert COLS <= set(t.columns), t.columns
        t = t[pd.DatetimeIndex(t["session"]).isin(daily.index[daily["in_phase"]])]
        st = core.day_block_bootstrap(t["gross_pts"].to_numpy(float), t["session"].values)
        yr = core.yearly(t["gross_pts"].to_numpy(float), t["session"])
        d = c["discovery"]
        print(c["id"], st, f"anni {int((yr['mean']>0).sum())}/{len(yr)}", "long", round(float(t["long_share"].mean()), 3))
        assert st["n"] == d["n"], (st["n"], d["n"])
        assert abs(st["mean"] - d["mean_gross"]) < 1e-3, st["mean"]
        assert abs(st["p_two"] - d["p_two"]) < 5e-4, st["p_two"]
        assert (t["entry_ts"] < t["exit_ts"]).all()
        # anti look-ahead minimo: tagliando le barre dopo il 2015-06-30 i valori fino a quella data non cambiano
        cut = pd.Timestamp("2015-06-30")
        b2 = bars[bars["session"] <= cut.to_datetime64()]
        d2 = daily[daily.index <= cut]
        t2 = c["fn"](b2.copy(), d2.copy()).set_index("session")["gross_pts"]
        t1 = t.set_index("session")["gross_pts"].loc[:cut]
        common = t1.index.intersection(t2.index)
        assert len(common) == len(t1) and np.allclose(t1.loc[common], t2.loc[common]), "dipendenza dal futuro"
        core.record("r2_costaware", f"CANDIDATO_{c['id']}", "Numeri discovery restituiti da fn (candidato congelato): "
                    + c["description"], "discovery", st, years_pos=f"{int((yr['mean']>0).sum())}/{len(yr)}")
        print("OK", c["id"])
