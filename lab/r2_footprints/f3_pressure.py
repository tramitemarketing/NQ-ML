"""F3/F4/F5 - pressione nella finestra di chiusura e rientro dopo. Regolarita' direzionali sul LORDO in punti:
gross = sign(segnale) * rendimento successivo (continuazione > 0, rientro < 0)."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C

pd.set_option("display.width", 250)


def px(D, t):          # close della barra t (prezzo "alle t+1 minuti")
    return D["Cf"][:, C.sm_of(t)]


def opn(D, t):
    return D["Of"][:, C.sm_of(t)]


if __name__ == "__main__":
    D, daily = C.get()
    n = len(D["sess"])
    ok = D["valid"] & D["in_phase"]
    nxt_ok = np.append(ok[1:], False)
    prev_ok = np.insert(ok[:-1], 0, False)
    sess = D["sess"]
    c1559 = px(D, "15:59")
    prev_close = np.insert(c1559[:-1], 0, np.nan)
    nxt_open = np.append(opn(D, "09:30")[1:], np.nan)
    posts = {"16:14": px(D, "16:14") - c1559, "16:59": px(D, "16:59") - c1559,
             "next0930": nxt_open - c1559}
    res = []

    def test(tid, desc, sig, fut, mask, **kw):
        m = mask & np.isfinite(sig) & np.isfinite(fut) & (sig != 0)
        g = np.sign(sig[m]) * fut[m]
        t = pd.DataFrame({"session": sess[m], "gross_pts": g})
        st = C.full_report(tid, desc, t, net=False, **kw)
        res.append(dict(id=tid, n=st["n"], mean=st["mean"], lo=st["lo"], hi=st["hi"], p2=st["p_two"],
                        yrs=st["years_pos"], d20=st["drop20"]))
        return st

    # F3: finestra di pressione W->16:00 e rientro dopo
    for w in ["15:45", "15:50", "15:55"]:
        sig = c1559 - px(D, f"{w[:3]}{int(w[3:]) - 1:02d}")
        for h, fut in posts.items():
            test(f"F3_press{w}_post{h}", f"F3 sign(prezzo 16:00 - prezzo {w}) x (prezzo {h} - prezzo 16:00), lordo punti",
                 sig, fut, ok & (nxt_ok if h == "next0930" else True))
    # settlement 15:59 (ultimo minuto) e rientro
    sig = c1559 - px(D, "15:58")
    for h, fut in posts.items():
        test(f"F3_settle1559_post{h}", f"F3 sign(rendimento barra 15:59) x (prezzo {h} - prezzo 16:00)", sig, fut,
             ok & (nxt_ok if h == "next0930" else True))
    # pubblicazione sbilanciamenti 15:50: il primo movimento 15:50-15:52 prosegue fino a 15:59?
    for a, b in [("15:52", "15:59"), ("15:55", "15:59")]:
        sig = px(D, "15:51") - px(D, "15:49")
        fut = px(D, b) - px(D, a)
        test(f"F3_imb1550_{a}_{b}", f"F3 sign(prezzo 15:52 - prezzo 15:50) x (prezzo {b}+1 - prezzo {a}), continuazione "
             "dell'informazione di sbilanciamento", sig, fut, ok)
    # F4 leveraged ETF: rendimento dal close di ieri alle 15:44 -> 15:45..16:00
    day = px(D, "15:44") - prev_close
    for a in ["15:45", "15:50"]:
        fut = c1559 - px(D, f"{a[:3]}{int(a[3:]) - 1:02d}")
        test(f"F4_letf_{a}", f"F4 LETF: sign(prezzo 15:45 - close 16:00 di ieri) x (prezzo 16:00 - prezzo {a})", day, fut,
             ok & prev_ok)
    # F4 rientro del flusso LETF dopo le 16:00
    for h, fut in posts.items():
        test(f"F4_letf_post{h}", f"F4 LETF rientro: sign(giorno fino alle 15:45) x (prezzo {h} - prezzo 16:00)", day, fut,
             ok & prev_ok & (nxt_ok if h == "next0930" else True))
    print(pd.DataFrame(res).round(3).to_string())

    # F4 trend nel tempo: beta OLS per anno di r(15:45->16:00) su r(ieri->15:45) (in % per scala)
    raw = D["rawCf"][:, C.sm_of("15:44")]
    y = (c1559 - px(D, "15:44")) / raw * 100
    x = day / raw * 100
    m = ok & prev_ok & np.isfinite(x) & np.isfinite(y)
    df = pd.DataFrame({"x": x[m], "y": y[m], "yr": sess[m].year})
    rows = []
    for yr, g in df.groupby("yr"):
        b = np.polyfit(g.x, g.y, 1)[0]
        big = g[g.x.abs() > 1.0]
        rows.append(dict(yr=yr, beta=b * 100, corr=g.x.corr(g.y), n=len(g),
                         beta_big=np.polyfit(big.x, big.y, 1)[0] * 100 if len(big) > 10 else np.nan, n_big=len(big)))
    print("beta (x100) del rendimento 15:45-16:00 sul rendimento del giorno, per anno:")
    print(pd.DataFrame(rows).round(3).to_string())
    C.rec("F4_letf_beta_by_year", "F4 LETF: pendenza OLS per anno di r(15:45->16:00) su r(close ieri->15:45), in % "
          "(descrittivo: trend con l'AUM)", np.array([r["beta"] for r in rows]),
          np.array([pd.Timestamp(f"{r['yr']}-06-30") for r in rows]), by_year={r["yr"]: r["beta"] for r in rows})
