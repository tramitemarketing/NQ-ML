"""r3_adaptive F — estensione di A (dichiarata dopo s01, stessa misura, nessuna scelta sui risultati):
persistenza a scale brevi. IC di Spearman fra le N regole: lordo medio nelle w sessioni precedenti contro
lordo medio nelle w sessioni successive, blocchi non sovrapposti, w in {1, 5, 10}; e w_passato = 63 contro
w_futuro = 5. Nullo segno-per-giorno (300)."""
import numpy as np
import pandas as pd
from scipy.stats import rankdata

from lab import core
from lab.r3_adaptive import common as c

PAIRS = [(1, 1), (5, 5), (10, 10), (63, 5)]


def ic_blocks(g, i0, wp, wf):
    cs = np.vstack([np.zeros((1, g.shape[1])), np.cumsum(g, 0)])
    st = np.arange(max(i0, wp), len(g) - wf + 1, wf)
    past = (cs[st] - cs[st - wp]) / wp; fut = (cs[st + wf] - cs[st]) / wf
    rp = rankdata(past, axis=1); rf = rankdata(fut, axis=1)
    rp -= rp.mean(1, keepdims=True); rf -= rf.mean(1, keepdims=True)
    den = np.sqrt((rp ** 2).sum(1) * (rf ** 2).sum(1))
    ic = np.where(den > 0, (rp * rf).sum(1) / np.where(den > 0, den, 1), np.nan)
    return np.nanmean(ic), len(st)


if __name__ == "__main__":
    P = c.discovery_panel()
    SIDE, GR, meta = c.library(P)
    sess = P["sessions"]
    i0 = int(np.searchsorted(sess, c.SEARCH[0]))
    gross, _, _ = c.gross_net(SIDE, GR)
    rng = np.random.default_rng(4242)
    signs = [rng.choice([-1.0, 1.0], size=len(sess)) for _ in range(300)]
    for wp, wf in PAIRS:
        real, n = ic_blocks(gross, i0, wp, wf)
        pl = np.array([ic_blocks(c.gross_net(SIDE, GR, s)[0], i0, wp, wf)[0] for s in signs])
        p = (pl >= real).mean()
        print(f"past {wp:>2} -> fut {wf:>2}: IC {real:+.4f}  placebo med {np.median(pl):+.4f} q95 {np.quantile(pl,.95):+.4f}  p {p:.3f}  n blocchi {n}")
        core.record(c.FAM, f"F_persist_w{wp}_{wf}", f"persistenza delle regole a scala breve: {wp} sessioni passate -> {wf} future",
                    "discovery", {"n": n, "mean": float(real), "p_pos": float(p)}, placebo_med=float(np.median(pl)), kind="regularity_meta")
