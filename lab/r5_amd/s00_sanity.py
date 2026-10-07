"""Controllo meccanico (nessuna statistica di P&L): conteggi di OB, eventi, trade e un esempio stampato."""
import time
import numpy as np
from lab import core
from lab.r5_amd import common as C

if __name__ == "__main__":
    t0 = time.time()
    bars, daily = core.load("discovery")
    D = C.Data(bars, daily)
    for sign in (+1, -1):
        o, h, l, c = C.space(D, sign)
        obs = C.bearish_obs(D, o, h, l, c)
        ev = C._events(D, o, h, l, c, obs, dict(C.DEFAULT))
        print("lato", "short" if sign > 0 else "long", "OB", len(obs), "toccati", int((obs.touch >= 0).sum()),
              "sessioni con evento", len(ev))
        # l'OB e' sopra il prezzo quando diventa noto?
        print("  bot > close alla nascita:", float((obs.bot.to_numpy() > c[obs.known.to_numpy() - 1]).mean()))
    t = C.simulate(D)
    print("trade", len(t), "per lato", t.side.value_counts().to_dict(), "uscite", t.why.value_counts().to_dict(),
          "ingresso NY min", np.percentile(bars.loc[t.entry_ts, "ny_min"], [0, 50, 100]),
          f"{time.time()-t0:.0f}s")
    r = t.iloc[len(t) // 2]
    print(r.to_dict())
    sl = bars.loc[r.entry_ts - np.timedelta64(20, "m"): r.entry_ts + np.timedelta64(5, "m"),
                  ["ny_min", "adj_open", "adj_high", "adj_low", "adj_close"]]
    print(sl.to_string())
