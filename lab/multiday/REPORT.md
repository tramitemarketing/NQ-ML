# Famiglia multiday — REPORT (solo discovery 2010-06-07 → 2018-12-31)

(Testo prodotto dall'agente della famiglia; salvato dal controller perché la scrittura dell'agente era stata bloccata.)

## In breve
- **Registro**: `lab/ledger/multiday.jsonl`, **281 righe, 157 test distinti**, in tre revisioni: rev1
  (91 righe, bug nei dati, rifatta), rev2 (121), rev3 (69: rendimenti % su prezzo raw e approfondimenti).
  Contano tutte come tentativi.
- **Un solo fenomeno sopravvive**: il **reversal a 1-3 settimane**. Se NQ è sceso nelle ultime ~10
  sessioni, nei giorni seguenti sale più della sua deriva, e viceversa.
- Due candidati **nidificati** (il secondo è la gamba long del primo): non due prove indipendenti.
- TSMOM, Moreira-Muir, NR7, serie di giorni consecutivi, 52 settimane, gap, turn-of-month, settimana
  opex: nulli o beta.
- Avvertenza: 2010-2018 è quasi tutto mercato rialzista con cali sempre recuperati; «comprare dopo i
  ribassi» è la regola che un campione così premia. Il 2022 in validazione è il test giusto.

## Convenzioni (`common.py`)
- P_t = open della prima barra 16:00-16:59 NY; segnali solo da barre RTH fino alle 15:59; trade da P_t
  a P_{t+h} su `adj_*`.
- Unità primaria: eccesso sulla deriva, `side·(r − μ·h)`, μ = 6,4 bp/giorno. Per le posizioni continue
  anche differenza di Sharpe vs buy-and-hold (bootstrap a blocchi mobili di 21 giorni).
- Costi 0,75 punti a/r sul cambio di posizione.

## Due trappole trovate
1. `adj_*` è aggiustato additivamente all'indietro: nel 2010 adj ≈ 5.600 contro ≈ 1.850 raw. I
   rendimenti % vanno calcolati come ΔP_adj / P_raw (le differenze in punti sono corrette).
2. 15 sessioni senza RTH (festivi, Sandy 2012-10-29/30, 2014-12-31, 2018-12-05): `rth_close` NaN
   rende NaN le medie mobili per settimane. Tolte e rifatto tutto.

## Ipotesi provate (eccesso sulla deriva; CI 95 % a blocchi mensili)
| # | Ipotesi | Esito |
|---|---|---|
| H01 | Reversal dopo giorno ±1,5/2 σ20 | Long dopo −1,5σ, 5 giorni: +41 bp [+8; +74], 7/9. A 1 giorno niente |
| H02 | Idem in ATR14 | Long 5 giorni +41 [−2; +87]; short ≈ 0 |
| H03 | 3-4 chiusure consecutive | Long dopo 3 cali +40 [−15; +95]; short ≈ 0 |
| H04 | TSMOM 1-12 settimane | **Segno opposto** a 2 settimane: −6,0 bp/g [−9,9; −2,2]; 4-12 settimane ≈ 0 |
| H05 | Moreira-Muir / vol targeting | ΔSharpe da −0,02 a +0,09, CI con lo zero. Scartato |
| H06 | NR7 / inside day | Nessuna direzione; range dopo NR7 −0,13 ATR sotto la media (persistenza, non espansione) |
| H07 | Chiusura agli estremi | Long dopo chiusura sul minimo +40 [−4; +84] |
| H08 | Reversal settimanale per quintili | Long quintile basso +38 [−1; +81]; short quintile alto +26 [−9; +61] |
| H09 | Chiusura sotto MA50 di oltre 3 ATR | +117 [+39; +233], n=84, pochi episodi |
| H10 | Drawdown > 10 % dal massimo a 252 g | +78 [−24; +206] |
| H11 | Dopo gap > 1 ATR | Nulla (n≈35) |
| H12 | Nuovo massimo a 52 settimane | Nulla |
| H14 | RSI(2) | Nulla |
| H15 | Dopo picco di vol (σ5/σ60 > 1,75) | +52 [−8; +121] |
| H16 | Autocorrelazioni / VR | Lag 1-2 ≈ 0; VR(10)=0,80, VR(20)=0,64 |
| H17 | Giorno in calo con volume > 2× | +128 [+65; +190], 8/8, ma n=43 in pochi episodi. Non promosso |
| H18 | Outside day agli estremi | ≈ 0 |
| H19 | Filtro di trend MA100/MA200 | ΔSharpe −0,19 / −0,24 |
| H20 | Turn-of-month | −0,4 bp/g |
| H21 | Segnale solo overnight vs solo RTH | Overnight +6,2 [+1,6; +10,8]; RTH −0,1 |
| H24 | Settimana opex | −0,7 bp/g |

## Il reversal
Contrarian continuo `pos = −segno(rendimento k giorni)`, eccesso sulla deriva: k=5 +3,9; **k=10 +6,0
bp/g [+2,2; +9,9], 8/8 anni**; k=15 +3,4; k=20 +1,1. Altopiano per k 7-14 (+3,2…+6,4). Esecuzione
ritardata 1-2 giorni: +5,3 / +6,0. Placebo circolare p = 0,002 (≈ 0,04 con Bonferroni sulle ~20
varianti). Sharpe 0,61 contro 0,89 del buy-and-hold: come strategia a sé non batte il passivo.

## Candidati (misura del controller: netto 0,75 punti, blocchi per giorno d'ingresso)
| Candidato | n | EV netto (pt) | CI 95 % | p | Anni + | EV − beta | Senza top 20 |
|---|---|---|---|---|---|---|---|
| `multiday_contra10_ls` | 300 | +9,8 | [−1,9; +20,9] | 0,044 | 6/9 | +13,6 | **−2,2** |
| `multiday_contra10_long` | 150 | +24,3 | [+8,5; +38,6] | <0,001 | 9/9 | +13,1 | +6,7 |

Lettura onesta: il long/short fallisce già in discovery il criterio «senza i 20 migliori»; la versione
long ha circa metà dell'EV in beta. Potenza stimata in validazione (K≈10): ~10 % e ~40 %.
