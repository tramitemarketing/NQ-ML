"""H8 autocorrelazione per ora del giorno. Griglia regolare: ai minuti :00/:15/:30/:45 (chiusura della
barra del minuto precedente), lato = segno del rendimento degli ultimi L minuti (continuazione);
uscita a H=L minuti. Un test per fascia oraria NY (ingresso nell'ora h) e per L in {15, 30}.
Registrato come regolarita' (lordo firmato, bilaterale) e con il netto."""
import numpy as np
from lab.micro.common import Data, evaluate, simulate
from lab import core

D = Data()
n = len(D.c)
idx = np.arange(n)
for Lm in (15, 30):
    prev = np.clip(idx - Lm, 0, None)
    same = (D.scode[prev] == D.scode) & (D.ts - D.ts[prev] == Lm * 60_000_000_000)
    mv = D.c - D.c[prev]
    # segnale alla chiusura della barra con ny_min = t-1 (ingresso all'open del minuto t, t multiplo di 15)
    grid = ((D.m + 1) % 15 == 0) & same & (mv != 0) & D.inph
    for hr in list(range(18, 24)) + list(range(0, 16)):
        entry_hr = ((D.m + 1) // 60) % 24
        sel = grid & (entry_hr == hr)
        if hr == 15:
            sel &= (D.m + 1) <= 960 - Lm
        t = simulate(D, idx[sel], np.sign(mv[sel]).astype(int), Lm, end="session", nonoverlap=True)
        st = evaluate(D, t, f"H8_ac_L{Lm}_h{hr:02d}", f"continuazione del rendimento a {Lm}m, ingresso nell'ora NY {hr}, griglia 15m, uscita {Lm}m",
                      record=True, quiet=True)
        print(f"L{Lm} h{hr:02d} n={st['n']:5d} gross={st['mean_gross']:+.3f} net={st['mean']:+.3f} "
              f"CI[{st['lo']:+.3f};{st['hi']:+.3f}] yrs={st['years_pos']} 1618={st['mean_1618']:+.3f} p2={st['p_two']:.3f}")
