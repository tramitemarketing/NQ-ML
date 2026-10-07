"""Scansione principale della famiglia calendar (discovery). Ogni test guardato viene registrato.

Uso: python -m lab.calendar.s01_scan
"""
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

# ------------------------------------------------------------------ A/B: giorno della settimana
names = ["lun", "mar", "mer", "gio", "ven"]
for d in range(5):
    m = (dow == d) & valid
    run(f"dow_rth_{names[d]}", f"Long RTH 9:30-16:00 il {names[d]}", rth[m], 1.0, rth, rth_p0)
for d in range(5):
    m = (dow == d)
    run(f"dow_ovn_{names[d]}", f"Long overnight 16:00 giorno prima -> 9:30 del {names[d]} (lun = weekend)",
        ovn[m], 1.0, ovn, cc_p0)

# ------------------------------------------------------------------ calendario di borsa e posizioni nel mese
ym = tc.year * 12 + tc.month
pos_fwd = pd.Series(pd.Series(1, index=tc).groupby(ym).cumsum().to_numpy(), index=tc)        # 1,2,3.. dall'inizio
pos_bwd = pd.Series(pd.Series(1, index=tc)[::-1].groupby(ym[::-1]).cumsum()[::-1].to_numpy(), index=tc)  # 1 = ultimo
tom_pos = pd.Series(np.where(pos_bwd <= 5, -pos_bwd.to_numpy() + 1, pos_fwd.to_numpy()), index=tc)
# tom_pos: 0 = ultimo giorno del mese, -1 penultimo, ..., 1 = primo giorno del mese nuovo, 2, ...
tp = tom_pos.reindex(S)

for k in [-3, -2, -1, 0, 1, 2, 3, 4]:
    m = (tp == k) & cc_ok
    run(f"tom_day_{k:+d}", f"Long close-to-close (16:00->16:00) sul giorno di borsa {k:+d} del turn-of-month "
        f"(0 = ultimo del mese)", cc[m], 1.0, cc.where(cc_ok), cc_p0)


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


# TOM classico Lakonishok-Smidt: ingresso al close del giorno -2 (penultimo = -1 nella nostra
# numerazione e' il giorno prima dell'ultimo), cioe' si tengono i giorni -1..+3 -> close di tom_pos==-2
for (a, n, lab) in [(-2, 5, "LS -1..+3"), (-1, 4, "0..+3"), (-1, 2, "0..+1"), (-3, 4, "-2..+1")]:
    g, p0 = hold(tp == a, n)
    run(f"tom_hold_{lab.replace(' ', '').replace('..', '_')}",
        f"Long TOM {lab}: close 16:00 del giorno {a} -> close {n} sessioni dopo", g, 1.0, base_hold(n), p0)

# ------------------------------------------------------------------ festivita'
hol = exchange_holidays(2009, 2019)
tcl = list(tc)
pre_h, post_h = set(), set()
for i in range(len(tcl) - 1):
    gap = [tcl[i] + pd.Timedelta(days=k) for k in range(1, (tcl[i + 1] - tcl[i]).days)]
    if any(g.date() in hol for g in gap):
        pre_h.add(tcl[i]); post_h.add(tcl[i + 1])
pre = pd.Series(S.isin(list(pre_h)), index=S)
post = pd.Series(S.isin(list(post_h)), index=S)
cc_any = cc.copy()        # pre-festivi sono spesso mezze giornate (invalid): close = ultimo prezzo
run("preholiday_cc", "Long close-to-close del giorno PRE-festivo (16:00 ieri -> fine sessione, anche mezze giornate)",
    cc_any[pre], 1.0, cc.where(cc_ok), cc_p0)
run("postholiday_cc", "Long close-to-close del giorno POST-festivo", cc_any[post], 1.0, cc.where(cc_ok), cc_p0)
g, p0 = hold(pd.Series(np.r_[pre.to_numpy()[1:], False], index=S), 2)
run("preholiday_2d", "Long 2 giorni: close del giorno prima del pre-festivo -> close del post-festivo", g, 1.0,
    base_hold(2), p0)

# ------------------------------------------------------------------ scadenze opzioni
def third_friday(y, m):
    return core._third_friday(y, m)


tf = pd.DatetimeIndex([pd.Timestamp(third_friday(y, m)) for y in range(2009, 2020) for m in range(1, 13)])
tf_adj = pd.DatetimeIndex([d if d in set(tc) else d - pd.Timedelta(days=1) for d in tf])  # Venerdi' Santo -> gio
quad = tf_adj[tf.month.isin([3, 6, 9, 12])]
wk = pd.Series(S.to_period("W-SUN"), index=S)
opex_weeks = set(pd.DatetimeIndex(tf_adj).to_period("W-SUN"))
is_opex_week = wk.isin(opex_weeks)
m = pd.Series(S.isin(tf_adj), index=S)
run("opex_fri_rth", "Long RTH il venerdi' di scadenza mensile", rth[m & valid], 1.0, rth, rth_p0)
run("quad_fri_rth", "Long RTH il venerdi' di quadrupla scadenza", rth[pd.Series(S.isin(quad), index=S) & valid], 1.0,
    rth, rth_p0)
run("opex_mon_rth", "Long RTH il lunedi' della settimana di scadenza", rth[(dow == 0) & is_opex_week & valid], 1.0,
    rth, rth_p0)
run("opex_week_cc", "Long close-to-close tutti i giorni della settimana di scadenza", cc[is_opex_week & cc_ok], 1.0,
    cc.where(cc_ok), cc_p0)
after_weeks = set(p + 1 for p in opex_weeks)
run("post_opex_week_cc", "Long close-to-close nella settimana DOPO la scadenza", cc[wk.isin(after_weeks) & cc_ok],
    1.0, cc.where(cc_ok), cc_p0)
qweeks = set(pd.DatetimeIndex(quad).to_period("W-SUN"))
run("quad_week_cc", "Long close-to-close nella settimana di quadrupla scadenza", cc[wk.isin(qweeks) & cc_ok], 1.0,
    cc.where(cc_ok), cc_p0)

# ------------------------------------------------------------------ roll
rs = daily["roll_session"]
run("roll_rth", "Long RTH nella sessione di roll (daily.roll_session)", rth[rs & valid], 1.0, rth, rth_p0)
roll_weeks = set(wk[rs])
run("roll_week_cc", "Long close-to-close nella settimana di roll", cc[wk.isin(roll_weeks) & cc_ok], 1.0,
    cc.where(cc_ok), cc_p0)

# ------------------------------------------------------------------ fine mese: ultima ora e ribilanciamento
last = (tp == 0)
lh, lh_p0 = win(hm(15, 0), RTH_CLOSE)
lh = lh.where(valid)
run("me_lasthour_long", "Long 15:00-16:00 l'ultimo giorno di borsa del mese", lh[last & valid], 1.0, lh, lh_p0)
qe = last & pd.Series(S.month.isin([3, 6, 9, 12]), index=S)
run("qe_lasthour_long", "Long 15:00-16:00 l'ultimo giorno del trimestre", lh[qe & valid], 1.0, lh, lh_p0)
# segnale ribilanciamento: rendimento del mese fino alle 15:00 dell'ultimo giorno (dal close dell'ultimo giorno
# del mese precedente). Lato = -segno (i fondi bilanciati vendono azioni dopo un mese forte).
p15 = pd.Series(px.price(hm(15, 0)), index=S)
prev_me_close = P16.where(last & is_td).shift(1).ffill()        # close dell'ultimo giorno del mese precedente
mtd = p15 - prev_me_close
side_rb = -np.sign(mtd)
run("me_rebal_lasthour", "Ultimo giorno del mese 15:00-16:00, lato = -segno(rendimento mese a data alle 15:00)",
    (lh * side_rb)[last & valid], side_rb[last & valid], lh, lh_p0)
# ultimi 3 giorni: dal close di tom_pos -3 al close del giorno 0, lato = -segno(MTD al close di -3)
ent = (tp == -3)
g, p0 = hold(ent, 3)
mtd3 = (P16 - prev_me_close).reindex(g.index)
sd3 = -np.sign(mtd3)
run("me_rebal_3d", "Close giorno -3 -> close ultimo giorno del mese, lato = -segno(MTD al close di -3)", g * sd3, sd3,
    base_hold(3), p0)

# ------------------------------------------------------------------ FOMC
fd = fomc_dates()
fd = fd[fd.isin(S)]
pre_g, pre_side, pre_p0, fomc_react, fomc_post, fomc_rth_pre, react_side = {}, {}, {}, {}, {}, {}, {}
for d in fd:
    i = S.get_loc(d)
    h, mi = fomc_time_ny(d)
    t = hm(h, mi)
    # 24 ore prima: stesso orario della sessione precedente -> 1 minuto prima del comunicato
    if prev_td[i] < 0:
        continue
    p_prev = px.price(t)[prev_td[i]]
    p_pre = px.price(t - 1)[i]
    pre_g[d] = p_pre - p_prev; pre_p0[d] = p_prev
    fomc_rth_pre[d] = p_pre - px.price(RTH_OPEN)[i]
    p_t15 = px.price(t + 15)[i]
    p_t = px.price(t)[i]
    p_c = px.price(RTH_CLOSE)[i]
    fomc_post[d] = p_c - p_t
    s_ = np.sign(p_t15 - p_t)
    react_side[d] = s_
    fomc_react[d] = s_ * (p_c - p_t15)
pre_g = pd.Series(pre_g); pre_p0 = pd.Series(pre_p0)
# base: stessa finestra 24h (14:00 ieri -> 13:59 oggi) su tutti i giorni
b24 = pd.Series(px.price(hm(13, 59)) - lagged(px.price(hm(14, 0))), index=S).where(valid)
run("fomc_pre24h", "Long pre-FOMC (Lucca-Moench): stesso orario del comunicato nella sessione prima -> 1 minuto "
    "prima del comunicato", pre_g, 1.0, b24, pre_p0)
b_open_14 = pd.Series(px.price(hm(13, 59)) - P930.to_numpy(), index=S).where(valid)
run("fomc_rth_pre", "Long giorno FOMC 9:30 -> 1 minuto prima del comunicato", pd.Series(fomc_rth_pre), 1.0, b_open_14,
    P930)
b_14_16 = pd.Series(P16.to_numpy() - px.price(hm(14, 0)), index=S).where(valid)
run("fomc_post_long", "Long giorno FOMC dal comunicato -> 16:00", pd.Series(fomc_post), 1.0, b_14_16, None)
run("fomc_react_follow", "Giorno FOMC: lato = segno dei primi 15 min dopo il comunicato, tenuto fino alle 16:00",
    pd.Series(fomc_react), pd.Series(react_side), None, None)
nxt = pd.Series(np.r_[False, S[:-1].isin(fd)], index=S)
run("fomc_nextday_rth", "Long RTH il giorno dopo il FOMC", rth[nxt & valid], 1.0, rth, rth_p0)
run("fomc_day_cc", "Long close-to-close del giorno FOMC", cc[pd.Series(S.isin(fd), index=S) & cc_ok], 1.0,
    cc.where(cc_ok), cc_p0)

# ciclo FOMC (Cieslak-Morse-Vissing-Jorgensen 2019): settimane pari dal FOMC. Giorno 0 = FOMC; settimana 0 =
# giorni -1..+3, settimana 2 = +9..+13, 4 = +19..+23, 6 = +29..+33 (in giorni di borsa).
tcpos = pd.Series(np.arange(len(tc)), index=tc)
fpos = tcpos.reindex(fomc_dates()).dropna().to_numpy().astype(int)
cyc = np.full(len(tc), 99)
for k, p in enumerate(tcpos.to_numpy()):
    # distanza dall'ultimo FOMC con giorno -1 incluso nel ciclo successivo
    prior = fpos[fpos <= p + 1]
    if len(prior):
        cyc[k] = p - prior[-1]
cyc = pd.Series(cyc, index=tc).reindex(S)
wkc = np.floor((cyc + 1) / 5)
even = wkc.isin([0, 2, 4, 6])
run("fomc_cycle_even_cc", "Long close-to-close nei giorni delle settimane PARI del ciclo FOMC (CMVJ 2019)",
    cc[even & cc_ok], 1.0, cc.where(cc_ok), cc_p0)
run("fomc_cycle_odd_cc", "Long close-to-close nelle settimane DISPARI del ciclo FOMC", cc[~even & cc_ok & (cyc < 99)],
    1.0, cc.where(cc_ok), cc_p0)

# ------------------------------------------------------------------ NFP
nf = nfp_dates(2009, 2019)
isn = pd.Series(S.isin(nf), index=S)
run("nfp_rth", "Long RTH nel giorno NFP", rth[isn & valid], 1.0, rth, rth_p0)
p830 = pd.Series(px.price(hm(8, 30)), index=S)
p925 = pd.Series(px.price(hm(9, 25)), index=S)
sd_n = np.sign(p925 - p830)
run("nfp_follow_premkt", "Giorno NFP: lato = segno(8:30->9:25), tenuto 9:30->16:00", (rth * sd_n)[isn & valid],
    sd_n[isn & valid], rth, rth_p0)
p835 = pd.Series(px.price(hm(8, 35)), index=S)
sd5 = np.sign(p835 - p830)
g = (p925 - p835) * sd5
run("nfp_follow_5m", "Giorno NFP: lato = segno(8:30->8:35), tenuto 8:35->9:25", g[isn], sd5[isn],
    (p925 - p835).where(valid), p835)
prenfp = pd.Series(np.r_[isn.to_numpy()[1:], False], index=S)
run("prenfp_rth", "Long RTH il giorno prima dell'NFP", rth[prenfp & valid], 1.0, rth, rth_p0)

# ------------------------------------------------------------------ stagionalita'
halloween = pd.Series(S.month.isin([11, 12, 1, 2, 3, 4]), index=S)
run("halloween_winter_cc", "Long close-to-close nei mesi nov-apr (Halloween / sell in May)", cc[halloween & cc_ok], 1.0,
    cc.where(cc_ok), cc_p0)
run("halloween_summer_cc", "Long close-to-close nei mesi mag-ott", cc[~halloween & cc_ok], 1.0, cc.where(cc_ok), cc_p0)
for mo in range(1, 13):
    run(f"month_{mo:02d}_cc", f"Long close-to-close nel mese {mo}", cc[pd.Series(S.month == mo, index=S) & cc_ok], 1.0,
        cc.where(cc_ok), cc_p0)
# Santa Claus: ultimi 5 giorni di dicembre + primi 2 di gennaio
santa = ((pd.Series(S.month == 12, index=S) & (tp >= -4) & (tp <= 0)) |
         (pd.Series(S.month == 1, index=S) & (tp >= 1) & (tp <= 2)))
run("santa_cc", "Long close-to-close nei 7 giorni del rally di Babbo Natale", cc[santa & cc_ok], 1.0, cc.where(cc_ok),
    cc_p0)

# turnaround tuesday: long martedi' RTH se lunedi' RTH < 0
mon_down = pd.Series(np.r_[False, (rth.to_numpy()[:-1] < 0)], index=S) & (dow == 1) & \
    pd.Series(np.r_[False, (dow.to_numpy()[:-1] == 0)], index=S)
run("turnaround_tue", "Long RTH martedi' se il lunedi' RTH ha chiuso in calo", rth[mon_down & valid], 1.0, rth, rth_p0)

# ------------------------------------------------------------------ ora della settimana (RTH, 7 blocchi orari x 5 giorni)
blocks = [(9, 30, 10, 30), (10, 30, 11, 30), (11, 30, 12, 30), (12, 30, 13, 30), (13, 30, 14, 30), (14, 30, 15, 30),
          (15, 30, 16, 0)]
for (h0, m0, h1, m1) in blocks:
    r, p0 = win(hm(h0, m0), hm(h1, m1))
    r = r.where(valid)
    for d in range(5):
        run(f"how_{names[d]}_{h0:02d}{m0:02d}", f"Long {h0}:{m0:02d}-{h1}:{m1:02d} il {names[d]}", r[(dow == d) & valid],
            1.0, r, p0)

pd.to_pickle(RESULTS, core.ROOT / "lab" / "calendar" / "_s01_results.pkl")
