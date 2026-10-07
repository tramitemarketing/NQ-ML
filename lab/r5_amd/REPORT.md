# r5_amd — il modello «AMD» del video di Tmac, messo alla prova (2026-09-28)

**In una riga:** tradotto in regole meccaniche e testato su 2010-06 → 2018-12 (2.100+ sessioni NQ), il
modello del video **non ha vantaggio**: il test primario pre-registrato perde −0,26 punti netti a trade
(1/9 anni positivi), la metà «contro trend» che il video indica come il suo punto di forza perde −0,89
(2/9), e in unità di rischio il lordo vale **+0,03R** [−0,19; +0,26], cioè zero. **Zero candidati**:
validazione e conferma non sono state usate. 49 righe nel registro (`lab/ledger/r5_amd.jsonl`).

## Il video
«How to trade high RR the RIGHT way (trend days vs reversal days)», Tmac, 2026-09-27, 11 minuti. Modello
ICT «AMD» (accumulazione → manipolazione → distribuzione):
- Asia e Londra accumulano; all'apertura di New York il prezzo «manipola» oltre il massimo notturno
  (Judas swing).
- Uno short contro una settimana rialzista si fa **solo** se la manipolazione arriva in un «PD array» di
  timeframe alto (order block a 4 ore): lì finiscono insieme la manipolazione intraday e la distribuzione
  del timeframe alto.
- Ingresso a limite sulla mitigazione dell'order block a 2 minuti formato in manipolazione; stop sopra il
  massimo; obiettivo l'ultimo swing / minimo asiatico o l'apertura del giorno. Trade mostrato: 12R.
- Le «prove» sono P&L di membri del Discord su **un solo giorno**. Sono aneddoti con selezione del
  sopravvissuto (chi ha perso non manda lo screenshot) e non entrano nella valutazione.

## Traduzione meccanica
Pre-registrata e committata **prima** di qualunque numero (`PREREG.md`, commit `ec42841`). Punti chiave:
OB 4h = ultima candela 4h rialzista seguita da una che chiude sotto il suo minimo, zona [open, high], nota
solo a candela chiusa, valida fino al primo tocco e per 30 sessioni; manipolazione = nella finestra
08:30-11:59 il prezzo supera il massimo notturno (18:00-08:29) **e** tocca per la prima volta un OB 4h;
ingresso = limite all'open dell'ultima candela 2m rialzista prima del massimo, armato quando una candela
2m chiude sotto il suo minimo, riempito solo con trade-through di 1 tick; stop = massimo + 1 tick;
obiettivo = minimo asiatico (18:00-23:59); uscita 15:59. Long speculare. Costi 0,75 punti a/r.

Cosa del video **non** è traducibile e quindi non è testato: il «mini ciclo» riconosciuto a occhio, gli
OB di altri timeframe «trascinati» da giorni prima (l'M15 di martedì), il giudizio discrezionale su quale
bassa sia «supportata». Chi sostiene che il vantaggio stia lì sostiene una cosa non falsificabile.

## Risultati (discovery 2010-06 → 2018-12, punti netti a contratto)

| test | cosa | n | netto | CI 95 % | p (>0) | anni + | senza 20 migliori |
|---|---|---|---|---|---|---|---|
| **P0** | modello completo, ambo i lati | 458 | **−0,26** | [−1,42; +1,01] | 0,66 | 1/9 | −2,29 |
| **P0_ct** | solo contro il trend di 5 sessioni (tesi del video) | 213 | **−0,89** | [−2,45; +0,88] | 0,86 | 2/9 | −3,90 |
| C5_pro | solo a favore del trend | 229 | +0,08 | [−1,52; +1,98] | 0,45 | 5/9 | −2,81 |
| P0 short / long | | 238 / 220 | +0,12 / −0,68 | | 0,43 / 0,81 | 3/9 / 4/9 | |
| C1 | senza la condizione OB 4h (solo Judas) | 1.797 | −0,49 | [−1,05; +0,11] | 0,95 | 2/9 | −1,33 |
| C2 | OB 4h senza presa del massimo notturno | 571 | −0,69 | [−1,59; +0,28] | 0,93 | 1/9 | −2,26 |
| C4 | specchio (continuazione) | 458 | −0,35 | [−1,40; +0,75] | 0,73 | 4/9 | −2,24 |
| C3 | placebo: zone OB spostate (20 semi) | ~384 | −1,97 (da −2,91 a −0,87) | | | | |

Per anno (P0): 2010 −0,56 · 2011 −2,54 · 2012 −0,18 · 2013 −0,02 · 2014 −0,76 · 2015 −2,77 · 2016 −0,37 ·
2017 −0,03 · 2018 +5,94. Uscite: 347 stop, 83 obiettivo, 28 a tempo. Vincenti 23 %. Beta irrilevante
(beta-corretto −0,25).

**Sensibilità** (11 varianti: zona [low, high], età OB 10/60, finestra fino alle 10:59/12:59, obiettivi
mezzanotte/2R/3R/fine giornata, ingresso a mercato): tutte fra −0,75 e +0,08 netti, nessuna con p < 0,4.
Il risultato non dipende da una scelta di traduzione.

## Perché non funziona (anatomia)
- **Il lordo in R è zero**: +0,03R [−0,19; +0,26]. Non c'è un vantaggio che i costi erodono: non c'è
  vantaggio.
- **Lo stop stretto moltiplica i costi**: stop mediano 4 punti, quindi 0,75 punti di costo = **0,19R a
  trade**. Una strategia che vince il 23 % delle volte deve incassare in media circa 4,2R lordi sulle vincenti solo
  per pareggiare i costi.
- **Il 12R è raro**: ≥ 2R nel 15 % dei trade, ≥ 5R nel 4,8 %, ≥ 10R nello **0,9 %** (circa un trade ogni
  due anni). Il video mostra il caso da 12R; il sistema produce molto più spesso −1R.
- **La tesi contro-trend va nel verso sbagliato**: la metà contro-trend è la peggiore (−0,89), quella a
  favore del trend è piatta (+0,08). Il consiglio generale del video («di norma segui il trend») è il più
  sensato, ma nemmeno lì c'è un vantaggio netto.
- **L'OB 4h non aggiunge informazione**: con OB (−0,26) e senza (C1 −0,49) sono statisticamente uguali.
  Il placebo C3 (−1,97) va peggio del vero, ma il confronto non è pulito (vedi deviazioni): le zone
  spostate sono più lontane dal prezzo e selezionano mattine diverse.

## Proposte (addendum 1, dichiarate e committate prima di farle girare, `5ce9764`)
Motivate dall'anatomia, quindi a posteriori; soglia p < 0,05/3 e tutti i criteri.

| proposta | idea | n | netto | CI | p | anni + | d20 | esito |
|---|---|---|---|---|---|---|---|---|
| PA | stop almeno 0,10·ATR20 (costo più leggero in R) | 456 | −0,07 | [−1,34; +1,29] | 0,53 | 5/9 | −2,33 | NO |
| PB | solo se il minimo asiatico è entro 0,5·ATR20 | 203 | +1,20 | [−0,34; +2,99] | 0,084 | 6/9 | −1,60 | NO |
| PC | «gira la candela»: ingresso oltre l'apertura di mezzanotte, obiettivo mezzanotte | 443 | −0,33 | [−1,34; +0,80] | 0,73 | 3/9 | −2,09 | NO |

PB è l'unica con il segno giusto, ma il +1,20 viene dal 2018 (+13,26 a trade; senza il 2018: +0,10, n 186, p 0,43)
e senza i 20 migliori è −1,60. È esattamente la forma dei candidati che nel laboratorio si sono sciolti
in validazione. Non la promuovo.

## Deviazioni dalla pre-registrazione (dichiarate)
- C3: la PREREG diceva «OB di un'altra data, stessa larghezza»; è stato implementato come spostamento della
  zona di u·ATR20 (u ~ U(0,5; 2), segno casuale, forzato sopra il prezzo alla nascita). Stesso spirito,
  forma diversa; non cambia nessuna conclusione (C1 basta a dire che l'OB non aggiunge).
- Nessun audit anti-look-ahead meccanico: non ci sono candidati da inviare. La simulazione usa solo OB noti
  a candela 4h chiusa, livelli notturni chiusi alle 08:29 e riempimenti a barra successiva.

## Conclusione
Il modello AMD del video, nella forma più fedele che si possa scrivere senza discrezionalità, su 8,5 anni
di NQ ha un valore atteso lordo nullo e netto negativo; il pezzo che il video vende come chiave (lo short
contro trend quando si tocca l'OB 4h) è la parte peggiore. Il trade da 12R del video è un evento raro e
reale, non un vantaggio. Nessun candidato: i blocchi di validazione e conferma restano intatti.

File: `PREREG.md` (spec e addendum), `common.py` (simulatore), `s00_sanity.py` (controllo meccanico),
`s01_battery.py` (P0, controlli, sensibilità), `s02_anatomy.py` (lordo, R, code), `s03_proposals.py`,
`candidates.py` (vuota), `test_candidates.py` (riproduce P0).
