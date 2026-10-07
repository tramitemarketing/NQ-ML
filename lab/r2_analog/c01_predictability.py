"""C01: la prevedibilita' come quantita' che varia nel tempo (dichiarato prima di guardare).

Per ogni sessione valida d:
  rho_d(a,b) = sum r_k r_{k+1} / sum r_k^2 sui rendimenti 5m (grezzi) della fascia [a,b) (autocorrelazione lag 1).
  vr_d(a,b)  = sum R30^2 / sum r5^2 - 1 (variance ratio 30m/5m, blocchi di 6 barre) nella fascia.
  lz_d       = complessita' di Lempel-Ziv (LZ76) della stringa dei segni dei rendimenti 1m della mattina
               09:30-12:00 (150 simboli, 0 = segno 0 -> contato come '0'), normalizzata per n/log2(n).
  eff_d(a,b) = |log P_b/P_a| / sum|r5| nella fascia (efficienza del cammino: 1 = linea retta).
Domande:
  P1 persistenza fra giorni: rho di oggi (tutto RTH) contro media rho delle 20 sessioni precedenti; idem vr.
  P2 persistenza intraday: rho / vr della mattina (09:30-12:00) contro quelli del pomeriggio (12:00-16:00).
  P3 compressione: lz della mattina predice efficienza / vol del pomeriggio oltre a eff e vol della mattina?
  P4 informazione: I(simbolo successivo; ultimi L) (simboli terzili 1m e 5m, L=1..3) contro placebo con
     simboli rimescolati DENTRO il giorno (tutta la dipendenza seriale distrutta); per anno.
Statistiche: q = z(x)*z(y) per giorno (correlazione), bootstrap a blocchi per giorno; parziali via residui OLS
in campione (diagnostiche)."""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_analog import common as C

bars, daily, M = C.setup_discovery()
ok = M["ok"] & M["in_phase"]
sess = M["sess"].to_numpy()
r5 = M["r5"]; n = len(ok)
rng = np.random.default_rng(5)


def rho(r):
    return (r[:, :-1] * r[:, 1:]).sum(1) / (r ** 2).sum(1)


def vr(r):
    nb = r.shape[1] // 6
    R = r[:, :nb * 6].reshape(len(r), nb, 6).sum(2)
    return (R ** 2).sum(1) / (r[:, :nb * 6] ** 2).sum(1) - 1


def eff(r):
    return np.abs(r.sum(1)) / np.abs(r).sum(1)


def resid(a, Z):
    Z = np.column_stack([np.ones(len(a)), Z])
    return a - Z @ np.linalg.lstsq(Z, a, rcond=None)[0]


def corr_test(x, y, m, tid, desc, **extra):
    m = m & np.isfinite(x) & np.isfinite(y)
    xs, ys = x[m], y[m]
    q = (xs - xs.mean()) / xs.std() * (ys - ys.mean()) / ys.std()
    st = core.day_block_bootstrap(q, sess[m], n_boot=2000)
    yr = pd.Series(q).groupby(M["year"][m]).mean()
    st["years_pos"] = f"{int((yr > 0).sum())}/{len(yr)}"
    st.update(extra)
    print(tid, C.fmt(st))
    C.rec(tid, desc, st)
    return st


def prev_mean(v, w=20):
    out = np.full(n, np.nan); idx = np.where(M["ok"])[0]
    for j, i in enumerate(idx):
        if j >= w:
            out[i] = np.nanmean(v[idx[j - w:j]])
    return out


rho_all, vr_all = rho(r5), vr(r5)
rho_m, rho_a = rho(r5[:, :30]), rho(r5[:, 30:])
vr_m, vr_a = vr(r5[:, :30]), vr(r5[:, 30:])
eff_m, eff_a = eff(r5[:, :30]), eff(r5[:, 30:])
lrv_m = np.log((r5[:, :30] ** 2).mean(1) / M["s5"] ** 2)
lrv_a = np.log((r5[:, 30:] ** 2).mean(1) / M["s5"] ** 2)

# P1
corr_test(prev_mean(rho_all), rho_all, ok, "c01_P1_rho_persist20", "persistenza fra giorni: rho5m RTH vs media 20 sessioni precedenti")
corr_test(prev_mean(vr_all), vr_all, ok, "c01_P1_vr_persist20", "persistenza fra giorni: VR30/5 RTH vs media 20 sessioni precedenti")
corr_test(prev_mean(rho_all, 1), rho_all, ok, "c01_P1_rho_persist1", "persistenza fra giorni: rho5m RTH vs rho di ieri")
# P2
corr_test(rho_m, rho_a, ok, "c01_P2_rho_intraday", "persistenza intraday: rho5m mattina (09:30-12) vs pomeriggio")
corr_test(vr_m, vr_a, ok, "c01_P2_vr_intraday", "persistenza intraday: VR30/5 mattina vs pomeriggio")
corr_test(eff_m, eff_a, ok, "c01_P2_eff_intraday", "persistenza intraday: efficienza mattina vs pomeriggio")


# P3: LZ76 dei segni 1m della mattina
def lz76(s):
    i, k, l, c, kmax, nn = 0, 1, 1, 1, 1, len(s)
    while True:
        if s[i + k - 1] == s[l + k - 1]:
            k += 1
            if l + k > nn:
                c += 1
                break
        else:
            kmax = max(k, kmax)
            i += 1
            if i == l:
                c += 1; l += kmax
                if l + 1 > nn:
                    break
                i, k, kmax = 0, 1, 1
            else:
                k = 1
    return c


C1 = M["C"]; O1 = M["O"]
lz = np.full(n, np.nan)
for i in np.where(ok)[0]:
    p = np.r_[O1[i, 0], C1[i, :150]]
    s = np.sign(np.diff(p)).astype(int).tolist()
    lz[i] = lz76(s) / (150 / np.log2(150))
Z = np.column_stack([eff_m, lrv_m, rho_m])
mm = ok & np.isfinite(lz) & np.isfinite(Z).all(1) & np.isfinite(eff_a) & np.isfinite(lrv_a)
for tgt, nm in ((eff_a, "eff_pom"), (lrv_a, "lrv_pom"), (np.abs(rho_a), "absrho_pom")):
    corr_test(lz, tgt, mm, f"c01_P3_lz_{nm}", f"compressione: LZ76 segni 1m mattina vs {nm} (grezza)")
    a = np.full(n, np.nan); b = np.full(n, np.nan)
    a[mm] = resid(lz[mm], Z[mm]); b[mm] = resid(tgt[mm], Z[mm])
    corr_test(a, b, mm, f"c01_P3_lz_{nm}_partial", f"compressione: LZ76 vs {nm}, parziale dato eff/lrv/rho della mattina")

# P4: informazione mutua simbolo successivo / passato
def terc(z, lib_n=250):
    sym = np.full(z.shape, -1, int); idx = np.where(M["ok"])[0]
    for j, i in enumerate(idx):
        if j < lib_n:
            continue
        qs = np.nanpercentile(z[idx[j - lib_n:j]], [33.333, 66.667], axis=0)
        sym[i] = (z[i][None, :] > qs).sum(0)
    return sym


def mi(sym_rows, L):
    ctx = np.zeros((sym_rows.shape[0], sym_rows.shape[1] - L), int)
    for i in range(L):
        ctx = ctx * 3 + sym_rows[:, i:sym_rows.shape[1] - L + i]
    nxt = sym_rows[:, L:]
    joint = np.bincount((ctx * 3 + nxt).ravel(), minlength=3 ** (L + 1)).reshape(3 ** L, 3).astype(float)
    p = joint / joint.sum(); pc = p.sum(1, keepdims=True); pn = p.sum(0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = p * np.log2(p / (pc * pn))
    return float(np.nansum(t))


r1 = np.diff(np.log(np.column_stack([O1[:, :1], C1])), axis=1)
s1_hat = M["s5"] / np.sqrt(5)
sym5 = terc(r5 / M["s5"][:, None]); sym1 = terc(r1 / s1_hat[:, None])
for nm, S in (("5m", sym5), ("1m", sym1)):
    good = ok & (S[:, 0] >= 0)
    for L in (1, 2, 3):
        rows = S[good]
        real = mi(rows, L)
        pl = []
        for _ in range(50):
            sh = rng.permuted(rows, axis=1)
            pl.append(mi(sh, L))
        yrs = {}
        for y in sorted(set(M["year"][good])):
            ry = S[good & (M["year"] == y)]
            pyl = [mi(rng.permuted(ry, axis=1), L) for _ in range(20)]
            yrs[int(y)] = round((mi(ry, L) - np.mean(pyl)) * 1000, 3)
        st = {"n": int(good.sum()), "mi_bits": real, "plac_mean": float(np.mean(pl)), "plac_p99": float(np.percentile(pl, 99)),
              "excess_mbits": (real - np.mean(pl)) * 1000, "plac_pct": float((np.array(pl) < real).mean()),
              "yearly_excess_mbits": yrs}
        print("P4", nm, L, st)
        C.rec(f"c01_P4_mi_{nm}_L{L}", f"informazione mutua simbolo successivo/ultimi {L} (terzili {nm}) vs placebo rimescolato nel giorno", st)
