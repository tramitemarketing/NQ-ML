# Laboratorio aperto su NQ — risultati (23 settembre 2026)

## La domanda
«Prova qualsiasi cosa, finché non trovi qualcosa di reale.» È il disegno che produce falsi positivi
garantiti: con abbastanza tentativi qualcosa passa sempre. Il laboratorio l'ha preso alla lettera
(libertà totale di esplorazione) e ha messo la credibilità nel **giudizio**, non nell'esplorazione.

## Il metodo in cinque righe
1. **Tre blocchi di tempo** con guardia nel codice (`lab/core.py`): scoperta 2010-2018 (libera),
   validazione 2019-2023/09 e conferma 2023/10-2026/03 (solo il controller, una volta per ipotesi).
   La cassaforte (dal 2026-03-20) **non è mai stata aperta**.
2. **Registro di ogni test guardato**: 4.551 righe in `lab/ledger/`, più 480.181 regole valutate
   dalla ricerca automatica e ~340 milioni di regole placebo.
3. **Criteri fissati e committati prima**: EV netto (0,75 punti a/r) significativo con Bonferroni,
   significativo anche tolto il beta, positivo nella maggioranza degli anni, positivo senza i 20 trade
   migliori.
4. **Calibrazione del caso**: 1.266 regole-placebo senza senso hanno misurato quanto «vince» il nulla.
   Hanno scoperto un buco nel criterio beta (l'11 % dei placebo long notturni passava tutto), corretto
   prima di qualunque validazione (emendamento 1).
5. **Audit meccanico del look-ahead** su ogni candidato: si altera il futuro dopo un istante T e si
   controlla che nessun trade deciso prima cambi (con controllo positivo: un trucco voluto viene
   catturato).

## I numeri
| | famiglie | test in discovery | candidati | passano validazione | confermati |
|---|---|---|---|---|---|
| Giro 1 | 8 | 2.699 | 13 (5 strategie, 8 regolarità) | 3 regolarità | **2 regolarità** |
| Giro 2 | 6 | ~1.600 + 480.181 regole | 5 (1 strategia, 4 regolarità) | 1 strategia + 2 regolarità | 0 |
| Giro 3 | 1 | 255 + ~70.000 pipeline placebo | 0 | — | — |
| Giro 4 (dati esterni: VXN, VIX, VVIX, SKEW, tassi, dollaro) | 2 | 378 | 2 regolarità | 0 | 0 |
| Giro 5 (modello AMD/ICT di un video YouTube, 2026-09-28) | 1 | 49 | 0 | — | — |

## Cosa è reale (confermato su tutti e tre i blocchi, 16 anni)
1. **La volatilità di domani è prevedibile.** Un HAR sul log della varianza realizzata RTH batte la
   media a 22 giorni: +0,182 (2010-18), +0,214 (2019-23), +0,175 (2023-26), p ≈ 0,0001 ovunque.
   R² fuori campione ~0,62 contro ~0,40.
2. **Una notte agitata anticipa una giornata agitata.** Il range 18:00-09:30 predice il range RTH anche
   controllando per ieri: +0,147 / +0,121 / +0,164, p ≈ 0,0001 ovunque, 9/9 anni nel discovery.

Sono letteratura nota e **non si incassano con il solo future**: dicono *quanto* si muoverà il prezzo,
non *dove*. Servirebbero le opzioni (o, per un trader, a dimensionare stop e rischio).

## Cosa sembrava reale e non lo era
- **Rottura delle bande di volatilità prevista** (giro 2): +3,1 punti netti in discovery, poi **+12,1**
  in validazione con tutti e quattro i criteri superati e robusto a costi triplicati — il primo
  candidato «da trading» del progetto a superare una validazione. In conferma: **−2,6**, CI 95 % [−15,8; +12,1]
  su 190 trade. Non ha retto, ma la conferma aveva potenza ~10 % contro metà della stima di validazione:
  per un vantaggio di qualche punto la domanda non è decidibile con il solo NQ (`lab/POTENZA.md`).
- **Direzione RTH che prosegue 16:15-17:00**: passa la validazione (+1,70 punti lordi, p 0,001), in
  conferma stesso segno ma non significativo (p 0,15).
- **Impronta degli algoritmi a fette** (:00/:15/:30/:45): 0,062 → 0,024 → 0,010. Si dimezza a ogni blocco:
  un'inefficienza che il mercato sta eliminando.
- Turnaround Tuesday, reversal a 10 giorni, ribilanciamento di fine mese: brillanti nel discovery
  rialzista 2010-18, distrutti dal 2022.

## Quattro cose che il laboratorio ha misurato (e non solo creduto)
1. **Lo spazio delle regole intraday semplici è vuoto a questi costi.** 480.181 regole: il miglior t
   reale (4,18) è indistinguibile dal miglior t di 700 mondi placebo (mediana 4,01; p corretto 0,31).
2. **Gli ordini limite non salvano i segnali.** Con simulazione conservativa (trade-through di 1 tick)
   la selezione avversa mangia tutto lo spread risparmiato: si viene eseguiti quando il segnale sbaglia,
   i trade mancati valevano +4/+17 punti.
3. **Non c'è persistenza in quale regola funziona** (giro 3): la performance recente di 374 regole non
   predice quella del mese dopo (p 0,10 contro il placebo corretto).
4. **La maledizione del vincitore, in numeri.** Le due regolarità vere mantengono la loro dimensione da
   un blocco all'altro (rapporto validazione/discovery 0,8-1,2); gli effetti trovati scavando si
   restringono a 0,35-0,7 appena escono dal campione in cui sono stati scelti.

## Quattro errori trovati durante il lavoro (tutti prima di qualunque verdetto)
- Il roll di NQ.v.0 rilevato «a occhio» era sbagliato; sostituito con le date esatte della simbologia
  Databento (i salti ora seguono il ciclo dei tassi, come devono).
- Il criterio beta chiedeva solo il segno (corretto grazie ai placebo).
- Tre regolarità non dichiaravano il segno atteso: un test bilaterale le avrebbe promosse anche
  rovesciate (fissato al segno del discovery prima della validazione).
- Il primo audit anti-look-ahead non catturava un trucco voluto: rafforzato finché non l'ha catturato.

## Giro 4: dati esterni gratuiti (24 settembre)
Volatilità implicita (VXN, VIX a 9 giorni/1 mese/3 mesi, VVIX, SKEW), tassi e dollaro da FRED e CBOE, con
ritardi di pubblicazione rispettati. Il premio per il rischio di varianza non predice la direzione di NQ a
1-20 giorni; tassi e dollaro nemmeno. L'unica cosa che reggeva nel discovery — il VXN migliora la
previsione della volatilità di domani — in validazione ha lo stesso segno ma metà dimensione e non è
significativa (p 0,09).

## Conclusione
Con barre da 1 minuto, un solo strumento e 0,75 punti di costo, **non esiste un vantaggio direzionale
che sopravviva a dati mai visti**, e ora non è un'opinione: è misurato su ~4.500 ipotesi, mezzo milione
di regole automatiche e tre blocchi di tempo indipendenti. Esistono invece fatti veri e stabili sulla
**volatilità**. La cassaforte (6 mesi, 2026-03-20 → 2026-09-18) è intatta: nessun candidato la merita.

## Dove guardare, se si continua
- **Opzioni su NQ** (o VXN): l'unico posto dove la volatilità prevedibile diventa denaro.
- **Altri future** (ES 20,79 $, RTY 11,10 $, ZN 19,08 $ su Databento): utili solo per ritestare in un
  colpo le ipotesi già scritte. Non sono un campione davvero indipendente: stessi anni, e ES si muove
  con NQ a correlazione ~0,9.
- Non fare un giro 5 su questi blocchi: validazione e conferma le hanno già usate 20 + 7 ipotesi, e ogni
  riuso le consuma.

File: `lab/PROTOCOLLO.md` (regole e diario delle decisioni), `lab/*/REPORT.md` (una relazione per
famiglia), `lab/verdicts/` (verdetti del controller), `lab/ledger/` (ogni test guardato).

## Giro 5: il modello «AMD» di un video (28 settembre)
Il modello ICT del video di Tmac (manipolazione all'apertura di NY oltre il massimo notturno dentro un order
block a 4 ore, ingresso sulla mitigazione dell'order block a 2 minuti, obiettivo il minimo asiatico), tradotto
in regole e pre-registrato: −0,26 punti netti a trade su 458 trade 2010-2018, 1/9 anni; la versione contro
trend, che il video presenta come il punto chiave, −0,89. In R il lordo è zero (+0,03R); lo stop da 4 punti fa
pesare il costo 0,19R a trade; i 10R+ sono lo 0,9 % dei trade. Dettagli in `lab/r5_amd/REPORT.md`.

## Giro 6: quattro ipotesi esterne (30 settembre)
Dal documento «Nuove ipotesi da testare» (29 settembre). Le ipotesi già testate nel laboratorio (momentum
dell'ultima mezz'ora, fine mese, finestre notturne) non sono state rifatte. Le quattro nuove sono state
pre-registrate, con le risposte al Passo 0 e due addendum, e giudicate solo sul 2010-2018. **0 candidati su 13
test primari.**
- **Filtro gamma (GEX SqueezeMetrics)**: con un GEX basso le giornate insistono un po' di più, in modo
  statisticamente solido (rango, placebo p 0,003, entrambe le metà), ma l'effetto è metà della soglia fissata
  (0,067 contro 0,10 di VR6). Reale e piccolo: non basta come filtro.
- **Statistiche della community (nqstats, NQ Hourly Edge…)**: rifatte contro un NQ casuale con la stessa
  volatilità, sono geometria. Il ritorno all'apertura delle 08:00 fa 73,5 % contro il 71,4 % del caso; lo
  sweep orario fa 61,6 % contro il 64,8 % del caso. Unica regolarità: l'apertura di mezzanotte viene
  ritoccata nelle RTH 6 punti più spesso del caso. Il fade non rende (−0,91 punti netti).
- **Noise Area di Zarattini**: il segnale non batte un orario casuale; la versione completa vive del 2018 ed è
  in buona parte la rottura delle bande di volatilità già bocciata.
- **ICT Silver Bullet**: 964 trade, −0,96 punti netti a trade, 0/9 anni positivi.
Dettagli in `lab/r6_*/REPORT.md` e in `lab/GIRO6_PASSO0.md`.

## Giro 7: machine learning sulla volatilità e opzioni (7 ottobre)
Dopo la review della potenza (`lab/POTENZA.md`). **0 candidati.**
- **Bande del range con il ML** (`r7_quantili`): un LightGBM a quantili con calendario macro e VXN fa il 3,2 %
  **peggio** della banda attuale del Range Atteso; una regressione quantile lineare fa l'1,3 % meglio, sotto la
  soglia del 2 % e con code mal calibrate. Il ML non aggiunge nulla dove la relazione è quasi lineare.
- **Previsione di volatilità contro le opzioni** (`r7_opzioni`, 15 $ di dati): non decidibile. Prima del 2019
  solo 53 venerdì hanno uno straddle NQ quotato all'apertura, con spread del 7-25 %; servirebbe un effetto
  sei volte più grande del plausibile per vederlo. Test non eseguiti, come pre-registrato.
