"""Contesto condiviso (definizioni senza test) estratto da s01_scan: dati, calendari, finestre base."""
import os

import numpy as np
import pandas as pd

from lab import core
from lab.calendar.common import (Px, hm, RTH_OPEN, RTH_CLOSE, full_check, rec, fmt, fomc_dates,
                                 fomc_time_ny, nfp_dates, exchange_holidays, trading_calendar)

bars, daily = core.load("discovery", warmup_days=30)
px = Px(bars, daily)
S = px.sessions
inph = daily["in_phase"].to_numpy()
valid = daily["valid"].to_numpy()
P16 = pd.Series(px.price(RTH_CLOSE), index=S)       # "close" RTH (open della barra 16:00 o ultimo close)
P930 = pd.Series(px.price(RTH_OPEN), index=S)
RESULTS = {}


def run(tid, desc, gross, side=1.0, base=None, entry=None, extra=None):
    g = gross[inph[S.get_indexer(gross.index)]] if len(gross) else gross
    g = g.dropna()
    sd = side if np.isscalar(side) else side.reindex(g.index)
    if base is not None:
        base = base[inph[S.get_indexer(base.index)]]
    st = full_check(g, sd, base, entry)
    if os.environ.get("CAL_DRY") == "1":      # prova di esecuzione: niente stampa, niente registro
        print("dry", tid, st["n"], flush=True)
        return st
    if extra:
        st.update(extra)
    rec(tid, desc, st)
    RESULTS[tid] = st
    print(fmt(tid, st), flush=True)
    return st


def win(t0, t1, lag=0):
    r, p0 = px.ret(t0, t1, lag)
    return r, p0


# giorni di borsa previsti (regola NYSE): le sessioni Globex dei festivi NON contano come giorni
tc = trading_calendar(2009, 2019)
is_td = S.isin(tc)
tc_pos = pd.Series(np.arange(len(tc)), index=tc)
s_pos = pd.Series(np.arange(len(S)), index=S)
# indice in S del giorno di borsa precedente (-1 se manca nei dati o se la sessione non e' giorno di borsa)
prev_td = np.full(len(S), -1)
for i, s_ in enumerate(S):
    if is_td[i]:
        k = tc_pos[s_]
        if k > 0 and tc[k - 1] in s_pos.index:
            prev_td[i] = s_pos[tc[k - 1]]
has_prev = prev_td >= 0


def lagged(arr):
    arr = np.asarray(arr, float)
    out = np.full(len(arr), np.nan)
    out[has_prev] = arr[prev_td[has_prev]]
    return out


# finestre base (long, tutti i giorni validi in fase)
rth, rth_p0 = win(RTH_OPEN, RTH_CLOSE)
rth = rth.where(valid)
P16prev = lagged(P16)
ovn = pd.Series(P930.to_numpy() - P16prev, index=S).where(valid)       # 16:00 giorno di borsa prima -> 9:30
cc = pd.Series(P16.to_numpy() - P16prev, index=S)                      # close-to-close fra giorni di borsa
cc_ok = pd.Series(has_prev, index=S)                                   # mezze giornate incluse
cc_p0 = pd.Series(P16prev, index=S)
dow = pd.Series(S.dayofweek, index=S)

names = ["lun", "mar", "mer", "gio", "ven"]
ym = tc.year * 12 + tc.month
pos_fwd = pd.Series(pd.Series(1, index=tc).groupby(ym).cumsum().to_numpy(), index=tc)        # 1,2,3.. dall'inizio
pos_bwd = pd.Series(pd.Series(1, index=tc)[::-1].groupby(ym[::-1]).cumsum()[::-1].to_numpy(), index=tc)  # 1 = ultimo
tom_pos = pd.Series(np.where(pos_bwd <= 5, -pos_bwd.to_numpy() + 1, pos_fwd.to_numpy()), index=tc)
# tom_pos: 0 = ultimo giorno del mese, -1 penultimo, ..., 1 = primo giorno del mese nuovo, 2, ...
tp = tom_pos.reindex(S)

def fwd_td(i, n):
    """Indice in S del giorno di borsa n passi dopo la sessione i (-1 se manca)."""
    k = tc_pos.get(S[i], None)
    if k is None or k + n >= len(tc) or tc[k + n] not in s_pos.index:
        return -1
    return s_pos[tc[k + n]]


def hold(entry_mask: pd.Series, n_days: int):
    """Long dal close 16:00 della sessione d'ingresso al close 16:00 di n_days giorni di borsa dopo."""
    p = P16.to_numpy()
    idx = np.where(entry_mask.reindex(S).fillna(False).to_numpy() & is_td)[0]
    j = np.array([fwd_td(i, n_days) for i in idx], dtype=int)
    ok = j >= 0
    idx, j = idx[ok], j[ok]
    g = pd.Series(p[j] - p[idx], index=S[idx])
    return g, pd.Series(p[idx], index=S[idx])


def base_hold(n_days):
    g, _ = hold(pd.Series(True, index=S), n_days)
    return g

hol = exchange_holidays(2009, 2019)
tcl = list(tc)
pre_h, post_h = set(), set()
for i in range(len(tcl) - 1):
    gap = [tcl[i] + pd.Timedelta(days=k) for k in range(1, (tcl[i + 1] - tcl[i]).days)]
    if any(g.date() in hol for g in gap):
        pre_h.add(tcl[i]); post_h.add(tcl[i + 1])
pre = pd.Series(S.isin(list(pre_h)), index=S)
post = pd.Series(S.isin(list(post_h)), index=S)
def third_friday(y, m):
    return core._third_friday(y, m)


tf = pd.DatetimeIndex([pd.Timestamp(third_friday(y, m)) for y in range(2009, 2020) for m in range(1, 13)])
tf_adj = pd.DatetimeIndex([d if d in set(tc) else d - pd.Timedelta(days=1) for d in tf])  # Venerdi' Santo -> gio
quad = tf_adj[tf.month.isin([3, 6, 9, 12])]
wk = pd.Series(S.to_period("W-SUN"), index=S)
opex_weeks = set(pd.DatetimeIndex(tf_adj).to_period("W-SUN"))
is_opex_week = wk.isin(opex_weeks)
last = (tp == 0)
lh, lh_p0 = win(hm(15, 0), RTH_CLOSE)
lh = lh.where(valid)
p15 = pd.Series(px.price(hm(15, 0)), index=S)
prev_me_close = P16.where(last & is_td).shift(1).ffill()        # close dell'ultimo giorno del mese precedente
