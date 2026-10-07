"""Passo 0 di r6_noise (PREREG): presenza delle barre che servono alle bande e al VWAP. Nessun segnale ne' esito."""
import numpy as np
import pandas as pd

from lab import core

GRID = [600 + 30 * i for i in range(12)]          # 10:00 ... 15:30 (P_tau = close della barra che inizia a tau-1)

if __name__ == "__main__":
    bars, daily = core.load("discovery")
    d = daily[daily["valid"] & daily["in_phase"]]
    b = bars[bars["rth"] & bars["session"].isin(d.index.values)]
    have = b.groupby(["session", "ny_min"]).size().unstack(fill_value=0) > 0
    have = have.reindex(d.index).fillna(False)
    y = d.index.year
    tab = pd.DataFrame({
        "barra 09:30 (O)": have[570],
        "barra 15:59 (C)": have[959],
        "tutte le 12 barre tau-1": have[[t - 1 for t in GRID]].all(1),
        "barre RTH a volume 0": b.groupby("session")["volume"].apply(lambda v: int((v == 0).sum())).reindex(d.index) > 0,
    })
    print("quota di sessioni valide, per anno")
    print(tab.groupby(y).mean().round(4).to_string())
    print("\nbarre RTH mancanti, media per sessione:", round(float(390 - b.groupby("session").size().mean()), 2))
    print("sessioni con 14 sessioni valide precedenti nel discovery:", int((np.arange(len(d)) >= 14).sum()), "su", len(d))
