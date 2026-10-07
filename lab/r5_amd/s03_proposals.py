"""Proposte dell'addendum 1 (PA, PB, PC), dichiarate e committate prima di questo script."""
from lab import core
from lab.r5_amd import common as C
from lab.r5_amd.s01_battery import run

if __name__ == "__main__":
    bars, daily = core.load("discovery")
    D = C.Data(bars, daily)
    for tid, desc, kw in [
        ("PA", "P0 con stop almeno 0,10*ATR20", dict(stop_atr=0.10)),
        ("PB", "P0 solo se ingresso-minimo asiatico <= 0,5*ATR20", dict(reach_atr=0.5)),
        ("PC", "gira la candela: ingresso oltre l'apertura di mezzanotte, obiettivo mezzanotte", dict(above_mid=True, target="midnight")),
    ]:
        t, st = run(D, bars, tid, desc, **kw)
        ok = (st["p_pos"] < 0.05 / 3 and st["mean"] > 0 and st["beta_adj_mean"] > 0 and st["beta_adj_p"] < 0.05 / 3
              and int(st["years_pos"].split("/")[0]) >= 6 and st["d20"] > 0)
        print("   anni", st["years"], "-> candidato" if ok else "-> NO")
