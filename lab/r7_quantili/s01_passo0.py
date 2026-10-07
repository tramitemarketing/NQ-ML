"""Passo 0 di r7_quantili: copertura e potenza (PREREG.md). Nessun esito dei modelli M1/M2."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from lab import core
from lab.r7_quantili import common as C


def main() -> None:
    t = C.table("discovery")
    oos = t[t.index >= pd.Timestamp("2013-01-01")]
    ev = oos[["fomc", "cpi", "nfp"]].sum(axis=1) > 0
    per_year = oos.groupby(oos.index.year).agg(sessioni=("y", "size"), fomc=("fomc", "sum"), cpi=("cpi", "sum"),
                                                nfp=("nfp", "sum"))
    print("sessioni valide nel discovery:", len(t), t.index.min().date(), "->", t.index.max().date())
    print(per_year.to_string())
    print("giorni con almeno un evento (2013-2018):", int(ev.sum()), "su", len(oos))
    print("VXN mancante:", int(t["lvxn"].isna().sum()))
    # potenza: B0 contro B0 con residui su 250 sessioni (coppia NON oggetto di test)
    q0 = C.walk_forward(t, C.b0)
    q1 = C.walk_forward(t, lambda tr, te: C.b0(tr, te, resid_window=250))
    y = t.loc[q0.index, "y"].to_numpy()
    l0 = C.pinball(y, q0.to_numpy())
    d = l0 - C.pinball(y, q1.to_numpy())
    n = len(d)
    z = norm.ppf(1 - 0.05 / 2) + norm.ppf(0.80)          # Holm k=2: soglia piu' severa alpha/2
    mde = z * d.std(ddof=1) / np.sqrt(n)
    rel = mde / l0.mean()
    print(f"n = {n}; loss media B0 = {l0.mean():.5f}; sd(d) = {d.std(ddof=1):.5f}; "
          f"MDE80 = {mde:.5f} = {100 * rel:.2f} % della loss di B0 (soglia del PREREG: 5 %)")
    core.record("r7_quantili", "passo0_potenza", "Passo 0: MDE80 da B0 contro B0 con residui a 250 sessioni "
                "(coppia non oggetto di test); nessun esito di M1/M2", "discovery",
                {"n": n, "loss_b0": float(l0.mean()), "sd_d": float(d.std(ddof=1)), "mde80": float(mde),
                 "mde80_rel": float(rel)}, eventi_oos=int(ev.sum()))


if __name__ == "__main__":
    main()
