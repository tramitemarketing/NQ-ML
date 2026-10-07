"""Test del muro, riusabile da tutti i candidati dello screening (§1 di
`docs/superpowers/specs/2026-09-22-screening-nuovi-setup.md`): g = media per evento di (label - prior
geometrico), con CI da bootstrap a blocchi per giorno (stessa costruzione di
`nqml.report.compare::paired_brier_ci` / `brier_per_day`). Nessun modello: aritmetico."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from nqml.backtest.metrics import block_bootstrap_ci


def g_per_day(df: pd.DataFrame) -> pd.DataFrame:
    """Somma e conteggio per giorno di (label - prior), stessa costruzione di
    nqml.report.compare::brier_per_day (media pesata per evento = somma delle somme / somma dei conteggi)."""
    prior = 1.0 / (1.0 + df["rr_ratio"].to_numpy(dtype=float))
    d = df["label"].to_numpy(dtype=float) - prior
    t = pd.DataFrame({"session_date": df["session_date"].to_numpy(), "d": d})
    g = t.groupby("session_date")
    return pd.DataFrame({"d_sum": g["d"].sum(), "n": g.size()})


def g_stat(t: pd.DataFrame) -> float:
    n = t["n"].sum()
    return float(t["d_sum"].sum() / n) if n > 0 else float("nan")


def wall_test(df: pd.DataFrame, n_boot: int, seed: int, alphas: list[float]) -> dict:
    """g = media per evento di (label - 1/(1+rr)) su df (una geometria), con CI a blocchi per giorno
    a ciascun alpha in `alphas`. Ritorna {n, freq, prior, g, ci: {alpha: (lo, hi)}}."""
    n = len(df)
    if n == 0:
        return dict(n=0, freq=float("nan"), prior=float("nan"), g=float("nan"),
                    ci={a: (float("nan"), float("nan")) for a in alphas})
    prior = 1.0 / (1.0 + df["rr_ratio"].astype(float))
    freq = float(df["label"].mean())
    prior_mean = float(prior.mean())
    tab = g_per_day(df)
    point = g_stat(tab)
    ci = {a: block_bootstrap_ci(tab, g_stat, n_boot, seed, alpha=a) for a in alphas}
    return dict(n=n, freq=freq, prior=prior_mean, g=point, ci=ci)


def geometry_descriptives(df: pd.DataFrame) -> dict:
    """Descrittivi di geometria (§1: entrano solo nei descrittivi, non nel criterio del muro):
    EV senza costi (label*rr - (1-label)) e R medio dopo costi (richiede apply_costs già applicato)."""
    if len(df) == 0:
        return dict(ev_no_cost=float("nan"), mean_r=float("nan"))
    ev_no_cost = float((df["label"] * df["rr_ratio"] - (1 - df["label"])).mean())
    mean_r = float(df["realized_R"].mean())
    return dict(ev_no_cost=ev_no_cost, mean_r=mean_r)


def geometry_row(geom: str, sub: pd.DataFrame, n_boot: int, seed: int, alpha_m1: float, alpha_m2: float,
                  m3_min_n: int) -> dict:
    """Una riga della tabella del muro per una geometria: statistica + descrittivi + M1/M2/M3."""
    n = len(sub)
    if n == 0:
        return dict(geom=geom, n=0, freq=float("nan"), prior=float("nan"), g=float("nan"),
                    ci95=(float("nan"), float("nan")), ci_m2=(float("nan"), float("nan")),
                    m1=False, m2=False, m3=False, ev_no_cost=float("nan"), mean_r=float("nan"))
    wt = wall_test(sub, n_boot, seed, [alpha_m1, alpha_m2])
    ci95, ci_m2 = wt["ci"][alpha_m1], wt["ci"][alpha_m2]
    m1 = bool(ci95[0] > 0)
    m2 = bool(ci_m2[0] > 0)
    m3 = bool(n >= m3_min_n)
    desc = geometry_descriptives(sub)
    return dict(geom=geom, n=n, freq=wt["freq"], prior=wt["prior"], g=wt["g"], ci95=ci95, ci_m2=ci_m2,
                m1=m1, m2=m2, m3=m3, ev_no_cost=desc["ev_no_cost"], mean_r=desc["mean_r"])


def event_descriptives(ev_df: pd.DataFrame, period_start: dt.date, period_end: dt.date) -> dict:
    """Descrittivi a livello di evento (non di geometria): eventi per anno, quota per lato."""
    n = len(ev_df)
    if n == 0:
        return dict(n=0, n_long=0, n_short=0, share_long=float("nan"), events_per_year=float("nan"))
    n_long = int((ev_df["side"] == "long").sum())
    n_short = int((ev_df["side"] == "short").sum())
    period_years = (period_end - period_start).days / 365.25
    return dict(n=n, n_long=n_long, n_short=n_short, share_long=n_long / n, events_per_year=n / period_years)


def fmt_ci(ci: tuple[float, float]) -> str:
    return f"[{ci[0]:+.4f}, {ci[1]:+.4f}]"


def pf(ok: bool) -> str:
    return "PASS" if ok else "FAIL"
