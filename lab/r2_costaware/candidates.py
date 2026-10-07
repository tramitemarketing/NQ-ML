"""Candidati congelati della famiglia r2_costaware (giro 2, discovery 2010-06 -> 2018-12).

Un solo candidato, di tipo "regularity". Nessun candidato tradeable: la regola di costo (operare solo se i punti
attesi b*segnale*sigma superano m volte il costo) non supera in discovery il criterio di promozione dichiarato nel
PIANO (fallisce "senza i 20 migliori" e il CI contiene lo zero; in punti vive sul 2018). Vedi REPORT.md.

r2_costaware_mom20_restofday: a 12 istanti fissi (10:00, 10:30, ..., 15:30 NY) si misura il rendimento fino alla
chiusura RTH (close della barra 15:59 meno open della barra dello slot), in UNITA' DI VOLATILITA'
(/ (sig1m*sqrt(minuti alla chiusura)), sig1m = media delle std 1m RTH delle 20 sessioni precedenti), firmato con
il segno di (z20 - mediana delle 3.000 z20 precedenti), dove z20 = r_20d / std delle 3.000 r_20d precedenti
(tagliato a +-3) e r_20d = (ultimo prezzo prima dello slot - chiusura RTH di 20 sessioni prima) /
(std delle variazioni giornaliere delle chiusure RTH delle 20 sessioni precedenti * sqrt(20)).
La quantita' per sessione (gross_pts) e' la media sugli slot disponibili. Atteso > 0.
ATTENZIONE UNITA': gross_pts NON e' in punti, e' in unita' di volatilita' (media giornaliera).
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from lab.ml.features import build_dataset, SLOTS

NY = ZoneInfo("America/New_York")
WIN, MINP = 3000, 1000


def _rows(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    ds, _ = build_dataset(bars, daily, horizons=(30,), slots=SLOTS)
    ds = ds.sort_values(["session", "slot"]).reset_index(drop=True)
    r = ds["r_20d"]
    z = (r / r.shift(1).rolling(WIN, min_periods=MINP).std()).clip(-3, 3)
    c = z - z.shift(1).rolling(WIN, min_periods=MINP).median()        # solo righe precedenti
    ds["c"] = c
    ok = np.isfinite(c) & np.isfinite(ds["y_close"]) & (c != 0)
    d = ds[ok].copy()
    d["q"] = np.sign(d["c"]) * d["y_close"]
    d["qp"] = np.sign(d["c"]) * d["pts_close"]
    return d


def mom20_restofday(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    d = _rows(bars, daily)
    g = d.groupby("session")
    q = g["q"].mean()
    s = pd.DatetimeIndex(q.index)
    first = g["slot"].min().to_numpy()
    entry = (s + pd.to_timedelta(first, unit="m")).tz_localize(NY).tz_convert("UTC")
    exit_ = (s + pd.Timedelta(minutes=960)).tz_localize(NY).tz_convert("UTC")
    return pd.DataFrame({
        "session": s.astype("datetime64[ns]"),
        "entry_ts": entry,
        "exit_ts": exit_,
        "side": 1,                                  # quantita' giornaliera (media di lati per slot), non un trade
        "gross_pts": q.to_numpy(float),              # UNITA' DI VOLATILITA'
        "gross_points_mean": g["qp"].mean().to_numpy(float),   # stessa misura in punti (diagnostica)
        "long_share": g["c"].apply(lambda x: float((x > 0).mean())).to_numpy(),
        "n_slots": g.size().to_numpy(),
    }).reset_index(drop=True)


CANDIDATES = [
    dict(
        id="r2_costaware_mom20_restofday",
        description=("A 12 istanti 10:00-15:30 NY: rendimento fino alla chiusura RTH in unita' di vol, firmato con il "
                     "segno del momentum a 20 sessioni (z20) meno la sua mediana sulle 3.000 osservazioni precedenti; "
                     "media giornaliera sugli slot. Regolarita': il momentum a 20 giorni, centrato, ordina il resto della "
                     "giornata RTH (unita' di vol, lato ~50/50)."),
        rationale=("Trend-following a medio termine / sotto-reazione (Moskowitz-Ooi-Pedersen 2012) che si manifesta "
                   "anche dentro la seduta; nel giro 1 r_20d era la feature univariata piu' forte del modello ML (a 30'). "
                   "Qui si mostra che il vantaggio in unita' di vol non decade con l'orizzonte (fino alla chiusura), "
                   "condizione necessaria perche' un filtro di costo possa mai funzionare. Non incassabile nel discovery: "
                   "in punti vive sul 2018."),
        warmup_days=520,
        kind="regularity",
        expected_sign=+1,
        fn=mom20_restofday,
        discovery=dict(n=1921, mean_gross=0.0688, lo=0.0314, hi=0.1060, p_two=0.0008, years_pos="8/8",
                       long_share=0.49,
                       note=("post hoc: trovato scomponendo il composito COMP2 (z_day+z_20d) dichiarato nel PIANO; "
                             "unita' vol; sensibilita' finestra 1000/6000: +0,079/+0,059; mattina +0,052, pomeriggio +0,086")),
    ),
]
