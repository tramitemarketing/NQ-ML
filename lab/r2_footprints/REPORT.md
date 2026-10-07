# r2_footprints — impronte meccaniche di orologi, obblighi e algoritmi (giro 2, solo discovery 2010-06 → 2018-12)

**In breve.** Il registro `lab/ledger/r2_footprints.jsonl` ha **258 righe**: 1 PIANO, 1 ERRATA (bug), 4 test di
riproduzione e **252 test guardati**. Nel conto ci sono 4 righe duplicate (F6a/F6b rieseguiti con il bug fix) e 36
righe F6c della prima versione, 12 delle quali non valide per il bug descritto sotto. **Nessuna strategia
incassabile.** **Due regolarità** congelate in `candidates.py`: sono impronte degli algoritmi che lavorano a orologio.
Il piano, le unità e le griglie sono stati fissati prima di guardare i dati, nella docstring di `common.py` e nella
riga PIANO.

## Candidati congelati (tutti `kind="regularity"`, `expected_sign=+1`, test bilaterale sul lordo)

| id | quantità per sessione | n | media | CI 95% | p | anni + | senza i 20 migliori |
|---|---|---|---|---|---|---|---|
| `r2_footprints_slice_continuation` | hit-rate di sign(trend 60m)·sign(r 1m) nei minuti :00/:15/:30/:45 meno quello negli altri minuti (10:05-15:39, esclusi 10:30, 11:30, 14:00, 15:00) | 2.121 | **+0,0623** | [+0,052; +0,073] | 0,0001 | 9/9 | +0,057 |
| `r2_footprints_close_clock_continuation` | media sulle barre 15:45/15:50/15:55/15:59 di sign(r_m)·(C_{m+15}−C_m)/σ1m | 2.111 | **+0,261 σ** | [+0,170; +0,351] | 0,0001 | 9/9 | +0,158 |

Il test `test_candidates.py` ricalcola entrambe le funzioni da `core.load("discovery")` e riproduce i numeri
dichiarati: righe REPRO nel registro.

**1 — Fette a orologio.** Ai quarti d'ora il volume è più alto di +13 % (in log) rispetto ai minuti non multipli di
5, e ai multipli di 5 di +7 %. La crescita è costante: da +0,085 nel 2010 a +0,15/0,17 nel 2015-18. In quei minuti
il rendimento 1m va nella direzione del trend dell'ora precedente. Negli altri minuti c'è invece un lieve rientro
(−0,018). Nel minuto successivo alla fetta il segno si inverte (:01, :16, :31 sono i minuti più negativi del
profilo): prima la pressione, poi il rientro. Il risultato regge:
- con trend di 30, 60 e 120 minuti;
- misurato in punti o in segno;
- su :00, :15/:45 e :30 presi separatamente;
- anno per anno, sempre positivo (9/9).

In punti vale circa 0,1-0,17 per minuto di fetta. È reale, ma non si incassa con 0,75 di costo.

**2 — Barre-orologio della chiusura.** La stessa misura (sign(r_m)·(C_{m+15} − C_m), in σ) calcolata sui 345 minuti
placebo 10:00-15:44 arriva al massimo a +0,19. Le quattro barre-orologio della chiusura valgono invece +0,22, +0,25,
+0,29 e +0,30, e i minuti fra l'una e l'altra rientrano. Gli stessi quattro minuti spostati 1 o 2 ore prima danno
−0,04 e −0,08. Il risultato regge con orizzonte 10, 15 e 20 minuti (+0,22, +0,26, +0,32).
**Avvertenza onesta:** l'effetto **cala nel tempo**. Vale +0,354 nel 2010-13, +0,195 nel 2014-18 e +0,090 (non
significativo) nel 2016-18. Anche la scelta delle 4 barre è **post hoc**: l'ho fatta dopo averle viste nella scansione
F3c. È il candidato più a rischio in validazione.

## Cosa ho provato e cosa ho scartato

**F1 — Orologi (volume e range al minuto contro la mediana dei vicini ±10).** Picchi grandi alle 15:59 (+1,83 in
log, settlement), alle 16:30 (riapertura dopo la pausa), alle 09:30, 16:00 e 16:14 (chiusura CME). Poi, più piccoli:
11:30, 15:50, 15:45, 10:00, 15:00, 14:00 e 11:00.
- **Orario MOC 15:50 — da quando:** nel 2010-11 l'impronta di volume delle 15:50 **non esiste** (−0,10). Compare
  nel 2012-Q3 (+0,11), sale a circa +0,5 nel 2014-15 e schizza a +0,9/+1,2 dal 2017-Q1 al 2018-Q3. Nel 2018-Q4 torna
  a +0,22, probabilmente perché in quel trimestre molto volatile i minuti vicini sono gonfiati. L'impronta delle
  15:45 invece è stabile (~0,3-0,5) in tutto il periodo. Le date esatte dei cambi di regole NYSE/Nasdaq non le
  verifico da qui (niente rete): riporto solo quello che si vede nei dati.
- L'impronta delle 11:00 cresce nel tempo (da +0,09 a +0,36).

**F2 — Esperimento naturale sull'ora legale (136 sessioni in cui Londra è 4 ore avanti invece di 5).**
- Il picco delle **11:00 NY non si sposta** alle 12:00 (differenza −0,03 alle 11:00, −0,02 alle 12:00): non è il
  fixing WM/R di Londra, è un orologio americano (inizio ora).
- La chiusura europea si sposta solo debolmente: 11:30 −0,06, 12:30 +0,08, con CI appena sopra lo zero.
- **Notte (F2b), risultato netto:** l'apertura europea segue l'orologio europeo. Il picco delle 04:00 NY passa da
  0,42 a **0,99** nelle settimane di disallineamento; quello delle 02:00 (08:00 CET) scende da 1,12 a 0,72. Tokyo,
  che non ha ora legale, segue il suo orologio: il picco delle 19:00 vale 0,53 quando a NY è ora solare e 0,26 con
  l'ora legale; quello delle 20:00 fa l'inverso (0,63 contro 0,76).
- Sono fatti veri e causali (identificati dal DST), ma solo di volume: **non li promuovo**, per non gonfiare K
  con una regolarità scontata.

**F3 — Pressione e rientro alla chiusura (lordo in punti).**
- Nessun rientro dopo le 16:00. Il segno di 15:45/15:50/15:55 → 16:00 prosegue fino alle 16:14 e alle 16:59
  (+0,15/+0,46 punti), ma i CI toccano lo zero e senza i 20 migliori la media diventa negativa.
- Verso l'open di domani il segno è negativo (da −0,4 a −0,7) e non significativo.
- Il **minuto 15:59** prosegue fino alle 16:14 per +0,49 punti (p 0,004, 9/9 anni). Da qui è nato il candidato 2.

Resa tradeable (F3b: ingresso all'open della barra successiva, netto 0,75, quantili causali di |z| in {0,5; 0,7; 0,9}):
- il lordo cresce con l'ampiezza del segnale (da 0,08 a 0,22 σ), ma il netto non è mai significativo (p ≥ 0,12)
  e senza i 20 migliori è sempre negativo;
- «voto» delle 4 barre-orologio (F3d, post hoc): netto +0,59/+1,27 punti, p da 0,06 a 0,13, senza i 20 migliori
  negativo. **Scartato**: è il miglior tradeable della famiglia, ma non abbastanza forte.

**F4 — Leveraged ETF (Cheng-Madhavan).** Il segno di (close di ieri → 15:45) prosegue in 15:45 → 16:00 solo
debolmente (+0,17/+0,36 punti, 4-5 anni positivi su 9). La pendenza per anno **non cresce con l'AUM** (−1,3, +2,2,
+1,2, −0,9, +1,4, +5,2, +0,3, −2,9, +0,3). Nessun rientro dopo le 16:00. **Scartato.**

**F5 / F9a — Obblighi di calendario.**
- Ribilanciamento di fine mese (Harvey-Mazzoleni-Melone), con −sign(rendimento del mese a data) × ultimi K giorni:
  - evento per mese: K = 2 dà +13,2 punti (p 0,013);
  - versione giornaliera: K = 2 dà +5,1 punti (p 0,048) e K = 3 dà +0,12 % (p 0,034); con K = 5 l'effetto
    svanisce;
  - senza i 20 migliori è sempre negativo, e con circa 100 eventi per 9 anni non c'è potenza. **Scartato**, pur
    avendo il segno della letteratura.
- Inversione a inizio mese: +4,6 punti, n.s.
- Intraday dell'ultimo giorno del mese: nulla.
- Opex: autocorrelazione 5m più bassa di −0,042 (CI [−0,074; −0,011], n 67), coerente con la gamma lunga dei
  dealer ma piccola. Quadruple witching: log RV −0,20 (al limite). Non promossi.

**F6 — Algoritmi.**
- Periodicità e direzione nelle fette: da qui il candidato 1.
- Sbilanciamento persistente BVC (Easley-López de Prado-O'Hara) ed efficienza del percorso ai checkpoint
  12:30/13:30/14:30, sulla griglia W {60, 120, 180} × H {30, 60} × q {0,5; 0,7; 0,9}: **tutto negativo o nullo al
  netto**. Il migliore è BVC W = 120, H = 60, q = 0,9: +0,57 netti, p 0,16, 5/9 anni. **L'ipotesi «ordine grosso
  non finito» non regge.**
- **BUG trovato e corretto:** nella prima versione (righe F6c senza `_v2`) con W = 180 l'indice `cum[:, k−W]`
  diventava −1 e leggeva la **fine della giornata**. Era look-ahead, e dava +1,0/+1,9 punti netti con p ≈ 0. Me ne
  sono accorto perché W = 180 era troppo diverso da W = 120. Dopo la correzione vale da −0,55 a +0,01.
  L'errata è registrata nel registro (riga BUG_F6c_v1).

**F7 — Tempo del volume.** Con barre di volume (circa 78 al giorno, soglia causale) i rendimenti sono quasi normali:
curtosi in eccesso 0,09 contro 1,60 delle barre di 5 minuti (Clark / Ané-Geman confermati). L'autocorrelazione a
lag 1 è la stessa (−0,022 contro −0,024). Il campionamento cambia la forma della distribuzione, non la
prevedibilità.

**F8 — Irreversibilità temporale (asimmetria di Zumbach sui 5m).**
- Nel campione ha un t HAC di −3,1 nel HAR del log RV di domani, anche controllando per l'effetto leva.
- **Fuori campione** (OLS mobile su 500 sessioni) il guadagno è **nullo o negativo** in 4 varianti su 4 (da −0,15 %
  a +0,02 % di MSE).
- Come segnale di direzione: 1/9 anni.
- **Scartato.**

**F9b — Fondi a volatilità obiettivo.** Dopo uno shock di volatilità (RV5/RV22 alto) lo short su domani perde:
dopo gli shock c'è rimbalzo, non vendita forzata visibile. **Scartato.**

## Note e limiti
- Unità decise prima: log-rapporti per le impronte, punti lordi per le regolarità direzionali, punti netti (costo
  0,75) per i tradeable, σ1m come diagnostica. Il candidato 2 usa σ1m: nella scansione F3c è la misura confrontabile
  fra minuti con volatilità diverse.
- `core.py`: nessun bug trovato. Il `day_block_bootstrap` è usato con n_boot = 4000 negli script e 10000 nel test
  di riproduzione.
- Tutti gli script sono in `lab/r2_footprints/`: `s00_piano`, `f1_clocks`, `f2_dst`, `f2b_overnight_dst`,
  `f3_pressure`, `f3b_magnitude`, `f3c_placebo`, `f3d_clockvote`, `f3e_sens`, `f5_obligations`, `f6_algos`,
  `f6b_slices`, `f78_voltime_irrev`, `f8b_irrev_oos`, `f9_dayflows`, `candidates`, `test_candidates`.
- La cache locale (`cache/disc.pkl`) contiene solo dati di discovery.
