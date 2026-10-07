# Famiglia r4_implied — volatilità implicita e NQ (giro 4, solo discovery 2010-06 → 2018-12)

**In sintesi.** Ho registrato 295 test in `lab/ledger/r4_implied.jsonl` e congelato **2 candidati, entrambi regolarità**:
la volatilità implicita del Nasdaq-100 (VXN) migliora la previsione della volatilità realizzata di domani, anche
oltre alle due regolarità confermate nel giro 1. **Nessun candidato tradeable**: nessun segnale basato sull'implicita
(premio per il rischio di varianza, struttura a termine, VVIX, SKEW) predice la direzione di NQ in modo robusto. I
pochi numeri brillanti erano artefatti di selezione, di finestre sovrapposte, oppure ritocchi di idee già bocciate.

## Regole che ho seguito (fissate prima di guardare)
- Dati esterni **solo** tramite `extdata.known_at_open(...)`: per la sessione S il valore usato è la chiusura CBOE del
  giorno lavorativo precedente, già nota alle 16:15 di S-1. Non ho mai letto i CSV né chiamato `extdata.raw()`.
  Ingressi all'apertura RTH di S o più tardi.
- HAR causale come in `lab/vol`: OLS mobile su 500 sessioni (minimo 250), con regressori ≤ S-1.
- Unità: la ricerca esplorativa è in % del prezzo grezzo, i tradeable in punti netti (0,75 punti andata e ritorno),
  le regolarità in log-varianza.
- Orizzonti di più giorni: P&L giornaliero a portafogli sovrapposti, così resta una riga al giorno. Ogni rendimento è
  misurato **in eccesso sulla deriva del campione**, cioè al netto del beta.
- VRP = log(VXN²/252) − previsione HAR del log RV RTH. È un rapporto in log, quindi il livello non conta: conta
  l'ordinamento. Soglie sempre come percentile mobile causale a 250 sessioni.

## Ipotesi provate (≥ 20) ed esito

| # | ipotesi | test | esito |
|---|---|---|---|
| H01 | 14 segnali × orizzonti 1/5/20 g × {timing lineare, quintile alto long, quintile basso long}: VRP (4 varianti: HAR, RV22, RV5, livelli), livello VXN, VIX/VIX3M, VIX9D/VIX, VVIX, VVIX/VIX, SKEW, VXN/VIX, ΔVXN 1 g e 5 g, VXN vs media 20 | 126 | **3/126 con p<0,05** (il caso ne attende ~6). Il VRP non predice nulla a nessun orizzonte (p 0,71-0,96; 3-6 anni positivi su 8) |
| H02 | L'implicita aggiunge informazione all'HAR per prevedere la volatilità? Varianti: +VXN, solo VXN, struttura a termine, VIX9D, VVIX, SKEW, VIX, oltre il range notturno, range RTH, settimana successiva, VRP → sorpresa di vol | 11 | **Sì.** HAR+VXN: +0,025, 8/8 anni. R² fuori campione 0,624 → 0,655. Anche su range RTH (8/8), settimana (8/8) e oltre il range notturno (7/8). VVIX, SKEW e VIX9D non aggiungono nulla oltre al VXN; la struttura a termine aggiunge poco (+0,007, p 0,02) |
| H03 | Intraday condizionato al regime (VRP, VXN, VIX9D/VIX: quintili): fade del gap (fino alle 16:00 e alle 10:30), prosecuzione della prima ora, ultima mezz'ora, long RTH, long notte; fade o prosecuzione dei gap oltre k σ implicite | 48 | Si veda sotto: ultima mezz'ora con VXN alto (ritocco, escluso) e VIX9D/VIX basso (H04, crolla) |
| H04 | Approfondimento: «VIX9D/VIX basso → deriva RTH positiva» | 24 | **Crolla.** Non è monotono (decili 1-2 +0,09/+0,11 %, decile 3 −0,15 %). Con soglia 0,3 va a zero. Soglie assolute n.s., segnale ritardato n.s., regressione con controlli t 0,74 |
| H05A | Bande di movimento implicito (apertura ± k σ_imp, k 0,5/0,75/1): prosecuzione o fade fino alle 16:00 | 6 | Niente (prosecuzione +0,2/+1,1 n.s.; il fade perde) |
| H05B/H06 | SKEW e VVIX alti → più giorni di coda sinistra nei 5/20 giorni successivi | 2+8 | p 0,0001 con bootstrap per giorno, ma sono **finestre sovrapposte**: con blocchi da 60 sessioni p 0,17-0,52; in OLS HAC con controlli t 0,1-1,5. **Artefatto** |
| H05C/H07 | VVIX → ampiezza della sorpresa di vol | 1+2 | +0,037, p 0,0008, ma aggiunge **zero** (+0,0001) a un modello con la media dei residui passati |
| H05D | Vol-targeting con 1/VXN² (long open→open) | 1 | Nessuna differenza dal long costante (+0,0002) |
| H05E | Ingresso e uscita dalla backwardation VIX/VIX3M → long 5/10/20 g | 6 | 56 eventi raggruppati nel 2011, 2015 e 2018. Uscita h10 +1,13 % (p 0,016), senza i 20 migliori −0,63 e gli altri orizzonti n.s. Pochi episodi di stress: **scartato** |
| H05F | Prima ora «sorpresa» (RV 9:30-10:30 / implicita): prosecuzione della prima ora; RV della prima ora → RV del resto del giorno | 3 | La direzione non c'è. Regolarità vol intraday forte (8/8) ma nota e non legata all'implicita |
| H07 | Robustezza delle regolarità: finestre 250/1000, VIX invece di VXN, livello invece di log, placebo VXN ritardato 5 g, blocchi mobili 20 | 18 | Il candidato 1 regge ovunque, tranne la versione in livello (n.s.). Il placebo ritardato vale −0,001: l'informazione utile è quella **fresca** |
| H08 | Reversal a 1 giorno condizionato a VXN/VRP (Nagel 2012); contro-shock oltre k σ implicite | 14 | Reversal a 1 g: niente in nessun regime. Contro-shock k 1,5 per 5 g: +52,8 netti (vedi H09) |
| H09 | Stress del contro-shock: griglia k × h, lato long o short, σ HAR o soglia fissa invece di σ implicita, bootstrap per cluster | 27 | Positivo su tutta la griglia ma con un picco isolato a h=5. Lo porta **tutto il lato long** (+65,9; short n.s.). Con σ HAR funziona uguale, quindi l'implicita non serve. È l'H01 del giro 1 (`multiday`, «long dopo −1,5 σ20, 5 giorni») ritoccato: **escluso per regola** |

Totale: **295 test registrati**. Sul solo segnale ordinato H01, la distribuzione dei p è quella del caso.

## Cosa ho scartato e perché (le cose che sembravano vere)
1. **Premio per il rischio di varianza → rendimenti.** È l'idea principale della famiglia (Bollerslev-Tauchen-Zhou) e
   su NQ a 1-20 giorni non c'è: in nessuna delle 4 definizioni né delle 3 forme, p ≥ 0,09. Nel campione di BTZ il
   VRP predice a 1-4 **mesi**, sull'indice e con dati mensili. Con 8 anni di discovery quell'orizzonte ha ~25 osservazioni
   indipendenti, troppo poche per un test serio, quindi non l'ho spinto oltre.
2. **Ultima mezz'ora nel verso della giornata quando VXN è alto** (+2,99 netti, p 0,003, senza i 20 migliori −0,04).
   È il candidato bocciato del giro 1 `intraday_momentum_hivol_last30`, con il regime misurato dall'implicita invece che
   dalla realizzata: è un ritocco, non si ripresenta. Nota: il regime basso dà −1,15 (0/8 anni), coerente con la lezione
   «negativo in regime calmo». Anni: 2012, 2016 e 2017 negativi.
3. **VIX9D/VIX basso → long RTH** (+3,33 netti, p 0,002, 7/8): nasce dalla selezione fra 126 test e non è monotono (vedi H04).
4. **SKEW/VVIX → code**: bootstrap sbagliato per finestre sovrapposte. Con la stima corretta non c'è nulla. È una
   lezione di metodo: con obiettivi a 20 giorni il bootstrap per giorno dà p 0,0001 al rumore.
5. **Contro-shock scalato sull'implicita**: vedi H09. Da notare che nel 2018 il lato short perde (−1,1 su 9 eventi)
   mentre il long guadagna +115 su 13: è il comportamento del «compra dopo i ribassi» in un mercato che sale, lo stesso
   che il 2022 ha già smentito nel giro 1.

## Candidati congelati (`lab/r4_implied/candidates.py`, test: `python -m lab.r4_implied.test_candidates`)

| id | tipo | n | media (log-var²) | CI 95 % | p bilaterale | anni + | senza top 20 |
|---|---|---|---|---|---|---|---|
| `r4_implied_har_plus_vxn` | regolarità, segno + | 1.849 | **+0,02541** | [+0,01566; +0,03572] | 0,0001 | 8/8 | +0,013 |
| `r4_implied_on_plus_vxn` | regolarità, segno + | 1.849 | **+0,01227** | [+0,00531; +0,01949] | 0,0009 | 7/8 (2016 −0,002) | +0,004 |

- **Candidato 1**: guadagno di errore quadratico fuori campione aggiungendo log(VXN²/252) di ieri all'HAR. R² 0,624
  → 0,655. Minimo annuale +0,006 (2012), massimo +0,058 (2018). Blocchi mobili da 20: p 0,0002. Finestre 250/1000:
  +0,024/+0,022. Col VIX al posto del VXN +0,015 (l'indice specifico del Nasdaq è più informativo). Placebo con VXN
  ritardato di 5 sessioni: −0,001.
- **Candidato 2**: stesso guadagno, ma con una base che contiene già il range notturno (regolarità confermata del
  giro 1). R² 0,652 → 0,667. Circa metà del contributo dell'implicita è già nel range notturno; l'altra metà è
  informazione nuova.
- Entrambi sono **letteratura nota** e **non incassabili con il solo future**: dicono quanto si muoverà NQ, non dove.
  Servono per dimensionare rischio e stop o per le opzioni. Sono correlati fra loro: non sono due prove indipendenti.
- Causalità: il VXN entra solo tramite `known_at_open` (chiusura del giorno lavorativo precedente), l'HAR usa dati
  ≤ S-1, il range notturno si chiude alle 09:29. Funzionano su qualunque fase con `warmup_days=560`.

## Note per il controller
- Nessun bug trovato in `core.py`. In `extdata.known_at_open` il ritardo `BDay(1)` non conosce le festività USA;
  questo può solo rendere il valore più vecchio, mai più recente (è il ffill dell'ultimo valore disponibile), quindi
  va a favore della prudenza.
- Nel discovery VIX9D esiste solo dal 2011-01. I test che lo usano hanno n più piccolo (1.724 invece di 1.849).
- Non ho toccato file fuori da `lab/r4_implied/` e `lab/ledger/r4_implied.jsonl`.
