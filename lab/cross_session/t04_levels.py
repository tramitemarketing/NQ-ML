"""Batteria 4: livelli notturni (massimo/minimo della notte, range asiatico) a livello di barra.
Unita': punti. Side del trade: dir (rottura/continuazione); media < 0 = il livello respinge (fade)."""
import numpy as np, pandas as pd
from lab import core
from lab.cross_session.build_cache import get
from lab.cross_session.common import evaluate, fmt, add_sm
from lab.cross_session.levels import first_cross_events

bars, daily = core.load("discovery")
bars = add_sm(bars)
t = get(); m = t["valid"] & t["in_phase"]; atr = t.atr20

def run(tid, desc, ev):
    side = ev["dir"].astype(float); g = side * (ev["exit_px"] - ev["entry_px"])
    # deriva della stessa finestra: approssimata con la deriva media per minuto RTH/notte * durata
    wr = pd.Series(0.0, index=t.index)  # beta calcolato a parte sotto
    r = evaluate(tid, desc, g, side, wr, atr, m)
    print(fmt(tid, r), "drift per minuto non sottratto qui")
    return r, g, side

# V4 primo tocco in RTH del massimo/minimo notturno (apertura RTH dentro il range notturno)
for hold in (30, 60):
    ev = first_cross_events(bars, t, t.on_hi, t.on_lo, 930, 1320, hold, mode="touch")
    run(f"V4_ONlevel_touch_rth_h{hold}", f"primo tocco in RTH di max/min notturno, side = direzione della rottura, uscita +{hold}m", ev)
ev = first_cross_events(bars, t, t.on_hi, t.on_lo, 930, 1320, None, mode="touch", exit_at=1320)
run("V4_ONlevel_touch_rth_toclose", "primo tocco in RTH di max/min notturno, side rottura, uscita 16:00", ev)
ev = first_cross_events(bars, t, t.on_hi, t.on_lo, 930, 1320, None, mode="close", exit_at=1320)
run("V4b_ONlevel_closebreak_rth_toclose", "prima chiusura 1m oltre max/min notturno in RTH, side rottura, uscita 16:00", ev)
# V12 rottura del range asiatico dopo l'apertura di Londra
ev = first_cross_events(bars, t, t.asia_hi, t.asia_lo, 540, 870, None, mode="close", exit_at=870, need_inside=True)
run("V12_asiarange_break_london_to0830", "prima chiusura 1m oltre il range asiatico fra 03:00 e 08:30, side rottura, uscita 08:30", ev)
ev = first_cross_events(bars, t, t.asia_hi, t.asia_lo, 540, 870, 60, mode="close", need_inside=True)
run("V12b_asiarange_break_london_h60", "idem, uscita +60m", ev)
# V12c il range asiatico come livello per la RTH (rottura in RTH, apertura RTH dentro al range asiatico)
ev = first_cross_events(bars, t, t.asia_hi, t.asia_lo, 930, 1320, None, mode="close", exit_at=1320)
run("V12c_asiarange_break_rth_toclose", "prima chiusura oltre il range asiatico in RTH (apertura dentro), side rottura, uscita 16:00", ev)
# V12d range europeo (02:00-08:30) come livello in RTH, uscita +60
t2 = t.copy()
ev = first_cross_events(bars, t, t.eur_hi, t.eur_lo, 930, 1320, 60, mode="touch")
run("V12d_eurrange_touch_rth_h60", "primo tocco in RTH del max/min europeo (02-08:30), side rottura, uscita +60m", ev)
