"""Bootstrap a blocchi per giorno, vettorizzato per lo screening v2 (pre-registrazione
`docs/superpowers/specs/2026-09-23-screening-v2-rifacimento.md`, §1): a differenza di
`nqml.backtest.metrics.block_bootstrap_ci` (un DataFrame ricostruito a ogni ricampionamento, O(n_boot) oggetti
Python), qui si ricampiona un'unica matrice di indici `(n_boot, n_days)` e si riduce con numpy puro — nessun
oggetto pandas dentro il ciclo. Serve a rendere praticabili i 58 test della famiglia BH (10.000 ricampionamenti
ciascuno) senza il collo di bottiglia che aveva bloccato il tentativo precedente.

La statistica supportata (`stat="ratio"`) e' quella di §1: `sum(s) / sum(n)`, cioe' la media per evento
pesata (non la media dei rapporti giornalieri) — stessa costruzione di `mean_r_stat` in
`nqml.backtest.metrics`, solo vettorizzata sull'intera matrice di ricampionamenti in un colpo."""
from __future__ import annotations

import numpy as np
import pandas as pd


def block_bootstrap_ci_fast(
    per_day: pd.DataFrame, n_boot: int, seed: int, alpha: float = 0.05, stat: str = "ratio"
) -> tuple[float, tuple[float, float], np.ndarray]:
    """`per_day` ha colonne `s` (somma per giorno) e `n` (conteggio per giorno). Ritorna
    (punto, (lo, hi), distribuzione_bootstrap_completa) cosi' i p-value si calcolano dalla stessa
    distribuzione senza un secondo passaggio. `n_days` giorni ricampionati con rimpiazzo, stesso indice
    di giorno per `s` e `n` (blocco = giorno intero, non l'evento singolo)."""
    if stat != "ratio":
        raise NotImplementedError(f"statistica non supportata: {stat!r}")

    s = per_day["s"].to_numpy(dtype=float)
    n = per_day["n"].to_numpy(dtype=float)
    n_days = len(per_day)

    n_total = float(n.sum())
    point = float(s.sum() / n_total) if n_total > 0 else float("nan")

    if n_days == 0:
        dist = np.full(n_boot, np.nan)
        return point, (float("nan"), float("nan")), dist

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_days, size=(n_boot, n_days))
    s_boot = s[idx].sum(axis=1)
    n_boot_counts = n[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        dist = s_boot / n_boot_counts

    lo = float(np.nanpercentile(dist, 100 * alpha / 2))
    hi = float(np.nanpercentile(dist, 100 * (1 - alpha / 2)))
    return point, (lo, hi), dist
