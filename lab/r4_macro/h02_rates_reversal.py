"""H03 approfondito: la variazione a 20g del 10 anni predice NQ a 20g con segno NEGATIVO. E' un effetto dei
tassi o un proxy del reversal di NQ stesso (azioni e tassi correlati positivamente nel 2010-18)?
Controlli: (a) correlazione d20_10y con il momentum NQ 20g noto; (b) IC parziale (residuo di d20_10y dopo
regressione sul momentum NQ, stimato in modo espanding per non usare il futuro -> qui solo diagnostico, OLS
sull'intero discovery); (c) IC del momentum NQ da solo; (d) sensibilita' orizzonti; (e) campionamento non
sovrapposto (una osservazione ogni 20 sessioni, 20 fasi)."""
import numpy as np
import pandas as pd
from lab import core
from lab.r4_macro import common as C

if __name__ == "__main__":
    d, bars, daily = C.load()
    y20, _ = C.fwd(d, 20)
    m = d[["d20_DGS10", "nq_mom20", "r20_USD", "d20_T10Y2Y"]].dropna()
    print("corr d20_10y vs nq_mom20:", m.corr(method="spearman").round(3).to_string())
    # (b) residuo (OLS, diagnostico)
    x = m["d20_DGS10"]; z = m["nq_mom20"]
    b = np.polyfit(z, x, 1)
    resid = x - np.polyval(b, z)
    st = C.ic_test(resid, y20)
    core.record(C.FAM, "H03b_d20_10y_resid_mom", "IC del residuo di d20_10y dopo il momentum NQ 20g (OLS diagnostico) -> NQ 20g", "discovery", st)
    print("resid", st)
    st = C.ic_test(d["nq_mom20"], y20)
    core.record(C.FAM, "H03c_nqmom20_f20", "IC momentum NQ 20g (noto all'apertura) -> NQ 20g (confronto)", "discovery", st)
    print("nqmom20", st)
    # (d) orizzonti
    for hs, hf in [(10, 10), (20, 10), (20, 5), (40, 20), (60, 60)]:
        col = f"d{hs}_DGS10"
        if col not in d:
            k = C.ext_known(d.index)["DGS10"]
            d[col] = (k - k.shift(hs)).reindex(d.index)
        y, _ = C.fwd(d, hf)
        st = C.ic_test(d[col], y)
        core.record(C.FAM, f"H03d_d{hs}_10y_f{hf}", f"IC variazione {hs}g del 10 anni -> NQ {hf}g (sensibilita')", "discovery", st)
        print(f"d{hs}->f{hf}", {k: st[k] for k in ('n', 'ic', 'lo', 'hi', 'p_two', 'years_pos')})
    # (e) non sovrapposto
    res = []
    for ph in range(20):
        sub = d.iloc[ph::20]
        yy = (sub["O"].shift(-1) - sub["O"]) / sub["Oraw"]
        mm = pd.concat([sub["d20_DGS10"], yy], axis=1).dropna()
        res.append(mm.corr(method="spearman").iloc[0, 1])
    res = np.array(res)
    print("non-overlap IC per fase: media %.3f min %.3f max %.3f n~%d" % (res.mean(), res.min(), res.max(), len(mm)))
    core.record(C.FAM, "H03e_nonoverlap", "IC d20_10y->NQ20g su campioni non sovrapposti (20 fasi)", "discovery",
                dict(mean_ic=float(res.mean()), min_ic=float(res.min()), max_ic=float(res.max()), n_per_phase=len(mm)))
