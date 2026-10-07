"""Nullo con deriva per i candidati direzionali (tenuta overnight, momentum ultima ora), identita' di Wald
(pre-registrazione `docs/superpowers/specs/2026-09-23-screening-v2-rifacimento.md`, §1): sotto un drift
costante mu al minuto, il valore atteso di un'uscita limitata dopo tau minuti e' u*mu*tau (u = direzione),
espresso in unita' di R dividendo per la distanza di stop. `mu_hat` e' la media mobile TRAILING a `window`
sessioni del rendimento per minuto del segmento (RTH o overnight stimati separatamente), nota alla sessione
PRECEDENTE l'evento e mai stimata sull'OOS — da cui lo shift(1) qui sotto: nessuna fuga d'informazione dalla
sessione stessa o da quelle successive."""
from __future__ import annotations

import numpy as np
import pandas as pd

from nqml.features.direction import up
from nqml.profile.sessions import on_mask, rth_mask, session_date


def _segment_return_per_minute(bars: pd.DataFrame, segment: str) -> pd.Series:
    if segment == "rth":
        mask = rth_mask(bars.index)
    elif segment == "overnight":
        mask = on_mask(bars.index)
    else:
        raise ValueError(f"segmento sconosciuto: {segment!r} (atteso 'rth' o 'overnight')")

    sub = bars.loc[mask]
    sd = pd.Index(session_date(sub.index), name="session_date")
    g = sub.groupby(sd)
    open_ = g["open"].first()
    close_ = g["close"].last()
    n_bars = g.size().astype(float)
    return ((close_ - open_) / n_bars).sort_index()


def segment_drift(bars: pd.DataFrame, segment: str, window: int = 252) -> pd.Series:
    """Media mobile TRAILING (in senso stretto) del rendimento per minuto del segmento, indicizzata per
    session_date: il valore alla sessione t usa solo le sessioni < t (rolling sulle `window` sessioni
    precedenti, poi shift(1) per escludere la sessione stessa)."""
    per_session = _segment_return_per_minute(bars, segment)
    return per_session.rolling(window=window, min_periods=1).mean().shift(1)


def wald_null(events: pd.DataFrame, drift_series: pd.Series) -> np.ndarray:
    """nullo_i = u_i * mu_hat_i * tau_i / r_unit_i (identita' di Wald, §1). `events` deve avere `side`,
    `session_date`, `minutes_held`, `r_unit_pts` (gli ultimi due prodotti da `nqml.screen.wall2.r_gross`).
    `mu_hat_i` e' `drift_series` allineata a `session_date` dell'evento (gia' trailing, mai la sessione
    stessa)."""
    u = events["side"].map(up).to_numpy(dtype=float)
    mu_hat = drift_series.reindex(events["session_date"]).to_numpy(dtype=float)
    minutes = events["minutes_held"].to_numpy(dtype=float)
    r_unit = events["r_unit_pts"].to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return u * mu_hat * minutes / r_unit
