"""Sensibilita' dei candidati in formato trade (misura del controller) a k = 5, 8, 9, 11, 12, 14, 15, 20."""
from lab import core
import lab.multiday.common as C
from lab.multiday import candidates as cand
from lab.multiday.test_candidates import measure

C.REV = 3
bars, daily = core.load("discovery", warmup_days=25)
for k in (5, 8, 9, 11, 12, 14, 15, 20):
    cand.K = k
    for c in cand.CANDIDATES:
        tr, s, y = measure(c, bars, daily)
        C.rec(f"S6_{c['id']}_k{k}", f"vicino di parametro k={k} del candidato {c['id']} (formato trade)", s)
        print(k, c["id"][9:], {x: (round(s[x], 2) if isinstance(s[x], float) else s[x]) for x in ("n", "mean_net", "lo", "p_pos", "years_pos", "beta_adj", "beta_lo", "drop20")})
cand.K = 10
