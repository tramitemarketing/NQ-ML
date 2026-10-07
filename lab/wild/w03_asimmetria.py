"""Giro 3: controlli sull'unica regolarita' emersa (W03m, POST-HOC): segno dell'asimmetria di
velocita' della mattina -> verso del rendimento lordo dell'ora successiva.

Tutto sul LORDO con test bilaterale (binario «regolarita'»), perche' al netto non paga (W03m_FOLLOW).
Griglia: finestra della mattina 60/90/120/150 min; orizzonte 30/60/90 min dopo la finestra.
Controllo di confusione: regressione del rendimento su segno(asimmetria) E segno(mattina) insieme.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from lab.wild import common as C
from lab.wild import features as F
from lab.wild.w01_idee import ev, OUT


def main():
    g = C.grid()
    P = g["P"]; S = len(g["sess"]); allS = np.arange(S)
    for win in (60, 90, 120, 150):
        asym = F.speed_asym(P, 0, win)
        for h in (30, 60, 90):
            t, st = ev(f"W03g_w{win}_h{h}_gross2", f"griglia regolarita': segno(asimmetria 09:30+{win}m) x "
                       f"rendimento lordo dei {h} min successivi (bilaterale)", allS, np.full(S, win),
                       np.full(S, win + h), np.sign(asym), gross_test=True)
            print(f"      p_two={st['p_two']:.4f}")
    # regressione con la direzione della mattina come controllo
    asym = F.speed_asym(P, 0, 120)
    y = P[:, 180] - P[:, 120]
    X = pd.DataFrame(dict(sasym=np.sign(asym), smorning=np.sign(P[:, 120] - P[:, 0]),
                          ret_morning_pts=P[:, 120] - P[:, 0]))
    ok = np.isfinite(X).all(1) & np.isfinite(y)
    m = sm.OLS(y[ok], sm.add_constant(X[ok])).fit(cov_type="HC1")
    print(m.summary().tables[1])
    # a scala libera: la stessa cosa in unita' di range della mattina (controllo di unita')
    rngm = P[:, :121].max(1) - P[:, :121].min(1)
    yn = y / rngm
    bo = C.core.day_block_bootstrap(np.sign(asym) * yn, g["sess"].to_numpy())
    print("in unita' di range mattutino:", {k: round(v, 4) for k, v in bo.items() if isinstance(v, float)})
    C.rec("wild_W03r_regression_controls", "regressione HC1: ret 11:30-12:30 su segno(asimmetria), "
          "segno(mattina), rendimento mattina; + versione in unita' di range mattutino",
          dict(n=int(ok.sum()), coef_sasym=float(m.params["sasym"]), t_sasym=float(m.tvalues["sasym"]),
               p_sasym=float(m.pvalues["sasym"]), coef_smorning=float(m.params["smorning"]),
               t_smorning=float(m.tvalues["smorning"]), range_units_mean=bo["mean"], range_units_p_two=bo["p_two"]))
    pd.DataFrame(OUT).to_csv(C.__file__.replace("common.py", "wild_results_3.csv"), index=False)


if __name__ == "__main__":
    main()
