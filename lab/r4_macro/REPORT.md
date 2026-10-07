# r4_macro — tassi, curva e dollaro → NQ (giro 4, solo discovery)

**Esito: 83 test registrati (`lab/ledger/r4_macro.jsonl`, più 98 placebo a spostamento circolare contati in
una riga) → 0 candidati.** Un segnale ha un'ombra di evidenza (sotto), ma non abbastanza da meritare uno
slot di Bonferroni nel K del giro 4.

## Convenzioni (fissate prima di guardare)
- Serie esterne solo da `extdata.known_at_open` (tassi +2 g.l., dollaro +8 g. di calendario), chieste su un
  calendario lavorativo che parte 400 giorni prima per avere i lookback, poi lette alle sessioni NQ.
- Ingresso/uscita all'**apertura RTH** (09:30); NQ noto fino alla chiusura RTH di S−1. Rendimento % =
  Δadj_open / open grezzo. Il 10 anni noto a S è quello di ~2 g.l. prima: per le correlazioni azioni-tassi
  si abbina al rendimento NQ della sessione S−2.
- Inferenza: IC di Spearman con bootstrap a blocchi **mensili** (finestre a h giorni sovrapposte);
  controllo del beta con la deriva open→open e con `lab.controller.beta_component`.
- **Limite dichiarato del campione**: 2010-2018 è quasi tutto ZIRP (3 mesi ≈ 0 fino a fine 2015), poi rialzi
  lenti; correlazione mobile NQ-tassi positiva l'87 % del tempo (regime «crescita»). Il regime 2022
  (inflazione, rialzi rapidi, correlazione negativa) è **fuori campione**. La curva non si è mai invertita
  (minimo 10a-2a 0,11): le ipotesi di inversione non sono testabili.
- Unica variabile «vol» usata: il VIX come controllo (H28). Niente vol implicita/VRP/struttura (altra famiglia).

## Ipotesi provate (tutte sul discovery; IC su rendimento %, p bilaterale a blocchi mensili)
| id | ipotesi | risultato |
|---|---|---|
| H01 | Δ10a 1g → NQ 1g | IC +0,001, p 0,97 |
| H02 | Δ10a 5g → NQ 5g | −0,026, p 0,44 |
| H03 | Δ10a 20g → NQ 20g | **−0,148**, p 0,024, 8/9 anni negativi |
| H04 | Δ3 mesi 5g/20g → NQ | −0,008 / −0,037, nulla |
| H05 | pendenza 10a-2a livello / z-score | +0,041 / −0,089, nulla |
| H06 | Δ pendenza 5g/20g | +0,002 / −0,084 (p 0,16) |
| H07 | 10a z-score a 250g → NQ 20g | −0,137, p 0,046 |
| H08 | dollaro 1/5/20g → NQ | +0,012 / +0,018 / −0,052, nulla |
| H10 | regime di correlazione NQ-tassi (60g) | corr>0: NQ 20g +1,19 % contro +1,88 % (p 0,04, 3/9 anni); modula H03 (IC −0,31 con corr>0,2, −0,05 altrimenti: split a posteriori, non usato) ; corr×Δ1g → 1g nulla |
| H11 | shock di tasso (|Δ1g|>2σ, 104 giorni) → continuazione NQ 1/5/20g | nulla (p 0,62-0,66) |
| H12 | reazione ritardata (NQ non ha reagito allo shock; «gap» beta×Δtasso − ret NQ) | nulla (p 0,90-0,95) |
| H13 | momentum 10a 60g → NQ 20g | −0,132, p 0,057 |
| H14 | livello 3 mesi (carry del cash) | −0,062, nulla |
| H15 | vol realizzata del 10a → NQ 20g | +0,084, nulla |
| H16 | stretta (tassi su e dollaro su a 20g) → NQ 20g | −0,70 pp vs resto, p 0,10 |
| H17 | vol dei tassi → vol realizzata NQ oltre la sua vol (regolarità) | IC +0,028, nulla |
| H18 | curva piatta (<0,5, quasi solo 2018) | diagnostico, n piccolo, p 0,12 |
| H19 | Δ10a / dollaro noti all'apertura → NQ open→close della stessa sessione | IC 0,01-0,02, nulla |
| H20 | 10a al massimo a 52 settimane → NQ 20g | +0,5 pp vs resto, p 0,53 |
| H28 | H03 (d40) con VIX basso/alto (mediana espanding) | −0,15 / −0,39 |
| H31 | momentum tassi e NQ concordi → NQ 20g | p 0,27 |
| H32 | d40 standardizzato per la vol dei tassi | −0,213 (identico a d40) |
| H36-37 | dollaro 60g; spread 10a-3m livello / Δ40g | nulla / nulla / −0,185 (è lo stesso segnale: Δ del lato lungo) |
| H39 | grandi movimenti del dollaro → NQ 5g | nulla |

## L'unica osservazione: «tassi lunghi saliti nelle ultime ~8 settimane → NQ più debole nel mese dopo»
- Superficie lookback × orizzonte (H22): IC negativo in tutte le 15 celle (−0,08 … −0,21), massimo a
  L=40, h=20: **IC −0,213** [−0,34; −0,09], 8/9 anni negativi, negativo in entrambe le metà (2010-14 −0,18,
  2015-18 −0,25). Conta il lato **lungo** (10 anni, pendenza), non il 3 mesi (−0,06) né il dollaro.
- Non è il reversal di NQ travestito: nella regressione congiunta con il momentum NQ a 20 e 40 giorni il
  coefficiente di d40 resta −0,157 [−0,31; −0,02], quello del momentum NQ va a ~0.
- Placebo a spostamento circolare del segnale (98 spostamenti, stessa persistenza): IC placebo 0 ± 0,08;
  nessuno arriva a −0,213 (z ≈ 2,6). **Prima** della selezione (≈16 segnali esplorati, 5 lookback, 3 orizzonti).
- **Ma nella forma che il controller può giudicare correttamente** (righe giornaliere non sovrapposte:
  −segno(d40) × rendimento open→open del giorno dopo) l'effetto è debole: **+4,4 bp/giorno [−0,04; +8,8],
  p 0,053**, 8/9 anni; e la superficie non regge: L=20 −1,4 bp (segno opposto), L=30 +3,8 (p 0,10),
  L=60 +2,7 (p 0,24), segnale continuo +2,4 (p 0,33). L'IC a 20 giorni «più forte» è in gran parte l'effetto
  della sovrapposizione (IC_h ≈ IC_1·√h per un segnale persistente), non informazione in più.
- **Versione negoziabile** (T1: long/short −segno(d40), tenuto finché il segno non cambia, 177 trade, ~12
  sessioni): +17,9 punti netti [−1,7; +38,1], p 0,040, 8/9 anni; netto del beta del controller +16,4 p 0,049;
  **senza i 20 migliori −13,2** (fallisce già in discovery il criterio 4). Solo long (T2) +41,7 ma il beta se
  ne prende la maggior parte (+16,3, p 0,078; senza i 20 migliori −5,6); solo short (T3) −7,8. Placebo
  circolare: il 5 % dei segnali spostati fa un EV ≥ del reale.

### Perché non lo promuovo
1. Evidenza corretta per la sovrapposizione ≈ p 0,05, scelta come migliore di una griglia dopo ~16 segnali:
   compatibile con il caso.
2. Tradeable: fallisce «senza i 20 migliori» già nel discovery.
3. **Contaminazione**: come modello conosco a grandi linee il 2019-2026 (2020 tassi giù e Nasdaq su, 2022
   tassi su e Nasdaq giù). Questo segno sarebbe favorito proprio dal regime che il discovery non contiene;
   un PASS in validazione non sarebbe una prova pulita. Il controller conosce gli stessi fatti (PROTOCOLLO §15).
4. Ogni candidato aumenta K e toglie potenza agli altri del giro 4.
Se si volesse comunque testarlo, andrebbe fatto su un **altro strumento** (ES/RTY) con la forma giornaliera
congelata qui (`candidates.observation_d40_daily`), non sul blocco di validazione di NQ.

## File
`common.py` (dati e statistica), `h01…h08` (script dei test, in ordine), `candidates.py` (lista vuota +
funzione dell'osservazione), `test_candidates.py` (riproduce +4,45 bp p 0,060 — esclusi i giorni con d40
esattamente 0; +4,39 p 0,053 contandoli come zero — e IC −0,213). Nessun bug trovato in `core.py`/`extdata.py`.
Nota: nei test «shock» (H11-H12) la colonna `years_pos` del registro non è significativa (differenza vs resto
non definita su un campione mascherato).
