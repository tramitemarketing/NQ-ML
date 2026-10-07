# Range Atteso NQ (RTH)

Un indicatore per TradingView che **alle 09:29 di New York, prima dell'apertura, stima quanto sarà ampio il
range della sessione regolare di NQ** (massimo − minimo fra 09:30 e 16:00). Sul grafico disegna le bande
`apertura RTH ± k × range previsto` e in una tabella mostra il range previsto in punti, in dollari per
contratto NQ e MNQ e il confronto con l'ATR(14) giornaliero.

**È uno strumento di rischio, non un segnale.** Dice *quanto* è probabile che il prezzo si muova oggi, non
*dove*. Nessuna delle strategie direzionali testate nel laboratorio ha soddisfatto tutti i criteri di
conferma. Diversi risultati restano inconcludenti per effetti più piccoli; i periodi temporali sono stati
riutilizzati fra fasi della ricerca, come chiarisce il paper v4.1. Questo indicatore non promette un vantaggio.

## Da dove viene

Si basa sulle due sole regolarità che il laboratorio (`lab/RISULTATI.md`) ha confermato su tutti e tre i
blocchi di tempo, cioè su 16 anni:

1. la volatilità di domani è prevedibile da quella dei giorni precedenti (modello HAR: ieri, ultima settimana,
   ultimo mese);
2. una notte agitata (18:00 → 09:29) anticipa una giornata agitata, anche tenendo conto di ieri.

## Il modello

Coefficienti **fissi**, stimati una volta sola con i minimi quadrati sulle sessioni dal 2010-07-08 al
2023-09-29 (3.286 sessioni) e mai più ricalcolati:

```
ln(range RTH in % dell'apertura) = 0,2206 + 0,1446·l1 + 0,2981·m5 + 0,1431·m22 + 0,3004·lon
range previsto (punti) = exp(...) / 100 × prezzo di chiusura delle 09:29
```

| termine | significato | coeff. | errore std. (HAC) |
|---|---|---|---|
| l1 | ln del range % dell'ultima sessione completa | 0,1446 | 0,022 |
| m5 | media degli ultimi 5 | 0,2981 | 0,038 |
| m22 | media degli ultimi 22 | 0,1431 | 0,032 |
| lon | ln del range notturno 18:00→09:29 in % del prezzo delle 09:29 | 0,3004 | 0,017 |
| costante | 0,1441 + ln(1,0795): correzione di smearing di Duan | 0,2206 | |

- Le sessioni valide sono quelle con almeno 10 barre RTH da 30 minuti. Le mezze giornate (per esempio la
  vigilia di Natale, chiusura alle 13:00) non entrano nella storia.
- La correzione di smearing fa sì che la previsione sia il range **medio** atteso, non il mediano: in una
  giornata tipica il range reale finisce un po' sotto il previsto (mediana del rapporto reale/previsto: 0,91).
- I valori completi sono in `coefficienti.json`.

## Come si legge

- **Range previsto**: per esempio 420 punti (1,70 %). In dollari fa 8.400 $ per un contratto NQ (20 $ a
  punto) e 840 $ per un MNQ (2 $ a punto). È la distanza media fra massimo e minimo di oggi, non un obiettivo
  di prezzo.
- **Bande**: si fissano all'apertura delle 09:30 e restano ferme fino alle 16:00.
  - Banda interna (k = 0,5 di default): nel test almeno uno dei due lati è stato toccato nel 77 % delle
    sessioni. È una misura di dove arriva un giorno «normale», non un livello di inversione.
  - Banda esterna (k = 1,0): nel test massimo e minimo sono rimasti entrambi dentro nel 78 % delle sessioni.
    Un'uscita è un'informazione (giornata fuori dal comune), non un segnale di ingresso.
- **Previsto / ATR(14)**: l'ATR giornaliero di TradingView misura la sessione Globex completa (23 ore), quindi
  di solito supera il range RTH. In media il range RTH vale circa 0,80 volte l'ATR. Se il rapporto è molto
  sopra 0,8, la notte o gli ultimi giorni dicono «oggi più mosso del solito».
- **Range RTH finora**: quanta parte del range previsto la giornata ha già usato.

## Numeri fuori campione

Il test è onesto: coefficienti stimati fino al 2023-09-30, valutati sulle 611 sessioni valide dal 2023-10-02
al 2026-03-19, mai usate nella stima. La cassaforte del laboratorio (dal 2026-03-20) non è stata aperta.
Tutti i metodi sono confrontati sulle stesse sessioni.

| metodo | R² (punti) | R² (log) | errore medio assoluto | errore mediano | errore % medio | distorsione |
|---|---|---|---|---|---|---|
| **Range Atteso (HAR + notte, fisso)** | **0,378** | **0,369** | **89,2 pt** | **60,6 pt** | **34,1 %** | +2,9 pt |
| con anche il VXN (fisso) | 0,392 | 0,394 | 87,4 pt | 61,8 pt | 33,1 % | −0,1 pt |
| stesso modello senza la notte | 0,303 | 0,285 | 94,1 pt | 65,4 pt | 36,5 % | 0,0 pt |
| stesso modello ristimato ogni giorno (500 sessioni) | 0,352 | 0,354 | 90,1 pt | 61,8 pt | 34,6 % | +2,6 pt |
| media del range RTH a 20 giorni | 0,132 | 0,194 | 102,9 pt | 72,4 pt | 38,4 % | −2,7 pt |
| ATR(14) giornaliero così com'è | 0,026 | −0,107 | 127,2 pt | 102,5 pt | 55,8 % | +67,0 pt |
| ATR(14) × 0,803 (fattore fisso stimato in campione) | 0,202 | 0,231 | 100,4 pt | 72,5 pt | 38,0 % | −2,8 pt |

Nel periodo di test il range RTH medio è stato di 287 punti. Sulla perdita quadratica in log, con un
bootstrap per giorni, il vantaggio sulla media a 20 giorni e sull'ATR scalato è significativo (p ≈ 0,0001).
Anche il contributo della notte è significativo (p ≈ 0,0001). I coefficienti fissi non perdono nulla rispetto
alla ristima quotidiana: vanno anzi leggermente meglio (p 0,05).

**Copertura delle bande nel test** (fra parentesi i valori in campione 2010-2023, che sono quasi identici):

| | nel test | in campione |
|---|---|---|
| range reale ≤ 0,5 × previsto | 4,7 % | 4,8 % |
| range reale ≤ 1,0 × previsto | 62,0 % | 59,3 % |
| range reale ≤ 1,5 × previsto | 90,5 % | 88,9 % |
| max e min dentro apertura ± 0,5 × previsto | 22,6 % | 24,7 % |
| max e min dentro apertura ± 0,75 × previsto | 54,8 % | 56,5 % |
| max e min dentro apertura ± 1,0 × previsto | 77,9 % | 77,1 % |
| max e min dentro apertura ± 1,5 × previsto | 93,3 % | 93,8 % |

Con k = 1 la banda **inferiore** viene toccata più del doppio delle volte rispetto a quella superiore (15,5 %
contro 6,7 %): le giornate più ampie di NQ sono più spesso ribassiste. Con le baseline la copertura è
peggiore a parità di k: dentro ± 1 × previsto, 74,6 % con la media a 20 giorni e 75,1 % con l'ATR scalato.

Il rapporto fra range reale e previsto ha questi quantili: 5 % 0,50 · 25 % 0,70 · 50 % 0,91 · 75 % 1,16 ·
95 % 1,78.

### Da non leggere male

- **Il R² in campione (0,75 in punti) non è confrontabile con quello del test (0,38).** Su 13 anni il livello
  di NQ passa da circa 2.000 a 15.000 punti, e basta seguire quel livello per spiegare gran parte della
  varianza. Anno per anno, in campione, il R² va da 0,00 a 0,47. Il test su 2,5 anni è in linea con questo.
  L'errore percentuale medio, che non dipende dal livello, è lo stesso dentro e fuori (35 % e 34 %).
- **Anno per anno nel test.** Errore medio assoluto dell'indicatore contro media a 20 giorni e ATR scalato:
  - 2023 (ultimo trimestre): 50,6 contro 56,5 e 55,3;
  - 2024: 76,3 contro 83,1 e 81,5;
  - 2025: 107,4 contro 133,7 e 129,8;
  - **2026 (53 sessioni): 109,9 contro 107,6 e 104,9.**

  Nel primo trimestre del 2026 l'indicatore **non** ha battuto le baseline. Il grosso del vantaggio arriva nei
  cambi di regime (aprile 2025), quando le medie lente restano indietro.
- Anche il laboratorio aveva un R² fuori campione di circa 0,62, ma su un'altra cosa: il log della varianza
  realizzata a 5 minuti, un bersaglio più liscio del range massimo−minimo.

## La variante con il VXN: vale la complessità?

La variante aggiunge ln(VXN), la volatilità implicita del Nasdaq-100, con il valore di chiusura del giorno
lavorativo precedente (`lab/extdata.py`, `known_at_open`). Nel test migliora in modo **statisticamente
reale** (perdita log −0,0058, p 0,005) e il suo coefficiente è stabile nei due sotto-periodi di stima (0,62 e
0,65). Qui regge meglio di quanto il laboratorio avesse visto sulla varianza realizzata.

**In pratica, però, il guadagno è piccolo**:

- errore medio da 89,2 a 87,4 punti (−2 %);
- R² da 0,37 a 0,39;
- copertura delle bande identica (77,3 % contro 77,9 % dentro ± 1×);
- nel 2026 va leggermente peggio (111,7 contro 109,9).

Su TradingView costerebbe un secondo simbolo (CBOE:VXN, con orari diversi dal future). Costerebbe anche un
allineamento delicato: il valore di ieri alle 09:30, prima che il VXN di oggi esista. Un errore lì
introdurrebbe proprio lo sguardo al futuro che il resto dello script evita. **Verdetto: non vale la
complessità. Lo script Pine usa solo il modello base.** I coefficienti della variante sono comunque in
`coefficienti.json`.

## Limiti

- **Non predice la direzione.** Le bande sono simmetriche attorno all'apertura. Dire «il prezzo tornerà dentro
  la banda» o «rompe la banda, quindi entro» sono cose che il laboratorio ha testato: la rottura delle bande di
  volatilità prevista è passata in validazione e poi è fallita in conferma (−2,6 punti netti).
- **Nei giorni di notizie può sbagliare molto.** Il modello conosce solo prezzi passati e la notte, non il
  calendario. Le sottostime peggiori del test:
  - 2025-10-10: reale 1.004 contro 213 previsti (4,7×);
  - 2024-12-18 (Fed): 898 contro 233 (3,9×);
  - 2025-04-09 (sospensione dei dazi): 2.185 contro 769 (2,8×);
  - 2025-04-07: 1.688 contro 611;
  - 2025-11-20: 1.212 contro 475;
  - 2024-08-01: 814 contro 325.

  Nei giorni di FOMC, CPI, occupazione o trimestrali delle big tech, considera la banda esterna come un minimo,
  non come un tetto. Una notizia delle 08:30 entra nella previsione solo attraverso il range notturno. Una
  notizia delle 10:00 o delle 14:00 non entra affatto.
- Una sessione su dieci ha un range reale oltre 1,5 volte il previsto e una su venti oltre 1,78 volte.
- I coefficienti sono fissi: se il mercato cambia struttura, il modello non se ne accorge. Il 2026 (53 sessioni
  sotto le baseline) è da tenere d'occhio.
- È stimato su NQ. Su MNQ vale identico, perché è lo stesso sottostante. Su altri future (ES, RTY) i numeri
  non sono stati verificati.
- Le prime 22 sessioni di storia servono a scaldare il modello: fino ad allora mostra «riscaldamento».

## I file

| file | cosa contiene |
|---|---|
| `range_atteso.pine` | lo script per TradingView (Pine Script v5) |
| `features.py` | costruisce le grandezze esattamente come le vede il Pine: barre da 30 minuti, prezzi del contratto della sessione |
| `model.py` | stima dei coefficienti fissi e valutazione fuori campione. Scrive `coefficienti.json`, `risultati_oos.json` e `verifica_tradingview.csv` |
| `pine_reference.py` | implementazione di riferimento, barra per barra, della logica del Pine (legge coefficienti e input direttamente dal file `.pine`) con le verifiche |
| `verifica_riferimento_pine.csv` | numeri attesi per le ultime 10 sessioni prima del 2026-03-20, da confrontare su TradingView |

Per rilanciare, dalla radice del repository:
`.venv/Scripts/python.exe product/indicator/model.py`, poi `.venv/Scripts/python.exe product/indicator/pine_reference.py`.
Entrambi caricano i dati solo tramite `lab.core.load`. Impostano `LAB_CONTROLLER=1` per le fasi
validation/confirmation (uso autorizzato solo per questo indicatore) e non toccano la cassaforte.

Verifiche già fatte da `pine_reference.py`:

1. la previsione del riferimento coincide con quella di `model.py` su 4.019 sessioni (differenza relativa
   massima 1,5·10⁻⁶, dovuta ai coefficienti arrotondati a 6 decimali nel Pine); anche l'ATR coincide;
2. **audit anti-look-ahead**: su 60 sessioni a caso la previsione è stata ricalcolata cancellando tutti i dati
   dopo le 09:29:59 e falsificando la barra delle 09:30 (prezzi a 10⁹). È risultata identica 60 volte su 60;
3. i numeri fuori campione ricalcolati dal riferimento coincidono con la tabella qui sopra (R² 0,378, errore
   medio 89,2, dentro ± 1× 77,9 %).

## Cosa controllare a mano su TradingView al primo caricamento

Lo script **non è stato compilato né eseguito**: qui non c'è TradingView. Prima di fidarti:

1. **Compilazione**: incolla lo script nel Pine Editor e controlla che non ci siano errori o avvisi rossi. Gli
   avvisi gialli su `f_forecast` e `timeframe.change` dentro `request.security` sono attesi.
2. **Grafico**: apri NQ1! (o MNQ1!) con un timeframe di 1, 5 o 15 minuti. Con timeframe superiori a 30 minuti,
   o che non dividono 30, lo script si ferma apposta.
3. **Storia sufficiente**: la riga «Storia (sessioni)» deve dire 22/22. Se su 1 minuto resta sotto 22, vuol
   dire che il contesto a 30 minuti non ha abbastanza barre (dipende dal piano). In quel caso prova il grafico
   a 5 minuti e segnalamelo.
4. **Confine di sessione**: il giorno di TradingView per NQ deve iniziare alle 18:00 di New York (17:00 di
   Chicago). Controlla che alle 18:00 le bande spariscano e che alle 09:30 ne compaiano di nuove.
5. **Numeri**: confronta alcune sessioni di `verifica_riferimento_pine.csv` con la tabella e con la finestra
   dati (clic su una barra RTH di quel giorno). Per esempio, 2026-03-19:
   - range previsto ≈ 379 pt (1,55 %);
   - apertura 24.428,25;
   - banda ± 0,5× 24.238,6 / 24.617,9;
   - banda ± 1× 24.048,9 / 24.807,6;
   - ATR(14) ≈ 510.

   Sono attese piccole differenze (qualche punto), per due ragioni. Il continuo NQ1! di TradingView può
   cambiare contratto in date diverse da quelle di Databento. E l'ATR di Wilder dipende da quanta storia è
   caricata. Se la differenza supera circa il 2 % sul range previsto, qualcosa non torna: controlla il punto 4
   e che l'opzione «back-adjustment» del continuo sia disattivata.
6. **Niente repainting**: in tempo reale, annota il range previsto alle 09:31. Ricarica il grafico dopo le
   10:00 e controlla che la barra delle 09:31 mostri lo stesso numero nella finestra dati («Range previsto
   (punti)»).
7. **Festivi e mezze giornate**: il giorno dopo il Ringraziamento e la vigilia di Natale devono mostrare
   bande normali, ma non devono entrare nella storia. Il giorno successivo non deve avere un range previsto
   anomalo.
8. **Dollari**: righe NQ = punti × 20, MNQ = punti × 2. Se usi un altro contratto, cambia i valori negli input.

## Avvertenza

Questo indicatore è uno strumento statistico a scopo informativo e didattico. **Non è consulenza finanziaria,
né una raccomandazione a comprare o vendere alcunché.** I risultati passati, anche fuori campione, non
garantiscono quelli futuri. Il trading di future con leva può far perdere più del capitale investito. Chi lo
usa è l'unico responsabile delle proprie decisioni.
