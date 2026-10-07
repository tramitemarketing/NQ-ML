"""Candidati congelati della famiglia ml.

ml_rank30 (kind="regularity"): un modello LightGBM generico (media di 5 semi) (40 feature solo passate: rendimenti su piu'
scale, notte, ieri, volatilita' realizzata, volume relativo per ora, posizione nei range, distanze da
massimi/minimi notturni, VWAP, forma della distribuzione recente, ora, giorno) prevede il rendimento dei
30 minuti successivi in unita' di volatilita' a 12 istanti fissi (10:00, 10:30, ..., 15:30 NY).
A ogni istante si prende posizione nel verso di (previsione - mediana delle 3.000 previsioni precedenti):
il centraggio sulla mediana passata rende il lato ~50/50 long/short, cosi' la misura e' la capacita' di
ORDINARE i rendimenti futuri e non il beta. Uscita a tempo fisso dopo 30 minuti.
ATTENZIONE UNITA': per questo candidato `gross_pts` e' il rendimento firmato in UNITA' DI VOLATILITA'
(punti / (sig1m*sqrt(30)), sig1m = media delle dev. std. dei rendimenti 1m RTH delle 20 sessioni precedenti),
non in punti: e' la misura naturale di una capacita' di ordinamento (pesa ugualmente anni calmi e agitati).
Il valore in punti lordi e' nella colonna `gross_points`.

Modelli (salvati in lab/ml/models/, addestrati da lab/ml/train_models.py):
- sessioni dell'anno Y <= 2018: modello walk-forward addestrato su sessioni < 1 gen Y (meno 5 di embargo),
  quindi sul discovery `fn` restituisce previsioni FUORI CAMPIONE;
- sessioni dal 2019 in poi: modello addestrato una volta su tutto il discovery (lgb_y30_final.txt).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import lightgbm as lgb
import numpy as np
import pandas as pd

from lab.ml.features import FEATURES, build_dataset

MODELS = Path(__file__).resolve().parent / "models"
NY = ZoneInfo("America/New_York")
H = 30
WINDOW, MIN_HIST = 3000, 2000


SEEDS = (7, 11, 23, 42, 99)


@lru_cache(maxsize=None)
def _models(year: int):
    """5 modelli (semi diversi) per l'anno: la previsione e' la loro media."""
    tag = "final" if year >= 2019 else str(year)
    fs = [MODELS / f"lgb_y30_{tag}_s{s}.txt" for s in SEEDS]
    if not all(f.exists() for f in fs):
        return None
    return [lgb.Booster(model_file=str(f)) for f in fs]


def predictions(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    ds, _ = build_dataset(bars, daily)
    ds = ds.sort_values(["session", "slot"]).reset_index(drop=True)
    yrs = pd.DatetimeIndex(ds["session"]).year
    pred = np.full(len(ds), np.nan)
    for y in np.unique(yrs):
        ms = _models(int(y))
        if ms is None:
            continue
        idx = np.where(yrs == y)[0]
        X = ds.loc[idx, FEATURES]
        pred[idx] = np.mean([m.predict(X) for m in ms], axis=0)
    ds["pred"] = pred
    return ds


def ml_rank30(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    ds = predictions(bars, daily)
    ds = ds[np.isfinite(ds["pred"])].reset_index(drop=True)
    med = ds["pred"].shift(1).rolling(WINDOW, min_periods=MIN_HIST).median()   # solo previsioni passate
    side = np.sign(ds["pred"] - med)
    ok = np.isfinite(med) & (side != 0) & np.isfinite(ds[f"pts{H}"])
    t = ds[ok].copy()
    local = pd.DatetimeIndex(t["session"]) + pd.to_timedelta(t["slot"].to_numpy(), unit="m")
    entry = local.tz_localize(NY).tz_convert("UTC")
    out = pd.DataFrame({
        "session": pd.DatetimeIndex(t["session"]).astype("datetime64[ns]"),
        "entry_ts": entry,
        "exit_ts": entry + pd.Timedelta(minutes=H),
        "side": side[ok].astype(int).to_numpy(),
        # QUANTITA' MISURATA (regolarita'): rendimento firmato in UNITA' DI VOLATILITA' (sig1m*sqrt(30)),
        # la stessa unita' del target dichiarato prima di guardare. La versione in punti e' in gross_points.
        "gross_pts": (side[ok] * t[f"y{H}"]).to_numpy(),
        "gross_points": (side[ok] * t[f"pts{H}"]).to_numpy(),
        "pred": t["pred"].to_numpy(),
    })
    return out.reset_index(drop=True)


CANDIDATES = [
    dict(
        id="ml_rank30",
        description=("LightGBM generico (media di 5 semi, 40 feature passate) a 12 istanti fissi 10:00-15:30 NY: lato = segno di "
                     "(previsione - mediana delle 3.000 previsioni precedenti), uscita dopo 30 minuti; si misura il "
                     "rendimento LORDO firmato in unita' di volatilita' (colonna gross_pts; i punti sono in gross_points). "
                     "Regolarita': il modello ordina i rendimenti a 30 minuti?"),
        rationale=("Il walk-forward 2012-2018 da' IC +0,020 [+0,006; +0,034] positivo in 7 anni su 7; tra semi l'effetto "
                   "varia 0,013-0,028 (da qui la media di 5 semi), tra obiettivi/orizzonti IC 0,019-0,032. Meccanismo plausibile: combinazione di momentum multi-giorno (r_20d, r_5d), "
                   "ritorno alla media a breve (r5-r30) e regime di volatilita'; nessuna singola feature lo spiega. "
                   "Il lordo (~0,2 punti) e' sotto il costo (0,75): e' una regolarita', non una strategia."),
        warmup_days=400,
        kind="regularity",
        fn=ml_rank30,
        # gross_pts in unita' di vol; *_points = stessa misura in punti lordi; mean_net_points = punti netti (0,75)
        discovery=dict(n=18700, mean_gross=0.0228, lo=0.0085, hi=0.0373, p_two=0.0022, years_pos="7/7",
                       mean_gross_points=0.2103, lo_points=0.0464, hi_points=0.3745, p_two_points=0.0112,
                       mean_net_points=-0.5397, long_share=0.506),
    ),
]
