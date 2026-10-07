# r6_noise — report (2026-09-30, solo discovery)

Pre-registrazione: `PREREG.md` con addendum 1 e PROTOCOLLO §19. Codice committato prima dell'esecuzione
(`0d04dc0`; la correlazione, `s02_correlation.py`, è stata scritta dopo aver visto A e B). Righe nel
registro: 3.

**Verdetto: chiusa, senza varianti.** Parametri del paper, 1272 trade su 2107 giorni, 52 % long.

| | A: segnale nudo fino alle 16:00 | B: regole complete (VWAP/bande) |
|---|---|---|
| media giornaliera (bps, zeri inclusi) | +1,82 lordi, t 1,44, p 0,074 | +1,73 netti a 0,75, t 2,06, p 0,020 |
| p Holm | 0,074 | 0,039 |
| metà 2010-14 / 2015-18 (t) | 1,45 / 0,65 | 1,04 / 1,83 |
| per trade | +1,44 punti lordi, +3,0 bps | +2,41 punti lordi; netto a 1,25: +0,07 / +2,44 nelle due metà |
| placebo p | **0,76** (il τ casuale fa meglio: mediana +3,8 bps) | 0,020 |
| criteri §3 | — | netto p 0,008, netto − beta ok, 7/9 anni, **senza i 20 migliori −0,33** |

Criteri per il GO che falliscono:
- A non è significativo;
- A in una delle due metà ha t < 1;
- A non batte il placebo;
- B dipende dai 20 trade migliori;
- **correlazione 0,54 con `r2_range_pcband_breakout`**, oltre il limite di 0,5 dell'addendum 1.

Le altre 24 serie chiuse stanno fra 0,02 e 0,42; la più alta è la prima ora S1_T2.

Lettura: il segnale di rottura in sé non dice nulla, perché un orario casuale nel verso del movimento
dall'apertura rende di più. Quel poco che resta in B viene dal trailing stop, dipende dal 2018 (+11,4 punti
netti a trade, contro fra −2,5 e +1,6 negli altri anni) ed è in larga parte la stessa scommessa della
rottura delle bande di volatilità, già bocciata in conferma. È coerente con Quantitativo su ES, «piatta
2010-2017». Nessun candidato: la validazione non è usata.
