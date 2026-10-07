"""Strumenti comuni della famiglia cross_session.

Minuto di sessione `sm`: 0 = 18:00 NY (apertura Globex della sessione), 480 = 02:00, 540 = 03:00
(Londra), 870 = 08:30 (macro USA), 930 = 09:30 (RTH), 1320 = 16:00, 1380 = 17:00.
Le barre 17:00-17:59 (presenti negli anni 2010-2015, che core assegna gia' alla sessione successiva)
hanno sm < 0 e non entrano in nessun segmento.

Convenzioni di prezzo (tutte su adj_*, perche' il roll cade alle 00:00 UTC dentro la notte):
  sig(b)  = adj_close dell'ultima barra con sm < b      -> prezzo NOTO al confine b (per i segnali)
  ent(b)  = adj_open  della prima barra con sm >= b     -> prezzo di esecuzione al confine b
  ts(b)   = timestamp UTC di quella prima barra
Un trade "da b1 a b2" guadagna side * (ent(b2) - ent(b1)): ingresso all'open della prima barra
dal confine b1, uscita all'open della prima barra dal confine b2.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core

FAMILY = "cross_session"

B = {  # confini in minuti di sessione
    "s18": 0, "s20": 120, "s00": 360, "s02": 480, "s03": 540, "s0330": 570, "s04": 600,
    "s0830": 870, "s0845": 885, "s09": 900, "s0930": 930, "s10": 960, "s1030": 990,
    "s12": 1080, "s15": 1260, "s1530": 1290, "s2130": 210, "s2230": 270, "s01": 420, "s1545": 1305, "s16": 1320, "s1615": 1335, "s17": 1380,
}
MAX_GAP = 30  # minuti: se la prima barra dopo il confine arriva oltre, il prezzo e' NaN


def add_sm(bars: pd.DataFrame) -> pd.DataFrame:
    m = bars["ny_min"].to_numpy().astype(int)
    bars = bars.copy()
    bars["sm"] = np.where(m >= 1020, m - 1080, m + 360).astype(np.int16)
    return bars


def session_table(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Una riga per sessione: prezzi ai confini, estremi e volumi dei segmenti, ATR."""
    if "sm" not in bars:
        bars = add_sm(bars)
    bars = bars[bars["sm"] >= 0]
    sess = bars["session"].to_numpy()
    sm = bars["sm"].to_numpy()
    out = pd.DataFrame(index=daily.index)
    g_all = bars.groupby("session", sort=True)
    for name, b in B.items():
        before = bars[sm < b].groupby("session", sort=True)
        out["sig_" + name] = before["adj_close"].last()
        x = bars[(sm >= b) & (sm < b + MAX_GAP)]
        y = x[~x["session"].duplicated()]
        si = pd.DatetimeIndex(y["session"].to_numpy())
        out["ent_" + name] = pd.Series(y["adj_open"].to_numpy(), index=si)
        out["ts_" + name] = pd.Series(y.index, index=si)
    # estremi per segmento
    segs = {"asia": (0, 480), "eur": (480, 870), "pre": (870, 930), "on": (0, 930),
            "rth": (930, 1320), "post": (1320, 1380), "lon1": (540, 600), "asia_eur": (0, 870)}
    for k, (a, z) in segs.items():
        x = bars[(sm >= a) & (sm < z)].groupby("session", sort=True)
        out[k + "_hi"] = x["adj_high"].max()
        out[k + "_lo"] = x["adj_low"].min()
        out[k + "_vol"] = x["volume"].sum()
        out[k + "_n"] = x.size()
    out["full_hi"] = g_all["adj_high"].max()
    out["full_lo"] = g_all["adj_low"].min()
    out["range_full"] = out["full_hi"] - out["full_lo"]
    out["range_rth"] = out["rth_hi"] - out["rth_lo"]
    # ATR a 20 sessioni della sessione intera (noto prima della sessione: shift 1)
    out["atr20"] = out["range_full"].rolling(20, min_periods=10).mean().shift(1)
    out["atr20_rth"] = out["range_rth"].rolling(20, min_periods=10).mean().shift(1)
    out["valid"] = daily["valid"]
    out["in_phase"] = daily["in_phase"]
    out["dow"] = daily["dow"]
    out["roll_session"] = daily["roll_session"]
    return out


def ret(t: pd.DataFrame, a: str, z: str, kind_a="ent", kind_z="ent") -> pd.Series:
    return t[f"{kind_z}_{z}"] - t[f"{kind_a}_{a}"]


# ------------------------------------------------------------------ valutazione

def evaluate(tid: str, desc: str, gross: pd.Series, side: pd.Series, window_ret: pd.Series,
             atr: pd.Series, mask_valid: pd.Series, record: bool = True, **extra) -> dict:
    """gross: punti lordi per trade (indice = sessione); side: +1/-1; window_ret: rendimento della
    stessa finestra per TUTTE le sessioni valide (per la deriva/beta); atr: normalizzatore."""
    ok = gross.notna() & side.notna() & (side != 0) & mask_valid.reindex(gross.index).fillna(False)
    g = gross[ok].astype(float)
    s = side[ok].astype(float)
    days = g.index.to_numpy()
    net = g - core.COST_RT_POINTS
    st = core.day_block_bootstrap(net.to_numpy(), days)
    st_g = core.day_block_bootstrap(g.to_numpy(), days, n_boot=4000, seed=1)
    wr = window_ret[mask_valid.reindex(window_ret.index).fillna(False)].dropna()
    drift = float(wr.mean()) if len(wr) else np.nan
    beta_adj = float((net - s * drift).mean())
    a = atr.reindex(g.index)
    ga = (g / a).replace([np.inf, -np.inf], np.nan)
    st_a = core.day_block_bootstrap(ga.to_numpy(), days, n_boot=4000, seed=2)
    yr = core.yearly(net.to_numpy(), days)
    res = dict(st)
    res.update(mean_gross=st_g["mean"], p_two_gross=st_g["p_two"], lo_gross=st_g["lo"], hi_gross=st_g["hi"],
               mean_gross_atr=st_a["mean"], p_two_gross_atr=st_a["p_two"],
               long_share=float((s > 0).mean()), drift_window=drift, net_beta_adj=beta_adj,
               drop20_net=core.drop_top(net.to_numpy(), 20),
               years_pos_net=f"{int((yr['mean'] > 0).sum())}/{len(yr)}",
               years_pos_gross=f"{int((core.yearly(g.to_numpy(), days)['mean'] > 0).sum())}/{len(yr)}")
    res.update(extra)
    if record:
        core.record(FAMILY, tid, desc, "discovery", res)
    return res


def fmt(tid, r):
    return (f"{tid:34s} n={r['n']:5d} gross={r['mean_gross']:+7.3f} [{r['lo_gross']:+.2f};{r['hi_gross']:+.2f}] "
            f"p2={r['p_two_gross']:.3f} atr={r['mean_gross_atr']:+.4f} p2a={r['p_two_gross_atr']:.3f} "
            f"net={r['mean']:+.3f} ppos={r['p_pos']:.3f} beta_adj={r['net_beta_adj']:+.3f} L={r['long_share']:.2f} "
            f"yrs={r['years_pos_net']} yg={r['years_pos_gross']} d20={r['drop20_net']:+.3f}")
