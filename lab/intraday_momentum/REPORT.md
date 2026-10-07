# Famiglia intraday_momentum: report di discovery

(Testo prodotto dall'agente della famiglia; salvato dal controller perché la scrittura dell'agente era stata rifiutata.)

Solo discovery (2010-06-07 → 2018-12-31). **98 righe nel registro** `lab/ledger/intraday_momentum.jsonl`,
ognuna è un test guardato: 34 ipotesi distinte più griglie di sensibilità, controlli, placebo e
regressioni. **Candidati congelati: 2** (uno incassabile, una regolarità), in `candidates.py`.
Il test minimo è `test_candidates.py`: rigira le `fn` sul discovery e ritrova i numeri dichiarati.

## Convenzioni (fissate prima di guardare)
- **Unità di decisione: netto in punti per contratto** (lordo − 0,75), perché è la metrica del
  controller. Per controllo è riportato anche il **netto in bps** (punti / prezzo grezzo × 1e4), che
  pesa gli anni allo stesso modo.
- I **segnali** usano rendimenti relativi: differenza dei prezzi adj divisa per il prezzo **grezzo**.
- Il prezzo «alle HH:MM» è il close della barra che chiude a HH:MM. Il trade entra all'open della barra
  successiva. La «chiusura di ieri» è il close della barra 15:59 dell'ultima sessione valida
  precedente. Solo sessioni `valid`.
- Controllo beta: netto − (esposizione × deriva long media della stessa finestra). La deriva
  dell'ultima mezz'ora 2010-2018 è **negativa**: −0,24 lordo; sempre long dà netto −0,99, 0/9 anni.

## 1. Repliche della letteratura (tutte le sessioni, netto pt)
| test | regola | n | netto [CI 95 %] | lordo | anni + |
|---|---|---|---|---|---|
| H01 GHLZ | segno(chiusura ieri→10:00) → 15:30-16:00 | 2109 | −0,56 [−1,03; −0,08] | +0,19 | 1/9 |
| H02 GHLZ | segno(15:00-15:30) → ultima mezz'ora | 2087 | −0,52 [−1,02; −0,02] | +0,23 | 2/9 |
| H03 GHLZ | entrambi concordi | 1029 | −0,30 [−0,96; +0,37] | +0,45 | 2/9 |
| H04 BDLM | segno(chiusura ieri→15:30) → ultima mezz'ora | 2113 | −0,37 [−0,86; +0,11] | +0,38 | 1/9 |
| H08 | segno(09:30→15:30) → ultima mezz'ora | 2114 | −0,13 [−0,60; +0,34] | +0,62 | 3/9 |
| H09 | segno(overnight) → ultima mezz'ora | 2109 | −0,70 | +0,05 | 0/9 |
| H06/H07 LPS | ±segno(overnight) → 09:30-16:00 | 2109 | −0,84 / −0,66 | ∓0,09 | 2/9, 1/9 |

OLS HAC dell'ultima mezz'ora: 09:30→15:30 **t=+2,25** (R² 0,6 %); chiusura ieri→15:30 t=+1,76;
overnight t=+0,22. Il predittore GHLZ non funziona su NQ; l'informazione sta nella parte intraday. Il
lordo incondizionato (+0,62, p 0,011) è sotto il costo e concentrato nel 2018 (senza: +0,23).

## 2. Varianti scartate (netto pt)
Soglie |predittore| > k·σ60 (fino a +2,7 ma tutto 2018); volume; ultima ora; dopo le 14:00;
penultima mezz'ora; ultimi 10 minuti; uscita 16:15; reversal/momentum della mattina; pausa pranzo;
periodicità HKS; reversal nei giorni tranquilli; giorno della settimana; terzo venerdì; fine mese;
efficienza del percorso; posizione nel range; nuovo estremo 15:00-15:30. Diagnostica adimensionale:
z ≈ +0,02, hit rate ~49 %: l'effetto incondizionato viene da pochi giorni grandi nei periodi volatili.

## 3. Il filone che regge: momentum dell'ultima mezz'ora in regime di alta volatilità
Regime solo dal passato: vol realizzata RTH 1m media delle L sessioni precedenti > quantile q delle
250 sessioni precedenti. Griglia dichiarata prima (netto pt):

| predittore | L10 q.5 | L10 q.67 | L20 q.5 | L20 q.67 | L60 q.5 | L60 q.67 |
|---|---|---|---|---|---|---|
| 09:30→15:30 | +1,01 | +2,16 | +1,05 | **+2,29** | +1,22 | +1,30 |
| chiusura ieri→15:30 (BDLM) | +0,73 | +1,50 | +0,66 | +1,53 | +0,77 | +1,05 |
| chiusura ieri→10:00 (GHLZ) | −0,16 | +0,33 | −0,07 | +0,46 | −0,14 | −0,10 |

Nel regime basso lo stesso segnale fa −1,14. Scelta: L20 q0,67, **il massimo della griglia**
(selezione dichiarata). Anni: 2011 +2,79 · 2012 +0,92 · 2013 −2,42 · 2014 +0,22 · 2015 +3,81 ·
2016 −0,84 · 2017 −0,14 · 2018 +5,31. Senza il 2018 +1,30 [+0,24; +2,41]. Senza i 20 migliori
+0,10 (fragile). Beta-corretto +2,31. Placebo col segno di ieri negli stessi giorni −0,91.

## 4. Candidati
1. `intraday_momentum_hivol_last30` (tradeable, warmup 280): n=587, netto +2,29 [+0,86; +3,74],
   p 0,0017, 5/8 anni, senza i 20 migliori +0,10, beta-corretto +2,31.
2. `intraday_momentum_rin_last30_gross` (regolarità, bilaterale sul lordo): n=2114, lordo +0,62
   [+0,16; +1,10], p 0,011, 4/9 anni.

## 5. Avvertenze
- 98 test; circa 20 con p < 0,05, quasi tutti nello stesso filone (correlati).
- Fuori campione solo in parte: S7 di `screening_looks.md` aveva schermato il momentum incondizionato
  dell'ultima ora su 2016-2023. Il condizionamento al regime è nuovo.
