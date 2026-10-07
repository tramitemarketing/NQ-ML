"""H10-H20: regimi di correlazione azioni-tassi, shock di tasso, reazione ritardata, combinazioni,
intraday, massimi a 52 settimane, vol dei tassi -> vol NQ. Tutto noto all'apertura RTH di S.
Allineamento: il valore del 10 anni noto a S e' (circa) quello di 2 g.l. prima; la variazione d1 nota a S
si abbina al rendimento NQ close-to-close della sessione S-2 (nq_ret_cc.shift(2)), noto a S."""
import numpy as np
import pandas as pd
from lab import core
from lab.r4_macro import common as C


def rec(tid, desc, st, **kw):
    core.record(C.FAM, tid, desc, "discovery", st, **kw)
    show = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in st.items() if k != "years"}
    print(tid, show)


if __name__ == "__main__":
    d, bars, daily = C.load()
    nq_lag2 = d["nq_ret_cc"].shift(2)                  # ret NQ del giorno dell'osservazione del tasso
    dy = d["d1_DGS10"]
    corr60 = nq_lag2.rolling(60).corr(dy)
    d["corr60"] = corr60
    y1, _ = C.fwd(d, 1); y5, _ = C.fwd(d, 5); y20, _ = C.fwd(d, 20)
    print("corr60 quantili:", corr60.describe().round(3).to_dict(), "frazione >0:", float((corr60 > 0).mean()))
    # H10a: regime di correlazione -> rendimento NQ a 20g
    rec("H10a_corr_pos_f20", "corr60(NQ,d10y)>0 vs <0 -> NQ 20g (media % nei giorni con corr>0 e diff vs resto)",
        C.cond_mean(y20, corr60 > 0))
    # H10b: la corr modula l'effetto d40? IC di d40 nei due regimi
    k = C.ext_known(d.index)["DGS10"]; d["d40_DGS10"] = (k - k.shift(40)).reindex(d.index)
    for lab_, msk in (("pos", corr60 > 0.2), ("neg", corr60 <= 0.2)):
        st = C.ic_test(d["d40_DGS10"].where(msk), y20)
        rec(f"H10b_d40_ic_corr_{lab_}", f"IC d40_10y->NQ20g solo con corr60 {'>' if lab_=='pos' else '<='}0,2", st)
    # H10c: la corr modula il segno del giorno dopo uno shock? -> segnale = corr60 * d1 (NQ "dovrebbe" muoversi con)
    st = C.ic_test(corr60 * dy, y1)
    rec("H10c_corrxd1_f1", "IC (corr60 x d1_10y) -> NQ 1g: continuazione della reazione attesa", st)
    # H11 shock di tasso: |d1| > 2 sd250
    sh = (dy.abs() > 2 * d["sd250_d1_DGS10"])
    print("giorni shock:", int(sh.sum()))
    sgn = -np.sign(dy)          # tassi su -> atteso NQ giu' (duration)
    for h, y in ((1, y1), (5, y5), (20, y20)):
        st = C.cond_mean((sgn * y).where(sh), sh)
        rec(f"H11_shock_f{h}", f"shock |d1_10y|>2sd250: rendimento NQ {h}g firmato -segno(shock)", st, n_shocks=int(sh.sum()))
    # H12 reazione ritardata: shock in cui NQ non ha reagito nella direzione attesa il giorno dello shock
    under = sh & (np.sign(nq_lag2) != sgn)
    for h, y in ((1, y1), (5, y5)):
        st = C.cond_mean((sgn * y).where(under), under)
        rec(f"H12_underreact_f{h}", f"shock con NQ che il giorno dello shock NON si e' mosso -segno(shock): NQ {h}g firmato", st)
    # H12b: rendimento NQ residuo rispetto al beta sui tassi (sorpresa)-> ogni giorno, 'gap' = beta60*dy - nq_lag2
    beta60 = nq_lag2.rolling(60).cov(dy) / dy.rolling(60).var()
    gap = beta60 * dy - nq_lag2
    st = C.ic_test(gap, y1); rec("H12b_gap_f1", "IC (beta60*d1_10y - ret NQ stesso giorno) -> NQ 1g: aggiustamento ritardato", st)
    st = C.ic_test(gap, y5); rec("H12c_gap_f5", "IC gap -> NQ 5g", st)
    # H16: tassi su e dollaro su (stretta delle condizioni finanziarie) 20g
    tight = (d["d20_DGS10"] > 0) & (d["r20_USD"] > 0)
    rec("H16_tight_f20", "d20_10y>0 e dollaro 20g>0 -> NQ 20g (diff vs resto)", C.cond_mean(y20, tight))
    # H19: intraday open->close RTH della sessione S dato d1 noto all'apertura
    oc = (d["rth_close"] - d["O"]) / d["Oraw"]
    rec("H19a_d1_10y_oc", "IC d1_10y -> NQ open->close RTH della stessa sessione", C.ic_test(dy, oc))
    rec("H19b_d5_10y_oc", "IC d5_10y -> NQ open->close RTH", C.ic_test(d["d5_DGS10"], oc))
    rec("H19c_usd1_oc", "IC dollaro 1g -> NQ open->close RTH", C.ic_test(d["r1_USD"], oc))
    # H20: 10 anni al massimo a 250 g.l.
    k250 = k.rolling(250).max().reindex(d.index)
    hi = d["DGS10"] >= k250
    rec("H20_10y_52w_high_f20", "10 anni al massimo a 250 g.l. -> NQ 20g (diff vs resto)", C.cond_mean(y20, hi), n_days=int(hi.sum()))
    # H18: curva piatta (<0,5): quasi solo 2018 -> diagnostico
    flat = d["T10Y2Y"] < 0.5
    rec("H18_flat_curve_f20", "pendenza 10a-2a < 0,5 -> NQ 20g (quasi solo 2018: diagnostico)", C.cond_mean(y20, flat), n_days=int(flat.sum()))
    # H17 regolarita': vol dei tassi -> vol realizzata NQ a 20g, oltre la vol NQ passata (IC parziale diagnostico)
    rv_f = d["nq_ret_cc"].rolling(20).std().shift(-20)
    rv_p = d["nq_rv20"]
    lr = np.log(d["sd20_d1_DGS10"]); lrv = np.log(rv_p)
    m = pd.concat([lr, lrv], axis=1).dropna(); b = np.polyfit(m.iloc[:, 1], m.iloc[:, 0], 1)
    resid = lr - np.polyval(b, lrv)
    rec("H17_ratevol_resid_rv", "IC vol del 10 anni (residuo della vol NQ a 20g) -> vol realizzata NQ 20g successivi", C.ic_test(resid, np.log(rv_f)))
