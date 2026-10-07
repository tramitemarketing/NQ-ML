"""Lotto di ipotesi su eventi a orario/struttura:
 H9a  prima barra dopo una pausa di liquidita' (>=5 minuti senza barre, notte): fade/cont del suo corpo.
 H9b  riapertura delle 18:00: movimento 18:00-18:05 in z (sigma60 fine sessione precedente... si usa
      il range medio del giorno prima) -> fade/cont fino a 60m.
 H13  08:30 (dati macro): movimento della barra 08:30 (z vs sigma60) -> cont/fade 15/30/55m (esce alle 09:25).
 H14  10:00: idem sulla barra 10:00.
 H15  14:00 con volume >= 5x stagionale (annuncio, noto alla chiusura della barra): cont/fade.
 H22b 16:00-16:10 dopo la chiusura cash (utili): |mov| >= 3 sigma -> cont/fade fino a 16:59 (H=45).
 H11  sequenze di N barre 1m RTH nello stesso verso (close>open): N=5,7,9.
 H16  nuovo massimo/minimo di sessione RTH dopo >=60 minuti senza nuovi estremi: cont/fade.
 H17  compressione: range degli ultimi 30m <= 0,5 x media dei range 30m del giorno prima... usata
      la regola: range 30m <= 3 x rng60 medio 1m; rottura del range con close -> cont/fade."""
import numpy as np
import pandas as pd
from lab.micro.common import Data, evaluate_pair

D = Data()
n = len(D.c)
idx = np.arange(n)
body = D.c - D.o
z1 = body / D.sig60
base = D.inph & np.isfinite(D.sig60) & (D.sig60 > 0)
MIN = 60_000_000_000

# H9a pause
gap = np.r_[0, np.diff(D.ts)] // MIN
first = D.sess_first == idx
sel = base & (~D.rth) & (gap >= 5) & (~first) & ((D.m >= 1085) | (D.m < 509)) & (body != 0)
for H in (15, 60):
    evaluate_pair(D, idx[sel], -np.sign(body[sel]).astype(int), H, f"H9a_pause5_H{H}",
                  f"prima barra dopo >=5 min senza barre (notte), fade corpo, uscita {H}m")
sel2 = sel & (np.abs(z1) >= 2)
for H in (15, 60):
    evaluate_pair(D, idx[sel2], -np.sign(body[sel2]).astype(int), H, f"H9a_pause5_z2_H{H}",
                  f"prima barra dopo pausa >=5 min con |corpo|>=2 sigma60, fade corpo, uscita {H}m")

# H9b riapertura 18:00: segnale alla chiusura della barra 18:04, movimento dall'open 18:00
def at_minute(mm):
    a = np.full(D.scode.max() + 1, -1, np.int64)
    w = np.nonzero(D.m == mm)[0]
    a[D.scode[w]] = w
    return a

o18 = at_minute(1080); c1804 = at_minute(1084)
ok = (o18 >= 0) & (c1804 >= 0)
s_i = c1804[ok]; mv = D.c[s_i] - D.o[o18[ok]]
# confronto con la chiusura della sessione precedente (16:59)
prev_last = np.r_[-1, np.nonzero(np.diff(D.scode))[0]]
pc = np.array([D.c[prev_last[s]] if prev_last[s] >= 0 else np.nan for s in D.scode[s_i]])
gapmv = D.c[s_i] - pc
good = D.inph[s_i] & np.isfinite(gapmv) & (gapmv != 0)
for H in (15, 60):
    evaluate_pair(D, s_i[good], -np.sign(gapmv[good]).astype(int), H, f"H9b_reopen_H{H}",
                  f"riapertura 18:00: segno di (close 18:04 - close 16:59), fade, uscita {H}m")

# H13/H14/H15: barre macro
for mm, tag, Hs in ((510, "0830", (15, 30, 55)), (600, "1000", (15, 30, 60)), (840, "1400", (15, 30, 60))):
    w = idx[(D.m == mm) & base & (body != 0)]
    vr = D.v[w] / D.vseas[w]
    for thr in (2, 4):
        cond = np.abs(z1[w]) >= thr
        if tag == "1400":
            cond &= vr >= 5
        s = w[cond]
        for H in Hs:
            evaluate_pair(D, s, -np.sign(body[s]).astype(int), H, f"H13_{tag}_z{thr}_H{H}",
                          f"barra {tag} con |corpo|>={thr} sigma60{' e vrel>=5' if tag=='1400' else ''}, fade corpo, uscita {H}m")

# H22b post-chiusura cash 16:00-16:10
c1609 = at_minute(969); o16 = at_minute(960)
ok = (c1609 >= 0) & (o16 >= 0)
s_i = c1609[ok]; mv = D.c[s_i] - D.o[o16[ok]]
zz = mv / (D.sig60[s_i] * np.sqrt(10))
for thr in (2, 3):
    g = D.inph[s_i] & (np.abs(zz) >= thr)
    evaluate_pair(D, s_i[g], -np.sign(mv[g]).astype(int), 45, f"H22b_post16_z{thr}_H45",
                  f"16:00-16:10 |mov|>={thr} sigma60*sqrt10, fade, uscita 45m (entro 16:59)")

# H11 sequenze
up = np.sign(body)
rth_b = D.rth & (D.m >= 575) & (D.m < 900)
for N in (5, 7, 9):
    run = np.ones(n, bool)
    for q in range(N):
        sh = np.r_[np.zeros(q), up[:n - q]] if q else up
        run &= (sh == up) & (up != 0)
    # stesso verso nelle ultime N barre, ed e' la prima volta (barra i-N non nello stesso verso)
    prevN = np.r_[np.zeros(N), up[:n - N]]
    s = idx[run & (prevN != up) & rth_b & base]
    for H in (15, 60):
        evaluate_pair(D, s, -up[s].astype(int), H, f"H11_run{N}_H{H}",
                      f"{N} barre 1m RTH consecutive nello stesso verso (corpo), fade, uscita {H}m", end="rth")

# H16 nuovo estremo di sessione RTH dopo >=60 minuti
bars = pd.DataFrame({"s": D.scode, "h": D.h, "l": D.l, "rth": D.rth, "m": D.m})
r = bars[bars.rth].copy()
r["hmax_prev"] = r.groupby("s")["h"].cummax().groupby(r["s"]).shift(1)
r["lmin_prev"] = r.groupby("s")["l"].cummin().groupby(r["s"]).shift(1)
r["i"] = r.index.to_numpy() if False else np.nonzero(D.rth)[0]
r["newh"] = r["h"] > r["hmax_prev"]
r["newl"] = r["l"] < r["lmin_prev"]
for col in ("newh", "newl"):
    last = r["i"].where(r[col]).groupby(r["s"]).ffill().groupby(r["s"]).shift(1)
    r["age_" + col] = r["i"] - last
for gapm in (60, 120):
    eh = r[(r.newh) & (r.age_newh >= gapm) & (r.m >= 575) & (r.m < 900) & (~r.newl)]["i"].to_numpy()
    el = r[(r.newl) & (r.age_newl >= gapm) & (r.m >= 575) & (r.m < 900) & (~r.newh)]["i"].to_numpy()
    s = np.r_[eh, el]; side = np.r_[-np.ones(len(eh), int), np.ones(len(el), int)]
    m_ = base[s]
    for H in (15, 60):
        evaluate_pair(D, s[m_], side[m_], H, f"H16_newext_age{gapm}_H{H}",
                      f"nuovo max/min di sessione RTH dopo >={gapm} barre senza, fade, uscita {H}m", end="rth")

# H17 compressione e rottura
hh30 = pd.Series(D.h).rolling(30).max().shift(1).to_numpy()
ll30 = pd.Series(D.l).rolling(30).min().shift(1).to_numpy()
same30 = D.scode[np.clip(idx - 30, 0, None)] == D.scode
rng30 = hh30 - ll30
comp = same30 & (rng30 <= 3 * D.rng60 * 1.0) & base & rth_b
for kname, fac in (("c3", 3.0), ("c5", 5.0)):
    comp = same30 & (rng30 <= fac * D.rng60) & base & rth_b
    bu = comp & (D.c > hh30); bd = comp & (D.c < ll30)
    s = np.r_[idx[bu], idx[bd]]; side = np.r_[-np.ones(bu.sum(), int), np.ones(bd.sum(), int)]
    for H in (15, 60):
        evaluate_pair(D, s, side, H, f"H17_compress_{kname}_H{H}",
                      f"range 30m <= {fac} x range medio 1m (60), close oltre il range 30m, fade, uscita {H}m", end="rth")
