"""r7_opzioni: costruzione dei venerdì di scadenza con straddle ATM (PREREG.md). Solo discovery."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from lab import core
from lab.r7_quantili import common as Q

DIR = core.ROOT / "data" / "ext_paid" / "opzioni"
NY = "America/New_York"
PARENTS = ["NQ_OPT", "QN1_OPT", "QN2_OPT", "QN3_OPT", "QN4_OPT", "QN5_OPT"]
FEE_PTS = 0.25          # 1,25 $ per lato per opzione: 4 x 1,25 $ = 5 $ a straddle a/r = 0,25 punti (20 $/punto)


def load_defs() -> pd.DataFrame:
    parts = [pd.read_parquet(DIR / f"{p}_definition.parquet").assign(parent=p) for p in PARENTS
             if (DIR / f"{p}_definition.parquet").exists()]
    d = pd.concat(parts)
    d = d[d["instrument_class"].isin(["C", "P"])].drop_duplicates("instrument_id", keep="last")
    d["exp_ny"] = pd.DatetimeIndex(d["expiration"]).tz_convert(NY)
    d["exp_date"] = d["exp_ny"].dt.tz_localize(None).dt.normalize()
    return d


def load_tbbo() -> pd.DataFrame:
    parts = [pd.read_parquet(DIR / f"{p}_tbbo.parquet") for p in PARENTS if (DIR / f"{p}_tbbo.parquet").exists()]
    t = pd.concat(parts, ignore_index=True)
    t["ts"] = pd.DatetimeIndex(t["ts_recv"]).tz_convert(NY)
    return t.sort_values("ts")


def front_contract_ids() -> pd.Series:
    m = json.load(open(core.CACHE / "nq_v0_mapping.json"))
    rows = {}
    for seg in m:
        for d in pd.date_range(seg["d0"], pd.Timestamp(seg["d1"]) - pd.Timedelta(days=1)):
            rows[d] = int(seg["s"])
    return pd.Series(rows)


def build_days(bars: pd.DataFrame, d: pd.DataFrame, t: pd.DataFrame) -> pd.DataFrame:
    """Una riga per venerdì con scadenza NQ e straddle ATM quotato (regole del PREREG). Colonne di ingresso
    (f0, k, bid/ask delle gambe) e di esito (f_t = close della barra 1m che termina alla scadenza)."""
    sess = pd.DatetimeIndex(bars["session"].unique())
    front = front_contract_ids()
    rth = bars[bars["rth"]]
    c0944 = rth[rth["ny_min"] == 584].set_index("session")["close"]
    close_by_ts = bars["close"]
    tid = {k: g for k, g in t.groupby("instrument_id")}
    rows = []
    for day, g in d[d["exp_date"].isin(sess)].groupby("exp_date"):
        if day.dayofweek != 4:
            continue
        g = g[g["underlying_id"] == front.get(day, -1)]
        f0 = c0944.get(day, np.nan)
        if g.empty or not np.isfinite(f0):
            continue
        t0 = pd.Timestamp(day).tz_localize(NY) + pd.Timedelta("9h45min")
        g = g[g["exp_ny"] > t0]                    # le scadenze al mattino (SOQ) sono già scadute a t0
        if g.empty:
            continue
        exp = g["exp_ny"].min()                    # se più scadenze nello stesso giorno, la prima dopo t0
        g = g[g["exp_ny"] == exp]
        strikes = np.sort(g["strike_price"].unique())
        k = float(strikes[np.argmin(np.abs(strikes - f0))])
        legs = g[g["strike_price"] == k].set_index("instrument_class")["instrument_id"]
        lo = pd.Timestamp(day).tz_localize(NY) + pd.Timedelta("9h15min")
        hi = pd.Timestamp(day).tz_localize(NY) + pd.Timedelta("9h45min")
        r = {"day": day, "f0": float(f0), "k": k, "exp": exp}
        ok = True
        for cls in ("C", "P"):
            q = tid.get(legs.get(cls, -1))
            if q is None:
                ok = False
                break
            q = q[(q["ts"] >= lo) & (q["ts"] < hi) & (q["bid_px_00"] > 0) & (q["ask_px_00"] > q["bid_px_00"])]
            if q.empty:
                ok = False
                break
            last = q.iloc[-1]
            r[f"{cls}_bid"], r[f"{cls}_ask"] = float(last["bid_px_00"]), float(last["ask_px_00"])
        if not ok:
            continue
        # esito: close della barra 1m che termina all'orario di scadenza (barra che inizia 1 minuto prima)
        ts_last = (exp - pd.Timedelta(minutes=1)).tz_convert("UTC")
        r["f_t"] = float(close_by_ts.get(ts_last, np.nan))
        rows.append(r)
    P = pd.DataFrame(rows).set_index("day")
    P["mid"] = (P["C_bid"] + P["C_ask"] + P["P_bid"] + P["P_ask"]) / 2
    return P


def forecasts(days: pd.DatetimeIndex) -> pd.Series:
    """E|F_T - F0| = c * range previsto; OLS log-HAR + notte e c ristimati ogni anno sul solo passato
    (finestra espandente dal 2010-07). c = media di |close 15:59 - close 09:44| / range previsto sui
    venerdì di stima. Primo anno previsto: 2012."""
    bars, _ = core.load("discovery")
    tq = Q.table("discovery")
    rth = bars[bars["rth"]]
    c0944 = rth[rth["ny_min"] == 584].set_index("session")["close"].reindex(tq.index)
    c1559 = rth[rth["ny_min"] == 959].set_index("session")["close"].reindex(tq.index)
    mv = (c1559 - c0944).abs()
    out = {}
    for y in range(2012, 2019):
        tr = tq[tq.index < pd.Timestamp(y, 1, 1)]
        A = np.column_stack([np.ones(len(tr)), tr[Q.HAR].to_numpy()])
        b, *_ = np.linalg.lstsq(A, tr["y"].to_numpy(), rcond=None)
        smear = float(np.mean(np.exp(tr["y"].to_numpy() - A @ b)))
        pred_tr = np.exp(A @ b) * smear / 100 * tr["ref"].to_numpy()
        fri = (tr.index.dayofweek == 4) & np.isfinite(mv.reindex(tr.index).to_numpy())
        c = float(np.mean(mv.reindex(tr.index).to_numpy()[fri] / pred_tr[fri]))
        te = tq[(tq.index >= pd.Timestamp(y, 1, 1)) & (tq.index < pd.Timestamp(y + 1, 1, 1))]
        At = np.column_stack([np.ones(len(te)), te[Q.HAR].to_numpy()])
        pred = np.exp(At @ b) * smear / 100 * te["ref"].to_numpy()
        for dd, v in zip(te.index, c * pred):
            out[dd] = v
    return pd.Series(out).reindex(days)
