"""Controlli sui due finalisti.
A) regolarita' continuazione (k15, z3, H30, tutte le ore tranne 15:00-18:05): per fascia RTH/ETH,
   quota long e beta, variante sigma_pre, e segno per anno.
B) ON break fade 09:35-12:00 H120: anno per anno, beta, quota long, distribuzione oraria degli
   eventi, finestra 09:35-10:30 contro 10:30-12:00 (sensibilita' temporale), netto 2016-2018."""
import numpy as np
from lab import core
from lab.micro.common import Data, evaluate, simulate, fwd_regularity, drift_table
from lab.micro.h05_levels import level_events, levels

D = Data()
idx = np.arange(len(D.c))
# ---- A
k, z, H = 15, 3, 30
prev = np.clip(idx - k, 0, None)
mv = D.c - D.c[prev]
zz = mv / (D.sig60 * np.sqrt(k))
base = D.inph & (D.scode[prev] == D.scode) & np.isfinite(zz) & (np.abs(zz) >= z)
for tag, bm in (("RTHpart", D.rth & (D.m < 900)), ("ETHpart", (~D.rth) & ((D.m >= 1085) | (D.m < 570)))):
    s = idx[base & bm]
    fwd_regularity(D, s, np.sign(mv[s]).astype(int), H, f"H18A_reg_{tag}", f"regolarita' k15 z3 H30, solo {tag}")
s = idx[base & ((D.m >= 1085) | (D.m < 900))]
t = simulate(D, s, np.sign(mv[s]).astype(int), H, end="session"); t = t[t.in_phase]
tab = drift_table(D, H, "session")
b = (t.side * tab[t.entry_min]).mean()
print("A long share", (t.side > 0).mean(), "beta pts", b, "gross", t.gross_pts.mean(), "gross ex beta", t.gross_pts.mean() - b)
core.record("micro", "H18A_reg_beta", "regolarita' k15 z3 H30: quota long e beta", "discovery",
            {"n": len(t), "long_share": float((t.side > 0).mean()), "beta_pts": float(b), "mean": float(t.gross_pts.mean())})
sp = D.sig60[np.clip(idx - k + 1, 0, None)]
zp = mv / (sp * np.sqrt(k))
s2 = idx[D.inph & (D.scode[prev] == D.scode) & np.isfinite(zp) & (np.abs(zp) >= z) & ((D.m >= 1085) | (D.m < 900))]
fwd_regularity(D, s2, np.sign(mv[s2]).astype(int), H, "H18A_reg_sigpre", "regolarita' k15 z3 H30 con sigma_pre")
# ---- B
L = levels(D); U, Dn = L["ON"]
for lo, hi in ((575, 720), (575, 630), (630, 720)):
    ei, es, ek = level_events(D.h, D.l, D.c, D.m, D.scode, U.astype(float), Dn.astype(float), lo, hi)
    sel = D.inph[ei] & (ek == 1)
    t = simulate(D, ei[sel], es[sel], 120, end="rth")
    st = evaluate(D, t, f"H18B_ONbreak_{lo}-{hi}_H120", f"ON break fade finestra {lo}-{hi}, uscita 120m")
    if (lo, hi) == (575, 720):
        tt = t[t.in_phase]
        print(core.yearly(tt.gross_pts - 0.75, tt.session).round(2).T.to_string())
        print("minuti evento (quantili):", np.percentile(D.m[tt.sig_i], [10, 25, 50, 75, 90]))
        print("motivi uscita", tt.reason.value_counts().to_dict())
