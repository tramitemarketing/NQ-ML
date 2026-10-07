"""Il placebo sfasato di 20 giorni (C3) NON e' nullo (+4,0 bp/g [0,05; 8,1]). Prima di andare avanti:
 1) contrarian con il segnale sfasato di 30, 60, 120 giorni: il 'reversal' e' un fenomeno a finestra corta
    o un generico "dopo un calo il mercato sale" tipico di un campione tutto rialzista?
 2) placebo a spostamento circolare: il segnale k10 spostato di un offset casuale (>= 60 giorni) sulla
    serie dei rendimenti. Conserva persistenza e sbilanciamento del segnale, rompe l'allineamento.
    Distribuzione dell'eccesso su 1000 spostamenti -> p empirico del valore osservato.
 3) stesso esame per la sola gamba overnight (C4_ononly)."""
import numpy as np
import pandas as pd

import lab.multiday.common as C
from lab.multiday.common import load_daily, position_eval, boot, years_pos, rec

C.REV = 3
d, bars = load_daily()
mu = d["r"].mean()
c = d["rth_close"]
START = d.index[260]
r_next = d["r"].shift(-1)
s10 = -np.sign(c - c.shift(10))
on = d["rth_open"] - d["rth_close"].shift(1)
son = -np.sign(on.rolling(10).sum())

for L in (30, 60, 120):
    pe = position_eval(d, s10.shift(L), mu)
    pe = pe[pe.index >= START]
    st = boot(pe["exc"].to_numpy() * 1e4, pe.index)
    rec(f"P1_contra_k10_lag{L}", f"placebo: contrarian k10 sfasato di {L} giorni", dict(st, unit="bp/giorno eccesso", years=years_pos(pe["exc"], pe.index)))
    print(f"lag {L}: {st['mean']:.2f} [{st['lo']:.2f}, {st['hi']:.2f}] {years_pos(pe['exc'], pe.index)}")


def circ(sig, name, n=1000, seed=1):
    ok = (d.index >= START) & r_next.notna().to_numpy() & sig.notna().to_numpy()
    x = sig.to_numpy()[ok]; y = (r_next - mu).to_numpy()[ok]
    obs = np.mean(x * y) * 1e4
    rng = np.random.default_rng(seed)
    offs = rng.integers(60, len(x) - 60, n)
    dist = np.array([np.mean(np.roll(x, o) * y) * 1e4 for o in offs])
    p = float((dist >= obs).mean())
    rec(f"P2_circ_{name}", f"placebo a spostamento circolare (1000 offset >= 60g) per {name}",
        dict(n=int(ok.sum()), mean=float(obs), p_pos=p, placebo_mean=float(dist.mean()), placebo_p95=float(np.percentile(dist, 95))))
    print(f"{name}: osservato {obs:.2f} bp/g, placebo media {dist.mean():.2f}, p95 {np.percentile(dist,95):.2f}, p empirico {p:.3f}")


circ(s10, "contra_k10")
circ(son, "contra_k10_overnight")
