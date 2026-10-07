"""Decadimento in-sample -> out-of-sample e rapporto di restringimento.

Riferimento misurato nel laboratorio (lab/RISULTATI.md, "maledizione del vincitore"): le regolarità
vere mantengono la dimensione da un blocco all'altro (rapporto fuori/dentro 0,8-1,2); gli effetti
trovati scavando si restringono a 0,35-0,7 appena escono dal campione in cui sono stati scelti, e
spesso cambiano segno.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import day_block_bootstrap


def decay_analysis(net, entry_ts, sessions, is_end=None, n_boot: int = 10000, seed: int = 0) -> dict:
    """`is_end`: ultimo giorno del periodo in cui la strategia è stata costruita/ottimizzata.
    Senza `is_end` si confrontano i primi 2/3 con l'ultimo terzo: NON è un vero fuori campione
    (è solo stabilità nel tempo) e il report lo dice."""
    net = np.asarray(net, float)
    sess = pd.DatetimeIndex(sessions)
    if is_end is not None:
        cut = pd.Timestamp(is_end).tz_localize(None) if pd.Timestamp(is_end).tz is not None else pd.Timestamp(is_end)
        is_mask = np.asarray(sess <= cut)
        true_oos = True
    else:
        order = np.argsort(np.asarray(sess))
        cut_i = int(len(net) * 2 / 3)
        cut = sess[order[cut_i - 1]] if cut_i > 0 else sess.min()
        is_mask = np.asarray(sess <= cut)
        true_oos = False
    oos_mask = ~is_mask
    days = np.asarray(sess)
    ins = day_block_bootstrap(net[is_mask], days[is_mask], n_boot=n_boot, seed=seed)
    oos = day_block_bootstrap(net[oos_mask], days[oos_mask], n_boot=n_boot, seed=seed)
    ratio = oos["mean"] / ins["mean"] if ins["n"] and ins["mean"] > 0 and oos["n"] else np.nan
    if not oos["n"] or not ins["n"]:
        cls = "non valutabile"
    elif ins["mean"] <= 0:
        cls = "nessun vantaggio nemmeno in-sample"
    elif oos["mean"] <= 0:
        cls = "il vantaggio sparisce (cambia segno)"
    elif ratio < 0.5:
        cls = "forte restringimento (tipico di un effetto trovato scavando)"
    elif ratio < 0.8:
        cls = "restringimento moderato"
    else:
        cls = "tiene (come le regolarità vere)"
    return {"true_oos": true_oos, "cut": str(pd.Timestamp(cut).date()), "is": ins, "oos": oos,
            "ratio": float(ratio) if np.isfinite(ratio) else np.nan, "class": cls}
