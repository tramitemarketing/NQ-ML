"""H3 picchi di volume: climax (volume alto + barra grande) vs assorbimento (volume alto + barra piccola).
vrel = volume / mediana del volume allo stesso minuto NY nelle 20 sessioni precedenti (causale).
Climax: fade = contro il corpo della barra. Assorbimento: fade = contro il movimento dei 15 minuti
precedenti (chi spingeva e' stato assorbito). H12 rapporto volume/range: barre 'illiquide'
(range grande con volume basso) -> fade del corpo."""
import numpy as np
from lab.micro.common import Data, evaluate_pair

D = Data()
n = len(D.c)
idx = np.arange(n)
vrel = D.v / D.vseas
body = D.c - D.o
p15 = np.clip(idx - 15, 0, None)
m15 = D.c - D.c[p15]
same15 = D.scode[p15] == D.scode
base = D.inph & np.isfinite(vrel) & (D.vseas > 0) & (D.sig60 > 0)
bands = {"RTH": (D.rth & (D.m >= 575) & (D.m < 900), "rth"),
         "ETH": ((~D.rth) & ((D.m >= 1085) | (D.m < 509)), "session")}
for band, (bm, end) in bands.items():
    for vt in (3, 5, 10):
        big = base & bm & (vrel >= vt)
        # climax
        sel = big & (np.abs(body) >= 2 * D.sig60)
        for H in (15, 30, 60):
            evaluate_pair(D, idx[sel], -np.sign(body[sel]).astype(int), H, f"H3_climax_{band}_v{vt}_H{H}",
                          f"climax: vrel>={vt}, |corpo|>=2 sigma60, {band}, fade corpo, uscita {H}m", end=end)
        # assorbimento
        sel = big & (np.abs(body) <= 0.5 * D.sig60) & same15 & (np.abs(m15) >= 2 * D.sig60)
        for H in (15, 30, 60):
            evaluate_pair(D, idx[sel], -np.sign(m15[sel]).astype(int), H, f"H3_absorb_{band}_v{vt}_H{H}",
                          f"assorbimento: vrel>={vt}, |corpo|<=0.5 sigma60, |mov 15m|>=2 sigma60, {band}, fade 15m, uscita {H}m", end=end)
# H12: barre illiquide: range >= 3 x range medio 60 con vrel <= 1.5
for band, (bm, end) in bands.items():
    sel = base & bm & (D.rng >= 3 * D.rng60) & (vrel <= 1.5) & (body != 0)
    for H in (15, 30, 60):
        evaluate_pair(D, idx[sel], -np.sign(body[sel]).astype(int), H, f"H12_illiquid_{band}_H{H}",
                      f"barra illiquida: range>=3x rng60 e vrel<=1.5, {band}, fade corpo, uscita {H}m", end=end)
    sel = base & bm & (D.rng >= 3 * D.rng60) & (vrel >= 4) & (body != 0)
    for H in (15, 30, 60):
        evaluate_pair(D, idx[sel], -np.sign(body[sel]).astype(int), H, f"H12_liquid_{band}_H{H}",
                      f"barra grande e liquida: range>=3x rng60 e vrel>=4, {band}, fade corpo, uscita {H}m", end=end)
