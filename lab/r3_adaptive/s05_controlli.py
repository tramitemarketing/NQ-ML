"""r3_adaptive E — controlli completi (netto, anni, senza i 20 migliori, beta, placebo) sull'intera finestra
2011-07 -> 2018-12 per: (1) la vincitrice della pipeline (hedge_eta1.0_hl0), (2) la configurazione
'canonica' del momentum delle strategie (mese, L = 3, k = 1, media), (3) la miglior regola FISSA della
ricerca (r_on_follow_T720_hclose). Beta = somma su regole di peso x lato x deriva media del (T, h) su tutte
le sessioni della finestra. Placebo = 300 repliche segno-per-giorno di s02 (stessa configurazione)."""
import numpy as np
import pandas as pd

from lab import core
from lab.r3_adaptive import common as c
from lab.r3_adaptive import s02_meta as m

if __name__ == "__main__":
    S = m.setup()
    names = m.config_names()
    sess = S["sess"]; mall = (sess >= c.SEARCH[0]).to_numpy() if hasattr(sess >= c.SEARCH[0], "to_numpy") else sess >= c.SEARCH[0]
    gross, net, traded = c.gross_net(S["SIDE"], S["GR"])
    drift = np.where(mall[:, None], S["GR"], np.nan)
    drift = np.nanmean(np.where(traded, drift, np.nan), 0)              # deriva long media del (T,h) di ogni regola
    bet_rule = S["SIDE"] * drift[None, :]                                # beta per regola e giorno
    out = {}
    # (1) hedge
    W = c.hedge_weights(net, traded, S["P"]["atr"], 1.0, 0)
    Wt = W * traded; sw = Wt.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        out["hedge_eta1.0_hl0"] = ((Wt * net).sum(1) / sw, (Wt * bet_rule).sum(1) / sw)
    # (2) top-k canonica
    pos = c.topk_positions(net, traded, S["pids"]["month"], 3, 1, "mean", False)
    a = pos & traded; n = a.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        out["topk_month_L3_k1_mean_all"] = ((net * a).sum(1) / n, (bet_rule * a).sum(1) / n)
    # (3) regola fissa
    j = int(np.flatnonzero(S["meta"].rule == "r_on_follow_T720_hclose")[0])
    out["fixed_r_on_follow_T720_hclose"] = (np.where(traded[:, j], net[:, j], np.nan), np.where(traded[:, j], bet_rule[:, j], np.nan))
    pl = pd.read_csv(c.CACHE / "meta_placebo.csv")
    for k, (y, b) in out.items():
        ok = mall & np.isfinite(y)
        yy, bb, dd = y[ok], b[ok], sess[ok].values
        st = core.day_block_bootstrap(yy, dd)
        stb = core.day_block_bootstrap(yy - bb, dd)
        yr = core.yearly(yy, dd)
        print(f"{k}: netto {st['mean']:+.3f} [{st['lo']:+.3f};{st['hi']:+.3f}] p_pos {st['p_pos']:.3f} | "
              f"netto-beta {stb['mean']:+.3f} p {stb['p_pos']:.3f} | anni+ {(yr['mean']>0).sum()}/{len(yr)} | "
              f"senza top20 {core.drop_top(yy):+.3f} | beta medio {bb.mean():+.3f}")
        print("    ", yr["mean"].round(2).to_dict())
        core.record(c.FAM, f"E_controls_{k}", f"controlli completi 2011-07..2018 di {k} (netto, beta, anni, drop20)", "discovery",
                    st, beta_adj_mean=stb["mean"], beta_adj_p=stb["p_pos"], years_pos=f"{(yr['mean']>0).sum()}/{len(yr)}",
                    drop20=core.drop_top(yy), kind="controls")
