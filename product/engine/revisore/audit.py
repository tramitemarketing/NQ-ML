"""Orchestrazione dell'audit completo: dati -> statistiche -> beta -> placebo -> decadimento ->
look-ahead -> semafori e verdetto. Restituisce un dizionario R consumato da report.py."""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from . import __version__
from .beta import beta_analysis
from .decay import decay_analysis
from .lookahead import audit_lookahead, cheating_strategy
from .market import Market, ns
from .placebo import run_placebo
from .stats import (basic, bootstrap_max_dd, daily_series, day_block_bootstrap, default_top_k, deflated_sharpe,
                    drawdown, drop_top, power, yearly)
from .trades import attach_market, session_of
from .verdict import build_checks, grade


@dataclass
class AuditConfig:
    n_tried: int = 1                  # varianti/strategie provate prima di scegliere questa
    cost: float = 0.0                 # costo andata e ritorno in PUNTI per unità
    point_value: float = 1.0          # valuta per punto (NQ: 20)
    pnl_is_net: bool = False          # True se il P&L del file è già al netto dei costi
    tz: str = "America/New_York"
    session_start: str = "17:00"
    rth: str | None = "09:30-16:00"   # finestra "diurna" per la scomposizione del movimento del mercato
    is_end: str | None = None         # fine del periodo di costruzione/ottimizzazione
    n_boot: int = 10000
    n_placebo: int = 1000
    seed: int = 0
    top_k: int | None = None
    sr_var: float | None = None
    tol_minutes: float = 15.0
    title: str = "Revisione del backtest"
    client: str = ""
    instrument: str = ""
    currency: str = "$"
    extra: dict = field(default_factory=dict)


def _quality(t: pd.DataFrame, market: Market) -> dict:
    g = t["gross_pts"].to_numpy(float)
    m = t["market_pts"].to_numpy(float)
    ok = np.isfinite(g) & np.isfinite(m)
    # se il riprezzato è costante (es. tutti i trade cadono a mercato chiuso) la relazione è nulla
    corr = float(np.corrcoef(g[ok], m[ok])[0, 1]) if ok.sum() > 2 and np.std(g[ok]) > 0 and np.std(m[ok]) > 0 else 0.0
    diff = g - m
    q = {"corr": corr, "mean_diff": float(np.nanmean(diff)), "median_abs_diff": float(np.nanmedian(np.abs(diff))),
         "share_aligned": float(t["aligned"].mean()), "n": int(len(t)),
         "slope": float(np.polyfit(m[ok], g[ok], 1)[0]) if ok.sum() > 2 and np.std(m[ok]) > 0 else np.nan}
    # diagnosi del fuso: la correlazione migliora spostando gli orari di qualche ora?
    if not market.daily and len(t) >= 20:
        rng = np.random.default_rng(0)
        sub = t.iloc[np.sort(rng.choice(len(t), size=min(400, len(t)), replace=False))]
        e, x = ns(sub["entry_ts"]), ns(sub["exit_ts"])
        best = (0, corr if np.isfinite(corr) else 0.0)
        for h in range(-12, 13):
            if h == 0:
                continue
            k0 = market.locate(e + h * 3_600_000_000_000, "entry")
            k1 = np.maximum(market.locate(x + h * 3_600_000_000_000, "exit"), k0)
            mm = sub["side"].to_numpy() * (market.pt_px[k1] - market.pt_px[k0])
            gg = sub["gross_pts"].to_numpy(float)
            if np.std(mm) > 0:
                c = float(np.corrcoef(gg, mm)[0, 1])
                if np.isfinite(c) and c > best[1] + 0.2:
                    best = (h, c)
        q["tz_hint_hours"], q["tz_hint_corr"] = best
    return q


def run_audit(trades: pd.DataFrame, market: Market | None = None, cfg: AuditConfig | None = None,
              strategy=None, strategy_bars: pd.DataFrame | None = None) -> dict:
    cfg = cfg or AuditConfig()
    R: dict = {"cfg": asdict(cfg), "version": __version__, "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
               "notes": list(trades.attrs.get("notes", []))}
    t = trades.copy()
    if market is not None:
        t = attach_market(t, market, cfg.tol_minutes)
        out = ~t["in_market"]
        if out.any():
            R["notes"].append(f"{int(out.sum())} trade fuori dal periodo dei dati di mercato: esclusi dall'audit.")
            t = t[~out].reset_index(drop=True)
        sessions = pd.DatetimeIndex(t["session"])
    else:
        sessions = session_of(t, cfg.tz, cfg.session_start)
        t["session"] = sessions
    if len(t) < 3:
        raise ValueError("servono almeno 3 trade")
    gross = t["gross_pts"].to_numpy(float)
    if cfg.pnl_is_net:
        net, gross = gross, gross + cfg.cost
    else:
        net = gross - cfg.cost
    t["net_pts"] = net
    R["trades"] = t
    R["period"] = (str(sessions.min().date()), str(sessions.max().date()))
    R["basic"] = basic(net, gross)
    R["boot"] = day_block_bootstrap(net, sessions, n_boot=cfg.n_boot, seed=cfg.seed, return_dist=True)
    cal = None
    if market is not None:
        cal = market.sessions[market.valid_sess]
    ds = daily_series(net, sessions, cal)
    R["daily"] = ds
    R["dsr"] = deflated_sharpe(ds.to_numpy(), max(1, cfg.n_tried), cfg.sr_var)
    R["sharpe_ann"] = R["dsr"]["sr"] * np.sqrt(252) if np.isfinite(R["dsr"]["sr"]) else np.nan
    R["years"] = yearly(net, sessions)
    k = cfg.top_k or default_top_k(len(net))
    R["top_k"] = k
    R["drop_top"] = drop_top(net, k)
    R["drop_top_curve"] = {kk: drop_top(net, kk) for kk in sorted({1, 5, 10, k, 20, 50}) if kk < len(net) - 1}
    order = np.argsort(ns(t["exit_ts"]), kind="stable")
    eq = np.cumsum(net[order]) * cfg.point_value
    R["equity"] = pd.Series(eq, index=pd.DatetimeIndex(t["exit_ts"].to_numpy()[order]))
    R["dd"] = drawdown(eq)
    ddb = bootstrap_max_dd(ds.to_numpy() * cfg.point_value, n_boot=500, seed=cfg.seed + 1)
    R["dd_boot"] = {"median": float(np.median(ddb)), "q95": float(np.percentile(ddb, 95))}
    R["power"] = power(R["boot"]["mean"], R["boot"]["se"], len(net), span_days=len(ds))
    if market is not None:
        R["quality"] = _quality(t, market)
        R["beta"] = beta_analysis(market, t, net, window=cfg.rth, n_boot=cfg.n_boot, seed=cfg.seed)
        R["placebo"] = run_placebo(market, t, cfg.cost, n_sims=cfg.n_placebo, seed=cfg.seed)
        R["placebo"]["client_net_mean"] = float(np.mean(net))
        R["market_info"] = {"daily": market.daily, "bar_minutes": market.bar_ns / 6e10 if not market.daily else None,
                            "n_sessions": int(market.n_sessions), "tz": market.tz,
                            "first": str(market.bars.index[0]), "last": str(market.bars.index[-1])}
    R["decay"] = decay_analysis(net, t["entry_ts"], sessions, cfg.is_end, n_boot=cfg.n_boot, seed=cfg.seed)
    if strategy is not None:
        bars = strategy_bars if strategy_bars is not None else (market.bars if market is not None else None)
        if bars is None:
            raise ValueError("per l'audit del look-ahead servono le barre di mercato")
        la = audit_lookahead(strategy, bars, seed=cfg.seed + 123)
        ctrl = audit_lookahead(cheating_strategy, bars, seed=cfg.seed + 7, n_random=6, n_entries=4)
        la["control_caught"] = not ctrl["ok"]
        la["control_runs"] = ctrl["n_runs"]
        la["control_problems"] = len(ctrl["problems"])
        R["lookahead"] = la
    R["checks"] = build_checks(R)
    R["verdict"] = grade(R, R["checks"])
    return R
