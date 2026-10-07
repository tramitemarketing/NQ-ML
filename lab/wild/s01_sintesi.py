"""Sintesi dal registro (nessun test nuovo: legge solo lab/ledger/wild.jsonl)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from lab import core

rows = [json.loads(l) for l in open(core.LEDGER_DIR / "wild.jsonl", encoding="utf-8")]
df = pd.DataFrame(rows)
pd.set_option("display.width", 220)
pl = df[df.test_id.str.startswith("placebo_")].copy()
wi = df[df.test_id.str.startswith("wild_")].copy()
print("righe registro:", len(df), " placebo:", len(pl), " wild:", len(wi))
print("test_id duplicati:", df.test_id.duplicated().sum())

pl["bat"] = pl["battery"]
pl["hor"] = pl.test_id.str.extract(r"_(h15|h60|hclose|h390|c2c1|c2o|c2c5)")[0]
pl.loc[pl.test_id.str.contains("_D_c2c5"), "hor"] = "c2c5"
pl.loc[pl.test_id.str.contains("_D_c2c1"), "hor"] = "c2c1"
pl.loc[pl.test_id.str.contains("_D_c2o"), "hor"] = "c2o"
pl["sym"] = np.where(pl.side_scheme.isin(["hash"]), "simmetrico", np.where(pl.side_scheme == "long", "long",
                     np.where(pl.side_scheme == "short", "short", "luna")))
pl["p01"] = pl.p_pos < 0.01
pl["c1c3c4"] = pl.c1 & pl.c3 & pl.c4
g = pl.groupby(["bat", "sym"])
tab = pd.DataFrame({"N": g.size(), "EV netto medio": g["mean"].mean(), "beta medio": g.mean_beta.mean(),
                    "p<0,05": g.c1.sum(), "p<0,01": g.p01.sum(), "p<0,05/24": g.c1_bonf.sum(),
                    "c1+c3+c4": g.c1c3c4.sum(), "tutti e 4": g.pass_all.sum(), "4 con Bonf.": g.pass_all_bonf.sum()})
print(tab.round(3).to_string())
tot = pl
print("TOTALE placebo N=%d  p<0,05: %d (%.1f%%)  p<0,01: %d  tutti4: %d (%.1f%%)  tutti4-Bonf: %d (%.2f%%)" % (
    len(tot), tot.c1.sum(), 100 * tot.c1.mean(), tot.p01.sum(), tot.pass_all.sum(), 100 * tot.pass_all.mean(),
    tot.pass_all_bonf.sum(), 100 * tot.pass_all_bonf.mean()))
# per orizzonte (solo RTH A/B, simmetrici e long)
ab = pl[pl.bat.isin(["A", "B"])]
print(ab.groupby(["hor", "sym"]).agg(N=("n", "size"), p05=("c1", "mean"), pg05=("p_pos_gross", lambda s: (s < .05).mean()),
                                      pg2=("p_two_gross", lambda s: (s < .05).mean())).round(3).to_string())
# calibrazione sul lordo (tutti i simmetrici A,B,C,D che hanno p_two_gross)
sym = pl[(pl.sym == "simmetrico") & pl.p_two_gross.notna()]
print("simmetrici con p lordo: N=%d  bilaterale<0,05: %.3f  <0,01: %.3f  unilaterale<0,05: %.3f" % (
    len(sym), (sym.p_two_gross < .05).mean(), (sym.p_two_gross < .01).mean(), (sym.p_pos_gross < .05).mean()))
print("istogramma p lordo bilaterale simmetrici:", np.histogram(sym.p_two_gross, bins=10, range=(0, 1))[0])
E = pl[pl.bat == "E"]
print("batteria E long: N=%d tutti4=%d  tutti4-Bonf=%d  correzione(p_badj)=%d" % (
    (E.side_scheme == "long").sum(), E[E.side_scheme == "long"].pass_all.sum(),
    E[E.side_scheme == "long"].pass_all_bonf.sum(), E[E.side_scheme == "long"].pass_fixed.sum()))

# wild
wi["gross_test"] = wi.test_id.str.contains("gross2")
wn = wi[~wi.gross_test & wi.p_pos.notna()]
print("\nWILD netti: N=%d  p<0,05: %d  p<0,01: %d  tutti4: %d" % (len(wn), (wn.p_pos < .05).sum(),
      (wn.p_pos < .01).sum(), wn.pass_all.fillna(False).sum()))
print(wn.sort_values("p_pos").head(8)[["test_id", "n", "mean", "lo", "hi", "p_pos", "years_pos", "drop20"]].to_string())
wg = wi[wi.gross_test]
print("WILD lordi (regolarita'): N=%d  p_two<0,05: %d" % (len(wg), (wg.p_two < .05).sum()))
print(wg.sort_values("p_two")[["test_id", "n", "mean", "lo", "hi", "p_two", "years_pos"]].head(8).to_string())
