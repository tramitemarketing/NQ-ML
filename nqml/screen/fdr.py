"""Controllo di molteplicita' del lotto 5-8 (pre-registrazione
`docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`, §0): p-value bootstrap a due code
sulla stessa distribuzione bootstrap a blocchi per giorno usata da `nqml.backtest.metrics.block_bootstrap_ci`
(non ricalcolata con un'altra formula), e procedura standard di Benjamini-Hochberg per il False Discovery
Rate.

Dallo screening v2 (pre-registrazione `docs/superpowers/specs/2026-09-23-screening-v2-rifacimento.md`, §1-2)
in poi la famiglia dei 58 test e' **a una coda** (solo positivo, mai a due code come il lotto 5-8): vedi
`one_sided_p` qui sotto, gia' usata internamente da `nqml.screen.wall2.ev_test`. `benjamini_hochberg` non
cambia: e' generica rispetto al lato del test, riceve una lista di p-value gia' calcolati (a una o due
code) e applica la stessa procedura step-up."""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd


def one_sided_p(dist: np.ndarray, n_boot: int | None = None) -> float:
    """p = P*(stat* <= 0) con la correzione (k+1)/(B+1) (mai zero, minimo raggiungibile 1/(B+1)), sulla
    distribuzione bootstrap a blocchi per giorno gia' calcolata altrove (es. `dist` ritornato da
    `nqml.backtest.fastboot.block_bootstrap_ci_fast`) — nessun ricalcolo. `n_boot` di default e' `len(dist)`;
    si puo' passare il B nominale se `dist` contiene NaN da giorni senza eventi (denominatore B+1 comunque
    coerente con la correzione dichiarata)."""
    finite = dist[~np.isnan(dist)]
    b = n_boot if n_boot is not None else len(dist)
    k_le = int(np.sum(finite <= 0))
    return float((k_le + 1) / (b + 1))


def bootstrap_p(per_day: pd.DataFrame, stat: Callable[[pd.DataFrame], float], n_boot: int, seed: int) -> float:
    """p = 2 * min(P*(g* <= 0), P*(g* >= 0)) sulla distribuzione bootstrap a blocchi per giorno di `stat`
    applicata a `per_day` (stessa identica ricostruzione di block_bootstrap_ci: righe di `per_day`
    ricampionate con rimpiazzo, `stat` ricalcolata su ogni ricampionamento). Ciascuna probabilita' a una
    coda e' stimata con la correzione (k+1)/(B+1) (k = conteggio dei ricampionamenti che soddisfano la
    condizione, B = n_boot): mai zero, il minimo raggiungibile e' 1/(B+1) per lato, quindi 2/(B+1) per il
    p a due code."""
    rng = np.random.default_rng(seed)
    n = len(per_day)
    arr = per_day.to_numpy()
    cols = list(per_day.columns)
    vals = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        vals[i] = stat(pd.DataFrame(arr[idx], columns=cols))
    k_le = int(np.sum(vals <= 0))
    k_ge = int(np.sum(vals >= 0))
    p_le = (k_le + 1) / (n_boot + 1)
    p_ge = (k_ge + 1) / (n_boot + 1)
    return float(min(2.0 * min(p_le, p_ge), 1.0))


def benjamini_hochberg(pvalues: list[float], q: float) -> list[bool]:
    """Procedura step-up standard di BH: ordina i p-value crescenti, trova il rango i piu' grande tale che
    p_(i) <= q*i/m, dichiara scoperti tutti i test con p <= p_(i) (non solo il rango i-esimo). Nessun rango
    soddisfa la condizione -> nessuna scoperta."""
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    threshold = None
    for rank, idx in enumerate(order, start=1):
        if pvalues[idx] <= q * rank / m:
            threshold = pvalues[idx]
    if threshold is None:
        return [False] * m
    return [p <= threshold for p in pvalues]
