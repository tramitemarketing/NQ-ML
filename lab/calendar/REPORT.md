# Famiglia calendar — effetti di calendario ed eventi programmati (solo discovery)

(Testo prodotto dall'agente della famiglia; salvato dal controller perché la scrittura dell'agente era stata bloccata.)

Periodo: discovery 2010-06-07 → 2018-12-31 (2.196 sessioni). Registro: `lab/ledger/calendar.jsonl` —
**169 righe = 163 test distinti + 5 riletture + 1 diagnostica dei calendari**.

## Esito in una riga
**Un solo candidato inviato (`calendar_turnaround_tue_am`), debole.** Nessuno dei classici
(turn-of-month, pre-festivi, pre-FOMC, NFP, Halloween, giorno della settimana) regge il controllo beta.
Tre finalisti avevano EV netto con CI sopra zero, ma due falliscono già nel discovery il criterio 4.

## Metodo
- Unità: punti per contratto, netto = lordo − 0,75; secondaria in bp.
- Beta: lordo long medio della stessa finestra su tutti i giorni validi; eccesso con CI a blocchi.
- FOMC a mano dal calendario Fed (69 date), verificate sul volume (65/69 con picco; corretto un errore
  sul 30/1/2013, ancora alle 14:15). NFP per regola BLS + eccezioni (102 date, volume 8:30 mediano
  10,9×). Nessuna etichetta viene dal volume. CPI non testato.

## Idee provate (netto in punti)
- **Giorno della settimana (10)**: RTH lun −1,6, mar +2,2, mer −0,1, gio −0,8, ven −2,6; overnight tutti ≈ beta.
- **Turn-of-month (12)**: Lakonishok-Smidt +6,8 < beta +10,3. Su NQ 2010-18 è beta.
- **Festivi (5)**: pre-festivo +0,1 (Ariel assente); post-festivo 3 giorni +13,7 ma eccesso +8,0 [−5,6; +20,7].
- **Scadenze (20)**: SHORT venerdì di scadenza mensile +7,6 [+1,1; +14,9], ma quasi tutto quadruple e
  2018; senza i 20 migliori −4,3.
- **Roll (2)**: niente.
- **Fine mese (≈20)**: ribilanciamento contrarian +13,5 [+0,6; +27,0], cresce con la soglia, ma quasi
  tutto lato long e senza i 20 migliori −10,7.
- **FOMC (13)**: pre-FOMC Lucca-Moench +2,0 contro beta +2,3 (sparito dopo il 2011); vigilia non batte
  i martedì; ciclo FOMC nulla. Con 69 eventi il CI è ±5-10 punti.
- **NFP (4)**: niente.
- **Stagionalità (16)**: Halloween al contrario; luglio +6,4 9/9 ma 1 su 12.
- **Ora della settimana (38)**: unica struttura martedì 9:30-10:30 → filone turnaround.
- **Turnaround Tuesday (≈18)**: RTH martedì dopo lunedì in calo +7,6 [+1,1; +14,2], senza i 20 migliori
  −2,5. Uscite: 11:00 +5,0; **12:00 +7,4**; 13:00 +6,5. Specchio −1,1. Placebo «mattina dopo un giorno
  in calo» negli altri giorni: tutti negativi.

## Candidato inviato: `calendar_turnaround_tue_am`
Long martedì 9:30→12:00 se il lunedì RTH è chiuso in calo (nessun trade se il lunedì era festivo).
n 178, netto **+7,38 [+3,20; +11,67]**, p 0,0003, 8/9 anni, netto − beta +7,07, eccesso su tutti i
martedì +4,7 [+0,5; +9,0], senza i 20 migliori +0,47.
Perché dubitarne: finestra 12:00 **post hoc** (il test pianificato fallisce il criterio 4); Bonferroni
interno a 163 test richiede p < 0,00031; in validazione ~90 trade rendono il criterio 4 più severo.

## Note per il controller
- Il criterio 4 toglie il 20 % dei trade con n=100: per gli eventi mensili è quasi un divieto.
- Buchi nei dati: mancano 2014-06-13, 2014-09-24/25, 2016-09-02→19.
