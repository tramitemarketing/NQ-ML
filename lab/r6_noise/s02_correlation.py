"""r6_noise, addendum 1: correlazione del P&L giornaliero di B (zeri nei giorni senza trade) con le 25 serie chiuse,
ricostruite sul discovery dal codice esistente. ORB15 / prima ora / candidato 4 con `label_event` (etichettatura dello
screening: target con trade-through, uscita alle 15:55), P&L lordo in punti per geometria; bande di volatilita' con
la fn del candidato congelato. Descrittivo per il verdetto gia' negativo di B (vedi REPORT)."""
import json

import numpy as np
import pandas as pd

from lab import core
from lab.r2_range.candidates import pcband_breakout
from nqml.config import load_config
from nqml.data.bars import rth_bars
from nqml.labels.labeler import label_event
from nqml.screen import firsthour, orb, vabreak

if __name__ == "__main__":
    cfg = load_config()
    bars, daily = core.load("discovery", warmup_days=60)
    d = daily[daily["valid"] & daily["in_phase"]]
    S = pd.DatetimeIndex(d.index)
    B = pd.read_parquet(core.CACHE / "r6_noise_trades.parquet")
    b_day = B.groupby(pd.to_datetime(B["session"]))["gross_pts"].sum().reindex(S).fillna(0.0)
    series = {}
    ohlcv = ["open", "high", "low", "close", "volume"]
    recs = []
    for s in S:
        day = bars[bars["session"] == s.to_datetime64()][ohlcv]
        rth = rth_bars(day, cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]).drop(columns=["session_date"])
        sd = s.date()
        for fam, evs, mod, dd in (("ORB15", orb.orb_events(rth, sd, cfg), orb, rth),
                                  ("prima_ora", firsthour.firsthour_events(rth, sd, cfg), firsthour, rth),
                                  ("candidato4", vabreak.vabreak_events(day, sd, cfg), vabreak, rth)):
            for ev in evs:
                for g in mod.geometries(ev, cfg):
                    lab = label_event(g, dd, cfg)
                    recs.append({"session": s, "serie": f"{fam}_{g['geom']}", "pts": lab["pnl_pts_raw"]})
    R = pd.DataFrame(recs)
    for name, g in R.groupby("serie"):
        series[name] = g.groupby("session")["pts"].sum().reindex(S).fillna(0.0)
    pc = pcband_breakout(bars.copy(), daily.copy())
    pc["session"] = pd.to_datetime(pc["session"])
    series["r2_range_pcband_breakout"] = pc.groupby("session")["gross_pts"].sum().reindex(S).fillna(0.0)
    corr = {k: float(np.corrcoef(b_day, v)[0, 1]) for k, v in sorted(series.items())}
    out = {"n_serie": len(corr), "max_abs": max(abs(v) for v in corr.values()), "blocca_GO": any(v >= 0.5 for v in corr.values()),
           "corr": {k: round(v, 3) for k, v in corr.items()}}
    print(json.dumps(out, indent=1))
    core.record("r6_noise", "corr_famiglie_chiuse", "correlazione giornaliera di B con 25 serie chiuse (addendum 1)",
                "discovery", {"max_abs": out["max_abs"], "n_serie": len(corr)}, corr=out["corr"])
    (core.ROOT / "lab" / "r6_noise" / "correlation.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
