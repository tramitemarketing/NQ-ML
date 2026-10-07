"""Sensibilita' e tabelle per anno dei 4 finalisti (opex friday short, ribilanciamento fine mese,
turnaround Tuesday, vigilia FOMC). Ogni variante guardata e' registrata."""
from lab.calendar.ctx import *   # noqa: F401,F403
from lab.calendar.common import fomc_dates

opexF = pd.Series(S.isin(tf_adj), index=S) & valid
quadF = pd.Series(S.isin(quad), index=S) & valid


def show_year(tid):
    st = RESULTS.get(tid)
    if st:
        print("   anni:", st["yearly"])


# ---------------- opex friday short: finestre alternative e soglie di tempo
for (h0, m0, h1, m1) in [(9, 30, 15, 0), (10, 0, 16, 0), (9, 30, 15, 30)]:
    r, p0 = win(hm(h0, m0), hm(h1, m1))
    tid = f"opex_fri_short_{h0:02d}{m0:02d}_{h1:02d}{m1:02d}"
    run(tid, f"SHORT {h0}:{m0:02d}-{h1}:{m1:02d} venerdi' di scadenza", -r[opexF], -1.0, r.where(valid), p0)
show_year("opex_fri_short_0930_1500")
# ricalcolo del principale per stampare la tabella per anno (stesso test di s02, registrato come rilettura)
run("opex_fri_short_rth_reread", "Rilettura di opex_fri_short_rth per tabella annua (stesso test)", -rth[opexF], -1.0,
    rth, rth_p0)
show_year("opex_fri_short_rth_reread")
run("quad_fri_short_rth", "SHORT RTH solo venerdi' di quadrupla scadenza", -rth[quadF], -1.0, rth, rth_p0)
show_year("quad_fri_short_rth")

# ---------------- ribilanciamento: tabelle per anno e soglie
def rebal(entry_pos, n, thr=None):
    g, p0 = hold(tp == entry_pos, n)
    m = (P16 - prev_me_close).reindex(g.index)
    if thr is not None:
        keep = (m.abs() / p0) > thr
        g, p0, m = g[keep], p0[keep], m[keep]
    sd = -np.sign(m)
    return g * sd, sd, p0


g, sd, p0 = rebal(-3, 3)
run("me_rebal_3d_reread", "Rilettura di me_rebal_3d per tabella annua (stesso test)", g, sd, base_hold(3), p0)
show_year("me_rebal_3d_reread")
for thr in [0.01, 0.03]:
    g, sd, p0 = rebal(-3, 3, thr)
    run(f"me_rebal_3d_thr{int(thr*100)}", f"Ribilanciamento 3d solo se |MTD| > {thr:.0%}", g, sd, base_hold(3), p0)
# MTD misurato in % invece che in punti non cambia il segno: nessun test. Uscita alle 15:00 dell'ultimo giorno
# (prima del close dove il flusso di ribilanciamento dovrebbe gia' essere in corso)
ent = (tp == -3)
gi, p0 = hold(ent, 3)
idx_exit = np.array([fwd_td(S.get_loc(d), 3) for d in gi.index])
p15a = px.price(hm(15, 0))
g15 = pd.Series(p15a[idx_exit] - p0.to_numpy(), index=gi.index)
m = (P16 - prev_me_close).reindex(gi.index)
sd = -np.sign(m)
run("me_rebal_3d_exit15", "Ribilanciamento: close giorno -3 -> 15:00 ultimo giorno, lato -segno(MTD)", g15 * sd, sd,
    base_hold(3), p0)

# ---------------- turnaround Tuesday
mon_prev = pd.Series(np.r_[False, (dow.to_numpy()[:-1] == 0)], index=S)
rth_prev = pd.Series(np.r_[np.nan, rth.to_numpy()[:-1]], index=S)
rthp0_prev = pd.Series(np.r_[np.nan, rth_p0.to_numpy()[:-1]], index=S)
tue = (dow == 1) & mon_prev & valid
m = tue & (rth_prev < 0)
run("turnaround_tue_reread", "Rilettura turnaround_tue per tabella annua (stesso test)", rth[m], 1.0, rth, rth_p0)
show_year("turnaround_tue_reread")
for thr in [0.005, 0.01]:
    mm = tue & (rth_prev / rthp0_prev < -thr)
    run(f"turnaround_tue_thr{int(thr*1000)}", f"Long RTH martedi' se lunedi' RTH < -{thr:.1%}", rth[mm], 1.0, rth, rth_p0)
r12, p12 = win(RTH_OPEN, hm(12, 0))
run("turnaround_tue_am", "Long 9:30-12:00 martedi' se lunedi' RTH in calo", r12[m], 1.0, r12.where(valid), p12)
# stesso segnale il mercoledi' dopo un martedi' in calo (il 'turnaround' e' solo del martedi'?)
tue_prev = pd.Series(np.r_[False, (dow.to_numpy()[:-1] == 1)], index=S)
wed = (dow == 2) & tue_prev & valid & (rth_prev < 0)
run("placebo_turnaround_wed", "Placebo: long RTH mercoledi' se martedi' RTH in calo", rth[wed], 1.0, rth, rth_p0)

# ---------------- vigilia FOMC
fd = fomc_dates()
prefomc = pd.Series(np.r_[S[1:].isin(fd), False], index=S) & valid
run("fomc_eve_rth_reread", "Rilettura fomc_eve_rth per tabella annua (stesso test)", rth[prefomc], 1.0, rth, rth_p0)
show_year("fomc_eve_rth_reread")
tue_all = (dow == 1) & valid
run("fomc_eve_vs_tue", "Long RTH vigilia FOMC, beta/eccesso contro tutti i martedi'", rth[prefomc], 1.0, rth.where(tue_all),
    rth_p0)
r_a, p_a = win(hm(14, 0), RTH_CLOSE)
run("fomc_eve_1400_1600", "Long 14:00-16:00 vigilia FOMC", r_a[prefomc], 1.0, r_a.where(valid), p_a)
g2, p02 = hold(pd.Series(np.r_[S[2:].isin(fd), False, False], index=S), 1)
run("fomc_eve2_cc", "Long close-to-close due giorni prima del FOMC -> close vigilia (Lucca-Moench esteso)", g2, 1.0,
    base_hold(1), p02)
