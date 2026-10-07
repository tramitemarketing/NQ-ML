"""Strumenti della famiglia r5_amd: modello ICT «AMD» del video di Tmac (spec in lab/r5_amd/PREREG.md).

Tutto e' scritto per lo SHORT (manipolazione al rialzo dentro un order block 4h ribassista). Il LONG si
ottiene facendo girare la stessa logica sui prezzi negati (high -> -low, low -> -high): un OB ribassista dei
prezzi negati e' un OB rialzista di quelli veri, il minimo asiatico diventa il massimo asiatico, e il P&L
(entry - exit) nello spazio negato e' esattamente il P&L del long. Prezzi sempre adj_* (i livelli 4h
possono attraversare un roll).

Convenzioni di esecuzione (PREREG): limite riempito solo con trade-through di 1 tick; se la barra di
riempimento tocca anche lo stop conta lo stop; stop e obiettivo nella stessa barra -> stop; l'obiettivo
conta solo dalla barra dopo il riempimento; uscita a tempo al close della barra 15:59.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core

FAM = "r5_amd"
TICK = core.TICK

WIN_START = 510          # 08:30
ASIA_END = 1440          # Asia = 18:00 -> 23:59 (ny_min >= 1080)
EXIT_MIN = 959           # 15:59

DEFAULT = dict(zone="open_high", max_age=30, win_end=719, fill_end=779, target="asia_low",
               entry="limit", require_sweep=True, require_ob=True, mirror=False, zone_shift=None,
               stop_atr=0.0, reach_atr=None, above_mid=False)   # proposte PA/PB/PC (addendum 1)


# --------------------------------------------------------------------------- preparazione

class Data:
    """Array di barre e indici per sessione (discovery o qualunque fase passata)."""

    def __init__(self, bars: pd.DataFrame, daily: pd.DataFrame):
        self.bars = bars
        self.ts = bars.index
        self.sess = bars["session"].to_numpy().astype("datetime64[D]")
        self.m = bars["ny_min"].to_numpy().astype(np.int32)
        self.o = bars["adj_open"].to_numpy(float)
        self.h = bars["adj_high"].to_numpy(float)
        self.l = bars["adj_low"].to_numpy(float)
        self.c = bars["adj_close"].to_numpy(float)
        u, start = np.unique(self.sess, return_index=True)
        self.sessions = u
        self.start = start
        self.end = np.append(start[1:], len(self.sess))
        self.sess_code = np.repeat(np.arange(len(u)), self.end - self.start)
        d = daily.reindex(pd.DatetimeIndex(u))
        self.valid = d["valid"].fillna(False).to_numpy(bool)
        self.in_phase = d["in_phase"].fillna(False).to_numpy(bool) if "in_phase" in d else np.ones(len(u), bool)
        rc = d["rth_close"].to_numpy(float)
        # trend noto prima dell'apertura: segno(close RTH ieri - close RTH 5 sessioni prima)
        self.trend = np.sign(pd.Series(rc).shift(1) - pd.Series(rc).shift(6)).fillna(0).to_numpy()
        # ATR 20 giorni (range RTH) noto prima della sessione, per il placebo
        rng = (d["rth_high"] - d["rth_low"]).to_numpy(float)
        self.atr20 = pd.Series(rng).shift(1).rolling(20, min_periods=5).mean().to_numpy()


def space(D: Data, sign: int):
    """(o, h, l, c) nello spazio dello short: sign=+1 prezzi veri (short), -1 negati (long)."""
    if sign > 0:
        return D.o, D.h, D.l, D.c
    return -D.o, -D.l, -D.h, -D.c


def four_hour(D: Data, o, h, l, c):
    """Candele 4h allineate alle 18:00 NY. Ritorna DataFrame con o,h,l,c, i0,i1 (indici 1m) e sessione."""
    m18 = (D.m - 1080) % 1440
    key = D.sess_code.astype(np.int64) * 6 + m18 // 240
    brk = np.flatnonzero(np.diff(key)) + 1
    i0 = np.concatenate([[0], brk])
    i1 = np.concatenate([brk, [len(key)]]) - 1
    return pd.DataFrame({
        "o": o[i0], "h": np.maximum.reduceat(h, i0), "l": np.minimum.reduceat(l, i0), "c": c[i1],
        "i0": i0, "i1": i1, "sc": D.sess_code[i0],
    })


def bearish_obs(D: Data, o, h, l, c, zone="open_high", max_age=30, zone_shift=None) -> pd.DataFrame:
    """OB 4h ribassisti (nello spazio dato) e indice 1m del primo tocco (-1 se mai entro max_age sessioni).
    zone_shift: array (per OB) di spostamenti in punti per il placebo C3."""
    f = four_hour(D, o, h, l, c)
    bull = (f["c"] > f["o"]).to_numpy()
    disp = np.zeros(len(f), bool)
    disp[:-1] = bull[:-1] & (f["c"].to_numpy()[1:] < f["l"].to_numpy()[:-1])
    idx = np.flatnonzero(disp)
    ob = pd.DataFrame({
        "bot": (f["o"] if zone == "open_high" else f["l"]).to_numpy()[idx],
        "top": f["h"].to_numpy()[idx],
        "known": f["i1"].to_numpy()[idx + 1] + 1,          # prima barra 1m dopo la candela di spostamento
        "sc": f["sc"].to_numpy()[idx + 1],
    })
    ob = ob[ob["known"] < len(h)].reset_index(drop=True)
    if zone_shift is not None:
        sh = np.asarray(zone_shift)[: len(ob)]
        ob["bot"] += sh
        ob["top"] += sh
    touch = np.full(len(ob), -1, np.int64)
    last_sc = D.sess_code[-1]
    for k, (bot, kn, sc) in enumerate(zip(ob["bot"].to_numpy(), ob["known"].to_numpy(), ob["sc"].to_numpy())):
        sc_end = min(sc + max_age, last_sc)
        j1 = D.end[sc_end]
        seg = h[kn:j1] >= bot
        if seg.any():
            touch[k] = kn + int(np.argmax(seg))
    ob["touch"] = touch
    return ob


# --------------------------------------------------------------------------- simulazione

def _events(D: Data, o, h, l, c, obs: pd.DataFrame, p: dict) -> dict:
    """Per sessione: indice 1m dell'evento di manipolazione (short nello spazio dato) o -1."""
    tap_by_sess: dict[int, int] = {}
    t = obs["touch"].to_numpy()
    t = t[t >= 0]
    if len(t):
        mm = D.m[t]
        ok = (mm >= WIN_START) & (mm <= p["win_end"])
        for j in np.sort(t[ok]):
            sc = D.sess_code[j]
            if sc not in tap_by_sess:
                tap_by_sess[sc] = int(j)
    out = {}
    for sc in range(len(D.sessions)):
        if not D.valid[sc]:
            continue
        a, b = D.start[sc], D.end[sc]
        mm = D.m[a:b]
        night = (mm >= 1080) | (mm < WIN_START)
        if night.sum() < 60:
            continue
        on_high = h[a:b][night].max()
        win = np.flatnonzero((mm >= WIN_START) & (mm <= p["win_end"]))
        if len(win) == 0:
            continue
        sw = win[h[a:b][win] >= on_high + TICK]
        sweep = a + int(sw[0]) if len(sw) else -1
        tap = tap_by_sess.get(sc, -1)
        if p["require_sweep"] and p["require_ob"]:
            ev = max(sweep, tap) if (sweep >= 0 and tap >= 0) else -1
        elif p["require_sweep"]:
            ev = sweep
        else:
            ev = tap
        if ev >= 0:
            out[sc] = ev
    return out


def _trade(D: Data, o, h, l, c, sc: int, ev: int, p: dict):
    """Simula lo short (nello spazio dato) dopo l'evento ev. Ritorna dict o None."""
    a, b = D.start[sc], D.end[sc]
    mm = D.m[a:b]
    loc = np.flatnonzero(mm >= WIN_START)
    if len(loc) == 0:
        return None
    # target
    asia = np.flatnonzero(mm >= 1080)
    if len(asia) == 0:
        return None
    asia_low = l[a:b][asia].min()
    mid = np.flatnonzero((mm < 1080) & (mm >= 0))
    midnight_open = o[a + mid[0]] if len(mid) else np.nan
    # candele 2m dalle 08:30 alla scadenza del riempimento
    li = loc[mm[loc] <= p["fill_end"]] + a
    if len(li) == 0:
        return None
    key = D.m[li] // 2
    brk = np.flatnonzero(np.diff(key)) + 1
    s0 = np.concatenate([[0], brk])
    s1 = np.concatenate([brk, [len(li)]])
    co = o[li[s0]]
    chh = np.maximum.reduceat(h[li], s0)
    cl = np.minimum.reduceat(l[li], s0)
    cc = c[li[s1 - 1]]
    first = li[s0]
    last = li[s1 - 1]
    ke = int(np.searchsorted(first, ev, side="right") - 1)
    if ke < 0:
        return None
    M, kM = -np.inf, -1
    for k in range(ke):                       # manipolazione dalle 08:30 fino all'evento (escluso)
        if chh[k] > M:
            M, kM = chh[k], k
    limit = None
    fill_i = entry = None
    for k in range(ke, len(first)):
        if limit is not None:                 # riempimento sulle barre 1m della candela k
            for j in range(first[k], last[k] + 1):
                if h[j] >= limit + TICK:
                    fill_i, entry = j, limit
                    break
            if fill_i is not None:
                break
        if chh[k] > M:
            M, kM, limit = chh[k], k, None
            continue
        if limit is None and k > kM:
            bulls = [q for q in range(kM, -1, -1) if cc[q] > co[q]]
            if bulls and cc[k] < cl[bulls[0]]:
                if p["entry"] == "market":
                    fill_i, entry = last[k], cc[k]
                    break
                limit = co[bulls[0]]
    if fill_i is None:
        return None
    # M aggiornato fino alla barra di riempimento inclusa (per il limite, se la barra supera M e' stop)
    stop = M + TICK
    atr = D.atr20[sc]
    if p["stop_atr"] > 0:                     # PA: stop almeno a 0,10*ATR20 dall'ingresso
        if not np.isfinite(atr):
            return None
        stop = max(stop, entry + p["stop_atr"] * atr)
    risk = stop - entry
    if risk <= 0:
        return None
    tg = p["target"]
    if tg == "asia_low":
        target = asia_low
    elif tg == "midnight":
        target = midnight_open
    elif tg.endswith("R"):
        target = entry - float(tg[:-1]) * risk
    else:
        target = -np.inf
    if not np.isfinite(target) and tg != "eod":
        return None
    if tg != "eod" and target >= entry:
        return None
    if p["reach_atr"] is not None and not (np.isfinite(atr) and entry - target <= p["reach_atr"] * atr):
        return None                           # PB: obiettivo raggiungibile
    if p["above_mid"] and not entry > midnight_open:
        return None                           # PC: la candela del giorno e' ancora da girare
    mirror = p["mirror"]
    if mirror:                                # continuazione: long, livelli speculari in R
        stop_m, target_m = entry - risk, (entry + (entry - target) if tg != "eod" else np.inf)
    ex_end = a + int(np.flatnonzero(mm <= EXIT_MIN)[-1])
    if ex_end <= fill_i:
        return None
    exit_px, exit_i, why = c[ex_end], ex_end, "time"
    for j in range(fill_i, ex_end + 1):
        if not mirror:
            if h[j] >= stop:
                exit_px, exit_i, why = stop, j, "stop"
                break
            if j > fill_i and l[j] <= target:
                exit_px, exit_i, why = target, j, "target"
                break
        else:
            if j > fill_i and l[j] <= stop_m:
                exit_px, exit_i, why = stop_m, j, "stop"
                break
            if j > fill_i and h[j] >= target_m:
                exit_px, exit_i, why = target_m, j, "target"
                break
    pnl = (entry - exit_px) if not mirror else (exit_px - entry)
    return dict(fill_i=fill_i, exit_i=exit_i, entry=entry, stop=stop, target=target, risk=risk,
                pnl=pnl, why=why, ev=ev)


def simulate(D: Data, **kw) -> pd.DataFrame:
    """Trade della regola (un trade per sessione: vince l'evento che arriva prima fra short e long)."""
    p = dict(DEFAULT)
    p.update(kw)
    sides = {}
    for sign in (+1, -1):
        o, h, l, c = space(D, sign)
        zs = p["zone_shift"][sign] if p["zone_shift"] is not None else None
        obs = bearish_obs(D, o, h, l, c, zone=p["zone"], max_age=p["max_age"], zone_shift=zs)
        sides[sign] = (_events(D, o, h, l, c, obs, p), (o, h, l, c))
    rows = []
    for sc in range(len(D.sessions)):
        cand = [(sides[s][0][sc], s) for s in (+1, -1) if sc in sides[s][0]]
        if not cand:
            continue
        ev, sign = min(cand)
        o, h, l, c = sides[sign][1]
        tr = _trade(D, o, h, l, c, sc, ev, p)
        if tr is None:
            continue
        side = -sign if not p["mirror"] else sign    # short nello spazio vero = -1
        rows.append(dict(session=pd.Timestamp(D.sessions[sc]), entry_ts=D.ts[tr["fill_i"]],
                         exit_ts=D.ts[tr["exit_i"]], side=side, gross_pts=tr["pnl"], R=tr["pnl"] / tr["risk"],
                         risk=tr["risk"], why=tr["why"], trend=D.trend[sc],
                         ct=bool(D.trend[sc] * side < 0),          # contro il trend di 5 sessioni
                         in_phase=D.in_phase[sc]))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- statistiche

def summarize(t: pd.DataFrame, bars: pd.DataFrame | None = None) -> dict:
    if len(t) == 0:
        return {"n": 0}
    net = t["gross_pts"].to_numpy(float) - core.COST_RT_POINTS
    st = core.day_block_bootstrap(net, t["session"].values)
    yr = core.yearly(net, t["session"])
    st["years_pos"] = f"{int((yr['mean'] > 0).sum())}/{len(yr)}"
    st["years"] = yr["mean"].round(2).to_dict()
    st["d20"] = core.drop_top(net, 20)
    st["gross"] = float(np.mean(t["gross_pts"]))
    st["meanR_net"] = float(np.mean(net / t["risk"].to_numpy(float)))
    st["win"] = float((net > 0).mean())
    st["why"] = t["why"].value_counts().to_dict()
    st["risk_med"] = float(t["risk"].median())
    if bars is not None:
        from lab.controller import beta_component
        beta = beta_component(bars, t)
        sb = core.day_block_bootstrap(net - beta, t["session"].values)
        st["beta_adj_mean"] = sb["mean"]
        st["beta_adj_p"] = sb["p_pos"]
    return st


def fmt(name: str, st: dict) -> str:
    if st.get("n", 0) == 0:
        return f"{name:<34} n=0"
    s = (f"{name:<34} n={st['n']:>4} netto {st['mean']:+6.2f} [{st['lo']:+6.2f};{st['hi']:+6.2f}] "
         f"p+ {st['p_pos']:.3f} anni+ {st['years_pos']} d20 {st['d20']:+6.2f} R {st['meanR_net']:+.3f} "
         f"win {st['win']:.2f} rischio~{st['risk_med']:.1f}")
    if "beta_adj_mean" in st:
        s += f" beta-adj {st['beta_adj_mean']:+.2f} (p {st['beta_adj_p']:.3f})"
    return s
