"""Eventi di livello a livello di barra: primo tocco / prima rottura di un livello notturno."""
import numpy as np, pandas as pd
from lab.cross_session.common import add_sm

def first_cross_events(bars, t, lvl_hi, lvl_lo, win_a, win_z, hold, mode="touch", exit_at=None,
                       need_inside=True):
    """Per ogni sessione cerca nella finestra [win_a, win_z) di minuti di sessione il PRIMO evento:
    mode='touch': adj_high >= lvl_hi (evento alto, dir=+1) o adj_low <= lvl_lo (basso, dir=-1);
    mode='close': adj_close > lvl_hi o < lvl_lo (rottura in chiusura).
    Ingresso all'open della barra successiva; uscita all'open della barra `hold` minuti dopo
    l'ingresso (o la prima successiva), oppure al minuto di sessione `exit_at` se dato, e comunque
    non oltre l'ultima barra della finestra/sessione. Restituisce DataFrame per evento con dir
    (direzione del livello), entry/exit price e ts."""
    if "sm" not in bars:
        bars = add_sm(bars)
    out = []
    sm_all = bars["sm"].to_numpy()
    sess_all = bars["session"].to_numpy()
    starts = np.r_[0, np.flatnonzero(sess_all[1:] != sess_all[:-1]) + 1, len(bars)]
    H = bars["adj_high"].to_numpy(); L = bars["adj_low"].to_numpy(); C = bars["adj_close"].to_numpy()
    O = bars["adj_open"].to_numpy(); idx = bars.index
    for a, z in zip(starts[:-1], starts[1:]):
        s = pd.Timestamp(sess_all[a])
        if s not in lvl_hi.index:
            continue
        hi, lo = lvl_hi.get(s, np.nan), lvl_lo.get(s, np.nan)
        if not (np.isfinite(hi) and np.isfinite(lo)):
            continue
        sm = sm_all[a:z]
        w = np.flatnonzero((sm >= win_a) & (sm < win_z))
        if len(w) < 2:
            continue
        w0 = a + w[0]
        if need_inside:
            p0 = O[w0]
            if not (lo < p0 < hi):
                continue
        seg = slice(a + w[0], a + w[-1] + 1)
        if mode == "touch":
            up = H[seg] >= hi; dn = L[seg] <= lo
        else:
            up = C[seg] > hi; dn = C[seg] < lo
        iu = np.flatnonzero(up); idn = np.flatnonzero(dn)
        fu = iu[0] if len(iu) else 10**9; fd = idn[0] if len(idn) else 10**9
        if fu == fd == 10**9 or fu == fd:
            continue   # nessun evento, o entrambi nella stessa barra (ambiguo): scartato
        k = min(fu, fd); d = 1 if fu < fd else -1
        ei = a + w[0] + k + 1
        if ei >= z or sm_all[ei] >= win_z + (hold or 0) + 600:
            continue
        if exit_at is not None:
            xs = np.flatnonzero(sm_all[ei:z] >= exit_at)
            xi = ei + xs[0] if len(xs) else z - 1
            xp = O[xi] if len(xs) else C[z - 1]
        else:
            xs = np.flatnonzero(sm_all[ei:z] >= sm_all[ei] + hold)
            xi = ei + xs[0] if len(xs) else z - 1
            xp = O[xi] if len(xs) else C[z - 1]
        if xi <= ei:
            continue
        out.append((s, d, idx[ei], O[ei], idx[xi], xp, sm_all[ei]))
    return pd.DataFrame(out, columns=["session", "dir", "entry_ts", "entry_px", "exit_ts", "exit_px", "entry_sm"]).set_index("session")
