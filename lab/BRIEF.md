# Brief per gli agenti del laboratorio

Leggi prima `lab/PROTOCOLLO.md` e `lab/core.py` (è corto). Il progetto intorno (cartella `nqml/`,
`screening_looks.md`, `docs/paper/`) documenta mesi di test su NQ con esito negativo e **quattro
errori di misura** trovati dopo: leggi almeno le righe «TEST A/B/C» e «PASSO 0» di
`screening_looks.md` per sapere quali trappole sono già costate care (look-ahead nella scelta del
lato, ponderazione che seleziona sull'esito, time stop contati come −1R, beta scambiato per alpha).

## Dati
- `bars, daily = core.load("discovery", warmup_days=N)` — barre 1m NQ (continuo front-month per
  volume, 2010-06 → 2018-12), indice `ts_event` UTC. Colonne: `open high low close volume`
  (prezzi GREZZI: da usare per livelli assoluti tipo numeri tondi), `adj_open adj_high adj_low
  adj_close` (aggiustati per i roll: da usare per QUALUNQUE rendimento che attraversa una notte o
  più giorni), `session` (data della sessione: dalle 18:00 NY conta il giorno dopo), `ny_min`
  (minuto NY 0..1439), `dow`, `rth` (09:30-16:00), `roll_bar`, `in_phase`.
- `daily`: una riga per sessione (`rth_open/high/low/close`, `glbx_open`, `day_close`,
  `rth_volume`, `roll_session`, `valid` = almeno 300 barre RTH, `in_phase`). Prezzi già aggiustati.
- Le fasi validation/confirmation sono **vietate** (la guardia alza PermissionError: non aggirarla,
  né leggendo i parquet grezzi a mano). La cassaforte non esiste per te.
- Python: `.venv/Scripts/python.exe` (pandas, numpy, scipy, statsmodels, lightgbm, sklearn).
  Esegui dalla radice del repo: `.venv/Scripts/python.exe -m lab.<famiglia>.<script>` oppure con
  `sys.path` alla radice. Macchina Windows, bash disponibile. 32 core.
- Costi: `core.COST_RT_POINTS` = 0,75 punti per contratto andata e ritorno. NQ = 20 $/punto.
  L'ATR del 2010 era ~4 punti su barre 5m, nel 2018 ~15: se misuri in punti, gli anni recenti pesano
  di più; dichiara l'unità (punti, ATR, %) PRIMA di guardare e tienila.

## Cosa devi fare
1. Esplora la tua famiglia di idee sul discovery con fantasia: più ipotesi diverse, meglio è.
   Registra OGNI test che guardi con `core.record(famiglia, test_id, descrizione, "discovery", stats)`
   (`stats` = l'output di `core.day_block_bootstrap`, più ciò che vuoi).
2. Per le idee più promettenti fai i controlli: netto dei costi, anno per anno (`core.yearly`),
   senza i 20 trade migliori (`core.drop_top`), beta (una strategia sbilanciata long su un mercato
   che sale «vince» per costruzione: confronta con l'esposizione passiva equivalente), specchio o
   placebo quando serve, sensibilità ai parametri (un vero effetto non vive su un solo valore).
3. Scegli **al massimo 3 candidati** e congelali in `lab/<famiglia>/candidates.py`:

```python
CANDIDATES = [
    dict(
        id="<famiglia>_<nome>",
        description="regola esatta in una frase",
        rationale="perché dovrebbe esistere (meccanismo economico o letteratura)",
        warmup_days=20,                   # sessioni di lookback necessarie prima della fase
        kind="tradeable",                 # oppure "regularity" (binario «reale ma non incassabile»)
        fn=nome_funzione,                 # fn(bars, daily) -> DataFrame
        discovery=dict(n=..., mean_net=..., lo=..., hi=..., p_pos=..., years_pos="7/9"),
    ),
]
```
   `fn` deve funzionare su QUALUNQUE fase (il controller la chiamerà sui dati di validazione con il
   warmup), usare solo informazione nota prima dell'ingresso, e restituire un trade per riga con
   colonne: `session` (datetime64), `entry_ts`, `exit_ts` (UTC), `side` (+1/−1), `gross_pts`
   (punti lordi per 1 contratto, da prezzi adj se attraversa la notte). Il controller toglierà i costi
   e filtrerà `in_phase`. Per `kind="regularity"`, `gross_pts` è la quantità misurata e il test sarà
   bilaterale sul lordo.
   Aggiungi un test minimo che `fn` giri su `core.load("discovery")` e restituisca i numeri dichiarati.
4. Scrivi `lab/<famiglia>/REPORT.md` (italiano): tutte le idee provate, numero totale di test dal
   registro, cosa hai scartato e perché, i candidati con i numeri. Onestà prima di tutto: «niente
   regge» è un risultato valido e utile. Non gonfiare.

## Cosa NON fare
- Non toccare file fuori da `lab/<famiglia>/` e `lab/ledger/<famiglia>.jsonl` (niente modifiche a
  `nqml/`, `lab/core.py`, config, documenti). Se `core.py` ha un bug, scrivilo nel REPORT.
- Niente git commit (lo fa il controller). Niente acquisti di dati, niente rete.
- Non scegliere il lato di un trade con informazione successiva all'ingresso; non campionare o
  pesare eventi con regole che dipendono dall'esito.
