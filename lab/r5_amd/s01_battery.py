"""Batteria pre-registrata (PREREG.md): P0, P0_ct, controlli C1-C5, sensibilita'. Tutto nel registro."""
import numpy as np
from lab import core
from lab.r5_amd import common as C

FAM = C.FAM


def run(D, bars, tid, desc, t=None, **kw):
    if t is None:
        t = C.simulate(D, **kw)
    st = C.summarize(t, bars)
    core.record(FAM, tid, desc, "discovery", {k: v for k, v in st.items()}, params={k: str(v) for k, v in kw.items()})
    print(C.fmt(tid, st))
    return t, st


if __name__ == "__main__":
    bars, daily = core.load("discovery")
    D = C.Data(bars, daily)
    print("== primario")
    t0, s0 = run(D, bars, "P0", "AMD completo: sweep ON_high + tocco OB4h, limite a mitigazione OB2m, stop M+1t, target Asia, ambo i lati")
    run(D, bars, "P0_ct", "P0 solo contro il trend di 5 sessioni (tesi del video)", t=t0[t0.ct].reset_index(drop=True))
    run(D, bars, "C5_pro", "P0 solo a favore del trend di 5 sessioni", t=t0[~t0.ct & (t0.trend != 0)].reset_index(drop=True))
    run(D, bars, "P0_short", "P0 solo short", t=t0[t0.side < 0].reset_index(drop=True))
    run(D, bars, "P0_long", "P0 solo long", t=t0[t0.side > 0].reset_index(drop=True))
    print("== controlli")
    run(D, bars, "C1", "senza condizione OB 4h (solo Judas oltre il massimo notturno)", require_ob=False)
    run(D, bars, "C2", "tocco OB 4h senza presa del massimo notturno", require_sweep=False)
    run(D, bars, "C4", "specchio: continuazione con livelli speculari in R", mirror=True)
    # C3 placebo: zone spostate di u*ATR20 (u~U(0.5,2)), segno casuale, forzato sopra il prezzo alla nascita
    pl = []
    for seed in range(20):
        rng = np.random.default_rng(seed)
        zs = {}
        for sign in (+1, -1):
            o, h, l, c = C.space(D, sign)
            obs = C.bearish_obs(D, o, h, l, c)
            atr = D.atr20[D.sess_code[obs.known.to_numpy()]]
            atr = np.where(np.isfinite(atr), atr, np.nanmedian(D.atr20))
            s = rng.choice([-1, 1], len(obs)) * rng.uniform(0.5, 2, len(obs)) * atr
            below = obs.bot.to_numpy() + s <= c[obs.known.to_numpy() - 1]
            s[below] = np.abs(s[below])
            zs[sign] = s
        t = C.simulate(D, zone_shift=zs)
        st = C.summarize(t)
        core.record(FAM, f"C3_seed{seed}", "placebo: zone OB spostate di u*ATR20", "discovery", st)
        pl.append((st["n"], st["mean"], st["meanR_net"]))
    pl = np.array(pl)
    print(f"C3 placebo 20 semi: n medio {pl[:,0].mean():.0f}, netto medio {pl[:,1].mean():+.2f} "
          f"(min {pl[:,1].min():+.2f} max {pl[:,1].max():+.2f}), R {pl[:,2].mean():+.3f}; "
          f"quota placebo >= P0: {(pl[:,1] >= s0['mean']).mean():.2f}")
    print("== sensibilita'")
    run(D, bars, "S_zone_lowhigh", "zona OB [low, high]", zone="low_high")
    run(D, bars, "S_age10", "eta' OB max 10 sessioni", max_age=10)
    run(D, bars, "S_age60", "eta' OB max 60 sessioni", max_age=60)
    run(D, bars, "S_win1059", "manipolazione fino alle 10:59", win_end=659)
    run(D, bars, "S_win1259", "manipolazione fino alle 12:59", win_end=779, fill_end=839)
    run(D, bars, "S_tgt_mid", "target apertura di mezzanotte", target="midnight")
    run(D, bars, "S_tgt_2R", "target 2R", target="2R")
    run(D, bars, "S_tgt_3R", "target 3R", target="3R")
    run(D, bars, "S_tgt_eod", "nessun target, uscita 15:59", target="eod")
    run(D, bars, "S_market", "ingresso a mercato alla chiusura della candela di spostamento", entry="market")
    run(D, bars, "S_market_C1", "mercato, senza OB 4h", entry="market", require_ob=False)
    print("== P0 per anno", {k: round(v, 2) for k, v in s0["years"].items()}, "uscite", s0["why"])
