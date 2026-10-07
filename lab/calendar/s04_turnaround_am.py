"""Controlli sul turnaround Tuesday mattutino (variante emersa in s03: post hoc, dichiarato)."""
from lab.calendar.ctx import *   # noqa: F401,F403

rth_prev = pd.Series(np.r_[np.nan, rth.to_numpy()[:-1]], index=S)
prev_dow = pd.Series(np.r_[-1, dow.to_numpy()[:-1]], index=S)
r12, p12 = win(RTH_OPEN, hm(12, 0))
r12 = r12.where(valid)
base = r12
tue = (dow == 1) & (prev_dow == 0) & valid
m = tue & (rth_prev < 0)
st = run("turnaround_tue_am_reread", "Rilettura turnaround_tue_am per anno", r12[m], 1.0, base, p12)
print("   anni:", st["yearly"])
run("turnaround_tue_am_mirror", "Specchio: SHORT 9:30-12:00 martedi' se lunedi' RTH in rialzo", -r12[tue & (rth_prev > 0)],
    -1.0, base, p12)
run("turnaround_tue_am_vs_tue", "Long 9:30-12:00 martedi' dopo lunedi' in calo, eccesso contro tutti i martedi'",
    r12[m], 1.0, r12.where(tue), p12)
for d, nm in [(2, "mer"), (3, "gio"), (4, "ven")]:
    md = (dow == d) & (prev_dow == d - 1) & valid & (rth_prev < 0)
    run(f"placebo_am_after_down_{nm}", f"Placebo: long 9:30-12:00 {nm} se il giorno prima RTH in calo", r12[md], 1.0, base,
        p12)
mmon = (dow == 0) & (prev_dow == 4) & valid & (rth_prev < 0)
run("placebo_am_after_down_lun", "Placebo: long 9:30-12:00 lunedi' se venerdi' RTH in calo", r12[mmon], 1.0, base, p12)
for (h0, m0, h1, m1) in [(9, 30, 10, 30), (9, 30, 11, 0), (9, 30, 13, 0)]:
    r, p0 = win(hm(h0, m0), hm(h1, m1))
    run(f"turnaround_tue_{h0:02d}{m0:02d}_{h1:02d}{m1:02d}", f"Long {h0}:{m0:02d}-{h1}:{m1:02d} martedi' se lunedi' RTH in calo",
        r[m], 1.0, r.where(valid), p0)
