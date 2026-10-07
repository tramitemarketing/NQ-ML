# Lezioni del giro 1 (per gli agenti del giro 2)

Giro 1: 8 famiglie, 2.699 test in discovery, 13 candidati. **Nessuna strategia direzionale è
sopravvissuta** a validazione e conferma. **Due regolarità sono state confermate** su tutti e tre i
blocchi (2010-18, 2019-23, 2023-26) — entrambe note in letteratura:
1. **La volatilità realizzata di domani è prevedibile**: un HAR (Corsi 2009) sul log della varianza
   realizzata RTH (somma dei rendimenti log 5m al quadrato, prezzi grezzi) stimato su 500 sessioni
   precedenti batte nettamente la media a 22 giorni (R² fuori campione ~0,62 contro ~0,40).
2. **Una notte agitata anticipa una giornata agitata**: il range 18:00-09:30 (normalizzato sulla sua
   media a 20 notti) predice il range RTH, anche controllando per il range di ieri.
Le funzioni che le calcolano sono in `lab/vol/candidates.py` e `lab/cross_session/candidates.py`
(puoi importarle o copiarne la logica; non modificarle).

## Cosa abbiamo imparato in discovery (tutto qui è dato di discovery)
- **I costi sono il nemico principale.** 0,75 punti a/r. Quasi tutti gli effetti direzionali trovati
  valgono 0,1-0,7 punti lordi per trade: veri o no, sono sotto i costi. Il modello ML generico
  (`lab/ml`) ha un IC reale ma piccolo (+0,02 a 30 minuti, 7/7 anni) → lordo ~0,2 punti.
- **Il costo è fisso in punti, il movimento no**: scala con la volatilità. Un vantaggio in «unità di
  volatilità» vale più punti quando la volatilità è alta. (Nel discovery il momentum dell'ultima
  mezz'ora nel verso della giornata era negativo in regime calmo e positivo in regime agitato.)
- **Beta**: nel 2010-2018 il 90 % della salita di NQ è avvenuto fuori dall'RTH. Qualunque long che
  attraversa la notte «vince» per costruzione. Il controller ora chiede che l'EV meno beta sia
  significativo (PROTOCOLLO §7). In RTH la deriva è quasi zero.
- **Calibrazione del caso** (`lab/wild/REPORT.md`): su regole-placebo intraday al netto dei costi, p<0,05
  capita di rado; sulle regole long notturne/multi-giorno capita nel 45 % dei casi. Sulle regolarità
  lorde ~4 %.
- **Criterio «senza i 20 trade migliori»**: ha bocciato quasi tutto. Gli effetti che vivono su pochi
  giorni enormi (2018 Q4, 2011, 2015) non sono effetti. Con pochi eventi (n < 150) è severissimo.
- **Il 2022 (mercato orso lungo) ha distrutto le regole «compra dopo i ribassi»**, che il discovery
  2010-18 (quasi tutto rialzista) premiava.
- **Trappole dei dati** (non bug, ma attenzione):
  - `adj_*` è aggiustato additivamente all'indietro: i livelli vecchi sono spostati di migliaia di punti.
    Rendimenti % = Δadj / prezzo GREZZO; mai adj/adj.
  - Fra il 2010 e il 2015 NQ scambiava fino alle 17:15: le barre 17:00-17:15 finiscono nella sessione
    successiva (e `daily.glbx_open` in quegli anni è il prezzo delle 17:00).
  - Pausa 16:15-16:30 presente fino a metà 2021, poi tolta.
  - 15 sessioni senza RTH (festivi, uragano Sandy): `rth_close` NaN → le medie mobili diventano NaN.
  - Mancano 2014-06-13, 2014-09-24/25, 2016-09-02→19.
- **Già esplorato e fallito** (non rifarlo identico): fade/rottura della value area, ORB15, gap, prima e
  ultima ora incondizionate, VWAP, overnight long, momentum intraday della letteratura (Gao, Baltussen),
  turnaround Tuesday, reversal a 10 giorni, turn-of-month, pre-FOMC, NFP, numeri tondi, massimi/minimi
  notturni come livelli, NR7, Moreira-Muir, TSMOM, fade dei movimenti estremi a 1-5 minuti.
