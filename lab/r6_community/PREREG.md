# r6_community — pre-registrazione (2026-09-30, PRIMA di guardare qualunque risultato)

Ipotesi 4 del documento dell'utente del 2026-09-29. Regole comuni in `lab/PROTOCOLLO.md` §19.

## Tesi
Le «probabilità» pubblicate su NQ (nqstats, edgeful, tradingstats.net, lo script TradingView NQ Hourly
Edge) potrebbero essere in gran parte geometria del caso: un prezzo che si muove a caso tocca spesso i
livelli vicini. Il test le rifà su un NQ «senza memoria» e le confronta con la versione reale. Lo scopo
principale è uno strumento di revisione, coerente con il prodotto Controprova. Trovare un vantaggio
netto è improbabile: sono tutte varianti del fade, famiglia già chiusa.

## Passo 0 (risposte prima dei test, solo discovery)
1. Copertura 00:00-09:30 ET per anno (% di minuti con una barra).
2. σ per il test A: deviazione standard dei 20 rendimenti close-to-close delle 16:00 fino a t−1,
   moltiplicata per P_08:00. Le nostre definizioni possono differire da quelle di nqstats, e va detto.
3. Placebo: rendimenti a 1 minuto rimescolati fra giorni dello stesso anno, a parità di minuto ET,
   200 storie. Verificare che conservi il profilo di volatilità per minuto e le code.
4. Fill: ingresso e target a limite eseguiti solo con attraversamento di almeno 1 tick; uscita a tempo al
   close della barra. Regole identiche nel placebo.

## Definizioni nostre (da dichiarare nel report)
O_08 = open della barra delle 08:00 ET.
- **A — AM TBR**: primo tocco di O_08 ± 0,25σ fra le 08:00 e le 08:59. Successo = ritorno a O_08 entro
  le 12:00.
- **B — trade di A**: fade al tocco, target O_08, uscita alle 12:00. Sensibilità, non decisiva: stop a
  1σ oltre l'ingresso. EV lordo e netto (0,75 e 1,25) in punti, bps e σ.
- **C — ore 08-15 ET**: l'ora apre dentro il range dell'ora precedente, poi c'è il primo sweep oltre
  un suo estremo. Successo = ritorno all'apertura dell'ora entro la fine dell'ora. Si riporta anche per
  terzo d'ora dello sweep.
- **D — tocco dell'apertura del lunedì** (09:30; se festivo, primo giorno della settimana) nelle RTH da
  martedì a venerdì. Fasce di distanza fra l'apertura RTH del martedì e l'apertura del lunedì: < 0,25 %,
  0,25-0,5 %, 0,5-1 %, 1-1,5 %, > 1,5 %. Il test è sul tasso complessivo.
- **E — ritocco dell'apertura delle 00:00 ET** nelle RTH, sopra e sotto separati. Il test è sul tasso
  complessivo.
- **F — Noon Curve** (AM 08-12, PM 12-16). Si riporta la versione pubblicata, condizionata a sessioni
  «opposte», che si riconoscono solo alle 16:00. Si testa la versione in tempo reale, che usa solo
  informazione disponibile entro le 12:00. Si riporta quanti punti percentuali aggiunge il
  condizionamento sul futuro.

## Regole di decisione (fissate ora)
- Holm k = 6 su A-F, con p = (1 + #placebo ≥ reale)/201.
- Claim «reale» (A, C, D, E, F): il tasso supera il placebo con p di Holm < 0,05 e lo scarto ha lo stesso
  segno in entrambe le metà. Altrimenti è «spiegato dal random walk».
- «Sfruttabile» solo B, se valgono tutte:
  - EV netto a 1,25 > 0 in entrambe le metà;
  - p di Holm < 0,05;
  - placebo ≥ 95° percentile;
  - i criteri del §19.
  Solo allora B diventa candidato `tradeable`.
- I claim reali di A e C-F restano descrittivi in questo giro. Mandarli in validazione come regolarità
  richiederebbe un riferimento casuale fissato prima, cioè un addendum scritto prima della validazione.

Onestà dichiarata ora: il 2019-2023 ha già giudicato fade simili (`micro_overnight_break_fade`, value
area). Il revisore vale comunque, perché la sua risposta principale («geometria o effetto?») non dipende
dal trade.

## Addendum 1 (2026-09-30, dopo il Passo 0 e prima di qualunque test primario; deciso dall'utente)
Il Passo 0 (`lab/GIRO6_PASSO0.md`) ha mostrato che il rimescolamento semplice dei minuti fra i giorni non
conserva le code e la persistenza della volatilità giornaliera. La curtosi del rendimento RTH giornaliero
passa da 6,37 a 1,69 e l'autocorrelazione del suo valore assoluto da 0,26 a 0,10. La decisione si basa
solo sulla qualità del placebo, non su tassi di successo, che non sono stati guardati.

**Placebo primario: rimescolamento scalato.**
- Ogni sessione viene divisa per la propria volatilità realizzata (radice della somma dei quadrati dei
  rendimenti a 1 minuto della sessione, 18:00-16:59).
- I rendimenti standardizzati vengono rimescolati minuto per minuto fra le sessioni valide dello stesso
  anno, poi ogni sessione viene rimoltiplicata per la volatilità della sessione di destinazione.
- Le sessioni si concatenano dentro l'anno, partendo dal prezzo reale d'inizio anno.
- 200 storie, come nel PREREG; il σ dei test si ricalcola sulla storia placebo.
- Implementazione di riferimento: `shuffle(..., scaled=True)` in `lab/r6_community/s00_passo0.py`.

Il rimescolamento semplice del documento resta come descrittivo e non entra nelle regole di decisione.
Tutto il resto del PREREG resta invariato.
