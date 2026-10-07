"""Volume profile a passo tick da barre OHLCV e value area al 70% (spec §4)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ValueArea:
    poc: float
    vah: float
    val: float
    total_volume: float
    n_levels: int


def value_area_from_histogram(levels: np.ndarray, volumes: np.ndarray, pct: float) -> ValueArea:
    n = len(levels)
    total = float(volumes.sum())
    center = (levels[0] + levels[-1]) / 2.0
    # POC: volume massimo; a parità il più vicino al centro; a parità ancora, il più basso
    max_vol = volumes.max()
    candidates = np.flatnonzero(volumes == max_vol)
    p = int(candidates[np.argmin(np.abs(levels[candidates] - center))])  # argmin: primo (più basso) a parità
    lo = hi = p
    acc = float(volumes[p])
    target = pct * total
    while acc < target - 1e-12:
        up_slice = volumes[hi + 1 : min(hi + 3, n)]
        dn_slice = volumes[max(lo - 2, 0) : lo]
        up = float(up_slice.sum()) if len(up_slice) else -1.0
        dn = float(dn_slice.sum()) if len(dn_slice) else -1.0
        if up < 0 and dn < 0:
            break
        if up >= dn:
            hi = min(hi + 2, n - 1)
            acc += up
        else:
            lo = max(lo - 2, 0)
            acc += dn
    return ValueArea(
        poc=float(levels[p]), vah=float(levels[hi]), val=float(levels[lo]),
        total_volume=total, n_levels=n,
    )


class VolumeProfile:
    """Accumulatore: si aggiungono barre, si interroga la value area quando serve."""

    def __init__(self, tick_size: float = 0.25):
        self.tick_size = tick_size
        self._vol: dict[int, float] = {}
        self.n_bars = 0

    def _idx(self, price: float) -> int:
        return int(round(price / self.tick_size))

    def add_bar(self, low: float, high: float, volume: float) -> None:
        lo, hi = self._idx(low), self._idx(high)
        if hi < lo:
            lo, hi = hi, lo
        n = hi - lo + 1
        share = float(volume) / n
        for i in range(lo, hi + 1):
            self._vol[i] = self._vol.get(i, 0.0) + share
        self.n_bars += 1

    def add_bars(self, df: pd.DataFrame) -> None:
        for low, high, vol in zip(df["low"].to_numpy(), df["high"].to_numpy(), df["volume"].to_numpy()):
            self.add_bar(float(low), float(high), float(vol))

    def histogram(self) -> tuple[np.ndarray, np.ndarray]:
        """Livelli contigui (anche quelli a volume zero) e volumi. Vettoriale: viene chiamata
        78 volte al giorno per 2500 giorni, un ciclo Python qui costerebbe minuti."""
        if not self._vol:
            return np.array([]), np.array([])
        keys = np.fromiter(self._vol.keys(), dtype=np.int64, count=len(self._vol))
        vals = np.fromiter(self._vol.values(), dtype=np.float64, count=len(self._vol))
        lo, hi = int(keys.min()), int(keys.max())
        vols = np.zeros(hi - lo + 1)
        vols[keys - lo] = vals
        return np.arange(lo, hi + 1) * self.tick_size, vols

    def value_area(self, pct: float = 0.70) -> ValueArea | None:
        levels, vols = self.histogram()
        if len(levels) == 0:
            return None
        return value_area_from_histogram(levels, vols, pct)
