"""Caricamento della lista dei trade del cliente e collegamento ai dati di mercato.

Formato interno (una riga per trade):
    entry_ts, exit_ts : Timestamp UTC
    side              : +1 long, -1 short
    gross_pts         : risultato lordo del cliente in PUNTI per 1 unità (contratto/azione)
    qty               : quantità (informativa; gross_pts è già per unità)
Colonne del file mappabili con `columns={"entry_time": "...", "exit_time": "...", "side": "...",
"pnl": "...", "qty": "..."}`; senza mappatura si riconoscono i nomi più comuni (italiano e inglese).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .market import Market, _read_any, ns

ALIASES = {
    "entry_time": ["entry_time", "entry_ts", "entry", "entrytime", "entry_date", "open_time", "opentime",
                   "time_in", "data_ingresso", "ingresso", "apertura", "date/time", "entry_datetime"],
    "exit_time": ["exit_time", "exit_ts", "exit", "exittime", "exit_date", "close_time", "closetime",
                  "time_out", "data_uscita", "uscita", "chiusura", "exit_datetime"],
    "side": ["side", "direction", "dir", "lato", "posizione", "position", "type", "market_pos.", "market_pos",
             "long_short", "tipo"],
    "pnl": ["pnl", "pnl_points", "pnl_pts", "gross_pts", "points", "punti", "profit", "p&l", "pl", "net_profit",
            "profit/loss", "risultato", "pnl_usd", "profit_usd", "gross_pnl", "net_pnl"],
    "qty": ["qty", "quantity", "contracts", "size", "contratti", "quantita", "lots", "shares"],
}
LONG = {"long", "buy", "b", "l", "1", "+1", "1.0", "acquisto", "compra", "rialzo", "lungo", "buy to open", "bto"}
SHORT = {"short", "sell", "s", "-1", "-1.0", "vendita", "vendi", "ribasso", "corto", "sell short", "sellshort", "sto"}
MONEY_HINTS = ("usd", "$", "eur", "€", "money", "currency", "valuta", "profit", "net_profit")
POINT_HINTS = ("point", "pts", "punti", "gross_pts", "tick")


def _norm(c: str) -> str:
    return str(c).strip().lower().replace(" ", "_")


def _find(df: pd.DataFrame, field: str, columns: dict) -> str | None:
    if field in columns:
        if columns[field] not in df.columns:
            raise ValueError(f"colonna {columns[field]!r} (per {field}) non trovata nel file: {list(df.columns)}")
        return columns[field]
    by_norm = {_norm(c): c for c in df.columns}
    for a in ALIASES[field]:
        if _norm(a) in by_norm:
            return by_norm[_norm(a)]
    return None


def parse_side(v: pd.Series) -> np.ndarray:
    s = v.astype(str).str.strip().str.lower()
    out = np.where(s.isin(LONG), 1, np.where(s.isin(SHORT), -1, 0))
    num = pd.to_numeric(v, errors="coerce")
    out = np.where((out == 0) & num.notna().to_numpy(), np.sign(num.fillna(0).to_numpy()), out)
    bad = out == 0
    if bad.any():
        raise ValueError(f"lato non riconosciuto per {int(bad.sum())} trade (es. {v[bad].iloc[0]!r}); "
                         "valori ammessi: long/short, buy/sell, 1/-1")
    return out.astype(np.int64)


def _to_utc(v: pd.Series, tz: str, dayfirst: bool) -> pd.DatetimeIndex:
    t = pd.DatetimeIndex(pd.to_datetime(v, dayfirst=dayfirst, format="mixed"))
    if t.tz is None:
        t = t.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
    return t.tz_convert("UTC").as_unit("ns")


def load_trades(src, columns: dict | None = None, tz: str = "America/New_York", pnl_unit: str = "auto",
                point_value: float = 1.0, dayfirst: bool = False) -> pd.DataFrame:
    """Legge i trade. `pnl_unit`: 'points' (punti per unità), 'currency' (valuta: diviso per
    point_value e per la quantità), 'auto' (dal nome della colonna; se ambiguo: punti).
    Restituisce il DataFrame interno ordinato per ingresso, con attributo .attrs['notes']."""
    df = src.copy() if isinstance(src, pd.DataFrame) else _read_any(src)
    columns = dict(columns or {})
    notes = []
    cols = {f: _find(df, f, columns) for f in ALIASES}
    for f in ("entry_time", "side", "pnl"):
        if cols[f] is None:
            raise ValueError(f"colonna '{f}' non trovata fra {list(df.columns)}: usa la mappatura colonne "
                             f"(--cols {f}=NOME)")
    entry = _to_utc(df[cols["entry_time"]], tz, dayfirst)
    if cols["exit_time"] is not None:
        exit_ = _to_utc(df[cols["exit_time"]], tz, dayfirst)
    else:
        exit_ = entry
        notes.append("Nessuna colonna di uscita: i trade sono trattati come istantanei (beta e placebo non affidabili).")
    side = parse_side(df[cols["side"]])
    pnl = pd.to_numeric(df[cols["pnl"]], errors="coerce").to_numpy(float)
    qty = np.ones(len(df))
    if cols["qty"] is not None:
        qty = np.abs(pd.to_numeric(df[cols["qty"]], errors="coerce").fillna(1).to_numpy(float))
        qty[qty == 0] = 1
    unit = pnl_unit
    if unit == "auto":
        name = _norm(cols["pnl"])
        if any(h in name for h in POINT_HINTS):
            unit = "points"
        elif any(h in name for h in MONEY_HINTS) and point_value != 1.0:
            unit = "currency"
        else:
            unit = "points"
            notes.append(f"Unità del P&L dedotta come PUNTI dalla colonna {cols['pnl']!r}: se è valuta usa --pnl-unit currency.")
    if unit == "currency":
        gross = pnl / point_value / qty
    else:
        gross = pnl / qty if cols["qty"] is not None else pnl
    out = pd.DataFrame({"entry_ts": entry, "exit_ts": exit_, "side": side, "gross_pts": gross, "qty": qty})
    bad = out["entry_ts"].isna() | out["exit_ts"].isna() | ~np.isfinite(out["gross_pts"].to_numpy(float))
    if bad.any():
        notes.append(f"{int(bad.sum())} righe scartate (data o P&L non leggibili, o ora inesistente per il cambio d'ora).")
        out = out[~bad]
    inv = out["exit_ts"] < out["entry_ts"]
    if inv.any():
        notes.append(f"{int(inv.sum())} trade con uscita prima dell'ingresso: scartati.")
        out = out[~inv]
    out = out.sort_values("entry_ts", kind="stable").reset_index(drop=True)
    out.attrs["notes"] = notes
    out.attrs["unit"] = unit
    out.attrs["columns"] = {k: v for k, v in cols.items() if v is not None}
    return out


def attach_market(trades: pd.DataFrame, market: Market, tol_minutes: float = 15.0) -> pd.DataFrame:
    """Aggiunge ai trade: punti di prezzo d'ingresso/uscita (k0, k1), sessioni, P&L riprezzato sul
    mercato (market_pts) e scostamento temporale dell'aggancio (per i controlli di qualità)."""
    t = trades.copy()
    e = ns(t["entry_ts"])
    x = ns(t["exit_ts"])
    k0 = market.locate(e, "entry")
    k1 = np.maximum(market.locate(x, "exit"), k0)
    t["k0"], t["k1"] = k0, k1
    t["sidx0"], t["sidx1"] = market.pt_sidx[k0], market.pt_sidx[k1]
    t["session"] = market.sessions[market.pt_sidx[k0]]
    t["exit_session"] = market.sessions[market.pt_sidx[k1]]
    t["market_pts"] = t["side"].to_numpy() * (market.pt_px[k1] - market.pt_px[k0])
    if market.daily:
        t["lag_min"] = 0.0
    else:
        lag0 = (market.pt_ts[k0] - e) / 6e10
        lag1 = (market.pt_ts[k1] - x) / 6e10
        t["lag_min"] = np.maximum(np.abs(lag0), np.abs(lag1))
    t["aligned"] = t["lag_min"] <= tol_minutes
    outside = (e < market.pt_ts[0]) | (x > market.pt_ts[-1])
    t["in_market"] = ~outside
    return t


def session_of(trades: pd.DataFrame, tz: str, session_start: str = "17:00") -> pd.DatetimeIndex:
    """Sessione di un trade senza dati di mercato (stessa regola del mercato)."""
    loc = pd.DatetimeIndex(trades["entry_ts"]).tz_convert(tz)
    h, m = (int(v) for v in session_start.split(":"))
    s0 = h * 60 + m
    minute = loc.hour * 60 + loc.minute
    shift = ((minute >= s0) & (s0 > 0)).astype(int)
    return pd.DatetimeIndex(loc.tz_localize(None).normalize() + pd.to_timedelta(shift, unit="D"))
