"""Approfondimento del contrarian a 10 giorni (A_contra_k10_ls: eccesso +6,0 bp/giorno [2,2; 9,9], 8/8 anni).
Controlli dichiarati prima:
 1) sensibilita' a k = 7..14 (un effetto vero non vive su un solo valore);
 2) ritardo d'esecuzione: segnale alle 15:59 di t ma posizione presa solo da P_{t+1} (un giorno dopo);
 3) placebo: stesso segnale sfasato di 20 giorni (dovrebbe essere ~0);
 4) scomposizione del segnale: rendimento passato solo overnight vs solo RTH (H21);
 5) come trade: sequenze di posizione costante -> un trade per sequenza (formato del controller), netto 0,75,
    anno per anno in PUNTI, senza i 20 migliori;
 6) H24 calendario a piu' giorni: settimana della scadenza mensile delle opzioni (3o venerdi') long vs resto."""
import numpy as np
import pandas as pd

from lab import core
import lab.multiday.common as C
from lab.multiday.common import load_daily, position_eval, sharpe_diff_boot, boot, years_pos, rec, sharpe

C.REV = 3
d, bars = load_daily()
mu = d["r"].mean()
c = d["rth_close"]
START = d.index[260]
bh = position_eval(d, pd.Series(1.0, index=d.index), mu)
pd.set_option("display.width", 220)
rows = []


def ev(tid, desc, pos, extra=None):
    pe = position_eval(d, pos, mu)
    pe = pe[pe.index >= START]
    st = boot(pe["exc"].to_numpy() * 1e4, pe.index)
    stn = boot(pe["pnl"].to_numpy() * 1e4, pe.index)
    sd = sharpe_diff_boot(pe["pnl"], bh.loc[pe.index, "pnl"], n_boot=2000)
    out = dict(st, unit="bp/giorno eccesso", net_raw_bp=stn["mean"], net_raw_lo=stn["lo"], sr=sd["sr_a"], dsr=sd["diff"],
               mean_pos=float(pe["pos"].mean()), years_exc_pos=years_pos(pe["exc"], pe.index),
               pts_net_day=float(pe["pts"].mean()), **(extra or {}))
    rec(tid, desc, out)
    rows.append(dict(id=tid, **{x: out[x] for x in ("mean", "lo", "hi", "p_pos", "net_raw_bp", "sr", "dsr", "mean_pos", "years_exc_pos", "pts_net_day")}))
    return pe


# 1) sensibilita' k
for k in (7, 8, 9, 11, 12, 14):
    ev(f"C1_contra_k{k}_ls", f"contrarian long/short -sign(rend. {k} giorni)", -np.sign(c - c.shift(k)))
# 2) ritardo di un giorno
s10 = -np.sign(c - c.shift(10))
ev("C2_contra_k10_lag1", "contrarian k10 con esecuzione ritardata di 1 giorno", s10.shift(1))
ev("C2_contra_k10_lag2", "contrarian k10 con esecuzione ritardata di 2 giorni", s10.shift(2))
# 3) placebo sfasato
ev("C3_contra_k10_lag20", "placebo: contrarian k10 sfasato di 20 giorni", s10.shift(20))
# 4) scomposizione overnight / RTH del rendimento passato (punti adj, somma su 10 giorni)
on = d["rth_open"] - d["rth_close"].shift(1)
intr = d["rth_close"] - d["rth_open"]
ev("C4_contra_k10_rthonly", "contrarian su somma 10 giorni dei soli rendimenti RTH (open->close)", -np.sign(intr.rolling(10).sum()))
ev("C4_contra_k10_ononly", "contrarian su somma 10 giorni dei soli rendimenti overnight (close->open)", -np.sign(on.rolling(10).sum()))
# 6) OPEX week
idx = d.index
third_fri = pd.Series([core._third_friday(t.year, t.month) for t in idx], index=idx)
days_to = (pd.to_datetime(third_fri) - idx).dt.days.to_numpy()
# posizione tenuta da P_t a P_{t+1}: long se la sessione t+1 cade nella settimana della scadenza (lun..ven)
nxt_days = pd.Series(days_to, index=idx).shift(-1)
opex = ((nxt_days >= 0) & (nxt_days <= 4)).astype(float)
ev("H24_opex_week_lf", "long nella settimana della scadenza mensile (sessioni lun-ven del 3o venerdi')", opex)
print(pd.DataFrame(rows).set_index("id").round(2).to_string())

# 5) contrarian k10 come trade (sequenze)
def runs_to_trades(pos: pd.Series) -> pd.DataFrame:
    p = pos.fillna(0)
    P = d["P"]
    out = []
    cur, start = 0, None
    for i, (t, v) in enumerate(p.items()):
        if v != cur:
            if cur != 0:
                out.append((start, t, cur))
            cur, start = v, t
    tr = pd.DataFrame(out, columns=["session", "exit_session", "side"])
    tr["gross_pts"] = tr["side"] * (P.loc[tr["exit_session"]].to_numpy() - P.loc[tr["session"]].to_numpy())
    tr["days"] = [d.index.get_loc(b) - d.index.get_loc(a) for a, b in zip(tr["session"], tr["exit_session"])]
    tr["net"] = tr["gross_pts"] - core.COST_RT_POINTS
    return tr[tr["session"] >= START]

tr = runs_to_trades(s10)
st = core.day_block_bootstrap(tr["net"].to_numpy(), tr["session"].to_numpy())
yr = core.yearly(tr["net"].to_numpy(), tr["session"])
# beta per trade: side * deriva media in punti per giorno x giorni (deriva in punti dell'anno di ingresso NON nota: uso quella del campione)
drift_pts = d["dP"].mean()
tr["beta_adj"] = tr["net"] - tr["side"] * drift_pts * tr["days"]
stb = core.day_block_bootstrap(tr["beta_adj"].to_numpy(), tr["session"].to_numpy())
out = dict(st, unit="punti netti per trade", n_long=int((tr.side > 0).sum()), mean_days=float(tr["days"].mean()),
           mean_long=float(tr.loc[tr.side > 0, "net"].mean()), mean_short=float(tr.loc[tr.side < 0, "net"].mean()),
           beta_adj=stb["mean"], beta_adj_lo=stb["lo"], drop20=core.drop_top(tr["net"].to_numpy()),
           years_pos=years_pos(tr["net"], tr["session"]), years_beta_pos=years_pos(tr["beta_adj"], tr["session"]))
rec("C5_contra_k10_trades", "contrarian k10 long/short come sequenze-trade, netto 0,75 punti, punti adj", out)
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()})
print(yr.round(2))
tr["yr"] = tr["session"].dt.year
print(tr.groupby(["yr", "side"])["net"].agg(["mean", "count"]).unstack().round(1))
