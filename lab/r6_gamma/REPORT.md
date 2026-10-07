# r6_gamma — report (2026-09-30, solo discovery)

Pre-registrazione: `PREREG.md` e PROTOCOLLO §19. Codice committato prima dell'esecuzione (`0d04dc0`). Righe
nel registro: 7 (Passo 0, primo giro con bug, secondo giro).

**Verdetto: il classificatore non passa. Il GEX si chiude come filtro per NQ.**

| test | coefficiente | t (NW 5) | p unilaterale | p Holm | metà 2010-14 | metà 2015-18 | placebo p |
|---|---|---|---|---|---|---|---|
| A: VR6 ~ 1[GEX<0] | +0,038 | 1,67 | 0,048 | 0,096 | +0,045 (t 1,40) | −0,006 (t −0,21) | 0,065 |
| B: VR6 ~ rango GEX | −0,067 | −2,40 | 0,008 | **0,025** | −0,097 (t −2,22) | −0,063 (t −1,67) | **0,003** |
| C: autocorr. 1m ~ 1[GEX<0] | +0,008 | 0,96 | 0,168 | 0,168 | +0,019 (t 1,16) | −0,003 (t −0,28) | 0,21 |

Il test B supera tre condizioni su quattro: Holm, stesso segno con t ≥ 1 in entrambe le metà, placebo. Fallisce
la quarta, cioè la dimensione minima fissata: passare dal rango più basso al più alto cambia VR6 di 0,067,
sotto la soglia di 0,10 scelta perché l'effetto regga i costi. L'effetto sembra reale ma è piccolo: con un GEX
basso le giornate insistono un po' di più (VR6 medio 0,90, dove 1 è un percorso casuale). La regola non si
cambia dopo aver visto il numero.

**Bug trovato dopo il primo giro.** Nei giorni prima di maggio 2011, quando il GEX non esiste, l'indicatore
«GEX < 0» valeva 0 invece di essere mancante. Nel primo giro A aveva quindi n = 2116 invece di 1893: p Holm
0,045, metà 2015-18 t −0,21, placebo 0,06. Il verdetto non cambia (A falliva comunque su metà e placebo) e B
non era toccato. Correzione: `where(GEX.notna())`. Entrambi i giri sono nel registro.

Descrittivo, VR6 medio per terzile di GEX × terzile di VXN: vedi `results.json`. Nessun candidato: la
validazione non è usata.
