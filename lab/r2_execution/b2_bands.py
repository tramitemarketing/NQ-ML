"""B2 - fornitura di liquidita' a fasce di volatilita' prevista (OCO simmetrico).
Ogni 15 minuti (chiusura delle barre :14/:29/:44/:59) si mettono un limite d'acquisto a c - k*sW e uno
di vendita a c + k*sW, sW = sig60*sqrt(15) (movimento atteso a 15 minuti); attesa N = 15 minuti; il
primo eseguito vince. Uscite dichiarate prima: (a) tempo 30 m; (b) target 1*sW a limite, tempo 30 m;
(c) target 1*sW, tempo 60 m. k in {1, 2, 3}. Finestre: apertura 09:44-10:30, mezzogiorno 12:29-15:00,
RTH 09:44-15:00, notte 20:00-08:00. Nessuno stop. Lato AGG di confronto = stesso lato del fill."""
import numpy as np

from lab.r2_execution.common import load, compare, summarize, xi_after

D, B = load()
m = D.m
ok = (m % 15 == 14) & np.isfinite(D.sig60) & (D.sig60 > 0)
WIN = {"open": (584, 630), "mid": (749, 900), "rth": (584, 900), "night": (1200, 480)}
for wn, (lo, hi) in WIN.items():
    w = (m >= lo) & (m < hi) if lo < hi else ((m >= lo) | (m < hi))
    s = np.nonzero(ok & w)[0]
    sW = D.sig60[s] * np.sqrt(15)
    for k in (1, 2, 3):
        for ex, (H, tg) in {"t30": (30, None), "tg1t30": (30, 1.0), "tg1t60": (60, 1.0)}.items():
            xi = xi_after(D, s, H)
            t = compare(D, B, s, 1, xi, k * sW, 15, tgt=None if tg is None else tg * sW, oco=True)
            summarize(t, f"B2_{wn}_k{k}_{ex}", f"OCO fasce k={k}*sig60*sqrt15, finestra {wn}, uscita {ex}")
