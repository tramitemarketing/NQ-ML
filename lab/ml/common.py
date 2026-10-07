"""Famiglia ml — strumenti comuni: dataset in cache, walk-forward, IC a blocchi, regola di trading fissa."""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from lab import core
from lab.ml.features import FEATURES, build_dataset

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
FAM = "ml"
COST = core.COST_RT_POINTS


def dataset(refresh: bool = False) -> pd.DataFrame:
    CACHE.mkdir(exist_ok=True)
    f = CACHE / "ds_discovery.parquet"
    if f.exists() and not refresh:
        return pd.read_parquet(f)
    bars, daily = core.load("discovery")
    ds, _ = build_dataset(bars, daily)
    ds.to_parquet(f)
    return ds


# --------------------------------------------------------------------------- IC con bootstrap per giorno

def ic_boot(pred, y, days, n_boot: int = 4000, seed: int = 0) -> dict:
    """Correlazione di rango (Spearman) previsione/esito, CI e p bilaterale a blocchi per giorno."""
    pred, y, days = np.asarray(pred, float), np.asarray(y, float), np.asarray(days)
    ok = np.isfinite(pred) & np.isfinite(y)
    pred, y, days = pred[ok], y[ok], days[ok]
    rx = pd.Series(pred).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    rx = (rx - rx.mean()) / rx.std()
    ry = (ry - ry.mean()) / ry.std()
    codes, _ = pd.factorize(days)
    nd = codes.max() + 1
    S = np.stack([np.bincount(codes, w, minlength=nd) for w in (np.ones_like(rx), rx, ry, rx * rx, ry * ry, rx * ry)])

    def corr(T):
        n, sx, sy, sxx, syy, sxy = T
        cov = sxy / n - sx / n * sy / n
        return cov / np.sqrt((sxx / n - (sx / n) ** 2) * (syy / n - (sy / n) ** 2))

    point = float(corr(S.sum(1)))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nd, size=(n_boot, nd))
    dist = np.array([corr(S[:, i].sum(1)) for i in idx])
    c = dist - point
    return {"ic": point, "ic_lo": float(np.percentile(dist, 2.5)), "ic_hi": float(np.percentile(dist, 97.5)),
            "ic_p_two": float(max((np.abs(c) >= abs(point)).mean(), 1 / n_boot)), "ic_n": int(len(pred)), "ic_days": int(nd)}


# --------------------------------------------------------------------------- modelli

LGB_GRID = [
    dict(num_leaves=3, min_data_in_leaf=200),
    dict(num_leaves=7, min_data_in_leaf=400),
    dict(num_leaves=15, min_data_in_leaf=800),
    dict(num_leaves=31, min_data_in_leaf=1500),
]
LGB_BASE = dict(objective="regression", learning_rate=0.02, feature_fraction=0.7, bagging_fraction=0.7,
                bagging_freq=1, lambda_l2=10.0, verbose=-1, seed=7, num_threads=8, deterministic=True)


def _spearman(a, b):
    return pd.Series(np.asarray(a, float)).corr(pd.Series(np.asarray(b, float)), method="spearman")


def fit_lgb(tr: pd.DataFrame, ycol, feats=FEATURES, clip=4.0, grid=LGB_GRID, objective=None):
    """Tuning SOLO su validazione interna nel passato: ultimo anno di `tr` come validazione, il resto
    come addestramento (con embargo di 5 sessioni). Scelta per IC di validazione; numero di alberi
    dall'early stopping. Poi riaddestra su tutto `tr` con la config scelta."""
    tr = tr[np.isfinite(tr[ycol])]
    years = pd.DatetimeIndex(tr["session"]).year
    vy = years.max()
    sess = np.sort(tr["session"].unique())
    va = tr[years == vy]
    first_va = va["session"].min()
    emb = sess[max(0, np.searchsorted(sess, first_va) - 5)]
    it = tr[tr["session"] < emb]
    yt = it[ycol].clip(-clip, clip)
    yv = va[ycol].clip(-clip, clip)
    base = dict(LGB_BASE)
    if objective:
        base.update(objective)
    best = None
    for g in grid:
        p = dict(base, **g)
        dtr = lgb.Dataset(it[feats], yt)
        dva = lgb.Dataset(va[feats], yv, reference=dtr)
        m = lgb.train(p, dtr, num_boost_round=1500, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(100, verbose=False)])
        nb = max(m.best_iteration, 20)
        ic = _spearman(m.predict(va[feats], num_iteration=nb), va[ycol])
        if best is None or ic > best[0]:
            best = (ic, g, nb)
    ic, g, nb = best
    p = dict(base, **g)
    m = lgb.train(p, lgb.Dataset(tr[feats], tr[ycol].clip(-clip, clip)), num_boost_round=nb)
    return LgbWrap(m, feats), dict(cfg=g, n_trees=nb, inner_ic=float(ic))


class LgbWrap:
    def __init__(self, m, feats):
        self.m, self.feats = m, list(feats)

    def predict(self, D):
        return self.m.predict(D[self.feats])


def fit_ridge(tr, ycol, feats=FEATURES, alpha=10.0, clip=4.0):
    """Ridge con standardizzazione stimata SOLO sul training (mediana/IQR robusti, poi clip)."""
    tr = tr[np.isfinite(tr[ycol])]
    X = tr[feats].to_numpy(float)
    med = np.nanmedian(X, 0)
    iqr = np.nanpercentile(X, 75, 0) - np.nanpercentile(X, 25, 0)
    iqr[iqr == 0] = 1.0

    def tf(D):
        Z = (D[feats].to_numpy(float) - med) / iqr
        Z = np.clip(np.nan_to_num(Z, nan=0.0), -5, 5)
        return Z

    Z = tf(tr)
    yv = tr[ycol].clip(-clip, clip).to_numpy()
    zm, ym = Z.mean(0), yv.mean()
    A = (Z - zm).T @ (Z - zm) + alpha * len(Z) / 1000 * np.eye(Z.shape[1])
    w = np.linalg.solve(A, (Z - zm).T @ (yv - ym))
    b0 = ym - zm @ w

    class R:
        coef = w
        def predict(self, D):
            return tf(D) @ w + b0
    return R(), dict(coef=dict(zip(feats, map(float, w))), b0=float(b0))


def walk_forward(ds, fitter, ycol, test_years=range(2012, 2019), embargo=5, **kw):
    """Addestra su anni < Y (meno `embargo` sessioni finali), prevede l'anno Y."""
    years = pd.DatetimeIndex(ds["session"]).year
    sess = np.sort(ds["session"].unique())
    out = pd.Series(np.nan, index=ds.index)
    info = {}
    for Y in test_years:
        te = ds[years == Y]
        cut = sess[max(0, np.searchsorted(sess, te["session"].min()) - embargo)]
        tr = ds[ds["session"] < cut]
        m, inf = fitter(tr, ycol=ycol, **kw)
        out.loc[te.index] = m.predict(te)
        info[Y] = inf
    return out, info


# --------------------------------------------------------------------------- regola di trading (fissata prima)

def trade_rule(ds, pred, h=30, q=0.9, window=3000, min_hist=2000, start_year=2013, side_mode="sign"):
    """R1: si opera quando |pred| >= quantile q delle |pred| delle `window` previsioni PRECEDENTI
    (solo passato); lato = segno della previsione; uscita a tempo fisso h minuti. Punti lordi."""
    d = ds[["session", "slot", "k", "sig1m", f"pts{h}", f"y{h}"]].copy()
    d["pred"] = pred
    d = d[np.isfinite(d["pred"])].sort_values(["session", "slot"])
    a = d["pred"].abs()
    if side_mode == "cost":
        # R2: si opera se il guadagno atteso in punti (pred in unita' di vol x sig1m x sqrt(h)) supera q x costo
        hm = h if isinstance(h, int) else (1380 - d["k"])
        exp_pts = a * d["sig1m"] * np.sqrt(hm)
        thr = pd.Series(q * COST, index=d.index)
        a = exp_pts
    else:
        thr = a.shift(1).rolling(window, min_periods=min_hist).quantile(q)
    sel = (a >= thr) & np.isfinite(thr) & np.isfinite(d[f"pts{h}"])
    sel &= pd.DatetimeIndex(d["session"]).year >= start_year
    t = d[sel].copy()
    t["side"] = np.sign(t["pred"]).astype(int)
    t["gross"] = t["side"] * t[f"pts{h}"]
    t["gross_v"] = t["side"] * t[f"y{h}"]
    t["net"] = t["gross"] - COST
    hmin = h if isinstance(h, int) else (1380 - t["k"])
    t["net_v"] = t["gross_v"] - COST / (t["sig1m"] * np.sqrt(hmin))
    return t


def evaluate(ds, pred, name, desc, h=30, record=True, q=0.9, start_year=2013, extra=None, verbose=True, side_mode="sign", window=3000, min_hist=2000):
    ycol, pcol = f"y{h}", f"pts{h}"
    m = np.isfinite(pred) & np.isfinite(ds[ycol])
    ev = ds[m & (pd.DatetimeIndex(ds["session"]).year >= 2012)]
    ic = ic_boot(pred[ev.index], ev[ycol], ev["session"])
    ic_year = {int(y): float(_spearman(pred[g.index], g[ycol])) for y, g in ev.groupby(pd.DatetimeIndex(ev["session"]).year)}
    t = trade_rule(ds, pred, h=h, q=q, start_year=start_year, side_mode=side_mode, window=window, min_hist=min_hist)
    st = core.day_block_bootstrap(t["net"].to_numpy(), t["session"].to_numpy())
    stv = core.day_block_bootstrap(t["net_v"].to_numpy(), t["session"].to_numpy(), n_boot=4000)
    yr = core.yearly(t["net"].to_numpy(), t["session"])
    # beta: esposizione x deriva media della stessa finestra (slot) nello stesso periodo
    per = ds[(pd.DatetimeIndex(ds["session"]).year >= start_year) & np.isfinite(ds[pcol])]
    drift = per.groupby("slot")[pcol].mean()
    beta = float((t["side"] * t["slot"].map(drift)).mean())
    res = dict(st)
    res.update(ic)
    res.update(dict(unit="punti NQ netti per trade (costo 0,75)", h=h, q=q, rule=side_mode,
                    mean_gross=float(t["gross"].mean()), mean_net_v=stv["mean"], lo_v=stv["lo"], hi_v=stv["hi"],
                    p_pos_v=stv["p_pos"], long_share=float((t["side"] > 0).mean()), beta_pts=beta,
                    net_ex_beta=float(st["mean"] - beta), drop_top20=core.drop_top(t["net"].to_numpy(), 20),
                    years_pos=f"{int((yr['mean'] > 0).sum())}/{len(yr)}",
                    yearly={int(k): round(float(v), 3) for k, v in yr["mean"].items()},
                    ic_year={k: round(v, 4) for k, v in ic_year.items()}))
    if extra:
        res.update(extra)
    if record:
        core.record(FAM, name, desc, "discovery", res)
    if verbose:
        print(f"[{name}] IC {ic['ic']:+.4f} [{ic['ic_lo']:+.4f};{ic['ic_hi']:+.4f}] p={ic['ic_p_two']:.3f} | "
              f"trade n={st['n']} netto {st['mean']:+.3f} pt [{st['lo']:+.3f};{st['hi']:+.3f}] p_pos={st['p_pos']:.3f} "
              f"| lordo {res['mean_gross']:+.3f} | netto_v {stv['mean']:+.4f} | long {res['long_share']:.2f} beta {beta:+.3f} "
              f"exbeta {res['net_ex_beta']:+.3f} | anni+ {res['years_pos']} | -top20 {res['drop_top20']:+.3f}")
        print("    IC per anno:", res["ic_year"], "\n    netto per anno:", res["yearly"])
    return res, t
