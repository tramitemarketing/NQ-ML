"""r3_adaptive — candidati congelati.

NESSUN candidato. Regola di decisione pre-registrata (s00_piano.py):
- tradeable solo se la meta-procedura vincitrice della ricerca 2011-07..2015 ha media netta > 0 e t > 1,645
  nella verifica 2016-18 E p(S3) < 0,05 sul placebo: esito t = -0,22 (media -0,42 punti), p(S3) = 0,38;
  tutte le 106 meta-procedure hanno t netto < 0 gia' in ricerca;
- regolarita' solo se la persistenza mensile (L = 3) passa entrambi i nulli: IC +0,022, p 0,10 sul nullo
  'segno per giorno' -> no.
La persistenza a 10 sessioni (IC +0,037, 0/300 placebo) e' POST-HOC (s06/s07) e non monetizzabile: resta nel
REPORT come indicazione da pre-registrare, non come candidato.
"""
CANDIDATES = []
