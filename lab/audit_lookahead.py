"""Audit meccanico del look-ahead per tutti i candidati congelati (solo discovery).

Per ogni istante di taglio T: tutte le barre con ts > T vengono alterate (random walk aggiunto ai prezzi,
volumi moltiplicati per un fattore casuale), la tabella giornaliera viene ricostruita dalle barre alterate.
Un candidato causale deve produrre, per i trade con entry_ts <= T, lo stesso lato e lo stesso ingresso;
e per i trade con exit_ts <= T anche lo stesso gross_pts. Qualunque differenza = uso di informazione futura.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from lab import core, controller


def rebuild_daily(bars: pd.DataFrame, daily_ref: pd.DataFrame) -> pd.DataFrame:
    g = bars.groupby("session", sort=True)
    r = bars[bars["rth"]].groupby("session", sort=True)
    d = daily_ref.copy()
    d["n_bars"] = g.size()
    d["n_rth"] = r.size()
    d["glbx_open"] = g["adj_open"].first()
    d["rth_open"] = r["adj_open"].first()
    d["rth_high"] = r["adj_high"].max()
    d["rth_low"] = r["adj_low"].min()
    d["rth_close"] = r["adj_close"].last()
    d["rth_volume"] = r["volume"].sum()
    d["day_close"] = g["adj_close"].last()
    d["valid"] = d["n_rth"] >= 300
    return d


def perturb(bars: pd.DataFrame, daily: pd.DataFrame, T: pd.Timestamp, seed: int, direction: int = 1):
    b = bars.copy()
    m = b.index > T
    n = int(m.sum())
    rng = np.random.default_rng(seed)
    scale = float(b["close"].diff().abs().median() or 0.25) * 3
    walk = np.round(np.cumsum(rng.normal(direction * scale, scale, n)) / core.TICK) * core.TICK   # tendenza forte
    for c in ("open", "high", "low", "close", "adj_open", "adj_high", "adj_low", "adj_close"):
        v = b[c].to_numpy().copy()
        v[m] = v[m] + walk
        b[c] = v
    vol = b["volume"].to_numpy().astype(float).copy()
    vol[m] = np.round(vol[m] * rng.uniform(0.3, 3.0, n))
    b["volume"] = vol.astype(np.uint64)
    return b, rebuild_daily(b, daily)


def key(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["entry_ts"] = pd.to_datetime(t["entry_ts"], utc=True)
    t["exit_ts"] = pd.to_datetime(t["exit_ts"], utc=True)
    return t.sort_values(["entry_ts", "side"]).reset_index(drop=True)


def audit(c: dict, cuts: list[pd.Timestamp]) -> list[str]:
    w = int(c.get("warmup_days", 0))
    bars, daily = core.load("discovery", warmup_days=w)
    base = key(c["fn"](bars.copy(), daily.copy()))
    problems = []
    # tagli mirati: esattamente all'ingresso di 10 trade reali (entry_ts incluso, tutto il dopo alterato)
    rs = np.random.default_rng(7)
    inphase = base[pd.to_datetime(base["session"]) >= pd.Timestamp("2011-06-01")]
    own = list(pd.DatetimeIndex(inphase["entry_ts"].to_numpy()[rs.choice(len(inphase), min(10, len(inphase)), replace=False)]))
    cuts = list(cuts) + own
    for i, T in enumerate([t for t in cuts for _ in (0, 1)]):
        pb, pd_ = perturb(bars, daily, T, seed=i, direction=1 if i % 2 == 0 else -1)
        alt = key(c["fn"](pb, pd_))
        b0 = base[base["entry_ts"] <= T]
        a0 = alt[alt["entry_ts"] <= T]
        if len(b0) != len(a0) or not (b0["entry_ts"].values == a0["entry_ts"].values).all() \
                or not (b0["side"].values == a0["side"].values).all():
            problems.append(f"T={T}: trade decisi prima di T cambiano (base {len(b0)} vs alterato {len(a0)})")
            continue
        closed = (b0["exit_ts"] <= T).to_numpy()
        if closed.any() and not np.allclose(b0["gross_pts"].to_numpy()[closed], a0["gross_pts"].to_numpy()[closed],
                                            equal_nan=True):
            problems.append(f"T={T}: gross_pts di trade chiusi prima di T cambia")
    return problems


def main() -> None:
    only = set(sys.argv[1:])
    rng = np.random.default_rng(123)
    _, daily = core.load("discovery")
    sess = daily.index[daily["valid"] & daily["in_phase"]]
    sess = sess[sess >= pd.Timestamp("2012-06-01")]          # oltre ogni warmup
    picks = rng.choice(len(sess), 12, replace=False)
    cuts = []
    for j, p in enumerate(sorted(picks)):
        s = sess[p]
        minute = [9 * 60 + 45, 10 * 60 + 30, 11 * 60 + 59, 13 * 60, 15 * 60 + 29, 15 * 60 + 45, 16 * 60 + 40,
                  20 * 60, 3 * 60, 8 * 60 + 45, 12 * 60 + 15, 14 * 60 + 10][j]
        day = s if minute < 17 * 60 else s - pd.Timedelta(days=1)
        cuts.append(pd.Timestamp(day.year, day.month, day.day, minute // 60, minute % 60, tz=core.NY).tz_convert("UTC"))
    for c in controller.all_candidates():
        if only and c["id"] not in only:
            continue
        pr = audit(c, cuts)
        print(f"{'OK ' if not pr else 'LEAK'} {c['id']}" + ("" if not pr else "\n   " + "\n   ".join(pr)), flush=True)


if __name__ == "__main__":
    main()
