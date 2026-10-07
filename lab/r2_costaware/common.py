"""Famiglia r2_costaware — pannello degli istanti di decisione, segnali compositi, regola di costo, valutazione.

Tutto causale: ogni scala e ogni pendenza usa solo righe di sessioni PRECEDENTI (o previsioni precedenti).
Riusa senza modificarli: lab.ml.features.build_dataset e i modelli congelati in lab/ml/models.
"""
from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from lab import core
from lab.ml.features import FEATURES, build_dataset, SLOTS
from lab.ml.candidates import _models

FAM = "r2_costaware"
NY = ZoneInfo("America/New_York")
COST = core.COST_RT_POINTS
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
HORIZONS = (30, 60, 120)
ZWIN, ZMIN = 3000, 1000


def _past_std(x: pd.Series, win=ZWIN, minp=ZMIN) -> pd.Series:
    return x.shift(1).rolling(win, min_periods=minp).std()


def _z(x: pd.Series) -> pd.Series:
    return (x / _past_std(x)).clip(-3, 3)


def ml_pred(ds: pd.DataFrame) -> np.ndarray:
    yrs = pd.DatetimeIndex(ds["session"]).year
    pred = np.full(len(ds), np.nan)
    for y in np.unique(yrs):
        ms = _models(int(y))
        if ms is None:
            continue
        idx = np.where(yrs == y)[0]
        X = ds.iloc[idx][FEATURES]
        pred[idx] = np.mean([m.predict(X) for m in ms], axis=0)
    return pred


def panel(bars: pd.DataFrame, daily: pd.DataFrame, with_ml: bool = True) -> pd.DataFrame:
    ds, _ = build_dataset(bars, daily, horizons=HORIZONS, slots=SLOTS)
    ds = ds.sort_values(["session", "slot"]).reset_index(drop=True)
    # orizzonte "close": minuti fino alla chiusura (close 15:59)
    ds["h_close"] = 960 - ds["slot"]
    if with_ml:
        p = pd.Series(ml_pred(ds))
        # centraggio e scala SOLO su previsioni passate (le righe senza modello restano NaN)
        pv = p.dropna()
        med = pv.shift(1).rolling(ZWIN, min_periods=2000).median()
        sd = pv.shift(1).rolling(ZWIN, min_periods=2000).std()
        zml = ((pv - med) / sd).clip(-3, 3)
        ds["pred"] = p
        ds["z_ml"] = zml.reindex(ds.index)
    ds["z_day"] = _z(ds["r_sess"])
    ds["z_20d"] = _z(ds["r_20d"])
    surp = ds["r15"].where(ds["r15"].abs() >= 3, 0.0)
    ds["z_surp"] = np.sign(surp)          # +-1 solo sugli eventi di sorpresa, 0 altrove
    ds["COMP2"] = (ds["z_day"] + ds["z_20d"]) / np.sqrt(2)
    if with_ml:
        ds["COMP3"] = (ds["z_ml"] + ds["z_day"] + ds["z_20d"]) / np.sqrt(3)
    return ds


def load_panel(refresh: bool = False) -> pd.DataFrame:
    CACHE.mkdir(exist_ok=True)
    f = CACHE / "panel_discovery.parquet"
    if f.exists() and not refresh:
        return pd.read_parquet(f)
    bars, daily = core.load("discovery")
    ds = panel(bars, daily)
    ds.to_parquet(f)
    return ds


def ycol(h):
    return "y_close" if h == "close" else f"y{h}"


def ptscol(h):
    return "pts_close" if h == "close" else f"pts{h}"


def hmin(ds, h):
    return ds["h_close"].to_numpy(float) if h == "close" else np.full(len(ds), float(h))


def causal_slope(ds: pd.DataFrame, sig: str, h, min_sess: int = 250) -> np.ndarray:
    """Pendenza OLS per l'origine di y_h (unita' vol) su `sig`, stimata sulle sessioni PRECEDENTI (espansiva)."""
    y = ds[ycol(h)].to_numpy(float)
    x = ds[sig].to_numpy(float)
    ok = np.isfinite(x) & np.isfinite(y)
    sess = ds["session"].to_numpy()
    codes, uniq = pd.factorize(sess, sort=True)
    sxy = np.bincount(codes, weights=np.where(ok, x * y, 0.0), minlength=len(uniq))
    sxx = np.bincount(codes, weights=np.where(ok, x * x, 0.0), minlength=len(uniq))
    has = np.bincount(codes, weights=ok.astype(float), minlength=len(uniq)) > 0
    csxy = np.concatenate([[0], np.cumsum(sxy)[:-1]])
    csxx = np.concatenate([[0], np.cumsum(sxx)[:-1]])
    nsess = np.concatenate([[0], np.cumsum(has)[:-1]])
    b = np.where((nsess >= min_sess) & (csxx > 0), csxy / np.maximum(csxx, 1e-12), np.nan)
    return b[codes]


def rule_trades(ds: pd.DataFrame, sig: str, h, m: float, sig_mult=None, nonoverlap: bool = True,
                side_override=None, slope=None) -> pd.DataFrame:
    """Regola di costo: E = b_h*sig*sigma_h (punti); opera se |E| >= m*costo. Un trade alla volta per sessione."""
    b = causal_slope(ds, sig, h) if slope is None else slope
    hm = hmin(ds, h)
    sigma = ds["sig1m"].to_numpy(float) * np.sqrt(hm)
    if sig_mult is not None:
        sigma = sigma * sig_mult
    E = b * ds[sig].to_numpy(float) * sigma
    pts = ds[ptscol(h)].to_numpy(float)
    y = ds[ycol(h)].to_numpy(float)
    q = np.isfinite(E) & (np.abs(E) >= m * COST) & np.isfinite(pts)
    side = np.sign(E)
    if side_override is not None:
        side = np.asarray(side_override, float)
    q &= side != 0
    slot = ds["slot"].to_numpy()
    sess = ds["session"].to_numpy()
    idx = np.where(q)[0]
    keep = []
    last_s, busy_until = None, -1
    for i in idx:
        if nonoverlap:
            if sess[i] == last_s and slot[i] < busy_until:
                continue
            last_s, busy_until = sess[i], slot[i] + hm[i]
        keep.append(i)
    keep = np.array(keep, int)
    local = pd.DatetimeIndex(ds["session"].to_numpy()[keep]) + pd.to_timedelta(slot[keep], unit="m")
    entry = local.tz_localize(NY).tz_convert("UTC")
    return pd.DataFrame({
        "session": pd.DatetimeIndex(sess[keep]).astype("datetime64[ns]"),
        "entry_ts": entry,
        "exit_ts": entry + pd.to_timedelta(hm[keep], unit="m"),
        "side": side[keep].astype(int),
        "gross_pts": side[keep] * pts[keep],
        "gross_vol": side[keep] * y[keep],
        "E": E[keep], "slot": slot[keep], "sigma": sigma[keep],
    })


_BARS = None


def bars_disc():
    global _BARS
    if _BARS is None:
        _BARS = core.load("discovery")[0]
    return _BARS


def evaluate(t: pd.DataFrame, beta: bool = True) -> dict:
    from lab.controller import beta_component
    if len(t) == 0:
        return {"n": 0}
    net = t["gross_pts"].to_numpy(float) - COST
    days = t["session"].values
    st = core.day_block_bootstrap(net, days)
    yr = core.yearly(net, days)
    out = dict(st)
    out["gross"] = float(np.mean(t["gross_pts"]))
    out["gross_vol"] = float(np.nanmean(t["gross_vol"])) if "gross_vol" in t else np.nan
    out["years"] = {int(k): round(float(v), 2) for k, v in yr["mean"].items()}
    out["years_n"] = {int(k): int(v) for k, v in yr["count"].items()}
    out["years_pos"] = f"{int((yr['mean'] > 0).sum())}/{len(yr)}"
    out["drop20"] = core.drop_top(net, 20)
    yrs = pd.DatetimeIndex(days).year
    ex = ~np.isin(yrs, [2011, 2015, 2018])
    out["ex_hivol_years"] = float(net[ex].mean()) if ex.any() else np.nan
    out["ex_hivol_n"] = int(ex.sum())
    out["long_share"] = float((t["side"] > 0).mean())
    if beta:
        bc = beta_component(bars_disc(), t)
        sb = core.day_block_bootstrap(net - bc, days)
        out["beta_mean"] = float(np.mean(bc))
        out["net_minus_beta"] = sb["mean"]
        out["net_minus_beta_p"] = sb["p_pos"]
    return out


def rec(test_id: str, desc: str, stats: dict, **extra):
    core.record(FAM, test_id, desc, "discovery", stats, **extra)


def fmt(s: dict) -> str:
    if s.get("n", 0) == 0:
        return "n=0"
    return (f"n={s['n']:5d} net={s['mean']:+.3f} [{s['lo']:+.2f};{s['hi']:+.2f}] p={s['p_pos']:.4f} "
            f"gross={s['gross']:+.3f} gv={s.get('gross_vol', np.nan):+.4f} yrs={s['years_pos']} d20={s['drop20']:+.2f} "
            f"exHV={s['ex_hivol_years']:+.2f}(n{s['ex_hivol_n']}) nmb={s.get('net_minus_beta', np.nan):+.2f} "
            f"L={s['long_share']:.2f}")
