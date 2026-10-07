"""Candidati congelati della famiglia `micro` (2026-09-23). Dettagli e numeri in REPORT.md.

Regole comuni (identiche al simulatore di `common.py`, usato qui senza modifiche):
  - segnale noto alla CHIUSURA della barra 1m i; ingresso all'OPEN della barra i+1 della stessa sessione;
  - uscita a tempo al close dell'ultima barra che termina entro ingresso + H minuti, mai oltre le 15:59;
  - prezzi adj_* (continui ai roll); nessun costo dentro gross_pts (li toglie il controller).
Ogni `fn(bars, daily)` accetta l'output di `core.load(fase, warmup_days)` di QUALUNQUE fase.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

from lab.micro.common import Data, simulate


# --------------------------------------------------------------------------- 1) regolarita'

def surprise_cont_signals(D: Data):
    """Barre RTH con minuto NY 09:45-14:59 e |close_i - close_{i-15}| >= 3 * sigma60_i * sqrt(15)
    (sigma60_i = dev. std. delle 60 variazioni 1m di close fino alla barra i-1; la barra i-15 deve
    essere della stessa sessione). Lato = verso del movimento."""
    idx = np.arange(len(D.c))
    prev = np.clip(idx - 15, 0, None)
    mv = D.c - D.c[prev]
    z = mv / (D.sig60 * np.sqrt(15))
    sel = (D.rth & (D.m >= 585) & (D.m < 900) & (D.scode[prev] == D.scode)
           & np.isfinite(z) & (np.abs(z) >= 3) & (mv != 0))
    s = idx[sel]
    return s, np.sign(mv[s]).astype(int)


def micro_surprise_continuation(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    D = Data(bars=bars, daily=daily, seasonal_volume=False)
    s, side = surprise_cont_signals(D)
    # regolarita': popolazione = TUTTE le barre di segnale (righe sovrapposte ammesse; il bootstrap
    # a blocchi per giorno tiene conto della dipendenza)
    t = simulate(D, s, side, 30, end="rth", nonoverlap=False)
    return t[["session", "entry_ts", "exit_ts", "side", "gross_pts"]].reset_index(drop=True)


# --------------------------------------------------------------------------- 2) fade del range notturno

@njit(cache=True)
def _on_break_events(h, l, c, m, scode, U, Dn, lo_m, hi_m):
    """Per ogni sessione e per ciascun livello (massimo U e minimo Dn della notte), il PRIMO
    attraversamento nella finestra [lo_m, hi_m) di minuti NY: close della barra precedente dal lato
    interno, estremo della barra oltre il livello. Se alla prima barra della finestra il prezzo e' gia'
    oltre il livello, quel livello e' ignorato per la sessione. Evento tenuto solo se la barra CHIUDE
    oltre il livello di almeno 1 tick ('break'). Lato = fade (short al massimo, long al minimo)."""
    n = len(c)
    out_i = np.empty(2 * (scode.max() + 1), np.int64)
    out_side = np.empty_like(out_i)
    k = 0
    i = 1
    while i < n:
        s = scode[i]
        j0 = i
        while i < n and scode[i] == s:
            i += 1
        for q in range(2):
            lv = U[s] if q == 0 else Dn[s]
            sgn = 1 if q == 0 else -1
            if lv != lv:
                continue
            for j in range(j0 + 1, i):
                if m[j] < lo_m or m[j] >= hi_m:
                    continue
                inside_prev = (c[j - 1] <= lv) if sgn > 0 else (c[j - 1] >= lv)
                if not inside_prev:
                    if m[j] == lo_m:
                        break
                    continue
                cross = (h[j] > lv) if sgn > 0 else (l[j] < lv)
                if not cross:
                    continue
                brk = (c[j] >= lv + 0.25) if sgn > 0 else (c[j] <= lv - 0.25)
                if brk:
                    out_i[k] = j; out_side[k] = -sgn; k += 1
                break
    return out_i[:k], out_side[:k]


def overnight_range(D: Data):
    """Massimo e minimo (adj) delle barre della sessione prima delle 09:30 NY (18:00-09:29)."""
    b = pd.DataFrame({"s": D.scode, "h": D.h, "l": D.l, "m": D.m})
    on = b[(b.m < 570) | (b.m >= 1080)].groupby("s").agg(h=("h", "max"), l=("l", "min"))
    ns = int(D.scode.max()) + 1
    U = on["h"].reindex(range(ns)).to_numpy(dtype=float)
    Dn = on["l"].reindex(range(ns)).to_numpy(dtype=float)
    return U, Dn


def micro_overnight_break_fade(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    D = Data(bars=bars, daily=daily, seasonal_volume=False)
    U, Dn = overnight_range(D)
    ei, es = _on_break_events(D.h, D.l, D.c, D.m, D.scode, U, Dn, 575, 720)
    t = simulate(D, ei, es, 120, end="rth", nonoverlap=True)
    return t[["session", "entry_ts", "exit_ts", "side", "gross_pts"]].reset_index(drop=True)


# --------------------------------------------------------------------------- elenco

CANDIDATES = [
    dict(
        id="micro_surprise_continuation",
        description=("RTH: a ogni barra 1m con minuto NY 09:45-14:59 in cui |close - close di 15 minuti prima| "
                     ">= 3 x sigma60 x sqrt(15) (sigma60 = std delle 60 variazioni 1m fino alla barra "
                     "precedente), si misura il rendimento nel verso del movimento dall'open della barra "
                     "successiva a 30 minuti dopo (uscita entro le 15:59). Popolazione = tutte le barre di segnale."),
        rationale=("Un salto improvviso rispetto alla volatilita' appena precedente segnala arrivo di "
                   "informazione; la sotto-reazione (diffusione graduale, esecuzione spezzata di ordini "
                   "grandi, stop a cascata) produce continuazione a breve. Sul discovery la continuazione "
                   "lorda e' positiva in quasi tutta la griglia k x soglia x orizzonte x fascia (H1, H16), "
                   "cresce con la soglia; il fade perde ovunque. Non incassabile: lordo ~1-1,5 punti "
                   "contro 0,75 di costi, netto non distinguibile da zero."),
        warmup_days=2,
        kind="regularity",
        fn=micro_surprise_continuation,
        discovery=dict(n=3347, mean_gross=1.4945, lo=0.4834, hi=2.5917, p_two=0.0048, years_pos="7/9",
                       nonoverlap_version=dict(n=1063, mean_gross=1.019, lo=0.322, hi=1.718, p_two=0.0041,
                                               years_pos="8/9", mean_net=0.269)),
    ),
    dict(
        id="micro_overnight_break_fade",
        description=("RTH 09:35-11:59: primo attraversamento nella sessione del massimo (minimo) della notte "
                     "18:00-09:29 in cui la barra 1m CHIUDE oltre il livello di >= 1 tick (close precedente "
                     "dentro il range notturno); short (long) all'open della barra successiva, uscita a "
                     "tempo dopo 120 minuti (entro le 15:59), un trade alla volta, nessuno stop."),
        rationale=("Gli estremi notturni si formano con liquidita' sottile; la loro prima rottura nella prima "
                   "ora e mezza di RTH scatta ordini stop concentrati appena oltre (Osler 2003/2005 sulle "
                   "cascate di stop) che, esauriti, lasciano rientrare il prezzo. Controllo: il fade del "
                   "movimento dall'apertura a orari fissi PERDE (H5c), quindi non e' il generico ritorno "
                   "del primo movimento; ma la stessa regola sui massimi/minimi di ieri e della settimana "
                   "scorsa va nel verso opposto (H14): candidato DEBOLE, dichiarato tale."),
        warmup_days=2,
        kind="tradeable",
        fn=micro_overnight_break_fade,
        discovery=dict(n=959, mean_net=1.234, lo=-0.127, hi=2.642, p_pos=0.043, years_pos="6/9",
                       mean_gross=1.984, drop20=-0.287, beta_pts=0.009, mean_net_1618=2.616),
    ),
]
