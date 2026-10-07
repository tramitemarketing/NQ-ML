"""Candidati CONGELATI della famiglia r2_analog (giro 2): NESSUNO.

Decisione presa alla fine del discovery (2026-09-23), motivata in REPORT.md:
- direzione (analoghi di mattine, analoghi di giorni, motivi simbolici, novita', compressione): nessuna
  configurazione si separa dal placebo in modo stabile; la selezione interna (2011-14 -> 2015-18) non regge;
  tutti i trade in punti hanno CI che contengono lo zero e «senza i 20 migliori» negativo;
- volatilita': gli analoghi migliorano la previsione della vol del pomeriggio rispetto a un benchmark lineare
  semplice (A03), ma il guadagno sparisce del tutto quando il benchmark include il rendimento della mattina con
  segno (effetto leva), due termini non lineari e la vol in tick (A04). Presentarlo come «regolarita' degli
  analoghi» sarebbe falso: e' l'effetto leva intraday, gia' esplorato nel giro 1 (vol A5 / vol_leverage_sign);
- informazione mutua in eccesso (C01-P4, C05): reale in 8/8 anni ma e' volatility clustering piu' la nota
  autocorrelazione negativa a 1-5 minuti (~0,001 bit/simbolo): gia' nota, sotto i costi, e presentarla
  gonfierebbe K per le altre famiglie senza portare un fatto nuovo.
"""
CANDIDATES: list[dict] = []
