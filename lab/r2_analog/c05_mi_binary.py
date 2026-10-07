"""C05: l'eccesso di informazione mutua di C01-P4 e' direzione o solo ampiezza (volatility clustering)?
Dichiarato prima: alfabeto binario (sopra/sotto la mediana causale dello slot, 250 sessioni) -> solo direzione;
alfabeto binario |z| sopra/sotto la mediana -> solo ampiezza. L = 1..3, 1m e 5m, placebo rimescolato nel giorno (50)."""
import numpy as np

from lab.r2_analog import common as C

bars, daily, M = C.setup_discovery()
ok = M["ok"] & M["in_phase"]; rng = np.random.default_rng(11)
O1, C1 = M["O"], M["C"]
r1 = np.diff(np.log(np.column_stack([O1[:, :1], C1])), axis=1)


def binar(z):
    s = np.full(z.shape, -1, int); idx = np.where(M["ok"])[0]
    for j, i in enumerate(idx):
        if j < 250:
            continue
        med = np.nanmedian(z[idx[j - 250:j]], axis=0)
        s[i] = (z[i] > med).astype(int)
    return s


def mi(S, L):
    ctx = np.zeros((S.shape[0], S.shape[1] - L), int)
    for i in range(L):
        ctx = ctx * 2 + S[:, i:S.shape[1] - L + i]
    nxt = S[:, L:]
    j = np.bincount((ctx * 2 + nxt).ravel(), minlength=2 ** (L + 1)).reshape(2 ** L, 2).astype(float)
    p = j / j.sum(); pc = p.sum(1, keepdims=True); pn = p.sum(0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(np.nansum(p * np.log2(p / (pc * pn))))


for tf, z in (("1m", r1 / (M["s5"][:, None] / np.sqrt(5))), ("5m", M["r5"] / M["s5"][:, None])):
    for kind, zz in (("dir", z), ("amp", np.abs(z))):
        S = binar(zz); g = ok & (S[:, 0] >= 0); R = S[g]
        for L in (1, 2, 3):
            real = mi(R, L); pl = [mi(rng.permuted(R, axis=1), L) for _ in range(50)]
            yrs = {}
            for y in sorted(set(M["year"][g])):
                Ry = S[g & (M["year"] == y)]
                yrs[int(y)] = round((mi(Ry, L) - np.mean([mi(rng.permuted(Ry, axis=1), L) for _ in range(10)])) * 1000, 3)
            st = {"n": int(g.sum()), "mi_bits": real, "plac_mean": float(np.mean(pl)), "plac_p99": float(np.percentile(pl, 99)),
                  "excess_mbits": (real - float(np.mean(pl))) * 1000, "yearly_excess_mbits": yrs}
            print(tf, kind, L, round(st["excess_mbits"], 3), yrs)
            C.rec(f"c05_mi_{tf}_{kind}_L{L}", f"informazione mutua binaria ({kind}) {tf}, ultimi {L} -> successivo, vs placebo", st)
