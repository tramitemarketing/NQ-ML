"""H05: altre ipotesi.
 A bande di movimento implicito: primo tocco di open_RTH +/- k*sigma_imp (sigma_imp = VXN/sqrt(252)*prezzo),
   ingresso all'open della barra 1m successiva, uscita 16:00; prosecuzione e fade. Punti netti.
 B SKEW / VVIX alti -> piu' giorni di coda sinistra nei 20 giorni successivi? (quota di sessioni con
   rendimento RTH < -2 sigma HAR); bilaterale.
 C VVIX -> |sorpresa di vol| (vol della vol): z(VVIX) * (|logRV - HAR_iv| - media); atteso >0.
 D vol-targeting con l'implicita: long open->open con peso (media VXN^2 250)/VXN^2 (cap 2) meno long costante.
 E fine/inizio della backwardation VIX/VIX3M: long h sessioni open->open (eccesso cumulato per evento).
 F prima ora "sorpresa" rispetto all'implicita: RV 9:30-10:30 annualizzata / VXN; prosecuzione della prima ora
   nei quintili estremi (punti netti); regolarita': RV prima ora predice logRV 10:30-16:00 oltre a HAR+iv.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.r4_implied import common as C
from lab.vol.candidates import _rolling_ols_pred


def bands(f, bars):
    rb = bars[bars["rth"] & bars["session"].isin(f.index.values)]
    sig = (f["VXN"] / 100 / np.sqrt(252) * f["raw_open"]).to_dict()
    op = f["rth_open"].to_dict()
    cl = f["rth_close"].to_dict()
    res = {}
    groups = [(pd.Timestamp(s), g) for s, g in rb.groupby("session")]
    for k in (0.5, 0.75, 1.0):
        rows = []
        for s, g in groups:
            if s not in sig or not np.isfinite(sig[s]):
                continue
            o = op[s]
            up = o + k * sig[s]
            dn = o - k * sig[s]
            hi = g["adj_high"].to_numpy()
            lo = g["adj_low"].to_numpy()
            ao = g["adj_open"].to_numpy()
            mins = g["ny_min"].to_numpy()
            iu = int(np.argmax(hi >= up)) if (hi >= up).any() else None
            idn = int(np.argmax(lo <= dn)) if (lo <= dn).any() else None
            if iu is None and idn is None:
                continue
            if idn is None or (iu is not None and iu < idn):
                i, side = iu, 1
            elif iu is None or idn < iu:
                i, side = idn, -1
            else:
                continue   # stessa barra: ambiguo, salto
            if i + 1 >= len(ao) or mins[i + 1] >= 945:
                continue
            rows.append((s, side, cl[s] - ao[i + 1]))
        res[k] = pd.DataFrame(rows, columns=["s", "side", "mv"]).set_index("s")
    return res


def main():
    f = C.load_features()
    bars = C._CACHE["bars"]
    # ---------------- A
    for k, d in bands(f, bars).items():
        for nm, sgn in (("cont", 1), ("fade", -1)):
            net = sgn * d["side"] * d["mv"] - core.COST_RT_POINTS
            tid = f"H05A_band{k}_{nm}"
            st = C.rec(tid, f"primo tocco open+/-{k} sigma implicita, {nm}, fino alle 16:00, punti netti",
                       net.to_numpy(), net.index.values, k=k, long_share=float(((sgn * d["side"]) > 0).mean()))
            print(C.fmt(tid, st))
    # ---------------- B
    rth_pct = (f["rth_close"] - f["rth_open"]) / f["raw_open"] * 100
    sd = np.sqrt(np.exp(f["har"]))
    tail = (rth_pct < -2 * sd).astype(float).where(sd.notna())
    fut = pd.concat([tail.shift(-j) for j in range(1, 21)], axis=1).mean(axis=1)
    for nm, col in (("skew", "skew_s"), ("vvix", "vvix_s")):
        rs = C.prank(f[col])
        v = ((rs - 0.5) * (fut - fut.mean())).dropna()
        tid = f"H05B_{nm}_left_tail20"
        st = C.rec(tid, f"(rank {nm} - 0.5) * (quota giorni RTH < -2 sigma HAR nei 20 successivi - media); >0 = predice code",
                   v.to_numpy(), v.index.values)
        print(C.fmt(tid, st), "tail rate", round(float(tail.mean()), 4))
    # ---------------- C
    y = f["logrv"]
    Xh = f[["h1", "h5", "h22"]].shift(1)
    p_iv = _rolling_ols_pred(y, pd.concat([Xh, f[["iv_log"]]], axis=1))
    absur = (y - p_iv).abs()
    lv = np.log(f["VVIX"])
    zz = (lv - lv.rolling(250, min_periods=120).mean().shift(1)) / lv.rolling(250, min_periods=120).std().shift(1)
    v = (zz * (absur - absur.expanding().mean().shift(1))).dropna()
    st = C.rec("H05C_vvix_abs_surprise", "z(VVIX) * (|logRV - HAR_iv| - media storica); >0 = VVIX predice sorprese piu' grandi",
               v.to_numpy(), v.index.values)
    print(C.fmt("H05C_vvix_abs_surprise", st))
    # ---------------- D
    r = f["oo1_pct"]
    iv2 = f["VXN"] ** 2
    w = (iv2.rolling(250, min_periods=120).mean() / iv2).clip(upper=2.0)
    m = w.notna() & r.notna()
    pw = (w * r)[m]
    pc = r[m]
    pw = pw * pc.std() / pw.std()
    diff = pw - pc
    st = C.rec("H05D_voltarget_implied", "long open->open pesato 1/VXN^2 (stessa vol) meno long costante, % grezzo",
               diff.to_numpy(), diff.index.values, sharpe_w=float(pw.mean() / pw.std() * np.sqrt(252)),
               sharpe_c=float(pc.mean() / pc.std() * np.sqrt(252)))
    print(C.fmt("H05D_voltarget_implied", st), st.get("sharpe_w"))
    # ---------------- E
    ts = f["ts_3m_s"]
    rx = f["oo1_pct"] - f["oo1_pct"].mean()
    for evn, ev in (("exit", (ts < 1) & (ts.shift(1) >= 1)), ("entry", (ts >= 1) & (ts.shift(1) < 1))):
        pos_i = np.where(ev.to_numpy())[0]
        print(evn, "eventi:", len(pos_i), [d.date().isoformat() for d in f.index[pos_i]])
        for h in (5, 10, 20):
            vals = np.array([rx.iloc[i:i + h].sum() for i in pos_i])
            tid = f"H05E_backw_{evn}_h{h}"
            st = C.rec(tid, f"long {h} sessioni dal primo giorno noto di {evn} della backwardation VIX/VIX3M, eccesso % cumulato per evento",
                       vals, f.index[pos_i].values, h=h)
            print(C.fmt(tid, st))
    # ---------------- F
    rb = bars[bars["rth"]]
    fh = rb[rb["ny_min"] < 630]
    r1 = np.log(fh["close"]).groupby(fh["session"]).diff()
    rv_fh = (r1 ** 2).groupby(fh["session"]).sum().reindex(f.index)
    rest = rb[rb["ny_min"] >= 630]
    r2 = np.log(rest["close"]).groupby(rest["session"]).diff()
    rv_rest = (r2 ** 2).groupby(rest["session"]).sum().reindex(f.index)
    ratio = np.log(rv_fh * 6.5 * 252 / (f["VXN"] / 100) ** 2)
    rk = C.prank(ratio)
    p1030 = rb[rb["ny_min"] == 630].groupby("session")["adj_open"].first().reindex(f.index)
    side = np.sign(p1030 - f["rth_open"])
    mv = side * (f["rth_close"] - p1030) - core.COST_RT_POINTS
    for nm, mm in (("top", rk >= 0.8), ("bot", rk <= 0.2)):
        v = mv[mm & mv.notna() & (side != 0)]
        tid = f"H05F_fh_cont_ratio_{nm}"
        st = C.rec(tid, f"prosecuzione prima ora 10:30->16:00 se RV prima ora/implicita nel quintile {nm}; punti netti",
                   v.to_numpy(), v.index.values)
        print(C.fmt(tid, st))
    yr = np.log(rv_rest)
    Xb = pd.concat([Xh, f[["iv_log"]]], axis=1)
    pb = _rolling_ols_pred(yr, Xb)
    pa = _rolling_ols_pred(yr, pd.concat([Xb, np.log(rv_fh).rename("lfh")], axis=1))
    q = ((yr - pb) ** 2 - (yr - pa) ** 2)[pb.notna() & pa.notna() & yr.notna()]
    st = C.rec("H05F_fh_rv_predicts_rest", "log RV 10:30-16:00: HAR+iv + log RV prima ora vs HAR+iv; guadagno MSE",
               q.to_numpy(), q.index.values)
    print(C.fmt("H05F_fh_rv_predicts_rest", st))


if __name__ == "__main__":
    main()
