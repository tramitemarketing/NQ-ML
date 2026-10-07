"""B01: motivi simbolici (il mercato come linguaggio). Regole dichiarate PRIMA di guardare:

Alfabeto: ogni rendimento 5m RTH diviso per s5_hat -> simbolo D/F/U secondo i terzili (33/67) della stessa
  quantita' ALLO STESSO SLOT 5m nelle 250 sessioni valide precedenti (causale, toglie il profilo orario).
Parole: L in {3, 4} simboli consecutivi (27 / 81 parole), che finiscono alla barra k (k = L-1 .. 71).
Esito: rendimento dall'open della barra k+1 (ingresso) alla close della barra k+6 (30 minuti), in unita'
  s5_hat*sqrt(6); per i trade in punti adj.
Selezione interna: periodo A = 2011-06..2015-12 (dopo le 250 sessioni di soglie), verifica B = 2016-2018.
  Parola "significativa" in A: |t| > 2,576 con errore standard a grappoli per giorno. In B: stesso segno e
  t > 1,645 nel verso di A (senza ritocchi).
Placebo (100): gli esiti del giorno d vengono appaiati alle parole del giorno pi(d) (permutazione dei giorni,
  stesso slot): conserva profilo orario e dipendenza interna delle parole, rompe il legame parola->esito.
Controllo lineare: stesse statistiche sul residuo dell'esito dopo OLS pooled (in A) su somma degli L
  rendimenti della parola e ultimo rendimento (z-unit): i motivi aggiungono qualcosa al ritorno alla media lineare?
Informazione: I(simbolo successivo; ultime L) in bit, reale contro placebo con simboli rimescolati a blocchi
  di 6 barre all'interno del giorno."""
import sys

import numpy as np
import pandas as pd

from lab import core
from lab.r2_analog import common as C

H = int(sys.argv[1]) if len(sys.argv) > 1 else 6
NS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
LS = tuple(int(x) for x in sys.argv[3].split(',')) if len(sys.argv) > 3 else (3, 4)
TAG = '' if (H, NS) == (6, 3) else f'_H{H}_S{NS}'
bars, daily, M = C.setup_discovery()
ok = M["ok"]
z = M["r5"] / M["s5"][:, None]
n, nb = z.shape
# terzili causali per slot
sym = np.full((n, nb), -1, int)
idx_ok = np.where(ok)[0]
for j, i in enumerate(idx_ok):
    if j < 250:
        continue
    lib = idx_ok[j - 250:j]
    qs = np.nanpercentile(z[lib], [100 * a / NS for a in range(1, NS)], axis=0)
    sym[i] = (z[i][None, :] > qs).sum(0)
has = ok & (sym[:, 0] >= 0) & M["in_phase"]
yr = M["year"]
A = has & (yr <= 2015); B = has & (yr >= 2016)
KMAX = 77 - H
# esiti per ogni (giorno, k)
out_z = np.full((n, nb), np.nan); out_p = np.full((n, nb), np.nan)
for k in range(KMAX + 1):
    out_z[:, k] = np.log(M["P5"][:, k + 1 + H] / M["P5"][:, k + 1]) / (M["s5"] * np.sqrt(H))
    out_p[:, k] = M["AC"][:, 5 * (k + 1 + H) - 1] - M["AO"][:, 5 * (k + 1)]


def words(L):
    w = np.full((n, nb), -1, int)
    for k in range(L - 1, KMAX + 1):
        code = np.zeros(n, int)
        for i in range(L):
            code = code * NS + sym[:, k - L + 1 + i]
        w[:, k] = code
    return w


def word_stats(W, Y, rows, nw):
    """t a grappoli per giorno per ogni parola: somme per giorno."""
    res = np.full((nw, 3), np.nan)
    wr = W[rows]; yr_ = Y[rows]
    for c in range(nw):
        m = (wr == c) & np.isfinite(yr_)
        cnt = m.sum(1); s = np.where(m, yr_, 0).sum(1)
        N = cnt.sum()
        if N < 30:
            continue
        mu = s.sum() / N
        e = s - mu * cnt
        se = np.sqrt((e ** 2).sum()) / N
        res[c] = (mu, mu / se, N)
    return res


rng = np.random.default_rng(2024)
summary = {}
for L in LS:
    Wd = words(L); nw = NS ** L
    for label, Y in (("raw", out_z), ("resid", None)):
        if Y is None:
            # residuo della regressione lineare pooled stimata su A
            s_sum = np.full((n, nb), np.nan); last = np.full((n, nb), np.nan)
            for k in range(L - 1, KMAX + 1):
                s_sum[:, k] = z[:, k - L + 1:k + 1].sum(1); last[:, k] = z[:, k]
            mA = A[:, None] & np.isfinite(out_z) & np.isfinite(s_sum) & (Wd >= 0)
            X = np.column_stack([np.ones(mA.sum()), s_sum[mA], last[mA]])
            b, *_ = np.linalg.lstsq(X, out_z[mA], rcond=None)
            Y = out_z - (b[0] + b[1] * s_sum + b[2] * last)
        rowsA = np.where(A)[0]; rowsB = np.where(B)[0]
        sa = word_stats(Wd, Y, rowsA, nw); sb = word_stats(Wd, Y, rowsB, nw)
        sig = np.abs(sa[:, 1]) > 2.576
        conf = sig & (np.sign(sb[:, 0]) == np.sign(sa[:, 0])) & (np.abs(sb[:, 1]) > 1.645)
        same = sig & (np.sign(sb[:, 0]) == np.sign(sa[:, 0]))
        # placebo
        pl_sig, pl_conf = [], []
        for r in range(100):
            pa = rng.permutation(rowsA); pb = rng.permutation(rowsB)
            Yp = Y.copy(); Yp[rowsA] = Y[pa]; Yp[rowsB] = Y[pb]
            a2 = word_stats(Wd, Yp, rowsA, nw); b2 = word_stats(Wd, Yp, rowsB, nw)
            s2 = np.abs(a2[:, 1]) > 2.576
            pl_sig.append(int(s2.sum()))
            pl_conf.append(int((s2 & (np.sign(b2[:, 0]) == np.sign(a2[:, 0])) & (np.abs(b2[:, 1]) > 1.645)).sum()))
        st = {"n_words": nw, "sig_A": int(sig.sum()), "same_sign_B": int(same.sum()), "confirmed_B": int(conf.sum()),
              "plac_sig_mean": float(np.mean(pl_sig)), "plac_sig_p95": float(np.percentile(pl_sig, 95)),
              "plac_sig_pct": float((np.array(pl_sig) < sig.sum()).mean()),
              "plac_conf_mean": float(np.mean(pl_conf)), "plac_conf_p95": float(np.percentile(pl_conf, 95))}
        alpha = "DFU" if NS == 3 else "0123456789"
        def name(c):
            s = ""
            for _ in range(L):
                s = alpha[c % NS] + s; c //= NS
            return s
        st["sig_words"] = {name(c): [round(float(sa[c, 0]), 3), round(float(sa[c, 1]), 2),
                                     round(float(sb[c, 0]), 3), round(float(sb[c, 1]), 2)] for c in np.where(sig)[0]}
        print(L, label, {k: v for k, v in st.items() if k != "sig_words"})
        for k_, v in st["sig_words"].items():
            print("   ", k_, v)
        C.rec(f"b01_L{L}_{label}{TAG}", f"motivi SAX {NS} simboli L={L} ({label}); esito {5*H}m; selezione A=2011-15, verifica B=2016-18, "
              "100 placebo (permutazione dei giorni)", st)
        summary[(L, label)] = (sa, sb, sig, conf, Wd)

# Trade in punti sulle parole CONFERMATE (raw, L=3 e 4): lato = segno in A, misurato solo in B
for L in LS:
    sa, sb, sig, conf, Wd = summary[(L, "raw")]
    for c in np.where(conf)[0]:
        rows = np.where(B)[0]
        m = (Wd[rows] == c)
        rr, kk = np.where(m)
        g = out_p[rows[rr], kk] * np.sign(sa[c, 0])
        g = g[np.isfinite(g)]
        net = g - core.COST_RT_POINTS
        st = core.day_block_bootstrap(net, M["sess"].to_numpy()[rows[rr]][np.isfinite(out_p[rows[rr], kk])], n_boot=2000)
        st["gross"] = float(g.mean())
        print("trade B", L, c, C.fmt(st))
        C.rec(f"b01_trade_L{L}_w{c}{TAG}", f"trade {5*H}m sulla parola confermata {c} (L={L}), lato di A, netto in B (2016-18)", st)
