# r6_silverbullet — report (2026-09-30, solo discovery)

Pre-registrazione: `PREREG.md` e PROTOCOLLO §19. Specifica del repo cjosh4toyotas-stack v1.1. Codice
committato prima dell'esecuzione (`0d04dc0`). Righe nel registro: 9. La prima riga, del Passo 0, ha due
conteggi sbagliati ed è superata dalla seconda.

**Verdetto: chiusa definitivamente, senza varianti.** 964 trade nel 2010-2018: 464 alle 03-04, 221 alle 10-11,
279 alle 14-15.

| | valore |
|---|---|
| A, segnale nudo a 60 minuti | −0,80 bps a trade (−0,17R); giornaliero t −1,07, p 0,86; metà t −0,77 / −0,75 |
| A a 15 / 30 / 120 minuti | +0,01 / −0,14 / −1,18 bps a trade |
| placebo A (τ casuale, lato contro il range delle 2 ore) | mediana +2,0 bps, 5°-95° percentile da +1,2 a +2,9: il reale sta sotto tutte le 200 storie |
| B, geometria del repo | lordo −0,21 punti (−0,09R), netto a 0,75 −0,96; a 1,25 −1,26 / −1,65 nelle due metà |
| uscite | 604 stop, 231 target, 129 a tempo |
| vincite / pareggio | 24,0 % contro 52,5 % (costo 1,25 su un rischio mediano di 3,25 punti); anche al lordo servirebbe il 33 % |
| criteri §3 | 0/4; 0/9 anni positivi |
| p Holm | A 1,0; B 1,0 |

Sensibilità, non decisive, tutte negative a 0,75:
- soglie originali 0,5/60 punti: 1393 trade, −1,01 punti netti;
- fill al tocco come nel repo: 1038 trade, −0,73;
- finestre separate: −1,11 / −1,53 / −0,24.

Lettura: lo sweep seguito dall'FVG non contiene direzione. Dopo il fill il prezzo prosegue un po' **contro**
il bias, mentre un ingresso a caso che va contro il range recente guadagna sul ritorno verso il centro del
range. Il rischio è piccolo, quindi il costo pesa per circa 0,4R a trade. Il risultato del repo (profit
factor 0,51 su 27 trade nel 2026) è coerente con quello che si vede qui su 9 anni. Nessun candidato: la
validazione non è usata.
