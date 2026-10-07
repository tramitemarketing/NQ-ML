"""Passo 0 di r6_gamma (PREREG): dati e definizioni, nessun test dell'ipotesi (niente GEX contro esito)."""
import numpy as np
import pandas as pd

from lab import core, extdata

if __name__ == "__main__":
    bars, daily = core.load("discovery")
    d = daily[daily["valid"]]
    ext = extdata.known_at_open(d.index)
    raw = extdata.raw()[["GEX", "DIX"]].dropna()
    rd = raw[raw.index <= pd.Timestamp(core.PHASES["discovery"][1])]
    print("GEX grezzo nel discovery:", rd.index.min().date(), "->", rd.index.max().date(), "righe", len(rd))
    print("GEX: min %.3g mediana %.3g max %.3g" % (rd.GEX.min(), rd.GEX.median(), rd.GEX.max()))
    print("\n3. quota di giorni con GEX < 0 (data di osservazione), per anno")
    print((rd.GEX < 0).groupby(rd.index.year).agg(["mean", "size"]).round(3).to_string())
    print("\nsessioni valide senza GEX noto all'apertura:", int(ext.GEX.isna().sum()), "su", len(d),
          "(prima del 2011-05-03 il GEX non esiste)")
    print("\n4. VXN: sessioni valide senza valore noto all'apertura, per anno")
    raw_vxn = extdata.raw()["VXN"].dropna()
    stale = pd.Series(d.index, index=d.index).map(lambda s: (s - raw_vxn.index[raw_vxn.index < s].max()).days)
    print(pd.DataFrame({"mancanti": ext.VXN.isna().groupby(d.index.year).sum(),
                        "ritardo>4 giorni": (stale > 4).groupby(d.index.year).sum()}).to_string())

    print("\n5. autocorrelazione dei rendimenti RTH (log adj), media delle giornate, per anno")
    b = bars[bars["rth"] & bars["session"].isin(d.index.values)]
    out = {}
    for k in (1, 5):
        c = b[b["ny_min"] % k == (k - 1)] if k > 1 else b   # close della barra che chiude al multiplo di k
        g = c.groupby("session")["adj_close"]
        r = np.log(c["adj_close"]).groupby(c["session"]).diff()
        df = pd.DataFrame({"r": r, "l": r.groupby(c["session"]).shift(1), "s": c["session"]}).dropna()
        ac = df.groupby("s").apply(lambda x: np.corrcoef(x.r, x.l)[0, 1] if len(x) > 5 else np.nan)
        out[f"ac1_{k}m"] = ac.groupby(pd.DatetimeIndex(ac.index).year).mean()
    print(pd.DataFrame(out).round(4).to_string())
    core.record("r6_gamma", "passo0_autocorr", "Passo 0: autocorrelazione media 1m/5m RTH per anno (incondizionata)",
                "discovery", {k: v.round(4).to_dict() for k, v in out.items()})
