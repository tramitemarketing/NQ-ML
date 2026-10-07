"""C04: la «novita'» di una mattina. Dichiarato prima: nov = log(distanza media dai 10 analoghi piu' vicini)
(rep in {ctx, dtw, shape}, W in {90, 150}), nota alla fine della finestra. Domande:
  (a) le mattine senza precedenti hanno un pomeriggio piu' agitato di quanto il benchmark esteso preveda?
      q = errore quadratico OOS di lrv: benchmark esteso vs benchmark esteso + nov (OLS mobile 500).
  (b) direzione: le mattine nuove proseguono o invertono? corr(nov * segno della mattina, y del pomeriggio)."""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_analog import common as C

bars, daily, M = C.setup_discovery()
ok = M["ok"]; sess = M["sess"].to_numpy(); inph = M["in_phase"]
for W in (90, 150):
    o = C.outcome(M, W); lrv, y = o["lrv"], o["y"]
    Xe = C.vol_bench_X(M, W, extended=True)
    be = C.roll_pred(lrv, Xe, ok)
    k = W // 5
    msign = np.sign(np.log(M["P5"][:, k] / M["P5"][:, 0]))
    for rep in ("ctx", "dtw", "shape"):
        D = C.distance_matrix(C.features(M, W, rep), rep)
        NN = C.neighbors(D, ok, 10)
        nov = np.full(len(ok), np.nan)
        h = NN[:, 0] >= 0
        rows = np.where(h)[0]
        nov[rows] = np.log(np.mean(D[rows[:, None], NN[rows]], 1) + 1e-9)
        aug = C.roll_pred(lrv, np.column_stack([Xe, nov]), ok & np.isfinite(nov))
        m = ok & inph & np.isfinite(aug) & np.isfinite(be)
        q = (lrv - be) ** 2 - (lrv - aug) ** 2
        st = core.day_block_bootstrap(q[m], sess[m], n_boot=2000)
        yrs = pd.Series(q[m]).groupby(M["year"][m]).mean()
        st["years_pos"] = f"{int((yrs > 0).sum())}/{len(yrs)}"
        print(f"W{W} {rep} vol", C.fmt(st))
        C.rec(f"c04_W{W}_{rep}_nov_vol", f"novita' (dist. media 10 analoghi, {rep}, W={W}) -> vol pomeriggio oltre benchmark esteso (OOS)", st)
        mm = ok & inph & np.isfinite(nov) & np.isfinite(y)
        z = (nov - np.nanmean(nov[mm])) / np.nanstd(nov[mm])
        st2 = C.ic_stats(z * msign, y, sess, mm)
        print(f"W{W} {rep} dir", C.fmt(st2))
        C.rec(f"c04_W{W}_{rep}_nov_dir", f"novita' x segno della mattina -> y pomeriggio (prosecuzione se >0), {rep}, W={W}", st2)
