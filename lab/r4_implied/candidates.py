"""Candidati CONGELATI della famiglia r4_implied (giro 4). Due regolarita' (binario «reale ma non incassabile»).

Ogni fn(bars, daily) restituisce una riga per sessione con `gross_pts` = quantita' misurata (guadagno di errore
quadratico fuori campione in log(%^2)^2, NON punti di prezzo). Test del controller: bilaterale sul lordo con
segno atteso `expected_sign`.
Causalita': la previsione per la sessione S usa logRV fino a S-1 (HAR), il range notturno 18:00-09:29 di S
(noto prima dell'apertura RTH) e la chiusura CBOE del VXN del giorno lavorativo precedente, letta SOLO tramite
extdata.known_at_open (gia' ritardata alla disponibilita' reale). OLS mobile sulle 500 sessioni precedenti (min 250).
Funzionano su qualunque fase con warmup_days=560.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import extdata
from lab.vol import common as VC
from lab.vol.candidates import _rolling_ols_pred, _rows


def _feat(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    f = VC.daily_features(bars, daily)
    E = extdata.known_at_open(f.index)
    f["iv_log"] = np.log(E["VXN"].to_numpy() ** 2 / 252.0)      # varianza implicita giornaliera, log(%^2)
    f["lon"] = np.log(f["on_range_pct"])
    return f


def _gain(y: pd.Series, Xb: pd.DataFrame, Xa: pd.DataFrame) -> pd.Series:
    b = _rolling_ols_pred(y, Xb)
    a = _rolling_ols_pred(y, Xa)
    m = b.notna() & a.notna() & y.notna()
    return ((y - b) ** 2 - (y - a) ** 2)[m]


def har_plus_vxn(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """q_S = (logRV_S - HAR_S)^2 - (logRV_S - HARiv_S)^2; HAR = OLS di logRV su (logRV, media5, media22) di S-1;
    HARiv = stesso piu' log(VXN_{S-1}^2/252)."""
    f = _feat(bars, daily)
    Xh = f[["h1", "h5", "h22"]].shift(1)
    q = _gain(f["logrv"], Xh, pd.concat([Xh, f[["iv_log"]]], axis=1))
    return _rows(q, bars)


def on_plus_vxn(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Come har_plus_vxn ma la base include gia' il log del range notturno 18:00-09:29 di S (regolarita' confermata
    del giro 1): l'implicita aggiunge informazione oltre a tutto cio' che i prezzi NQ dicono all'apertura?"""
    f = _feat(bars, daily)
    Xb = pd.concat([f[["h1", "h5", "h22"]].shift(1), f[["lon"]]], axis=1)
    q = _gain(f["logrv"], Xb, pd.concat([Xb, f[["iv_log"]]], axis=1))
    return _rows(q, bars)


CANDIDATES = [
    dict(
        id="r4_implied_har_plus_vxn",
        description=("Per ogni sessione: errore quadratico fuori campione di HAR-RV (OLS mobile 500 su logRV RTH 5m di ieri, "
                     "media 5, media 22) meno quello dello stesso HAR con in piu' log(VXN^2/252) di chiusura del giorno "
                     "lavorativo precedente; atteso >0: la vol implicita del Nasdaq-100 migliora la previsione della vol di domani"),
        rationale=("La vol implicita incorpora informazione prospettica (eventi in calendario, domanda di copertura) che la "
                   "storia dei prezzi non ha; letteratura: Blair-Poon-Taylor 2001, Busch-Christensen-Nielsen 2011 (HAR + VIX)"),
        warmup_days=560,
        kind="regularity",
        expected_sign=+1,
        fn=har_plus_vxn,
        discovery=dict(n=1849, mean_net=0.02541, lo=0.01566, hi=0.03572, p_pos=0.0001, p_two=0.0001, years_pos="8/8",
                       note=("unita' log(%^2)^2; R2 fuori campione 0,624 -> 0,655; blocchi mobili 20: p 0,0002; finestra 250/1000: "
                             "+0,024/+0,022; con VIX invece di VXN +0,015; placebo VXN ritardato 5 sessioni: -0,001 (n.s.); "
                             "senza i 20 migliori +0,013; minimo annuale 2012 +0,006")),
    ),
    dict(
        id="r4_implied_on_plus_vxn",
        description=("Come r4_implied_har_plus_vxn ma la previsione di base e' HAR + log del range notturno 18:00-09:29 della "
                     "sessione; si misura il guadagno di errore quadratico aggiungendo log(VXN^2/252); atteso >0"),
        rationale=("Test piu' severo: l'implicita deve aggiungere informazione oltre alle due regolarita' confermate nel giro 1 "
                   "(HAR e notte agitata), cioe' oltre a tutto cio' che i prezzi NQ rivelano all'apertura"),
        warmup_days=560,
        kind="regularity",
        expected_sign=+1,
        fn=on_plus_vxn,
        discovery=dict(n=1849, mean_net=0.01227, lo=0.00531, hi=0.01949, p_pos=None, p_two=0.0009, years_pos="7/8",
                       note="unita' log(%^2)^2; R2 fuori campione 0,652 -> 0,667; blocchi mobili 20: p 0,0010; senza i 20 migliori +0,004"),
    ),
]
