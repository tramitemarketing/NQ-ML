# r2_analog: il mercato come sistema dinamico e come linguaggio (giro 2, solo discovery)

**Esito: 194 test registrati (`lab/ledger/r2_analog.jsonl`), 0 candidati.** Non regge niente che
appartenga davvero a questa famiglia. Le poche cose «vere» che ho trovato erano fatti già noti travestiti:
effetto leva, volatility clustering, discretezza del tick, autocorrelazione negativa a 1-5 minuti.

Tutte le convenzioni (rappresentazioni, K, finestre, biblioteca, unità, placebo) sono state scritte nella
docstring di `common.py` e in quella di ogni script **prima** di eseguirli. Unità: y = rendimento del
pomeriggio in unità di volatilità prevista (s5_hat = RV 5m media delle 20 sessioni precedenti); i trade
sono in punti netti (costi 0,75), con il beta del controller. Biblioteca degli analoghi: le 750 sessioni
valide precedenti, minimo 250. Per questo il discovery utile parte da metà 2011.

## 1. Previsione per analoghi (Lorenz / nearest neighbours)

**A01, griglia completa dichiarata: 60 configurazioni** = finestra della mattina {09:30→10:30, 11:00, 12:00}
× rappresentazione {cammino cumulativo euclideo, cammino + notte + ieri, forma (correlazione), incrementi,
DTW con banda 3} × K {10, 25, 50, 100}. Esito: pomeriggio dalla fine della finestra alle 15:59. Placebo:
200 insiemi di K giorni presi a caso dalla stessa biblioteca.

- **Direzione: niente.** IC fra −0,057 e +0,048 (|IC| medio 0,019). 26 IC su 60 sono positivi. 3/60 hanno
  p < 0,05, cioè esattamente quanti ne produce il caso. 5/60 cadono fuori dal 95 % dei placebo. L'unico
  gruppo coerente (forma, W=60, IC da −0,044 a −0,051 per tutti i K, cioè analoghi anti-predittivi) ha
  2/8 anni e 0/8 anni.
- **A02, selezione interna** (scelta su 2011-14, verifica su 2015-18 senza ritocchi): le 60 configurazioni
  hanno lo stesso segno nei due periodi nel **50 %** dei casi (placebo: 50,5 %). La migliore in A
  (forma W60 K100, IC −0,071) vale −0,027 in B, al percentile 0,80 dei placebo. Come trade in punti su
  2015-18 (C03): +0,83 netti [−2,04; +3,65], 3/4 anni, **senza i 20 migliori −2,84**.
- **C03, configurazione canonica fissata a priori** (W=90, cammino + contesto, K=25, 11:00→15:59, 1.851
  trade): +0,08 netti [−1,44; +1,67], 3/8 anni, netto meno beta −0,01, senza i 20 migliori −1,66. Il filtro
  di «accordo fra analoghi» (≥ 0,2 / ≥ 0,4) non aiuta: +0,08 (n 897) e −0,80 (n 175). Quando gli analoghi
  sono d'accordo, sono d'accordo sul lato long (quota long 78-90 %): è il beta, non un'informazione.
- **Analoghi di giorni** (C03: ultimi 5 giorni come vettore → RTH di oggi, K 25/50/100): IC −0,005 / −0,012
  / −0,046 (placebo 0,54 / 0,35 / 0,07). I trade netti valgono da −1,36 a −1,66 punti.
- **Volatilità: vera ma presa in prestito.** La lrv media degli analoghi è correlata alla vol del
  pomeriggio (0,15-0,54) e ha una correlazione parziale data la vol della mattina di 0,03-0,21 (placebo
  ~0,01, percentile 0,88-1,00 in tutte le 60 configurazioni). **A03**: fuori campione (OLS mobile 500
  sessioni), aggiunti a un benchmark lineare (vol della mattina, ultimi 30 minuti, notte, ieri, efficienza),
  gli analoghi portano R² da 0,452 a 0,468 (W90 contesto: q +0,010 [+0,004; +0,016], 5/7 anni; forma
  7/7 anni). **A04, controllo decisivo**: se il benchmark include il rendimento della mattina **con segno**
  (effetto leva), notte e ieri con segno, mlrv², mlrv×efficienza e la vol espressa in tick, gli analoghi
  non aggiungono più **nulla**. 18 prove, tutte con CI che contiene lo zero, q fra −0,0016 e +0,0017.
  Gli analoghi costruiti sulle sole feature scalari fanno lo stesso (zero). Anche la dispersione dei futuri
  degli analoghi (dpred) non aggiunge nulla. Conclusione: la «memoria delle traiettorie» sulla vol è
  l'effetto leva intraday più un po' di non linearità, cose che il giro 1 aveva già (vol A5,
  vol_leverage_sign). Non la presento.
- **C04, novità** (distanza media dai 10 analoghi più vicini: le mattine «senza precedenti»): non aggiunge
  nulla alla vol oltre al benchmark esteso (6 prove, tutti i CI contengono lo zero). Come prosecuzione o
  inversione della mattina: IC fra −0,044 e +0,019, niente.

## 2. Motivi simbolici (SAX)

**B01.** Alfabeto: terzili causali dello stesso slot 5m (250 sessioni precedenti), quindi il profilo orario
è tolto. Parole di lunghezza L. Selezione su A = 2011-15 (|t| > 2,576, errore standard a grappoli per
giorno), verifica su B = 2016-18 (stesso segno e t > 1,645). Placebo: 100 permutazioni dei giorni fra
parole ed esiti (stesso slot). Controllo lineare: gli stessi conteggi sul residuo dopo aver regredito l'esito
sulla somma dei rendimenti della parola e sull'ultimo rendimento.

| alfabeto / esito | L | parole | signif. in A | placebo media (p95) | confermate in B | placebo conf. | residuo lineare: signif. / conf. |
|---|---|---|---|---|---|---|---|
| 3 simboli, 30m | 3 | 27 | 0 | 0,15 (1) | 0 | 0,02 | 0 / 0 |
| 3 simboli, 30m | 4 | 81 | 3 | 0,65 (3) | 1 | 0,05 | 2 / 0 |
| 3 simboli, 60m | 3 | 27 | 1 | 0,06 (1) | 1 | 0,00 | 0 / 0 |
| 3 simboli, 60m | 4 | 81 | 3 | 0,62 (3) | 0 | 0,03 | 0 / 0 |
| 3 simboli, 15m | 3 | 27 | 2 | 0,18 (1) | 1 | 0,01 | 0 / 0 |
| 3 simboli, 15m | 4 | 81 | 4 | 0,64 (2) | 2 | 0,03 | 0 / 0 |
| 5 simboli, 30m | 2 | 25 | 0 | 0,13 (1) | 0 | 0,00 | 0 / 0 |
| 5 simboli, 30m | 3 | 125 | 2 | 1,16 (3) | 0 | 0,04 | 3 / 0 |
| 5 simboli, 60m | 2 | 25 | 0 | 0,08 (1) | 0 | 0,01 | 0 / 0 |
| 5 simboli, 60m | 3 | 125 | 2 | 1,02 (3) | 1 | 0,04 | 1 / 0 |

Sul grezzo trovo in tutto **17 motivi significativi in A contro ~4,7 attesi dai placebo**, e **6 confermati
in B contro ~0,2**. Sul residuo del modello lineare le parole confermate diventano **0 in tutte e 10 le
batterie**. I motivi «veri» (per esempio DDDU → 30 minuti successivi negativi, UUFD → positivi) sono il
ritorno alla media lineare già noto scritto in simboli, non una grammatica. I 6 trade sulle parole
confermate, misurati in B, hanno tutti CI che contiene lo zero (da −0,35 a +1,25 punti netti; il migliore
ha n = 366, [−0,34; +2,92]).

## 3. Altre idee di questo spirito

- **C01, la prevedibilità come quantità che cambia nel tempo.** L'autocorrelazione 5m di oggi non è
  prevista né dalla media delle 20 sessioni precedenti (+0,030 [−0,013; +0,074]) né da quella di ieri. Il
  variance ratio 30/5 non persiste (−0,002). Mattina e pomeriggio non condividono autocorrelazione, VR o
  efficienza. **Non esistono «regimi di prevedibilità» persistenti** da sfruttare.
- **C01/C02, compressione.** La complessità di Lempel-Ziv dei segni 1m della mattina sembrava prevedere un
  pomeriggio più calmo (parziale −0,093 [−0,134; −0,051]). Ma ha correlazione 0,81 con la quota di barre a
  rendimento zero: è la discretezza del tick, non la struttura. Con LZ binaria (zeri tolti) o con
  l'entropia di permutazione, e controllando zeri, rho della mattina e il benchmark esteso, il guadagno fuori
  campione è zero (q −0,0007 / −0,0007 / −0,0002, CI con lo zero). Una giornata «comprimibile» non è più
  prevedibile.
- **C01-P4/C05, informazione mutua** fra il simbolo successivo e gli ultimi L. Contro i placebo rimescolati
  dentro il giorno c'è un eccesso **reale in 8/8 anni**, ma minuscolo: in direzione ~1 mbit a 1m e
  0,7-1,4 mbit a 5m (l'equivalente di una correlazione ~0,04), in ampiezza 3-6 mbit. È volatility
  clustering più l'autocorrelazione negativa di brevissimo periodo già misurata dal progetto (VR < 1).
  Economicamente vale molto meno dei costi.

## Cosa ho scartato e perché (riassunto)

| idea | test | motivo |
|---|---|---|
| analoghi di mattine → direzione del pomeriggio | 60 + 1 + 4 | IC ≈ caso, la selezione interna non si replica, trade con CI che contengono lo zero |
| analoghi di giorni → direzione di oggi | 6 | IC ≤ 0, netto negativo |
| analoghi → vol del pomeriggio | 30 + 22 | spiegato del tutto da effetto leva, non linearità e tick (A04) |
| accordo e dispersione degli analoghi | dentro A03/A04/C03 | nessuna informazione né sull'affidabilità né sulla vol |
| novità della mattina | 12 | zero su vol e direzione |
| motivi simbolici | 26 | oltre il lineare, 0 conferme su 10 batterie |
| regimi di prevedibilità, compressione | 18 + 3 | nessuna persistenza; LZ = discretezza del tick |
| informazione mutua | 6 + 12 | reale ma nota e sotto i costi; non la presento per non gonfiare K |

Due note per il controller. (1) La biblioteca di 750 sessioni rende gli analoghi costosi in warmup: un
eventuale uso in validazione richiederebbe ~800 sessioni di warmup. (2) Nessun bug trovato in `core.py`.
Il file `candidates.py` contiene `CANDIDATES = []`, e `test_candidates.py` verifica il registro (194 righe,
tutte in discovery).
