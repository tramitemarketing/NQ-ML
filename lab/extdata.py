"""Dati esterni gratuiti (giro 4), allineati a cio' che era NOTO all'apertura RTH di ogni sessione NQ.

Fonti (scaricate il 2026-09-23 in data/ext_free/):
  FRED  VXNCLS (VXN, vol implicita Nasdaq-100 a 30 gg), VIXCLS, VXVCLS (VIX 3 mesi), DGS10, DGS3MO, T10Y2Y,
        DTWEXBGS (dollaro ampio)
  CBOE  VIX9D, VVIX, SKEW (file *_History.csv)
  SqueezeMetrics DIX/GEX (giro 6, scaricato il 2026-09-30 13:01 UTC in data/ext_free/squeezemetrics_DIX.csv,
        sha256 2a3ae6695628b0886adc55421c467a152ac1019b6437732e462b7bc32748385a, 2011-05-02 -> 2026-09-29).
        Le righe dalla cassaforte in poi vengono scartate alla lettura.

Regola di disponibilita' (conservativa, fissata prima di qualunque test):
  - indici CBOE (VXN, VIX, VIX3M, VIX9D, VVIX, SKEW) e SqueezeMetrics (GEX, DIX): il valore del giorno t chiude alle 16:15 ET ->
    utilizzabile dalla sessione NQ successiva a t (cioe' per decisioni dalle 18:00 di t in poi; qui
    semplificato: a partire dalla sessione con data > t);
  - tassi H.15 (DGS10, DGS3MO, T10Y2Y): pubblicati il giorno lavorativo dopo -> sessione con data > t+1 g.l.;
  - dollaro H.10 (DTWEXBGS): pubblicato il lunedi' per la settimana prima -> ritardo di 7 giorni di calendario
    piu' un giorno lavorativo.
`known_at_open(daily_index)` restituisce, per ogni sessione S, l'ultimo valore disponibile prima dell'apertura
RTH di S. Nessun valore del giorno S stesso viene mai usato per S.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data" / "ext_free"

FRED = {"VXN": "VXNCLS", "VIX": "VIXCLS", "VIX3M": "VXVCLS", "DGS10": "DGS10", "DGS3MO": "DGS3MO",
        "T10Y2Y": "T10Y2Y", "USD": "DTWEXBGS"}
CBOE = {"VIX9D": "cboe_VIX9D", "VVIX": "cboe_VVIX", "SKEW": "cboe_SKEW"}
LAG_BDAYS = {"VXN": 1, "VIX": 1, "VIX3M": 1, "VIX9D": 1, "VVIX": 1, "SKEW": 1,
             "DGS10": 2, "DGS3MO": 2, "T10Y2Y": 2, "GEX": 1, "DIX": 1}
LAG_CAL_USD = 8   # giorni di calendario


def _fred(code: str) -> pd.Series:
    df = pd.read_csv(D / f"{code}.csv")
    df.columns = ["date", "v"]
    s = pd.to_numeric(df["v"], errors="coerce")
    s.index = pd.to_datetime(df["date"])
    return s.dropna()


def _cboe(name: str) -> pd.Series:
    df = pd.read_csv(D / f"{name}.csv")
    df.columns = [c.strip().upper() for c in df.columns]
    col = "CLOSE" if "CLOSE" in df.columns else df.columns[-1]
    s = pd.to_numeric(df[col], errors="coerce")
    s.index = pd.to_datetime(df["DATE"], format="%m/%d/%Y")
    return s.dropna()


def _squeeze(col: str) -> pd.Series:
    from lab.core import VAULT_START
    df = pd.read_csv(D / "squeezemetrics_DIX.csv")
    s = pd.to_numeric(df[col], errors="coerce")
    s.index = pd.to_datetime(df["date"])
    s = s[s.index < pd.Timestamp(VAULT_START)]      # la cassaforte non entra mai
    return s.dropna()


def raw() -> pd.DataFrame:
    """Valori per data di osservazione (NON allineati: non usare direttamente nei segnali)."""
    cols = {k: _fred(v) for k, v in FRED.items()}
    cols.update({k: _cboe(v) for k, v in CBOE.items()})
    if (D / "squeezemetrics_DIX.csv").exists():
        cols.update({"GEX": _squeeze("gex"), "DIX": _squeeze("dix")})
    return pd.DataFrame(cols).sort_index()


def known_at_open(sessions: pd.DatetimeIndex) -> pd.DataFrame:
    """Per ogni sessione S: ultimo valore di ogni serie disponibile prima dell'apertura RTH di S."""
    r = raw()
    sessions = pd.DatetimeIndex(sessions)
    out = {}
    for c in r.columns:
        s = r[c].dropna()
        if c == "USD":
            avail = s.index + pd.Timedelta(days=LAG_CAL_USD)
        else:
            avail = s.index + pd.offsets.BDay(LAG_BDAYS[c])
        # disponibile per le sessioni con data >= avail (avail e' gia' il giorno lavorativo successivo)
        ser = pd.Series(s.to_numpy(), index=pd.DatetimeIndex(avail)).sort_index()
        ser = ser[~ser.index.duplicated(keep="last")]
        out[c] = ser.reindex(sessions, method="ffill")
    df = pd.DataFrame(out, index=sessions)
    df.index.name = "session"
    return df


def macro_calendar(sessions: pd.DatetimeIndex) -> pd.DataFrame:
    """Giro 7: per ogni sessione S, 1 se S e' giorno di FOMC (comunicato), CPI o occupazione (NFP).
    Date pubblicate con mesi di anticipo (nessun look-ahead); file costruito da lab/r7_quantili/s00_calendario.py,
    copre 2010-2018. Fuori copertura restituisce NaN, mai 0, per non scambiare 'non so' con 'nessun evento'."""
    cal = pd.read_csv(D / "calendario_macro.csv", index_col=0, parse_dates=True)
    sessions = pd.DatetimeIndex(sessions)
    out = cal.reindex(sessions).fillna(0).astype(float)
    out[(sessions < pd.Timestamp("2010-01-01")) | (sessions > pd.Timestamp("2018-12-31"))] = np.nan
    out.index.name = "session"
    return out
