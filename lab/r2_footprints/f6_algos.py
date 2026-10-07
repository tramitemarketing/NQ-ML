"""F6 - impronte degli algoritmi di esecuzione.
(a) periodicita' del volume: minuti :00/:15/:30/:45 e multipli di 5 contro gli altri (10:05-15:40, esclusi 11:30, 15:00).
(b) direzione nei minuti "di fetta": nei minuti :00/:15/:30/:45 il rendimento 1m segue il trend dell'ora
    precedente piu' che negli altri minuti? (un TWAP che affetta un ordine grosso)
(c) sbilanciamento persistente (BVC, Easley-Lopez de Prado-O'Hara): OI_W = sum V*(2*Phi(dC/sig)-1) / sum V sulla
    finestra W; ai checkpoint 12:30/13:30/14:30 se |OI_W| > quantile causale q -> segue il segno per H minuti.
    Variante "ordine paziente": efficienza del percorso (|dP| / sum|dP 5m|) alta = macinare costante.
    Griglia dichiarata: W {60,120,180}, H {30,60}, q {0.5,0.7,0.9}. Netto 0,75, ingresso open barra dopo."""
import numpy as np
import pandas as pd
from scipy.stats import norm

from lab.r2_footprints import common as C
from lab.r2_footprints.f3b_magnitude import sigma1m, causal_q

pd.set_option("display.width", 250)

if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    sess = D["sess"]
    a0, b0 = C.sm_of("09:30"), C.sm_of("16:00")
    V = np.where(D["has"], D["V0"], np.nan)[:, a0:b0]
    Cp = D["Cf"][:, a0 - 1:b0]
    dC = np.diff(Cp, axis=1)                        # dC[:,k] = rendimento della barra 09:30+k
    minute = np.arange(b0 - a0) + 30               # minuti dall'ora 9:00 -> minuto dell'ora = (k+30)%60
    mo = minute % 60
    sel = (np.arange(b0 - a0) >= 35) & (np.arange(b0 - a0) < 370)   # 10:05-15:39
    sel &= ~np.isin(np.arange(b0 - a0), [120, 330])                  # esclusi 11:30, 15:00
    LV = np.log(V + 1)
    res = []
    # (a) periodicita'
    for nm, grp in (("q15", sel & (mo % 15 == 0)), ("m5", sel & (mo % 5 == 0) & (mo % 15 != 0))):
        oth = sel & (mo % 5 != 0)
        v = np.nanmean(LV[:, grp], 1) - np.nanmean(LV[:, oth], 1)
        st = C.rec(f"F6a_period_{nm}", f"F6a log-volume medio nei minuti {nm} meno minuti non multipli di 5 (10:05-15:39)",
                   v[ok], sess[ok], unit="log")
        y = pd.Series(v[ok]).groupby(sess[ok].year).mean().round(3).to_dict()
        print(nm, round(st["mean"], 3), (round(st["lo"], 3), round(st["hi"], 3)), y)
    # (b) direzione nei minuti di fetta
    tr = np.full_like(dC, np.nan)
    tr[:, 61:] = Cp[:, 61:-1] - Cp[:, 1:-61]       # trend dal close barra k-61 al close barra k-1 (noto prima)
    prod = np.sign(tr) * dC
    for nm, grp in (("q15", sel & (mo % 15 == 0)), ("q30", sel & (mo % 30 == 0))):
        oth = sel & (mo % 5 != 0)
        v = np.nanmean(prod[:, grp], 1) - np.nanmean(prod[:, oth], 1)
        st = C.rec(f"F6b_slice_dir_{nm}", f"F6b sign(trend 60m) x rendimento 1m nei minuti {nm} meno negli altri minuti, punti",
                   v[ok], sess[ok], unit="pts")
        print("slice", nm, round(st["mean"], 4), (round(st["lo"], 4), round(st["hi"], 4)), "p2", st["p_two"],
              "livello altri", round(np.nanmean(prod[ok][:, oth]), 4))
    # (c) BVC persistente
    sig1 = sigma1m(D, D["valid"])
    bf = norm.cdf(dC / sig1[:, None])
    OIv = np.nan_to_num(V) * (2 * bf - 1)
    # cumulate con una colonna di zeri in testa: cum[:, k+1] = somma delle barre 0..k (BUG corretto: la prima
    # versione usava cum[:, k-W] che per k-W = -1 pescava l'ULTIMA colonna della giornata -> look-ahead)
    z0 = np.zeros((len(sess), 1))
    cumOI = np.concatenate([z0, np.nancumsum(OIv, 1)], 1); cumV = np.concatenate([z0, np.nancumsum(np.nan_to_num(V), 1)], 1)
    absd = np.abs(np.diff(D["Cf"][:, a0 - 5:b0:5], axis=1))  # per efficienza a 5m
    drift = C.drift_per_sm(D, ok)
    rows_all = np.arange(len(sess))
    for W in [60, 120, 180]:
        for measure in ["bvc", "eff"]:
            for H in [30, 60]:
                for q in [0.5, 0.7, 0.9]:
                    trades = []
                    for cp in ["12:30", "13:30", "14:30"]:
                        k = C.sm_of(cp) - a0 - 1            # indice della barra che chiude alle cp (segnale)
                        if measure == "bvc":
                            assert k + 1 - W >= 0
                            x = (cumOI[:, k + 1] - cumOI[:, k + 1 - W]) / (cumV[:, k + 1] - cumV[:, k + 1 - W])
                            side = np.sign(x)
                        else:
                            kk = (k + 1) // 5
                            path = np.nansum(absd[:, kk - W // 5:kk], 1)
                            net = Cp[:, k + 1] - Cp[:, k + 1 - W]
                            x = np.abs(net) / path
                            side = np.sign(net)
                        ax = np.where(ok, np.abs(x), np.nan)
                        thr = causal_q(ax, q)
                        m = ok & np.isfinite(ax) & (ax > thr) & (side != 0)
                        i_sig = np.full(m.sum(), k + a0)
                        trades.append(C.trade(D, rows_all[m], i_sig, i_sig + H, side[m].astype(int), drift))
                    t = pd.concat(trades)
                    st = C.full_report(f"F6c_{measure}_W{W}_H{H}_q{q}_v2", f"F6c {measure} W={W} H={H} q={q}: segue il "
                                       "segno ai checkpoint 12:30/13:30/14:30, netto", t)
                    res.append(dict(m=measure, W=W, H=H, q=q, n=st["n"], gross=st["mean"] + C.COST, net=st["mean"],
                                    p=st["p_pos"], yrs=st["years_pos"], mb=st["minus_beta"]))
    print(pd.DataFrame(res).round(3).to_string())
