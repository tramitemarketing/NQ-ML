"""Approfondimenti sulle idee piu' promettenti della scansione s01 + qualche ipotesi nuova.
Ogni variante guardata viene registrata. Uso: python -m lab.calendar.s02_deep
"""
from lab.calendar.ctx import *   # noqa: F401,F403
from lab.calendar.common import fomc_dates, fomc_time_ny, nfp_dates

fri = (dow == 4) & valid
rth_fri = rth.where(fri)
opexF = pd.Series(S.isin(tf_adj), index=S) & valid
quadF = pd.Series(S.isin(quad), index=S) & valid

# =============================================================== 1. venerdi' di scadenza (lato short)
run("opex_fri_short_rth", "SHORT RTH 9:30-16:00 il venerdi' di scadenza mensile (base beta = tutti i giorni RTH)",
    -rth[opexF], -1.0, rth, rth_p0)
run("opex_fri_short_vs_fri", "SHORT RTH venerdi' di scadenza, eccesso contro tutti i venerdi'", -rth[opexF], -1.0,
    rth_fri, rth_p0)
run("opex_fri_short_nonquad", "SHORT RTH venerdi' di scadenza NON trimestrale", -rth[opexF & ~quadF], -1.0, rth,
    rth_p0)
am, am_p0 = win(RTH_OPEN, hm(12, 0))
pm, pm_p0 = win(hm(12, 0), RTH_CLOSE)
run("opex_fri_short_am", "SHORT 9:30-12:00 venerdi' di scadenza", -am[opexF], -1.0, am.where(valid), am_p0)
run("opex_fri_short_pm", "SHORT 12:00-16:00 venerdi' di scadenza", -pm[opexF], -1.0, pm.where(valid), pm_p0)
thu_before = pd.Series(np.r_[opexF.to_numpy()[1:], False], index=S) & valid
run("opex_thu_short_rth", "Placebo: SHORT RTH il giovedi' prima della scadenza", -rth[thu_before], -1.0, rth, rth_p0)
run("opex_fri_ovn_long", "Long overnight 16:00 gio -> 9:30 ven di scadenza (settlement SOQ all'apertura)",
    ovn[opexF], 1.0, ovn, cc_p0)
fri_m1 = pd.Series(S.isin(tf_adj - pd.Timedelta(days=7)), index=S) & fri
fri_p1 = pd.Series(S.isin(tf_adj + pd.Timedelta(days=7)), index=S) & fri
run("fri_before_opex_short", "Placebo: SHORT RTH il venerdi' una settimana PRIMA della scadenza", -rth[fri_m1], -1.0,
    rth, rth_p0)
run("fri_after_opex_short", "Placebo: SHORT RTH il venerdi' una settimana DOPO la scadenza", -rth[fri_p1], -1.0, rth,
    rth_p0)

# =============================================================== 2. ribilanciamento di fine mese (contrarian)
def rebal(entry_pos, n, mask_extra=None, thr=None):
    ent = (tp == entry_pos)
    if mask_extra is not None:
        ent = ent & mask_extra
    g, p0 = hold(ent, n)
    m = (P16 - prev_me_close).reindex(g.index)
    if thr is not None:
        keep = (m.abs() / p0) > thr
        g, p0, m = g[keep], p0[keep], m[keep]
    sd = -np.sign(m)
    return g * sd, sd, p0


for (a, n) in [(-4, 4), (-2, 2), (-3, 4), (-4, 3), (-4, 5)]:
    g, sd, p0 = rebal(a, n)
    run(f"me_rebal_{a}_{n}", f"Ribilanciamento: close giorno {a} -> {n} giorni di borsa dopo, lato = -segno(MTD)",
        g, sd, base_hold(n), p0)
g, sd, p0 = rebal(-3, 3, thr=0.02)
run("me_rebal_3d_big", "Ribilanciamento 3d solo se |MTD| > 2 %", g, sd, base_hold(3), p0)
g, sd, p0 = rebal(-3, 3, mask_extra=pd.Series(S.month.isin([3, 6, 9, 12]), index=S))
run("me_rebal_3d_qe", "Ribilanciamento 3d solo fine trimestre", g, sd, base_hold(3), p0)
g, sd, p0 = rebal(-3, 3)
run("me_rebal_3d_longonly", "Ribilanciamento 3d, solo i trade long (mese a data negativo)", g[sd > 0], sd[sd > 0],
    base_hold(3), p0)
run("me_rebal_3d_shortonly", "Ribilanciamento 3d, solo i trade short (mese a data positivo)", g[sd < 0], sd[sd < 0],
    base_hold(3), p0)
# placebo: stessa regola contrarian a meta' mese (giorno 10 dal primo del mese, MTD da fine mese scorso)
for (pos, lab) in [(8, "g8"), (11, "g11"), (14, "g14")]:
    ent = (tp == pos)
    gg, p0 = hold(ent, 3)
    m = (P16 - prev_me_close).reindex(gg.index)
    sd = -np.sign(m)
    run(f"placebo_rebal_{lab}", f"Placebo contrarian 3d a meta' mese: ingresso close giorno {pos} del mese, lato = "
        "-segno(rendimento dal fine mese scorso)", gg * sd, sd, base_hold(3), p0)
# placebo generico: contrarian 3d su tutti i giorni, lato = -segno(rendimento degli ultimi 15 giorni di borsa)
p = P16.to_numpy()
allg, allp0 = hold(pd.Series(is_td, index=S), 3)
lag15 = pd.Series(np.r_[np.full(15, np.nan), p[15:] - p[:-15]], index=S).reindex(allg.index)
sd = -np.sign(lag15)
run("placebo_rev15_3d_all", "Placebo: contrarian 3d su OGNI giorno, lato = -segno(ultimi 15 giorni)", allg * sd, sd,
    base_hold(3), allp0)

# =============================================================== 3. turnaround Tuesday
mon_prev = pd.Series(np.r_[False, (dow.to_numpy()[:-1] == 0)], index=S)
rth_prev = pd.Series(np.r_[np.nan, rth.to_numpy()[:-1]], index=S)
tue = (dow == 1) & mon_prev & valid
run("tue_after_up_mon_short", "Specchio: SHORT RTH martedi' se lunedi' RTH in rialzo", -rth[tue & (rth_prev > 0)], -1.0,
    rth, rth_p0)
anyday = valid & (dow != 1) & rth_prev.notna()
run("placebo_rev_any_day", "Placebo: long RTH in ogni giorno (non martedi') dopo un RTH in calo",
    rth[anyday & (rth_prev < 0)], 1.0, rth, rth_p0)
cc_prev = pd.Series(np.r_[np.nan, cc.to_numpy()[:-1]], index=S)
run("turnaround_tue_cc", "Long RTH martedi' se il close-to-close del lunedi' (ven 16:00 -> lun 16:00) e' negativo",
    rth[tue & (cc_prev < 0)], 1.0, rth, rth_p0)
run("turnaround_tue_ovn", "Long 16:00 lun -> 16:00 mar (close-to-close) se lunedi' RTH in calo", cc[tue & (rth_prev < 0)],
    1.0, cc.where(cc_ok), cc_p0)

# =============================================================== 4. ultima mezz'ora
l30, l30_p0 = win(hm(15, 30), RTH_CLOSE)
l30 = l30.where(valid)
fomc_day = pd.Series(S.isin(fomc_dates()), index=S)
run("last30_short_all", "SHORT 15:30-16:00 tutti i giorni", -l30[valid], -1.0, l30, l30_p0)
run("last30_short_wed_nofomc", "SHORT 15:30-16:00 il mercoledi' escluso FOMC", -l30[(dow == 2) & valid & ~fomc_day], -1.0,
    l30, l30_p0)
run("last30_short_wedthu", "SHORT 15:30-16:00 mercoledi' e giovedi'", -l30[dow.isin([2, 3]) & valid], -1.0, l30, l30_p0)

# =============================================================== 5. pre-festivo e fine trimestre
pre_prev = pd.Series(np.r_[pre.to_numpy()[1:], False], index=S)          # il giorno prima del pre-festivo
pre_prev2 = pd.Series(np.r_[pre.to_numpy()[2:], False, False], index=S)
g, p0 = hold(pre_prev, 1)
run("preholiday_1d_closeprev", "Long close del giorno prima del pre-festivo -> close del pre-festivo", g, 1.0, base_hold(1),
    p0)
g, p0 = hold(pre_prev2, 3)
run("preholiday_3d", "Long close di 2 giorni prima del pre-festivo -> close del post-festivo", g, 1.0, base_hold(3), p0)
g, p0 = hold(pre, 1)
run("holiday_bridge_1d", "Long close del pre-festivo -> close del post-festivo (attraversa la festa)", g, 1.0,
    base_hold(1), p0)
qe = last & pd.Series(S.month.isin([3, 6, 9, 12]), index=S) & valid
run("qe_lasthour_short", "SHORT 15:00-16:00 ultimo giorno del trimestre", -lh[qe], -1.0, lh, lh_p0)
run("me_lasthour_short_nonqe", "SHORT 15:00-16:00 ultimo giorno del mese NON di trimestre", -lh[last & valid & ~qe], -1.0,
    lh, lh_p0)

# =============================================================== 6. ipotesi nuove
# VIX expiration: mercoledi' 30 giorni prima del terzo venerdi' del mese successivo
vix = []
for y in range(2010, 2020):
    for mo in range(1, 13):
        ny, nm = (y, mo + 1) if mo < 12 else (y + 1, 1)
        d = pd.Timestamp(core._third_friday(ny, nm)) - pd.Timedelta(days=30)
        if d not in set(tc):
            d = d - pd.Timedelta(days=1)
        vix.append(d)
vixd = pd.Series(S.isin(vix), index=S) & valid
run("vixexp_wed_rth", "Long RTH il mercoledi' di scadenza VIX", rth[vixd], 1.0, rth, rth_p0)
# giorno prima del FOMC
fd = fomc_dates()
prefomc = pd.Series(np.r_[S[1:].isin(fd), False], index=S) & valid
run("fomc_eve_rth", "Long RTH il giorno prima del FOMC", rth[prefomc], 1.0, rth, rth_p0)
# verbali FOMC: 3 settimane dopo, 14:00 (quando cadono di mercoledi')
mins = pd.DatetimeIndex([d + pd.Timedelta(days=21) for d in fd])
mind = pd.Series(S.isin(mins), index=S) & valid & (dow == 2)
p14 = px.price(hm(14, 0)); p1415 = px.price(hm(14, 15))
sdm = pd.Series(np.sign(p1415 - p14), index=S)
gm = pd.Series(P16.to_numpy() - p1415, index=S) * sdm
run("fomc_minutes_follow", "Verbali FOMC: lato = segno 14:00-14:15, tenuto 14:15-16:00", gm[mind], sdm[mind], None, None)
# primo giorno di borsa dell'anno e ultima settimana dell'anno gia' in santa/month; aggiungo "settimana 1 del mese"
# (giorni 1-5) contro il resto
first_week = (tp >= 1) & (tp <= 5) & cc_ok
run("month_firstweek_cc", "Long close-to-close nei primi 5 giorni di borsa del mese", cc[first_week], 1.0,
    cc.where(cc_ok), cc_p0)
midm = (tp >= 9) & (tp <= 15) & cc_ok
run("month_mid_cc", "Long close-to-close nei giorni 9-15 del mese (debolezza di meta' mese)", cc[midm], 1.0,
    cc.where(cc_ok), cc_p0)
# overnight del lunedi' (weekend) solo domenica sera 18:00 -> 9:30: diverso da 16:00 ven -> 9:30
g18, p18 = win(0, RTH_OPEN)
run("sunday_eve_to_open", "Long dall'apertura Globex (18:00 dom) -> 9:30 lunedi'", g18[(dow == 0) & valid], 1.0,
    g18.where(valid), p18)

pd.to_pickle(RESULTS, core.ROOT / "lab" / "calendar" / "_s02_results.pkl")
