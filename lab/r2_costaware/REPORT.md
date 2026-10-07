# Famiglia r2_costaware (giro 2): un filtro di costo principiato — report di discovery

Solo discovery (2010-06-07 → 2018-12-31). Registro `lab/ledger/r2_costaware.jsonl`: **103 righe = 101 test
guardati + 1 riga PIANO + 1 riga CANDIDATO**. Consegna: **0 candidati tradeable, 1 regolarità**
(`r2_costaware_mom20_restofday`), in `candidates.py`. Il test `test_candidates.py` riproduce i numeri e fa un
controllo anti-look-ahead: tronca i dati al 30/06/2015 e verifica che i valori precedenti non cambino.

## In breve
- **La domanda.** Il costo è fisso in punti (0,75), mentre il movimento scala con la volatilità. Esiste allora una
  regola fissata prima di guardare che operi solo quando i punti attesi rendono il costo trascurabile?
- **Risposta del discovery: no, non in modo incassabile.**
  - Agli orizzonti di 30-120 minuti il filtro di costo seleziona quasi solo il 2018. È esattamente la trappola
    annunciata: 197 dei 206 trade di una regola cadono nel 2018.
  - Alla chiusura RTH i trade si distribuiscono su tutti gli anni. La regola migliore della griglia dichiarata fa
    +1,99 punti netti [−0,06; +4,06], p 0,029, 7/8 anni, ma **senza i 20 trade migliori −0,41**: i 20 migliori
    (18 del 2018) valgono più dell'intero totale.
  - Non supera il criterio di promozione che avevo dichiarato nel PIANO, quindi non la consegno.
- **Il mattone che regge è in unità di volatilità, non in punti.** Il vantaggio dei segnali deboli **non decade con
  l'orizzonte**: cresce da circa +0,025 a 30 minuti a circa +0,05 fino alla chiusura.
  - La componente che lo porta è il **momentum a 20 sessioni**, centrato sulla sua mediana passata: +0,069
    [+0,031; +0,106] in unità di vol, p 0,0008, **8/8 anni**, lato 49 % long.
  - È una regolarità: l'ho trovata scomponendo il composito (post hoc, dichiarato) e la consegno come tale.

## Convenzioni fissate prima di guardare (riga `PIANO`)
- **Istanti di decisione.** 12 slot (10:00, 10:30, …, 15:30 NY), dalla griglia di `lab/ml/features.build_dataset`,
  riusata senza modifiche. Ingresso all'open della barra dello slot. Uscita al close della barra t+h−1, con
  h = 30, 60, 120 minuti oppure la chiusura RTH (close della barra 15:59).
- **Unità.**
  - Diagnostica e regolarità: punti / (sig1m·√h), dove sig1m è la media delle std 1m RTH delle 20 sessioni precedenti.
  - Strategie: **punti netti** per contratto.
- **Componenti.** Il segno è fissato a priori dalle lezioni del giro 1, non stimato. Ognuna è scalata dalla propria
  std mobile passata (3.000 righe) e tagliata a ±3.
  - z_ml: ensemble dei 5 LightGBM congelati di `lab/ml/models`, centrato sulla mediana passata. È fuori campione
    (walk-forward) solo nel 2012-2018.
  - z_day: rendimento dall'apertura, lato continuazione.
  - z_20d: momentum a 20 sessioni.
  - z_surp: sorpresa a 15 minuti con |z| ≥ 3.
- **Compositi a pesi uguali fissi.** COMP2 = (z_day + z_20d)/√2 e COMP3 = (z_ml + z_day + z_20d)/√3.
- **Regola di costo (l'idea nuova).**
  - Punti attesi: E = b_h · COMP · sig1m·√h.
  - b_h è la pendenza per l'origine di y_h su COMP, stimata **solo sulle sessioni precedenti**, in modo espansivo,
    con almeno 250 sessioni.
  - Si opera se |E| ≥ m·0,75, con lato = segno(E) e un trade alla volta per sessione.
  - Griglia dichiarata: 2 compositi × 4 orizzonti × m ∈ {1; 1,5; 2} = 24 regole.
  - Sensibilità dichiarata: sigma moltiplicata per il rapporto tra la previsione HAR di oggi e la media delle
    20 RV passate. È la regolarità confermata nel giro 1.
- **Controlli su ogni regola.** Netto, CI a blocchi per giorno, anni, senza i 20 migliori, beta
  (`controller.beta_component`), **netto senza 2011/2015/2018**, specchio, lato casuale sugli stessi trade,
  placebo per permutazione.
- **Criterio di promozione personale** (dichiarato): i 4 criteri del protocollo sul discovery, più netto
  senza 2011/15/18 > 0, più placebo p < 0,05.

## Batteria 1: il vantaggio in unità di vol regge a orizzonti lunghi? (24 test, `s02_components.py`)
Rendimento firmato dal segno del segnale, su tutte le righe, con bootstrap per giorno.

| segnale | h=30 | h=60 | h=120 | chiusura | punti lordi a chiusura |
|---|---|---|---|---|---|
| z_ml (2012-18) | +0,023 (p 0,002) | +0,027 | +0,030 | +0,032 (p 0,018), 4/7 anni | +0,74 [−0,03; +1,55] |
| z_day | +0,012 (p 0,06) | +0,008 | +0,009 | +0,009 (p 0,55) | +0,47 |
| z_20d (non centrato) | +0,004 | 0,000 | 0,000 | +0,032 (p 0,08) | +0,36 |
| z_surp (n ≈ 300) | −0,036 | +0,012 | −0,005 | −0,012 | rumore |
| **COMP2** | +0,026 (p 0,0003) | +0,029 | +0,031 | **+0,046 (p 0,0035), 6/9** | +0,84 [+0,02; +1,68] |
| COMP3 (2012-18) | +0,025 | +0,022 | +0,027 | +0,049 (p 0,004), 7/7 | +0,91 [−0,05; +1,87] |

- Il composito batte le singole componenti. Il vantaggio in unità di vol **non si spegne** allungando l'orizzonte.
- La sorpresa a 15 minuti presa agli slot fissi è troppo rara (~300 casi) per dire qualcosa. L'ho lasciata fuori dai
  compositi, come previsto dal PIANO.

## Batteria 2: la griglia dichiarata della regola di costo (24 test, `s03_rule_grid.py`)
**Orizzonti 30-120 minuti: la trappola.** Il filtro qualifica quasi solo trade del 2018. Alcuni esempi:

| regola | trade nel 2018 |
|---|---|
| COMP2 h30 m1 | 197/206 |
| COMP2 h60 m1 | 271/337 |
| COMP3 h30 m1 | 580/716 |

- Nel 2012-2017 sig1m·√30 vale 5-10 punti. Con b ≈ 0,03 i punti attesi superano 0,75 solo con volatilità da 2018.
- Nessuna regola ha il CI sopra lo zero. Il netto senza gli anni agitati è negativo quasi ovunque, e senza i 20
  migliori sempre negativo.

**Orizzonte chiusura: i trade si spargono sugli anni** (netto in punti):

| regola | n | netto [CI] | p | anni + | senza top 20 | senza 2011/15/18 | netto − beta |
|---|---|---|---|---|---|---|---|
| COMP2 m1 | 1.412 | +1,99 [−0,06; +4,06] | 0,029 | 7/8 | −0,41 | +1,39 | +1,90 |
| COMP2 m1,5 | 1.045 | +1,80 [−0,93; +4,42] | 0,085 | 7/8 | −1,38 | +1,35 | +1,72 |
| COMP2 m2 | 725 | +2,31 [−1,34; +5,97] | 0,107 | 5/8 | −2,16 | +2,11 | +2,24 |
| COMP3 m1 | 998 | +1,75 [−1,16; +4,66] | 0,125 | 6/6 | −1,67 | +0,99 | +1,68 |
| COMP3 m1,5 / m2 | 701 / 505 | +1,77 / +1,86 | 0,19 / 0,23 | 4/6, 3/6 | < 0 | > 0 | ≈ netto |

## Batteria 3-4: controlli sulla chiusura (`s04_controls.py`, `s05_robust.py`)
- **Senza filtro** (m = 0, di fatto 10:00 → chiusura tutti i giorni): COMP2 +0,88 (p 0,17), 4/8 anni. Il filtro
  alza il netto a +1,99, ma resta dentro il rumore.
- **Specchio**: da −3,3 a −3,8 punti, 0/8 anni. È il riflesso del lordo positivo, non un'informazione in più.
- **Stessi trade con lato casuale** (hash della data): da −0,26 a +0,8, mai significativo. **Il filtro di
  volatilità da solo non crea guadagni.** È un buon segno: la selezione dei giorni non produce falsi positivi
  per costruzione.
- **Permutazione** (COMP2 rimescolato fra sessioni dentro lo slot, pendenza ristimata):
  - sulla media: p 0,25 su 100 permutazioni. Non è informativo, perché con il segnale rotto la pendenza va a zero
    e restano pochi trade molto rumorosi;
  - sul p: il reale (0,029) è minore di tutti i 200 p permutati.
- **Sensibilità HAR** (dichiarata): COMP2 m1 +2,08 (p 0,036), 6/8 anni; m1,5 +2,18 (p 0,066), 8/8 anni. Senza i
  20 migliori resta **sempre negativo**.
- **Un solo istante di decisione**: 10:00 dà +2,00 (p 0,047). 12:00 e 14:00 danno ≈ 0. Tutto il valore sta nel
  tenere dalle 10:00 alla chiusura.
- **Costruzione**: con il minimo di 500 sessioni per la pendenza +1,83 (p 0,067); con pendenza fissa 0,05, senza
  stima, +1,53 (p 0,051). È coerente ma debole.
- **Concentrazione**: somma netta +2.803 punti, 20 migliori +3.371 (18 nel 2018), 20 peggiori −3.074. In punti
  la regola è una lotteria sulle giornate di trend del 2018.
- **Per terzile di sigma** in punti (18 / 25 / 42): in unità di vol +0,050 / +0,011 / +0,083, non monotono; in
  netto +0,28 / −0,54 / +2,90. Il guadagno in punti viene tutto dal terzile agitato, cioè 2015-2018.

## Batteria 5-6: scomposizione e regolarità (`s06_reg_sens.py`, `s07_z20.py`; post hoc, dichiarato)
Misura della regolarità: media giornaliera sugli slot di segno(segnale − mediana delle 3.000 righe
precedenti) × y_close, in unità di vol. Il centraggio toglie lo sbilanciamento long di z_20d, che non centrato
è long al 68 %.

| variante | media [CI] | p₂ | anni + |
|---|---|---|---|
| COMP2 centrato | +0,042 [+0,009; +0,076] | 0,014 | 5/8 |
| z_day centrato | +0,012 | 0,47 | 5/8 |
| **z_20d centrato (candidato)** | **+0,069 [+0,031; +0,106]** | **0,0008** | **8/8** |
| z_20d, mediana su 1.000 / 6.000 | +0,079 / +0,059 | 0,002 / 0,002 | 6/7, 7/8 |
| z_20d, solo slot della mattina / del pomeriggio | +0,052 / +0,086 | 0,011 / 0,0001 | 8/8, 8/8 |
| z_20d, solo 10:00 | +0,045 | 0,059 | 6/8 |
| z_20d a h60 / h120 invece della chiusura | +0,021 / +0,023 | 0,023 / 0,079 | 7/8, 5/8 |
| z_20d **non** centrato | +0,031 | 0,082 | 7/9 |

La componente intraday (z_day) diluisce il composito, che quindi è più debole della sola z_20d. **La regola di
costo applicata a z_20d centrato** (5 test, post hoc) non cambia il quadro:

| m | netto | p | anni + | senza top 20 |
|---|---|---|---|---|
| 1 | +1,66 | 0,094 | 5/7 | −1,53 |
| 2 | +2,31 | 0,11 | 4/7 | −2,79 |

Il 2018 vale +7,5 per trade e gli altri anni stanno intorno a zero. Con lato casuale sugli stessi trade −0,23.

## Candidato: `r2_costaware_mom20_restofday` (kind = "regularity", expected_sign = +1)
**Regola.** A ogni slot 10:00-15:30 si calcolano:
- z20 = r_20d / std delle 3.000 r_20d precedenti, tagliato a ±3;
- r_20d = (ultimo prezzo prima dello slot − chiusura RTH di 20 sessioni prima) / (σ giornaliera a 20 sessioni · √20).

Si firma il rendimento fino alla chiusura RTH, in unità di vol, con segno(z20 − mediana delle 3.000 z20
precedenti), e si fa la media sugli slot della sessione. **Unità: `gross_pts` è in unità di vol, non in punti.**
La colonna `gross_points_mean` riporta la stessa misura in punti. Warmup 520 sessioni, per avere le finestre piene.

| discovery | valore |
|---|---|
| n (sessioni) | 1.921 |
| media, unità vol | **+0,0688 [+0,0314; +0,1060]**, p₂ 0,0008 |
| anni positivi | **8/8** (2011 +0,057 · 2012 +0,087 · 2013 +0,021 · 2014 +0,072 · 2015 +0,067 · 2016 +0,016 · 2017 +0,095 · 2018 +0,132) |
| lato long | 49 % (non è beta) |
| incassabile? | no: la regola di costo che lo usa fa +1,66 netti, p 0,09, senza top 20 negativo |

**Perché dubitarne.**
1. È **post hoc**: l'ho trovata scomponendo il composito dichiarato. Il composito, cioè il test pianificato, ha
   solo p 0,014 nella versione centrata.
2. 101 test guardati. Con la calibrazione della famiglia wild (≈ 4 % di p < 0,05 sui lordi simmetrici), un p di
   0,0008 resta raro, ma la selezione fra circa 6 varianti lo gonfia.
3. Si lega al momentum multi-giorno. La famiglia multiday aveva trovato un **reversal** a 10 giorni close-close,
   notte compresa. La coesistenza è possibile (momentum dentro la seduta, reversal la notte), ma non l'ho
   verificata.
4. So dal PROTOCOLLO §8 che `ml_rank30` (dove r_20d era la feature più forte) **non** ha passato la validazione.
   Lo dichiaro: questo candidato è diverso (una sola variabile, orizzonte fino alla chiusura, unità di vol), ma la
   parentela c'è.

## Cosa ho scartato e perché
- **Regola di costo a 30/60/120 minuti** (tutte le combinazioni): seleziona il 2018, cioè la trappola «alta
  volatilità = anni specifici».
- **Regola di costo alla chiusura** (COMP2, COMP3, variante HAR, pendenza fissa, un solo slot, z_20d): netti di
  +1,5 / +2,3 punti con p fra 0,03 e 0,2. **Senza i 20 migliori è sempre negativa** e il CI contiene sempre lo
  zero. Fallisce il mio criterio di promozione dichiarato. È la regola più vicina: non la consegno.
- **COMP3 (con il ML)**: non aggiunge nulla rispetto a COMP2 alla chiusura, e il ML copre solo il 2012-2018.
- **Sorpresa a 15 minuti agli slot fissi**: troppo rara.
- **Regolarità del composito COMP2**: più debole della sola componente z_20d, e le due sono annidate. Ne consegno una.
- Non testato di proposito:
  - orizzonti oltre la chiusura (attraverserebbero la notte, cioè la trappola del beta long 2010-18);
  - filtri di costo sui candidati bocciati del giro 1 (rth_to_evening, surprise_continuation, hivol_last30):
    sarebbero ritocchi vietati.

## Lettura per il laboratorio
- La logica «costo fisso, movimento che scala» è corretta come aritmetica. Nel discovery, però, il vantaggio in
  unità di vol dei segnali disponibili (≈ 0,05-0,07 a chiusura) moltiplicato per la sigma in punti del 2012-2017
  dà lordi di 1-3 punti **con code enormi**. La media netta positiva viene dalle giornate di trend, e il criterio
  «senza i 20 migliori» la uccide.
- Nel 2019-2023 la sigma in punti è molto più alta, quindi il costo relativo sarebbe più basso. È una previsione,
  non una scoperta: il discovery non la sostiene e non la mando avanti come strategia.

## Note tecniche
- **Riuso senza modifiche**: `lab.ml.features.build_dataset`, `lab.ml.candidates._models` (i modelli congelati),
  `lab.vol.candidates._har` (moltiplicatore HAR), `lab.controller.beta_component`.
- **`core.py`**: nessun bug trovato.
- **Sovrapposizione.** Le righe «fino alla chiusura» degli slot dello stesso giorno si sovrappongono. Le
  regolarità usano la media giornaliera, un valore per sessione. Le regole di trading fanno un trade alla volta.
- **File**: `common.py`, `s00_piano.py` … `s07_z20.py`, `candidates.py`, `test_candidates.py`. La cache del pannello
  è in `cache/`.
