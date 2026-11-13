# Dashboard «Scena» del laboratorio

Una pagina locale che mostra i registri del laboratorio una scena alla volta, pensata per essere registrata
con OBS. Legge soltanto file che il laboratorio scrive già. Non carica barre, non esegue test, non scrive nulla.

## Avvio

Dalla cartella del repo:

    python -m lab.dashboard

Si apre `http://127.0.0.1:8765`. La pagina si vede solo da questo computer. `Ctrl+C` nel terminale la chiude.

| Opzione | Effetto |
| --- | --- |
| `--port 9000` | usa un'altra porta |
| `--no-open` | non apre il browser |
| `--demo` | mostra anche le figure finte (vedi sotto) |
| `--lab <cartella>` | legge un'altra cartella `lab/` |

## Le scene

| Tasto | Scena | Che cosa mostra | Da dove legge |
| --- | --- | --- | --- |
| 1 | Storia | ogni risultato come un punto, in ordine di esecuzione, con la fascia del caso | `lab/ledger` |
| 2 | Distribuzione | dove cadono gli z-score rispetto alla curva «edge zero, senza costi» | `lab/ledger` |
| 3 | Test | un test: media, intervallo al 95 %, dettaglio per anno | `lab/ledger` |
| 4 | Verdetti | i candidati di validation e confirmation, con PASS e FAIL | `lab/verdicts` |
| 5 | Figura | un grafico salvato da un test con `lab.viz` | `lab/figures` |

Altri tasti: `spazio` fa ripartire l'animazione, `H` nasconde o mostra la barra dei controlli.
La barra si nasconde da sola dopo tre secondi senza muovere il mouse.

La pagina controlla i registri ogni quattro secondi: quando un test scrive una riga nuova, la scena si aggiorna.

## Registrare con OBS

1. In OBS aggiungi una sorgente «Cattura finestra» sul browser, oppure una sorgente «Browser» con l'indirizzo
   della scena.
2. La scena si adatta alla finestra: orizzontale per 16:9, verticale per 9:16.
3. L'indirizzo ricorda la scena scelta. Aggiungi `&ui=0` per non mostrare mai la barra dei controlli.

Esempi di indirizzo:

    http://127.0.0.1:8765/?scena=storia&dur=40&ui=0
    http://127.0.0.1:8765/?scena=storia&fam=r6_gamma&ui=0
    http://127.0.0.1:8765/?scena=verdetti&ui=0

`dur` è la durata in secondi del replay della Storia (20, 40, 60 o 90).

## Salvare il grafico di un test

Dentro lo script di un test, accanto a `core.record`:

    from lab import viz
    viz.bars("r10_fib", "T1", "per_anno", title="Netto medio per anno",
             labels=anni, values=netti, ylabel="punti NQ netti per trade")

Tipi disponibili: `viz.line`, `viz.bars`, `viz.scatter`, `viz.hist`, `viz.placebo`. Le istruzioni complete
sono in `lab/viz.py`. Ogni chiamata scrive un file in `lab/figures/<famiglia>/`.

**Solo aggregati.** Medie, quote, conteggi, istogrammi. Mai prezzi, barre o tick: i dati di mercato hanno una
licenza e questi grafici finiscono in video pubblici. `lab.viz` rifiuta più di 2.000 punti per serie.

## Figure di prova

    python -m lab.dashboard.demo
    python -m lab.dashboard --demo

Scrive cinque figure con numeri inventati in `lab/figures/_demo/`. Hanno DEMO nel titolo e un riquadro rosso
sullo schermo, e senza `--demo` non compaiono. Non vanno committate.

## Come leggere i numeri

- **z-score.** Distanza del risultato dallo zero, misurata in errori standard. Si ricava dal p-value registrato
  e dal segno della media. Se un test non ha registrato un p-value, non compare nelle scene 1 e 2.
- **Fascia del caso.** |z| < 1,96: un risultato lì dentro non si distingue dal caso al 5 %. Con migliaia di
  test molti punti cadono fuori dalla fascia per puro caso: per questo esistono validation e confirmation.
- **Punti allineati in alto e in basso.** Il bootstrap ha 10.000 repliche, quindi il p-value più piccolo che
  può registrare è 1 su 10.000. Tutti i risultati oltre quel limite finiscono sulla stessa riga.
- **Giri 8, 9 e 10.** Salvano il risultato in campi diversi dai giri vecchi, e la dashboard li legge così:
  blocco `netto` (media netta in punti, z dal `p_two` e dal segno, p mostrato = quello a una coda del test);
  `diff` con `p` a una coda (z dal p a una coda, ipotesi «diff > 0»); `mean_net_R` delle prove di futilità
  (media, intervallo e anni, ma nessuno z: il PREREG non registra un p, e la dashboard non ne inventa uno).
- **p-value a una coda uguale a 1.** Vuol dire «risultato dalla parte sbagliata», non «test superato».
- **Righe con due versi.** Un test che registra `fade_*` e `cont_*` diventa due punti, ma conta come un test.
- **Righe di controllo.** Le righe con `kind = "control"` non sono test di ipotesi: restano fuori dal conto e
  dalle scene 1 e 2.
- **Verdetti.** Errore standard ed effetto minimo visibile sono calcolati come in `lab/potenza.py`.
  La tacca grigia è la soglia `z` che corrisponde all'α del verdetto, dopo la correzione per K.
