"""Candidati della famiglia r2_execution (giro 2, 2026-09-23): NESSUNO.

Motivo (dettagli in REPORT.md): con la regola conservativa del trade-through di 1 tick, sui 202 test di
discovery l'esecuzione passiva non cambia mai il segno del netto in modo significativo. Sui placebo il
costo per trade eseguito resta ~0,70-0,80 punti, cioe' quanto l'aggressivo: la selezione avversa si
mangia lo spread risparmiato. Gli unici netti passivi con p < 0,05 vengono da segnali del giro 1 gia'
bocciati (non ripresentabili, PROTOCOLLO §10), e anche li' il passivo non batte l'aggressivo.
Mandare qualcosa in validazione alzerebbe soltanto K per le altre famiglie.
"""
CANDIDATES: list = []
