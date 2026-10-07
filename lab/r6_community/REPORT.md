# r6_community — report (2026-09-30, solo discovery)

Pre-registrazione: `PREREG.md` con addendum 1 (placebo scalato) e PROTOCOLLO §19. Codice committato prima
dell'esecuzione (`0d04dc0`). Righe nel registro: 7. Placebo: 200 storie scalate, più 50 storie semplici come
descrittivo.

| test | n | reale | placebo (media) | p placebo | p Holm | verdetto | dichiarato online |
|---|---|---|---|---|---|---|---|
| A: ritorno all'apertura delle 08:00 dopo 0,25σ | 717 | 73,5 % | 71,4 % | 0,11 | 0,33 | spiegato dal random walk | 78-80 % |
| B: fade di A (bps netti a trade) | 641 | −2,44 | −3,86 | 0,045 | 0,22 | **non sfruttabile** | — |
| C: sweep dell'ora precedente → ritorno all'apertura | 14.637 | 61,6 % | 64,8 % | 1,00 | 1,00 | spiegato dal random walk (sotto il caso) | 75-85 % |
| D: ritocco dell'apertura del lunedì (mar-ven) | 442 | 68,1 % | 64,3 % | 0,045 | 0,22 | spiegato dal random walk | 70 % |
| E: ritocco dell'apertura delle 00:00 nelle RTH | 2121 | 70,7 % | 64,7 % | 0,005 | **0,030** | **reale** (+8,5 e +3,3 punti nelle due metà) | — |
| F: Noon Curve in tempo reale (nostra definizione) | 2121 | 23,4 % | 24,1 % | 0,77 | 1,00 | spiegato dal random walk | 82 % (condizionata) |

**Cosa si impara.**
- Le percentuali pubblicate sono quasi tutte geometria. Un percorso casuale con la stessa volatilità ora per
  ora e la stessa volatilità del giorno dà già il 71 % sul ritorno delle 08:00 (lo studio del documento
  stimava 72-75 %) e il 65 % sullo sweep orario. Per lo sweep orario il reale fa addirittura **peggio** del
  caso. La distanza fra il 62 % nostro e il 75-85 % dichiarato viene dalle definizioni, non dal mercato.
- Il placebo semplice del documento dà 69,3 % su A: più basso di quello scalato, quindi avrebbe fatto
  sembrare «reale» un effetto che non lo è.
- **E è l'unica regolarità**: l'apertura di mezzanotte viene ritoccata nelle RTH 6 punti percentuali più
  spesso del caso, in entrambe le metà. È coerente con la lieve tendenza di NQ a tornare indietro già nota,
  ed è un tasso di tocco, non un trade. Per il PREREG resta descrittiva in questo giro: mandarla in
  validazione come regolarità richiede un addendum con un riferimento casuale fissato prima.
- **B, il trade**: lordo −0,16 punti, netto a 0,75 −0,91, metà 2010-14 −1,00 e 2015-18 −2,03 a 1,25; 2 anni
  positivi su 9. Nessun criterio del §3 è superato.
- F: la nostra definizione di Noon Curve non riproduce quella di nqstats (23 % contro 82 %). Il
  condizionamento sulle sessioni «opposte» aggiunge solo 1,5 punti, contro i circa 15 stimati nel documento.
  Il test F quindi non dice nulla sulla statistica pubblicata, ed è un limite dichiarato.

Descrittivi: C per terzo d'ora dello sweep 73 / 46 / 17 %. D per fascia di distanza (< 0,25 % … > 1,5 %)
84 / 62 / 45 / 50 / 63 %, con n 203 / 128 / 89 / 14 / 8. E: RTH che apre sopra il livello 68 %, sotto 74 %.

Il valore della famiglia è lo strumento: il motore «percorso casuale scalato» è in `s01_primary.py` (`World`)
e può verificare qualunque «X % di ritocco». Nessun candidato: la validazione non è usata.
