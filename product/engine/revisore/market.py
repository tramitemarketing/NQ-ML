"""Dati di mercato: caricamento OHLCV (1 minuto, qualunque barra intraday, o giornaliero) e
"percorso di prezzo" su cui si riprezzano i trade, si calcola il beta e si generano i placebo.

Convenzioni (documentate nel report):
- Le barre sono etichettate con l'istante di INIZIO (Databento, IB, la maggior parte dei fornitori).
  Con `bar_label="end"` l'indice viene arretrato di una barra.
- Prezzo a un istante t = primo "punto" con timestamp >= t, dove i punti sono l'apertura di ogni
  barra e, quando dopo la barra c'e' un buco (chiusura di sessione, weekend, dati mancanti), anche la
  sua chiusura all'istante di fine barra. Cosi' un'uscita alle 16:00 su un'azione (ultima barra 15:59)
  esce alla chiusura delle 15:59, non all'apertura del giorno dopo.
- Dati giornalieri: due punti per giorno, apertura e chiusura. Un ingresso prima delle 12:00 locali
  (o con sola data) entra all'apertura, dopo le 12:00 alla chiusura; un'uscita con sola data o dopo
  le 12:00 esce alla chiusura, prima delle 12:00 all'apertura.
- Sessione: con `session_start="17:00"` (default, vale per i future CME e per le azioni USA) le barre
  dalle 17:00 locali in poi appartengono alla sessione del giorno dopo.
- Ogni punto ha uno "slot": mezzo-minuto relativo all'inizio della sessione (2*minuto, +1 per i
  punti di chiusura). L'incremento fra un punto e il successivo appartiene allo slot del primo:
  la deriva media per slot è il "profilo" usato dal beta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

TIME_CANDIDATES = ["ts_event", "timestamp", "ts", "time", "datetime", "date_time", "date", "Date", "Datetime",
                   "Time", "Timestamp", "Gmt time", "Local time"]
NS_MIN = 60_000_000_000
NS_DAY = 86_400_000_000_000


def _read_any(path) -> pd.DataFrame:
    p = Path(path)
    suf = p.suffix.lower()
    if suf in (".parquet", ".pq"):
        return pd.read_parquet(p)
    if suf in (".csv", ".txt"):
        return pd.read_csv(p)
    if suf in (".feather",):
        return pd.read_feather(p)
    # niente pickle: i file arrivano dai clienti e un pickle può eseguire codice arbitrario
    raise ValueError(f"formato non supportato: {p.name} (usa CSV o parquet)")


def _hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _pick_ohlcv(df: pd.DataFrame, columns: dict | None, prefer_adj: bool) -> pd.DataFrame:
    """Restituisce un DataFrame con colonne open/high/low/close/volume (volume opzionale)."""
    columns = dict(columns or {})
    lower = {c.lower().replace(" ", "_"): c for c in df.columns}
    out = {}
    adj_close_yahoo = lower.get("adj_close") if "adj_open" not in lower else None
    for f in ("open", "high", "low", "close", "volume"):
        if f in columns:
            out[f] = df[columns[f]]
            continue
        cands = ([f"adj_{f}"] if prefer_adj and f != "volume" else []) + [f, f[0]]
        for c in cands:
            if c in lower:
                out[f] = df[lower[c]]
                break
    if "close" not in out:
        raise ValueError(f"nessuna colonna di chiusura trovata fra {list(df.columns)}; usa la mappatura colonne")
    for f in ("open", "high", "low"):
        if f not in out:
            out[f] = out["close"]
    res = pd.DataFrame({k: pd.to_numeric(v, errors="coerce").to_numpy(float) for k, v in out.items()}, index=df.index)
    # stile Yahoo: 'Adj Close' senza adj_open -> fattore moltiplicativo applicato a OHLC
    if prefer_adj and adj_close_yahoo is not None and "close" not in columns:
        raw_close = df[lower["close"]].to_numpy(float) if "close" in lower else None
        if raw_close is not None:
            fac = df[adj_close_yahoo].to_numpy(float) / raw_close
            for f in ("open", "high", "low"):
                res[f] = res[f] * fac
            res["close"] = df[adj_close_yahoo].to_numpy(float)
    if "volume" not in res:
        res["volume"] = np.nan
    return res


def _time_index(df: pd.DataFrame, time_col: str | None, tz: str) -> pd.DatetimeIndex:
    if time_col is not None:
        raw = df[time_col]
    elif isinstance(df.index, pd.DatetimeIndex):
        raw = df.index
    else:
        found = [c for c in TIME_CANDIDATES if c in df.columns]
        if not found:
            raise ValueError("colonna temporale non trovata: indicala con time_col / --market-time-col")
        raw = df[found[0]]
    idx = pd.DatetimeIndex(pd.to_datetime(raw))
    if idx.tz is None:
        idx = idx.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
    return idx.tz_convert("UTC").as_unit("ns")


def ns(x) -> np.ndarray:
    """Timestamp (Series/Index/array, con o senza fuso) -> int64 nanosecondi UTC."""
    idx = pd.DatetimeIndex(x)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    return idx.tz_convert("UTC").as_unit("ns").asi8.astype(np.int64)


@dataclass
class Market:
    bars: pd.DataFrame            # indice UTC, colonne open high low close volume
    tz: str = "America/New_York"
    session_start: str = "17:00"
    daily: bool = False
    # derivati (costruiti in __post_init__)
    bar_ns: int = field(init=False, default=0)
    pt_ts: np.ndarray = field(init=False, repr=False)
    pt_px: np.ndarray = field(init=False, repr=False)
    pt_slot: np.ndarray = field(init=False, repr=False)
    pt_sidx: np.ndarray = field(init=False, repr=False)      # indice di sessione di ogni punto
    pt_minute: np.ndarray = field(init=False, repr=False)    # minuto locale (0..1439) del punto
    sessions: pd.DatetimeIndex = field(init=False, repr=False)
    anchor_ns: np.ndarray = field(init=False, repr=False)     # mezzanotte locale della data di sessione, in UTC ns
    sess_end_off: np.ndarray = field(init=False, repr=False)  # ultimo punto della sessione - anchor
    valid_sess: np.ndarray = field(init=False, repr=False)    # sessioni "piene"
    nslots: int = field(init=False, default=2880)

    def __post_init__(self):
        b = self.bars.copy()
        b.index = pd.DatetimeIndex(b.index).as_unit("ns")
        b = b[~b.index.duplicated(keep="first")].sort_index()
        b = b[np.isfinite(b["close"].to_numpy(float))]
        self.bars = b
        if len(b) < 3:
            raise ValueError("troppo poche barre di mercato")
        ts = b.index.asi8.astype(np.int64)
        med = int(np.median(np.diff(ts)))
        self.daily = self.daily or med >= 20 * 3600 * 10**9
        if self.daily:
            self._build_daily(b)
        else:
            self.bar_ns = med
            self._build_intraday(b, ts)

    # ------------------------------------------------------------------ costruzione
    def _build_intraday(self, b: pd.DataFrame, ts: np.ndarray) -> None:
        o = b["open"].to_numpy(float)
        c = b["close"].to_numpy(float)
        o = np.where(np.isfinite(o), o, c)
        nxt = np.append(ts[1:], np.iinfo(np.int64).max)
        gap = nxt - ts > self.bar_ns
        cts = ts[gap] + self.bar_ns
        all_ts = np.concatenate([ts, cts])
        all_px = np.concatenate([o, c[gap]])
        is_close = np.concatenate([np.zeros(len(ts), bool), np.ones(len(cts), bool)])
        order = np.argsort(all_ts, kind="stable")
        self.pt_ts, self.pt_px, is_close = all_ts[order], all_px[order], is_close[order]
        # "istante proprietario": per i punti di chiusura l'ultimo istante della barra
        own = self.pt_ts - is_close.astype(np.int64)
        loc = pd.DatetimeIndex(own.view("datetime64[ns]")).tz_localize("UTC").tz_convert(self.tz)
        minute = (loc.hour * 60 + loc.minute).to_numpy().astype(np.int64)
        s0 = _hhmm(self.session_start)
        day = loc.tz_localize(None).normalize()
        shift = (minute >= s0) & (s0 > 0)
        sess = (day + pd.to_timedelta(shift.astype(int), unit="D")).to_numpy().astype("datetime64[D]")
        rel = (minute - s0) % 1440
        self.pt_minute = minute
        self.pt_slot = 2 * rel + is_close
        self.nslots = 2880
        self._finish_sessions(sess)

    def _build_daily(self, b: pd.DataFrame) -> None:
        d = b.index.tz_convert(self.tz).tz_localize(None).normalize()
        d_unique = ~d.duplicated()
        b, d = b[d_unique], d[d_unique]
        dates = d.to_numpy().astype("datetime64[D]")
        op = pd.DatetimeIndex(d).tz_localize(self.tz, nonexistent="shift_forward", ambiguous=False).tz_convert("UTC")
        cl = pd.DatetimeIndex(d + pd.Timedelta(hours=23, minutes=59)).tz_localize(
            self.tz, nonexistent="shift_forward", ambiguous=False).tz_convert("UTC")
        n = len(b)
        o = b["open"].to_numpy(float)
        c = b["close"].to_numpy(float)
        o = np.where(np.isfinite(o), o, c)
        self.pt_ts = np.empty(2 * n, np.int64)
        self.pt_ts[0::2], self.pt_ts[1::2] = ns(op), ns(cl)
        self.pt_px = np.empty(2 * n)
        self.pt_px[0::2], self.pt_px[1::2] = o, c
        self.pt_slot = np.tile([0, 1], n)
        self.pt_minute = np.tile([0, 1439], n)
        self.nslots = 2
        self._finish_sessions(np.repeat(dates, 2))

    def _finish_sessions(self, sess: np.ndarray) -> None:
        uniq, sidx = np.unique(sess, return_inverse=True)
        self.sessions = pd.DatetimeIndex(uniq.astype("datetime64[ns]"))
        self.pt_sidx = sidx.astype(np.int64)
        self.anchor_ns = ns(self.sessions.tz_localize(self.tz, nonexistent="shift_forward", ambiguous=False))
        last = np.zeros(len(uniq), np.int64)
        np.maximum.at(last, self.pt_sidx, self.pt_ts)
        self.sess_end_off = last - self.anchor_ns
        cnt = np.bincount(self.pt_sidx, minlength=len(uniq))
        self.valid_sess = cnt >= 0.5 * np.median(cnt)

    # ------------------------------------------------------------------ interrogazioni
    @property
    def n_sessions(self) -> int:
        return len(self.sessions)

    def locate(self, ts_ns: np.ndarray, role: str = "entry") -> np.ndarray:
        """Indice del punto di prezzo usato per un ingresso/uscita all'istante ts (UTC ns)."""
        ts_ns = np.asarray(ts_ns, np.int64)
        if self.daily:
            ts_ns = self._daily_query(ts_ns, role)
        k = np.searchsorted(self.pt_ts, ts_ns, side="left")
        return np.clip(k, 0, len(self.pt_ts) - 1)

    def _daily_query(self, ts_ns: np.ndarray, role: str) -> np.ndarray:
        loc = pd.DatetimeIndex(ts_ns.view("datetime64[ns]")).tz_localize("UTC").tz_convert(self.tz)
        mins = (loc.hour * 60 + loc.minute).to_numpy()
        day = loc.tz_localize(None).normalize()
        if role == "entry":
            use_close = mins >= 720
        else:
            use_close = (mins == 0) | (mins >= 720)
        q = day + pd.to_timedelta(np.where(use_close, 23 * 60 + 59, 0), unit="min")
        q = pd.DatetimeIndex(q).tz_localize(self.tz, nonexistent="shift_forward", ambiguous=False).tz_convert("UTC")
        return ns(q)

    def span_sessions(self, i0: int, i1: int) -> np.ndarray:
        return np.arange(max(i0, 0), min(i1, self.n_sessions - 1) + 1)

    def drift_profile(self, i0: int, i1: int) -> np.ndarray:
        """Deriva media per slot, per sessione, sulle sessioni [i0, i1] (indici)."""
        m = (self.pt_sidx >= i0) & (self.pt_sidx <= i1)
        m[-1] = False
        k = np.flatnonzero(m)
        d = self.pt_px[k + 1] - self.pt_px[k]
        sums = np.bincount(self.pt_slot[k], weights=d, minlength=self.nslots)
        n_sess = max(1, len(np.unique(self.pt_sidx[k])))
        return sums / n_sess

    def window_split(self, i0: int, i1: int, window: str | None) -> dict:
        """Quanto del movimento totale del mercato avviene dentro/fuori una finestra oraria locale."""
        m = (self.pt_sidx >= i0) & (self.pt_sidx <= i1)
        m[-1] = False
        k = np.flatnonzero(m)
        d = self.pt_px[k + 1] - self.pt_px[k]
        if self.daily:
            inside = self.pt_slot[k] == 0
            label = "apertura→chiusura"
        else:
            if not window:
                return {}
            a, b = (_hhmm(x) for x in window.split("-"))
            mi = self.pt_minute[k]
            # un punto di chiusura (fine barra) appartiene alla barra che chiude
            inside = (mi >= a) & (mi < b)
            label = window
        tot = float(d.sum())
        ins = float(d[inside].sum())
        return {"window": label, "total": tot, "inside": ins, "outside": tot - ins,
                "share_inside": ins / tot if tot != 0 else np.nan}


def load_market(src, tz: str = "America/New_York", columns: dict | None = None, time_col: str | None = None,
                prefer_adj: bool = True, session_start: str = "17:00", bar_label: str = "start",
                start=None, end=None) -> Market:
    """Carica OHLCV da CSV/parquet (o DataFrame). Timestamp senza fuso -> interpretati in `tz`.
    `columns` mappa i nomi standard (open, high, low, close, volume) sulle colonne del file.
    Con `prefer_adj` usa le colonne adj_* se presenti (serie continue aggiustate dei future)."""
    df = src if isinstance(src, pd.DataFrame) else _read_any(src)
    idx = _time_index(df, time_col, tz)
    bars = _pick_ohlcv(df, columns, prefer_adj)
    bars.index = idx
    bars = bars[~bars.index.isna()]
    if bar_label == "end":
        step = pd.Series(bars.index).diff().median()
        bars.index = bars.index - step
    if start is not None:
        bars = bars[bars.index >= _utc(start, tz)]
    if end is not None:
        bars = bars[bars.index <= _utc(end, tz)]
    return Market(bars, tz=tz, session_start=session_start)


def _utc(x, tz) -> pd.Timestamp:
    t = pd.Timestamp(x)
    if t.tz is None:
        t = t.tz_localize(tz)
    return t.tz_convert("UTC")
