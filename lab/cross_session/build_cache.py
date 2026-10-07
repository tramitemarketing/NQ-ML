"""Costruisce e salva la tabella per sessione (cache locale nello scratchpad del laboratorio)."""
import sys, time
from pathlib import Path
from lab import core
from lab.cross_session.common import session_table

CACHE = Path(__file__).resolve().parent / "_session_table.pkl"

def get():
    if CACHE.exists():
        import pandas as pd
        return pd.read_pickle(CACHE)
    bars, daily = core.load("discovery", warmup_days=30)
    t0 = time.time()
    t = session_table(bars, daily)
    t.to_pickle(CACHE)
    print(f"tabella in {time.time()-t0:.0f}s")
    return t

if __name__ == "__main__":
    t = get()
    print(t.shape)
    print(t.isna().sum()[t.isna().sum() > 0].to_string())
    print(t.filter(like="ent_").head(3).T)
