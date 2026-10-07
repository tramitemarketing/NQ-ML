"""Passo 0: calendario macro 2010-2018 (FOMC, CPI, occupazione), date note mesi prima.

Fonti (scaricate il 2026-10-07, in data/ext_free/calendario/):
- FOMC: pagine ufficiali federalreserve.gov/monetarypolicy/fomchistoricalYYYY.htm (fomc_YYYY.htm). Si tengono
  le sole riunioni programmate («Meeting»), giorno del comunicato = ultimo giorno della riunione. Le
  «Conference Call» non programmate sono escluse: non erano note in anticipo.
- CPI (release 10) e occupazione (Employment Situation, release 50): date di pubblicazione ALFRED
  (alfred.stlouisfed.org/release/downloaddates?rid=..&ff=txt), salvate in alfred_rid*_2010_2018.txt.
  ALFRED include anche le date di sole revisioni. Regola fissata prima di guardare i mercati:
  - CPI: in febbraio la revisione dei fattori stagionali esce pochi giorni PRIMA del dato di gennaio ->
    di due date a meno di 10 giorni si tiene la seconda;
  - occupazione: le date extra (revisioni) vengono DOPO la pubblicazione -> si tiene la prima.
  Controllo: 12 date l'anno per serie, tutte in giorni feriali.

Scrive data/ext_free/calendario_macro.csv (date, fomc, cpi, nfp). Nessun dato di mercato.
"""
from __future__ import annotations

import re

import pandas as pd

from lab import core

DIR = core.ROOT / "data" / "ext_free" / "calendario"
OUT = core.ROOT / "data" / "ext_free" / "calendario_macro.csv"
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}
PAT = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                 r"\s+(\d{1,2})(?:-(?:(January|February|March|April|May|June|July|August|September|October|"
                 r"November|December)\s+)?(\d{1,2}))?\s+Meeting")
# riunioni a cavallo di due mesi nelle pagine 2013-2018: «Jan/Feb 31-1 Meeting»
PAT2 = re.compile(r"\b([A-Z][a-z]{2})/([A-Z][a-z]{2})\s+(\d{1,2})-(\d{1,2})\s+Meeting")
ABBR = {m[:3]: i for m, i in MONTHS.items()}


def fomc(year: int) -> list[pd.Timestamp]:
    html = (DIR / f"fomc_{year}.htm").read_text(encoding="utf-8", errors="ignore")
    out = set()
    for m1, d1, m2, d2 in PAT.findall(html):
        month = MONTHS[m2] if m2 else MONTHS[m1]
        day = int(d2) if d2 else int(d1)
        out.add(pd.Timestamp(year, month, day))
    for _m1, m2, _d1, d2 in PAT2.findall(html):
        out.add(pd.Timestamp(year, ABBR[m2], int(d2)))
    return sorted(out)


def dedup(dates: list[pd.Timestamp], keep: str) -> list[pd.Timestamp]:
    dates = sorted(dates)
    out: list[pd.Timestamp] = []
    for d in dates:
        if out and (d - out[-1]).days < 10:
            if keep == "last":
                out[-1] = d
            continue
        out.append(d)
    return out


def main() -> None:
    f = [d for y in range(2010, 2019) for d in fomc(y)]
    cpi = dedup([pd.Timestamp(x) for x in (DIR / "alfred_rid10_2010_2018.txt").read_text().split()], "last")
    nfp = dedup([pd.Timestamp(x) for x in (DIR / "alfred_rid50_2010_2018.txt").read_text().split()], "first")
    for name, s in (("fomc", f), ("cpi", cpi), ("nfp", nfp)):
        per_year = pd.Series(1, index=pd.DatetimeIndex(s)).groupby(lambda d: d.year).sum()
        print(name, dict(per_year))
        assert all(d.weekday() < 5 for d in s), name
        assert (per_year == (8 if name == "fomc" else 12)).all(), (name, per_year)
    idx = pd.DatetimeIndex(sorted(set(f) | set(cpi) | set(nfp)))
    cal = pd.DataFrame({"fomc": idx.isin(f), "cpi": idx.isin(cpi), "nfp": idx.isin(nfp)}, index=idx).astype(int)
    cal.index.name = "date"
    cal.to_csv(OUT)
    print(f"scritto {OUT} ({len(cal)} giorni con almeno un evento)")


if __name__ == "__main__":
    main()
