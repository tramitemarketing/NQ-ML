"""Test minimo: ogni fn dei candidati gira su core.load('discovery') e riproduce i numeri dichiarati.
Uso: .venv/Scripts/python.exe -m lab.r4_implied.test_candidates   (verifica, non registra nel ledger)"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.r4_implied.candidates import CANDIDATES

COLS = {"session", "entry_ts", "exit_ts", "side", "gross_pts"}


def main():
    for c in CANDIDATES:
        bars, daily = core.load("discovery", warmup_days=c["warmup_days"])
        t = c["fn"](bars.copy(), daily.copy())
        assert COLS <= set(t.columns), t.columns
        t["session"] = pd.to_datetime(t["session"])
        t = t[t["session"].isin(daily.index[daily["in_phase"]])]
        st = core.day_block_bootstrap(t["gross_pts"].to_numpy(float), t["session"].values)
        d = c["discovery"]
        ok = st["n"] == d["n"] and abs(st["mean"] - d["mean_net"]) < 5e-4
        assert np.sign(st["mean"]) == np.sign(c["expected_sign"])
        print(f"{'OK ' if ok else 'ERR'} {c['id']:28s} n={st['n']} mean={st['mean']:+.5f} [{st['lo']:+.5f};{st['hi']:+.5f}] p2={st['p_two']:.4f}")
        assert ok, (st, d)


if __name__ == "__main__":
    main()
