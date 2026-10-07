"""Batteria 2: la griglia DICHIARATA nel PIANO. {COMP2, COMP3} x h {30,60,120,close} x m {1,1.5,2}.
Regola: E = b_h(causale) * COMP * sig1m*sqrt(h); opera se |E| >= m*0,75; un trade alla volta per sessione."""
import json

from lab.r2_costaware.common import load_panel, rule_trades, evaluate, rec, fmt

ds = load_panel()
for sig in ["COMP2", "COMP3"]:
    for h in [30, 60, 120, "close"]:
        for m in [1.0, 1.5, 2.0]:
            t = rule_trades(ds, sig, h, m)
            s = evaluate(t)
            rec(f"B2_{sig}_h{h}_m{m}", f"Batteria 2 (griglia dichiarata): regola di costo {sig}, h={h}, |E|>={m}x costo, netto punti",
                s)
            print(f"{sig} h={str(h):5s} m={m}: {fmt(s)}")
            if s.get("n", 0):
                print("      anni:", json.dumps(s["years"]), "n:", json.dumps(s["years_n"]))
