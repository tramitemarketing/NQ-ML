"""Rifacimento del test del muro con lo strumento corretto (pre-registrazione
`docs/superpowers/specs/2026-09-23-screening-v2-rifacimento.md`, §1). Sostituisce `nqml.screen.wall` per il
nuovo insieme di test: `R_lordo` a orizzonte finito invece del confronto frequenza/prior a orizzonte
infinito, target riempito solo su trade-through di 1 tick (non al tocco), nullo a zero per i setup
simmetrici o con deriva (identita' di Wald) per quelli direzionali, test dello specchio.

Modulo indipendente da `nqml.labels.labeler`: i riempimenti pre-registrati qui (target = trade-through, non
tocco) sono diversi da quelli usati dalle milestone gia' chiuse, quindi `labeler.py` non si tocca. Riusa
comunque `nqml.features.direction.up` e `nqml.profile.sessions.ny_minutes` — stessa normalizzazione
direzionale e stesso calcolo dei minuti-NY di tutto il resto della pipeline."""
from __future__ import annotations

import numpy as np
import pandas as pd

from nqml.backtest.fastboot import block_bootstrap_ci_fast
from nqml.features.direction import up
from nqml.labels.labeler import time_stop_minute
from nqml.profile.sessions import ny_minutes
from nqml.screen.fdr import one_sided_p


def r_gross(row: dict, rth1m_day: pd.DataFrame, cfg: dict) -> dict:
    """Etichetta un (evento x geometria) sotto le convenzioni di riempimento pre-registrate (§1):
    - target riempito solo su trade-through di 1 tick (una barra che tocca il target senza superarlo di un
      tick non e' un hit);
    - stop riempito al prezzo di stop (convenzione ottimista dichiarata: anche se la barra apre oltre);
    - uscita a tempo alla chiusura delle 15:55.

    Nessun costo qui (primaria = R_lordo, spec §1): `pnl_pts` e' il movimento di mercato puro, i costi si
    applicano dopo con `units`. `r_unit_pts` = distanza d'ingresso allo stop (senza slippage: e' la
    definizione della primaria, non il fill eseguibile)."""
    side = row["side"]
    u = up(side)
    entry_ts = pd.Timestamp(row["entry_ts"])
    entry = float(row["entry_price"])
    stop, target = float(row["stop_price"]), float(row["target_price"])
    tick = cfg["instrument"]["tick_size"]
    ts_stop = time_stop_minute(cfg)

    r_unit = abs(entry - stop)
    # Trade-through: il target si considera raggiunto solo quando il prezzo lo supera di 1 tick nella
    # direzione favorevole (u=+1 long -> target+tick, u=-1 short -> target-tick). Al tocco esatto (== target)
    # non e' un hit: la stessa formula con u copre entrambi i lati.
    target_through = target + u * tick

    def _finish(label: int, exit_reason: str, exit_ts: pd.Timestamp, exit_price: float, minutes_held: float) -> dict:
        pnl_pts = u * (exit_price - entry)
        R = pnl_pts / r_unit if r_unit > 0 else float("nan")
        return dict(label=label, exit_reason=exit_reason, pnl_pts=pnl_pts, r_unit_pts=r_unit,
                    R_gross=R, minutes_held=minutes_held)

    if u * (entry - stop) <= 0 or u * (target - entry) <= 0:
        return _finish(0, "gap", entry_ts, entry, 0.0)

    path = rth1m_day.loc[rth1m_day.index >= entry_ts]
    path = path.loc[ny_minutes(path.index) <= ts_stop]
    if len(path) == 0:
        return _finish(0, "no_bars", entry_ts, entry, 0.0)

    for ts, b in path.iterrows():
        hit_stop = b["low"] <= stop if side == "long" else b["high"] >= stop
        hit_target = b["high"] >= target_through if side == "long" else b["low"] <= target_through
        minutes_held = (ts - entry_ts).total_seconds() / 60.0
        if hit_stop:
            return _finish(0, "stop", ts, stop, minutes_held)
        if hit_target:
            return _finish(1, "target", ts, target, minutes_held)

    last_ts, last = path.index[-1], path.iloc[-1]
    minutes_held = (last_ts - entry_ts).total_seconds() / 60.0
    return _finish(0, "time", last_ts, float(last["close"]), minutes_held)


def _per_day_sums(df: pd.DataFrame, value_col: str, null_col: str | None) -> pd.DataFrame:
    values = df[value_col].to_numpy(dtype=float)
    if null_col is not None:
        values = values - df[null_col].to_numpy(dtype=float)
    t = pd.DataFrame({"session_date": df["session_date"].to_numpy(), "s": values})
    g = t.groupby("session_date")
    return pd.DataFrame({"s": g["s"].sum(), "n": g.size()})


def ev_test(df: pd.DataFrame, value_col: str = "R_gross", null_col: str | None = None,
            n_boot: int = 10000, seed: int = 0, alpha: float = 0.05) -> dict:
    """EV = media(value_col - null_col) [o media(value_col) se null_col e' None], CI a blocchi per giorno
    (§1), p a una coda `P*(stat* <= 0)` con la correzione (k+1)/(B+1) sulla STESSA distribuzione bootstrap
    che genera la CI (nessun secondo passaggio, spec del task). `per_day` (somme/conteggi per
    session_date) resta nel risultato: serve a `mirror_stats` per un bootstrap appaiato sugli stessi giorni."""
    per_day = _per_day_sums(df, value_col, null_col)
    point, ci, dist = block_bootstrap_ci_fast(per_day, n_boot=n_boot, seed=seed, alpha=alpha, stat="ratio")
    p_one_sided = one_sided_p(dist, n_boot=n_boot)
    return dict(point=point, ci=ci, p_one_sided=p_one_sided, n=int(len(df)), per_day=per_day)


def mirror_stats(ev_orig: dict, ev_mirror: dict, n_boot: int = 10000, seed: int = 0, alpha: float = 0.05) -> dict:
    """Test dello specchio (§1): micro = (EV_orig + EV_specchio)/2, deriva = (EV_orig - EV_specchio)/2. Le CI
    vengono da un bootstrap APPAIATO sulle somme per giorno di entrambi i lati (stesso giorno ricampionato
    insieme per orig e specchio, non due bootstrap indipendenti): i giorni mancanti da un lato valgono
    (s=0, n=0) su quel lato per quel giorno."""
    pa, pb = ev_orig["per_day"], ev_mirror["per_day"]
    a, b = ev_orig["point"], ev_mirror["point"]
    micro = (a + b) / 2.0
    drift = (a - b) / 2.0

    days = pa.index.union(pb.index)
    pa = pa.reindex(days, fill_value=0.0)
    pb = pb.reindex(days, fill_value=0.0)
    n_days = len(days)

    if n_days == 0:
        nan_ci = (float("nan"), float("nan"))
        return dict(micro=micro, drift=drift, ci_micro=nan_ci, ci_drift=nan_ci)

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_days, size=(n_boot, n_days))
    sa, na = pa["s"].to_numpy()[idx].sum(axis=1), pa["n"].to_numpy()[idx].sum(axis=1)
    sb, nb = pb["s"].to_numpy()[idx].sum(axis=1), pb["n"].to_numpy()[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        dist_a = sa / na
        dist_b = sb / nb
    dist_micro = (dist_a + dist_b) / 2.0
    dist_drift = (dist_a - dist_b) / 2.0

    def _ci(dist: np.ndarray) -> tuple[float, float]:
        return (float(np.nanpercentile(dist, 100 * alpha / 2)),
                float(np.nanpercentile(dist, 100 * (1 - alpha / 2))))

    return dict(micro=micro, drift=drift, ci_micro=_ci(dist_micro), ci_drift=_ci(dist_drift))


def units(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Aggiunge le unita' di misura richieste dallo screening v2: `R_gross`, `usd_gross`, `atr_units` (lordi,
    solo movimento di mercato) e i controparti netti dopo i costi (§1 co-primaria): commissione $2,50/lato
    (2 lati sempre: ingresso + uscita) e 1 tick/lato di slippage su ingresso E sulle uscite a mercato (stop,
    time) ma non sul target (limite, nessuno slippage aggiuntivo in uscita) — stessa convenzione di
    `nqml.labels.labeler.apply_costs`. `pnl_pts_net` converte anche la commissione in punti (commissione /
    point_value) cosi' che R_net, usd_net e atr_units_net siano scalati in modo coerente dallo stesso numero
    netto. Richiede `atr`, `pnl_pts`, `r_unit_pts`, `exit_reason`, `side` in `df` (i primi due da `r_gross`,
    `atr` dal chiamante — stesso campo usato dalle geometrie candidate, es. `nqml.screen.overnight`)."""
    out = df.copy()
    tick = cfg["instrument"]["tick_size"]
    pv = cfg["instrument"]["point_value_usd"]
    commission = cfg["costs"]["commission_per_side_usd"]
    slippage_ticks = cfg["costs"]["slippage_ticks_per_side"]

    r_unit = out["r_unit_pts"].astype(float)
    pnl_pts = out["pnl_pts"].astype(float)
    atr = out["atr"].astype(float)

    out["R_gross"] = pnl_pts / r_unit
    out["usd_gross"] = pnl_pts * pv
    out["atr_units"] = pnl_pts / atr

    market_exit = (out["exit_reason"] != "target").astype(float)
    slip_pts = slippage_ticks * tick * (1.0 + market_exit)  # 1 lato ingresso sempre + 1 lato uscita se a mercato
    commission_pts = 2.0 * commission / pv  # 2 lati, convertiti in punti
    pnl_pts_net = pnl_pts - slip_pts - commission_pts

    out["R_net"] = pnl_pts_net / r_unit
    out["usd_net"] = pnl_pts_net * pv
    out["atr_units_net"] = pnl_pts_net / atr

    no_trade = out["exit_reason"].isin(["no_bars", "gap"])
    out.loc[no_trade, ["R_gross", "usd_gross", "atr_units", "R_net", "usd_net", "atr_units_net"]] = 0.0
    return out
