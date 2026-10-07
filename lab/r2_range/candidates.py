"""Candidati CONGELATI della famiglia r2_range (giro 2, discovery 2010-06-07 -> 2018-12-31).

Un'unica regola, presentata in due binari:
  1. tradeable  -> netto in punti (quattro criteri del controller);
  2. regularity -> la stessa quantita' lorda divisa per R_hat (scale-free), test bilaterale, segno atteso +1.

Regola: R_hat = range RTH previsto alle 09:30 (HAR sul log range RTH + log range notturno, OLS mobile 500
sessioni stimata solo su sessioni precedenti; vedi common.forecast). Bande = close RTH di ieri +/- 0.9 * R_hat.
Primo tocco (trade-through di 1 tick) di una banda da parte di una barra 1m che chiude fra 09:45 e 15:00,
purche' quella banda non sia gia' stata superata dalle 09:30 alle 09:44 (una barra che tocca entrambe: nessun
trade). Ingresso all'open della barra successiva nel verso della rottura, stop 0.2 * R_hat dall'ingresso
(fill al livello o all'open se la barra apre oltre), nessun target, uscita alla close della barra 15:59.
Al massimo un trade per sessione. Solo informazione nota prima dell'ingresso.

AVVERTENZA dichiarata: il placebo con R_hat rimescolato fra sessioni dello stesso anno rende in media +2,2 punti
netti contro +3,1 (h10): la previsione giornaliera della volatilita' spiega al piu' un terzo dell'effetto.
Cio' che conta e' la dimensione del movimento dalla chiusura di ieri in unita' di volatilita' tipica.
Il punto h=0.9 e' il centro del plateau {0.75, 0.9, 1.0} scelto DOPO aver visto la griglia di h07 (post hoc).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.r2_range import common as C
from lab.r2_range.h04_bands import touches

H_BAND, STOP_R = 0.9, 0.2


def _trades(bars: pd.DataFrame, daily: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    M, F = C.prepare(bars, daily)
    si, m, d = touches(M, M["R_hat"], "pc", H_BAND)
    t = C.sim(M, si, m, d, STOP_R * M["R_hat"][si])
    return M, t[np.isfinite(t["gross_pts"])].reset_index(drop=True)


def pcband_breakout(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    M, t = _trades(bars, daily)
    return C.to_controller(M, t)


def pcband_breakout_R(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    M, t = _trades(bars, daily)
    out = C.to_controller(M, t)
    out["gross_pts"] = (t["gross_pts"] / t["R"]).to_numpy(float)   # quantita' misurata: lordo in unita' di R_hat
    return out


CANDIDATES = [
    dict(
        id="r2_range_pcband_breakout",
        description=("Banda = close RTH di ieri +/- 0,9 x range RTH previsto alle 09:30 (HAR su log range + range "
                     "notturno, OLS mobile causale). Al primo tocco (1 tick oltre) fra 09:45 e 15:00 di una banda non "
                     "gia' superata prima delle 09:45, entra nel verso della rottura all'open della barra dopo, stop "
                     "0,2 x range previsto, uscita 15:59; max un trade al giorno."),
        rationale=("Quando il prezzo si e' gia' allontanato dalla chiusura di ieri di quasi un range giornaliero atteso, "
                   "la giornata e' una giornata di tendenza (informazione nuova, ribilanciamenti e coperture gamma che "
                   "inseguono il movimento, Gao-Han-Li-Zhou 2018; Baltussen et al. 2021): la continuazione fino alla "
                   "chiusura ha coda destra (payoff da trend-following con stop). Misurare la distanza in unita' di "
                   "volatilita' rende la soglia stabile fra regimi; il costo fisso pesa meno nei regimi agitati."),
        warmup_days=560,
        kind="tradeable",
        fn=pcband_breakout,
        discovery=dict(n=617, mean_net=3.112, lo=1.300, hi=5.019, p_pos=0.001, years_pos="7/8",
                       drop20=0.124, net_minus_beta=3.097, p_pos_beta=0.001, gross=3.862, long_share=0.488,
                       note=("2010 senza trade (warmup della previsione). Senza 2018: +1,86 [+0,39;+3,35]. Costo 1,25: "
                             "+2,61. Ingresso 1 minuto dopo: +3,66. Trigger su chiusura oltre banda: +2,84. Specchio "
                             "(fade): -1,06. Placebo R_hat rimescolato: media +2,2 su 10 semi. Ancora = open: -0,39. "
                             "Punto dichiarato prima (h=0,75): +2,18 p 0,005, drop20 -0,32.")),
    ),
    dict(
        id="r2_range_pcband_breakout_R",
        description=("Stessa regola di r2_range_pcband_breakout; quantita' misurata = punti lordi del trade divisi per "
                     "il range previsto R_hat (scale-free). Test bilaterale sul lordo, segno atteso positivo."),
        rationale=("Binario 'reale ma non incassabile': anche se il netto in punti non reggesse, la continuazione dopo "
                   "un movimento di ~0,9 range attesi dalla chiusura di ieri e' un fatto sulla dinamica intraday che "
                   "non dipende dalla scala del prezzo (nel discovery 8/8 anni positivi in unita' di R)."),
        warmup_days=560,
        kind="regularity",
        expected_sign=+1,
        fn=pcband_breakout_R,
        discovery=dict(n=617, mean_gross=0.0687, lo=0.038, hi=0.101, p_two=0.0001, years_pos="8/8",
                       drop20=0.025, mean_net=None,
                       note="unita': R_hat (range RTH previsto); 2011 0,026 ... 2018 0,122"),
    ),
]
