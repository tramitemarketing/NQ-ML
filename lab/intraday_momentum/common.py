"""Strumenti comuni della famiglia intraday_momentum.

Convenzioni (fissate PRIMA di guardare qualunque risultato):
- Prezzo "alle HH:MM" = close (adj) della barra 1m che inizia a HH:MM-1 (cioè la barra che chiude a HH:MM).
- Ingresso di un trade che parte alle HH:MM = open (adj) della barra che inizia a HH:MM: il segnale usa
  solo barre chiuse fino a HH:MM, l'ingresso avviene dopo. Uscita alle HH:MM = close della barra HH:MM-1.
- "Chiusura di ieri" = rth_close (close della barra 15:59) dell'ultima sessione VALIDA precedente.
- Solo sessioni `valid` (>= 300 barre RTH) e con tutte le barre necessarie.
- UNITA' (dichiarata prima): la metrica di decisione e' il NETTO IN PUNTI per contratto (gross_pts - 0,75),
  perche' e' cio' che il controller misura. Come controllo si riporta anche il netto in punti-base del
  prezzo (bps = pts / prezzo grezzo * 1e4, costo convertito allo stesso modo), che pesa gli anni allo
  stesso modo. I SEGNALI usano sempre rendimenti relativi (pts / prezzo grezzo), mai punti, perche'
  i livelli adj sono spostati dall'aggiustamento additivo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core

FAM = "intraday_momentum"
COST = core.COST_RT_POINTS


def hm(h: int, m: int) -> int:
    return h * 60 + m


def build(bars: pd.DataFrame, daily: pd.DataFrame) -> dict:
    """Matrici sessione x minuto RTH (570..959) di adj_open, adj_close, close grezzo, volume."""
    r = bars[bars["rth"]]
    out = {}
    for col in ("adj_open", "adj_close", "close", "volume"):
        p = r.pivot_table(index="session", columns="ny_min", values=col, aggfunc="first")
        p = p.reindex(columns=range(570, 960))
        if col != "volume":
            p = p.ffill(axis=1)
        else:
            p = p.fillna(0.0)
        out[col] = p
    sess = out["adj_close"].index
    dv = daily.reindex(sess)
    ok = dv["valid"].fillna(False).to_numpy() & out["adj_close"][959].notna().to_numpy() \
        & out["adj_open"][570].notna().to_numpy()
    # chiusura dell'ultima sessione valida precedente
    rc = dv["rth_close"].where(dv["valid"].fillna(False))
    prev_close = rc.ffill().shift(1)       # ultima sessione valida STRETTAMENTE precedente
    out["prev_close"] = prev_close
    out["ok"] = pd.Series(ok, index=sess) & prev_close.notna()
    out["in_phase"] = dv["in_phase"].fillna(False)
    out["daily"] = dv
    out["sess"] = sess
    return out


def px(M: dict, t: int) -> pd.Series:
    """Prezzo adj alle t (minuti NY): close della barra t-1. t=570 -> apertura (open barra 570)."""
    if t == 570:
        return M["adj_open"][570]
    return M["adj_close"][t - 1]


def px_in(M: dict, t: int) -> pd.Series:
    """Prezzo d'ingresso alle t: open della barra t."""
    return M["adj_open"][t]


def raw(M: dict, t: int) -> pd.Series:
    return M["close"][t - 1] if t > 570 else M["close"][570]


def ret(M: dict, t0, t1) -> pd.Series:
    """Rendimento relativo fra t0 e t1 (t0 = 'pc' per la chiusura di ieri)."""
    a = M["prev_close"] if t0 == "pc" else px(M, t0)
    b = px(M, t1)
    return (b - a) / raw(M, t1)


def trade(M: dict, side: pd.Series, t_in: int, t_out: int, extra_mask=None) -> pd.DataFrame:
    """Trade da t_in (open barra t_in) a t_out (close barra t_out-1). side in {-1,0,+1}; 0 = niente."""
    e = px_in(M, t_in)
    x = px(M, t_out)
    mask = M["ok"] & side.fillna(0).ne(0) & e.notna() & x.notna()
    if extra_mask is not None:
        mask &= extra_mask.fillna(False)
    s = side[mask].astype(int)
    g = (x - e)[mask] * s
    rp = M["close"][t_in][mask]
    sess = M["sess"][mask.to_numpy()]
    return pd.DataFrame({"session": sess, "side": s.to_numpy(), "gross_pts": g.to_numpy(),
                         "raw_px": rp.to_numpy(), "in_phase": M["in_phase"][mask].to_numpy()})


def evaluate(tr: pd.DataFrame, drift: pd.Series | None = None, n_boot: int = 5000) -> dict:
    """Statistiche standard sul netto in punti + bps + beta. `drift` = rendimento long della stessa
    finestra (punti) su TUTTE le sessioni valide: il controllo beta e' mean(side) * mean(drift)."""
    tr = tr[tr["in_phase"]]
    net = tr["gross_pts"].to_numpy() - COST
    days = tr["session"].to_numpy()
    st = core.day_block_bootstrap(net, days, n_boot=n_boot)
    st["gross"] = float(tr["gross_pts"].mean()) if len(tr) else np.nan
    bps = (tr["gross_pts"] - COST) / tr["raw_px"] * 1e4
    sb = core.day_block_bootstrap(bps.to_numpy(), days, n_boot=n_boot)
    st["bps_mean"], st["bps_lo"], st["bps_hi"], st["bps_p_pos"] = sb["mean"], sb["lo"], sb["hi"], sb["p_pos"]
    y = core.yearly(net, days)
    st["years_pos"] = f"{int((y['mean'] > 0).sum())}/{len(y)}"
    st["yearly"] = {int(k): round(float(v), 3) for k, v in y["mean"].items()}
    st["drop20"] = core.drop_top(net, 20)
    st["long_frac"] = float((tr["side"] > 0).mean()) if len(tr) else np.nan
    if drift is not None and len(tr):
        exp = float(tr["side"].mean())
        st["exposure"] = exp
        st["drift_mean"] = float(drift.mean())
        st["beta_adj_net"] = float(st["mean"] - exp * drift.mean())
    return st


def fmt(st: dict) -> str:
    s = (f"n={st['n']:5d} net={st['mean']:+.3f} [{st['lo']:+.3f};{st['hi']:+.3f}] p+={st['p_pos']:.3f} "
         f"gross={st.get('gross', np.nan):+.3f} bps={st.get('bps_mean', np.nan):+.2f} yrs={st.get('years_pos')} "
         f"d20={st.get('drop20', np.nan):+.3f}")
    if "beta_adj_net" in st:
        s += f" exp={st['exposure']:+.2f} beta_adj={st['beta_adj_net']:+.3f}"
    return s


def rec(test_id: str, desc: str, st: dict, **extra) -> None:
    core.record(FAM, test_id, desc, "discovery", st, **extra)
    print(f"{test_id:28s} {fmt(st)}")
