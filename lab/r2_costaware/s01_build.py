"""Costruisce il pannello (nessun esito guardato qui: solo distribuzioni e correlazioni dei segnali)."""
import time

from lab.r2_costaware.common import load_panel

if __name__ == "__main__":
    t = time.time()
    ds = load_panel(refresh=True)
    print(ds.shape, round(time.time() - t))
    print(ds[["z_ml", "z_day", "z_20d", "z_surp", "COMP2", "COMP3"]].describe().T)
    print(ds[["z_ml", "z_day", "z_20d", "z_surp"]].corr().round(3))
