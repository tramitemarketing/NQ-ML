"""Beta: quanta parte del P&L è solo "stare dalla parte giusta del mercato" nelle ore in cui
la strategia è esposta, senza alcuna abilità di scelta.

Generalizza `lab.controller.beta_component`: per ogni trade,
    beta = lato x (deriva media del mercato, per sessione, sugli slot orari in cui il trade è aperto)
calcolata sul periodo coperto dai trade. Per i trade che attraversano la notte (o più sessioni) si
somma anche la deriva media delle sessioni intere intermedie. Il test decisivo è sul netto MENO beta
(emendamento 1 del protocollo: significatività, non solo segno).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .market import Market
from .stats import day_block_bootstrap


def _integrate(mu: np.ndarray, t: pd.DataFrame, market: Market) -> np.ndarray:
    M = np.concatenate([[0.0], np.cumsum(mu)])
    s0 = market.pt_slot[t["k0"].to_numpy()]
    s1 = market.pt_slot[t["k1"].to_numpy()]
    nsess = (t["sidx1"].to_numpy() - t["sidx0"].to_numpy()).astype(float)
    return t["side"].to_numpy() * (nsess * M[-1] + M[s1] - M[s0])


def outside_mask(market: Market, window: str | None) -> np.ndarray:
    """Slot fuori dalla finestra diurna (per i giornalieri: il tratto chiusura -> apertura)."""
    if market.daily:
        return np.array([False, True])
    if not window:
        return np.zeros(market.nslots, bool)
    a, b = (int(x.split(":")[0]) * 60 + int(x.split(":")[1]) for x in window.split("-"))
    s0 = int(market.session_start.split(":")[0]) * 60 + int(market.session_start.split(":")[1])
    minute = (np.arange(market.nslots) // 2 + s0) % 1440
    return ~((minute >= a) & (minute < b))


def beta_component(market: Market, t: pd.DataFrame, window: str | None = "09:30-16:00") -> tuple[np.ndarray, dict]:
    """`t` deve essere passato da trades.attach_market (colonne k0, k1, sidx0, sidx1, side).
    Restituisce il beta per trade e, in info, la parte maturata fuori dalla finestra diurna."""
    i0 = int(t["sidx0"].min())
    i1 = int(t["sidx1"].max())
    mu = market.drift_profile(i0, i1)
    beta = _integrate(mu, t, market)
    out = outside_mask(market, window)
    beta_out = _integrate(np.where(out, mu, 0.0), t, market)
    # esposizione fuori finestra: il trade tiene almeno uno slot fuori orario
    ones = _integrate(np.where(out, 1.0, 0.0), t, market) * t["side"].to_numpy()
    info = {"drift_per_session": float(mu.sum()), "profile": mu, "i0": i0, "i1": i1, "beta_outside": beta_out,
            "exposed_outside": ones > 0}
    return beta, info


def beta_analysis(market: Market, t: pd.DataFrame, net: np.ndarray, window: str | None = "09:30-16:00",
                  n_boot: int = 10000, seed: int = 0) -> dict:
    beta, info = beta_component(market, t, window)
    days = t["session"].to_numpy()
    st_net = day_block_bootstrap(net, days, n_boot=n_boot, seed=seed)
    st_adj = day_block_bootstrap(net - beta, days, n_boot=n_boot, seed=seed)
    overnight = (t["sidx1"] > t["sidx0"]).to_numpy() | info["exposed_outside"]
    held_min = (t["exit_ts"] - t["entry_ts"]).dt.total_seconds().to_numpy() / 60
    long_exposure = float(np.sum(held_min * (t["side"].to_numpy() > 0)) / max(np.sum(held_min), 1e-9))
    split = market.window_split(info["i0"], info["i1"], window)
    res = {
        "beta": beta,
        "beta_mean": float(np.mean(beta)),
        "beta_outside_mean": float(np.mean(info["beta_outside"])),
        "net_mean": float(np.mean(net)),
        "share_explained": float(np.mean(beta) / np.mean(net)) if np.mean(net) > 0 else np.nan,
        "stat_net": st_net,
        "stat_adj": st_adj,
        "n_overnight": int(overnight.sum()),
        "share_overnight": float(overnight.mean()),
        "beta_overnight_mean": float(beta[overnight].mean()) if overnight.any() else np.nan,
        "beta_intraday_mean": float(beta[~overnight].mean()) if (~overnight).any() else np.nan,
        "long_share_trades": float((t["side"] > 0).mean()),
        "long_share_time": long_exposure,
        "drift_per_session": info["drift_per_session"],
        "profile": info["profile"],
        "window_split": split,
        "market_move": float(market.pt_px[t["k1"].max()] - market.pt_px[t["k0"].min()]),
    }
    # beta "significativo": il mercato stesso, nelle ore di esposizione, spiega il risultato
    res["flag"] = bool(st_net["p_pos"] < 0.05 and st_net["mean"] > 0 and
                       (st_adj["p_pos"] >= 0.05 or res["share_explained"] >= 0.5))
    return res


def hourly_profile(market: Market, mu: np.ndarray) -> pd.Series:
    """Profilo per ora locale (somma della deriva per sessione), per il grafico."""
    if market.daily:
        return pd.Series({"apertura→chiusura": mu[0], "chiusura→apertura": mu[1]})
    s0 = int(market.session_start.split(":")[0]) * 60 + int(market.session_start.split(":")[1])
    rel_min = np.arange(len(mu)) // 2
    hour = ((rel_min + s0) % 1440) // 60
    order = [(s0 // 60 + h) % 24 for h in range(24)]
    return pd.Series(mu).groupby(hour).sum().reindex(order).fillna(0.0)
