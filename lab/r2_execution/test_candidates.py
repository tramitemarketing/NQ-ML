"""Test di riproduzione della famiglia r2_execution (non scrive nel registro).
1) CANDIDATES e' vuoto e importabile dal controller.
2) Il simulatore riproduce numeri chiave del registro:
   - B0_rth_H15_off0_N5 (placebo, calibrazione della selezione avversa);
   - B1_last30_hivol_off0_N15: l'AGG deve coincidere con il netto del giro 1 (+2,29, n 587), cosa che
     verifica che la convenzione aggressiva e' la stessa del progetto.
Uso: .venv/Scripts/python.exe -m lab.r2_execution.test_candidates"""
import json

import numpy as np
import pandas as pd

from lab import core
from lab.r2_execution.candidates import CANDIDATES
from lab.r2_execution.common import load, compare, summarize, xi_after
from lab.intraday_momentum.candidates import hivol_last30

assert CANDIDATES == []
led = {}
with open(core.LEDGER_DIR / "r2_execution.jsonl", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        led[r["test_id"]] = r

D, B = load(warmup_days=300)
n = len(D.c)
# 1) placebo B0
r = np.random.default_rng(11)
ok = (D.m >= 585) & (D.m < 900) & np.isfinite(D.sig60) & (D.sig60 > 0)
s = np.nonzero(ok & (r.random(n) < 1 / 30))[0]
sd = np.where(r.random(len(s)) < 0.5, 1, -1)
t = compare(D, B, s, sd, xi_after(D, s, 15), 0.0, 5)
st = summarize(t, "B0_rth_H15_off0_N5", "", record=False, quiet=True)
ref = led["B0_rth_H15_off0_N5"]
print("B0  n", st["n"], ref["n"], "PAS", round(st["mean"], 4), round(ref["mean"], 4),
      "fill", round(st["fill_rate"], 4), round(ref["fill_rate"], 4))
assert st["n"] == ref["n"] and abs(st["mean"] - ref["mean"]) < 1e-9 and abs(st["fill_rate"] - ref["fill_rate"]) < 1e-9

# 2) hivol last30: AGG = giro 1
idx_ts = pd.DatetimeIndex(pd.to_datetime(D.ts, utc=True))
tr = hivol_last30(D.bars, D.daily)
e = idx_ts.get_indexer(pd.DatetimeIndex(tr["entry_ts"]))
x = idx_ts.searchsorted(pd.DatetimeIndex(tr["exit_ts"])) - 1
t = compare(D, B, e - 1, tr["side"].to_numpy(), x, 0.0, 15)
st = summarize(t, "B1_last30_hivol_off0_N15", "", record=False, quiet=True)
ref = led["B1_last30_hivol_off0_N15"]
print("B1  n", st["n"], ref["n"], "PAS", round(st["mean"], 4), round(ref["mean"], 4),
      "AGG", round(st["agg_net"], 4), round(ref["agg_net"], 4))
assert st["n"] == ref["n"] == 587
assert abs(st["mean"] - ref["mean"]) < 1e-9 and abs(st["agg_net"] - 2.2905) < 1e-3
print("OK")
