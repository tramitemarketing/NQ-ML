"""r2_autosearch — candidati congelati.

NESSUN candidato. Regola di decisione pre-registrata (s00_piano.py): si consegna qualcosa solo se la
pipeline di ricerca+selezione si distingue dal caso (p(S2) < 0,05 oppure p(S3) < 0,05 sul nullo
«segno per giorno»). Esito: p(S2) = 0,874, p(S3) = 0,462 -> zero candidati. Vedi REPORT.md.
"""
CANDIDATES = []
