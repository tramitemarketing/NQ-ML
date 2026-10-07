# Calibrazione del Revisore

Generata da `calibrazione.py` (200 ripetizioni per scenario, 8 minuti). Strategie sintetiche di cui si conosce la verità, verdetto completo `run_audit` con i dati di mercato. Scenari nulli a costo zero (media netta attesa esattamente zero); vantaggi piantati con costo 0,5 punti a/r. Per velocità: 2000 bootstrap e 200 placebo per audit (in produzione 10.000 e 1.000).

## Falsi positivi: strategie senza vantaggio

Ogni A o B qui è un errore del Revisore. Fra parentesi l'intervallo al 95 % (Wilson).

| scenario | n | A | B | C | D | E | F | A+B (falsi positivi) |
|---|---|---|---|---|---|---|---|---|
| caso puro, N dichiarato = 1 | 200 | 2,0 % | 0,0 % | 0,0 % | 43,5 % | 54,5 % | 0,0 % | **2,0 %** [0,8 %; 5,0 %] |
| migliore fra 20, dichiara N = 1 | 200 | 56,5 % | 0,5 % | 0,0 % | 43,0 % | 0,0 % | 0,0 % | **57,0 %** [50,1 %; 63,7 %] |
| migliore fra 20, dichiara N = 20 | 200 | 0,0 % | 4,5 % | 52,5 % | 43,0 % | 0,0 % | 0,0 % | **4,5 %** [2,4 %; 8,3 %] |

## Potenza: vantaggi veri piantati

Trade di 60 minuti, σ del trade ≈ 7,7 punti. «Netto in σ» = vantaggio netto diviso σ del trade: è la grandezza confrontabile fra mercati (per NQ con trade di un'ora σ ≈ 40-100 punti).

| trade | lordo | netto | netto in σ | A+B (riconosciuto) | C | D+E (mancato) | MDE80 mediano (punti) |
|---|---|---|---|---|---|---|---|
| 250 | 0,75 | 0,25 | 0,032 | **16,0 %** | 0,0 % | 84,0 % | 1,22 |
| 250 | 1,00 | 0,50 | 0,065 | **30,0 %** | 0,0 % | 70,0 % | 1,22 |
| 250 | 1,50 | 1,00 | 0,129 | **62,0 %** | 0,0 % | 38,0 % | 1,21 |
| 250 | 2,00 | 1,50 | 0,194 | **92,0 %** | 0,0 % | 8,0 % | 1,21 |
| 250 | 3,00 | 2,50 | 0,323 | **100,0 %** | 0,0 % | 0,0 % | 1,21 |
| 250 | 4,00 | 3,50 | 0,452 | **100,0 %** | 0,0 % | 0,0 % | 1,21 |
| 750 | 0,75 | 0,25 | 0,032 | **25,0 %** | 0,0 % | 75,0 % | 0,70 |
| 750 | 1,00 | 0,50 | 0,065 | **55,0 %** | 0,0 % | 45,0 % | 0,70 |
| 750 | 1,50 | 1,00 | 0,129 | **99,0 %** | 0,0 % | 1,0 % | 0,71 |
| 750 | 2,00 | 1,50 | 0,194 | **100,0 %** | 0,0 % | 0,0 % | 0,70 |
| 750 | 3,00 | 2,50 | 0,323 | **100,0 %** | 0,0 % | 0,0 % | 0,71 |
| 750 | 4,00 | 3,50 | 0,452 | **100,0 %** | 0,0 % | 0,0 % | 0,70 |

## Come leggerlo

- **Caso puro**: la frazione di A+B è il tasso di falsi positivi quando l'utente è onesto sul numero di tentativi.
- **Migliore fra 20 che dichiara N = 1**: è il caso del venditore che sceglie la variante migliore e non lo dice. La differenza con la riga «dichiara N = 20» è quanto il Revisore dipende da ciò che l'utente dichiara: il Revisore non può vedere i tentativi nascosti, e la pagella deve dirlo.
- **Potenza**: sotto circa 0,1 σ netti a trade e con qualche centinaio di trade il Revisore di solito non riconosce un vantaggio vero. È un limite della statistica, non del software: la riga MDE80 della pagella lo dice caso per caso.
