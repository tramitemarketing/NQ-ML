"""Test di non-leakage delle feature: perturbare TUTTE le barre della sessione s a partire dal minuto t
(e tutte le sessioni successive) non deve cambiare di un bit le feature della riga (s, t)."""
import numpy as np, pandas as pd
from lab import core
from lab.ml.features import build_dataset, FEATURES, SLOTS

def main():
    bars, daily = core.load("discovery")
    # sottoinsieme per velocita': ultime 160 sessioni
    keep = daily.index[-160:]
    b = bars[bars["session"] >= keep[0].to_datetime64()].copy()
    d = daily.loc[keep].copy()
    base, _ = build_dataset(b, d)
    rng = np.random.default_rng(1)
    bad = 0
    for trial in range(12):
        s = keep[rng.integers(120, 160)]
        m = SLOTS[rng.integers(0, len(SLOTS))]
        bb = b.copy()
        ss = pd.DatetimeIndex(bb["session"].to_numpy())
        mask = (ss > s) | ((ss == s) & (bb["ny_min"].to_numpy() >= m) & (bb["ny_min"].to_numpy() < 1020))
        for c in ("adj_open", "adj_high", "adj_low", "adj_close", "open", "high", "low", "close"):
            bb.loc[mask, c] = bb.loc[mask, c] + rng.normal(0, 50, mask.sum())
        bb.loc[mask, "volume"] = rng.integers(0, 5000, mask.sum()).astype("uint64")
        pert, _ = build_dataset(bb, d)
        r0 = base[(base.session == s) & (base.slot == m)][FEATURES].to_numpy()
        r1 = pert[(pert.session == s) & (pert.slot == m)][FEATURES].to_numpy()
        same = np.allclose(r0, r1, equal_nan=True, rtol=0, atol=0)
        y0 = base[(base.session == s) & (base.slot == m)]["pts30"].to_numpy()
        y1 = pert[(pert.session == s) & (pert.slot == m)]["pts30"].to_numpy()
        print(s.date(), m, "feature identiche:", same, "| target cambiato (controllo positivo):", not np.allclose(y0, y1))
        bad += (not same)
    print("FALLITI:", bad)
    assert bad == 0

if __name__ == "__main__":
    main()
