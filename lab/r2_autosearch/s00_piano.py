"""r2_autosearch — PIANO PRE-REGISTRATO (scritto prima di guardare qualunque risultato).

Idea: la macchina inventa le regole; noi misuriamo quanto il data-mining da solo produce.

GRAMMATICA
- Istanti di decisione T (minuti NY, solo RTH): 09:45, 10:00, 10:30, ..., 15:30 (13 istanti).
  Le feature usano solo barre con ny_min < T; ingresso all'OPEN della barra T (la barra dopo il segnale).
- Orizzonti: 15, 30, 60, 120 minuti (uscita al close della barra T+h-1) e «fino alla chiusura»
  (close della barra 15:59). Gli orizzonti fissi che finiscono oltre le 16:00 o coincidono con la
  chiusura non esistono. Tutto dentro l'RTH: niente notte, niente roll, beta quasi nullo.
- Lato: long o short. Unità: PUNTI NQ netti per 1 contratto, costo 0,75 sempre.
- Feature (23, tutte causali, normalizzate con il range RTH medio delle 20 sessioni precedenti):
  rendimenti 5/15/60 min e dall'apertura, gap, notte (glbx_open->09:30), ieri, 5 giorni;
  sorpresa di volatilita' realizzata (oggi fino a T e ultimi 60 min, rispetto alla media delle 20
  sessioni precedenti allo stesso minuto); volume relativo per ora (cumulato e ultimi 60 min);
  posizione nel range di oggi / ieri / notte / 20 giorni; distanza dal massimo e dal minimo di oggi;
  range di oggi relativo; range notturno relativo; regime di volatilita' (ATR20/ATR250);
  minuti dal massimo e dal minimo di oggi. + giorno della settimana.
- Soglie: rango percentile CAUSALE del valore rispetto alle stesse feature allo stesso istante nelle
  250 sessioni precedenti (minimo 60). Condizioni: rango <=0,10 / <=0,25 / <=0,50 / >0,50 / >=0,75 /
  >=0,90 (6 per feature) + dow==d (5) = 143 condizioni.
- Regole: AND di 1 o 2 condizioni su feature diverse (enumerazione completa), piu' 3 condizioni via
  beam search (le 10 migliori coppie di ogni cella (T, h, lato) estese con ogni terza condizione).

RICERCA / SELEZIONE (discovery diviso in due, nessun ritocco fra le due)
- Ricerca: sessioni 2010-06-07 -> 2015-12-31. Punteggio = t della media netta (n >= 100 trade).
- Portafoglio della ricerca: le 2 migliori regole per cella (T, h, lato), poi le 100 migliori in
  assoluto per t di ricerca = TOP100.
- Selezione: 2016-01-01 -> 2018-12-31, TOP100 congelato. «Sopravvive» chi ha media netta > 0 e
  t_sel > 1,645 (unilaterale 5 %); «forte» chi ha t_sel > 3,29 (0,05/100).
- Statistiche della pipeline: S1 = max t di ricerca; S2 = numero di sopravvissuti nel TOP100;
  S3 = max t_sel nel TOP100; S4 = t_sel medio del TOP100; S5 = numero di regole con t_ric > 3.

PLACEBO (l'intera pipeline, identica, rifatta da capo)
- Nullo principale «segno per giorno»: ogni sessione riceve un segno casuale +-1 che moltiplica TUTTI i
  suoi rendimenti futuri (tutti gli istanti e orizzonti). Conserva il legame feature->ampiezza dei
  movimenti (la volatilita' e' prevedibile: giro 1) e la struttura dentro la giornata; distrugge la
  direzione (e la piccola deriva RTH). 500 repliche.
- Nullo secondario «blocchi di giorni»: i vettori dei rendimenti futuri delle sessioni sono permutati a
  blocchi di 20 sessioni, separatamente in ricerca e selezione. Conserva deriva e distribuzione, rompe
  il legame feature->ampiezza (da' un vantaggio alla realta' nelle regole ad alta volatilita', perche'
  il costo fisso pesa meno in t quando la deviazione standard e' grande): dichiarato come secondario.
  200 repliche.
- p-value corretto per la ricerca = quota di placebo con statistica >= reale (per S1..S5).

REGOLA DI DECISIONE SUI CANDIDATI (fissata ora)
- Un candidato puo' venire solo dai sopravvissuti della selezione.
- Si consegna qualcosa SOLO se la pipeline si distingue dal caso: p(S2) < 0,05 oppure p(S3) < 0,05
  sul nullo principale. Altrimenti zero candidati: il risultato e' la misura dello spazio vuoto.
- Se si consegna: al massimo 3, scelti per t_sel, e poi controllati sull'intero discovery (costi,
  anno per anno, senza i 20 migliori, beta = lato x deriva media della stessa finestra, bootstrap a
  blocchi per giorno). Chi fallisce questi controlli non si consegna.
"""
from lab import core

if __name__ == "__main__":
    core.record("r2_autosearch", "piano", "piano pre-registrato (vedi s00_piano.py)", "discovery",
                {"n": 0}, note="nessun dato guardato")
    print("piano registrato")
