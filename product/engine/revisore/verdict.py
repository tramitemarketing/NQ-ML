"""Semafori e verdetto A-F.

Il verdetto segue la logica del laboratorio: prima le condizioni necessarie (guadagna al netto dei
costi in modo significativo, non è spiegato dal beta, batte il caso con la stessa struttura), poi la
robustezza (Deflated Sharpe con N tentativi, anni, senza i migliori, fuori campione, numerosità).
Un difetto grave (look-ahead catturato, trade incoerenti con il mercato) dà F a prescindere.

  A  vantaggio solido: tutte le prove superate
  B  vantaggio probabile, con una riserva
  C  segnali deboli o misti: il risultato potrebbe dipendere dalla selezione o da pochi episodi
  D  nessun vantaggio dimostrato: compatibile con il caso o spiegato dal mercato (beta)
  E  perde al netto dei costi
  F  difetto grave: look-ahead o dati che non tornano con il mercato
"""
from __future__ import annotations

import numpy as np

GREEN, YELLOW, RED, GREY = "verde", "giallo", "rosso", "grigio"

GRADE_TEXT = {
    "A": "Vantaggio solido: la strategia supera tutte le prove, anche tenendo conto dei tentativi fatti.",
    "B": "Vantaggio probabile, con una riserva da tenere d'occhio.",
    "C": "Segnali deboli o misti: il risultato potrebbe dipendere dalla selezione o da pochi episodi.",
    "D": "Nessun vantaggio dimostrato: il risultato è compatibile con il caso o spiegato dal mercato.",
    "E": "Perde al netto dei costi.",
    "F": "Difetto grave: il backtest non è affidabile così com'è.",
}


def _c(key, title, status, value, why, graded=True):
    return {"key": key, "title": title, "status": status, "value": value, "why": why, "graded": graded}


def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/d"
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_checks(R: dict) -> list[dict]:
    ch = []
    q = R.get("quality")
    if q:
        corr, al = q.get("corr", np.nan), q.get("share_aligned", np.nan)
        st = GREEN if (corr >= 0.9 and al >= 0.95) else YELLOW if corr >= 0.6 else RED
        ch.append(_c("dati", "I trade tornano con i dati di mercato?", st,
                     f"correlazione {fmt(corr)}; agganciati {fmt(100 * al, 0)} %",
                     "Riprezziamo ogni trade sui dati di mercato: se il P&L dichiarato non somiglia al movimento "
                     "del mercato, il fuso orario, lo strumento o l'unità sono sbagliati (o i fill sono irrealistici)."))
    else:
        ch.append(_c("dati", "I trade tornano con i dati di mercato?", GREY, "nessun dato di mercato",
                     "Senza dati di mercato non possiamo verificare i prezzi dichiarati.", graded=False))
    n, nd = R["boot"]["n"], R["boot"]["n_days"]
    ch.append(_c("numerosita", "Ci sono abbastanza trade?", GREEN if (n >= 100 and nd >= 50) else YELLOW if n >= 30 else RED,
                 f"{n} trade in {nd} giorni",
                 "Con pochi trade anche un risultato brillante può essere fortuna."))
    b = R["boot"]
    ch.append(_c("netto", "Guadagna al netto dei costi, oltre il caso?",
                 GREEN if (b["mean"] > 0 and b["p_pos"] < 0.05) else YELLOW if b["mean"] > 0 else RED,
                 f"{fmt(b['mean'])} punti/trade, p = {fmt(b['p_pos'], 4)}",
                 "Bootstrap a blocchi per giorno: rimescoliamo le giornate per vedere quanto spesso il caso "
                 "produce una media così alta. p sotto 0,05 = raro per caso."))
    d = R["dsr"]
    ch.append(_c("dsr", f"Regge anche contando i tentativi fatti (N = {d['n_trials']})?",
                 GREEN if d["dsr"] >= 0.95 else YELLOW if d["dsr"] >= 0.80 else RED,
                 f"DSR = {fmt(d['dsr'], 3)} (Sharpe annuo {fmt(R['sharpe_ann'])}, soglia del caso {fmt(d['sr0'] * np.sqrt(252))})",
                 "Chi prova N varianti e tiene la migliore trova per caso uno Sharpe alto. Il Deflated Sharpe "
                 "Ratio misura la probabilità che il vantaggio sia vero dopo questa selezione (serve >= 0,95)."))
    be = R.get("beta")
    if be:
        sa = be["stat_adj"]
        st = GREEN if (sa["mean"] > 0 and sa["p_pos"] < 0.05) else YELLOW if sa["mean"] > 0 else RED
        if be["flag"]:
            st = RED
        ch.append(_c("beta", "È abilità o solo il mercato che sale?", st,
                     f"beta {fmt(be['beta_mean'])} su {fmt(be['net_mean'])} punti/trade; netto-beta p = {fmt(sa['p_pos'], 4)}",
                     "Il beta è quanto avrebbe guadagnato chiunque fosse esposto nelle stesse ore, nello stesso verso, "
                     "senza scegliere niente. Togliamo il beta e rifacciamo il test."))
    else:
        ch.append(_c("beta", "È abilità o solo il mercato che sale?", GREY, "nessun dato di mercato",
                     "Serve il mercato per misurare il beta.", graded=False))
    pl = R.get("placebo")
    if pl:
        s = pl["scenarios"]["caso_puro"]
        ch.append(_c("placebo", "Batte migliaia di strategie a caso con la stessa struttura?",
                     GREEN if s["percentile"] >= 95 else YELLOW if s["percentile"] >= 80 else RED,
                     f"percentile {fmt(s['percentile'], 1)} su {pl['n_sims']} placebo",
                     "Stessi giorni con trade, stessi orari e durate, stessi costi, ma giorni e lati a caso: se la "
                     "strategia vera non sta sopra il 95 % di queste, non si distingue dal caso."))
        s2 = pl["scenarios"].get("stessi_lati")
        if s2:
            ch.append(_c("placebo_lati", "Il momento scelto conta, oltre allo sbilanciamento long/short?",
                         GREEN if s2["percentile"] >= 90 else YELLOW if s2["percentile"] >= 75 else RED,
                         f"percentile {fmt(s2['percentile'], 1)}",
                         "Placebo con gli stessi lati della strategia ma giorni casuali: se la strategia non li batte, "
                         "il suo risultato viene dall'essere long (o short) e non dalla scelta dei giorni."))
    else:
        ch.append(_c("placebo", "Batte migliaia di strategie a caso con la stessa struttura?", GREY,
                     "nessun dato di mercato", "Serve il mercato per generare i placebo.", graded=False))
    y = R["years"]
    ny = len(y)
    pos = int((y["mean"] > 0).sum())
    share = pos / ny if ny else np.nan
    ch.append(_c("anni", "Guadagna nella maggior parte degli anni?",
                 GREY if ny < 2 else GREEN if (share >= 0.6 and ny >= 3) else YELLOW if share >= 0.5 else RED,
                 f"{pos} anni positivi su {ny}",
                 "Un vantaggio vero si vede in quasi tutti gli anni; se vive di un anno solo è fragile.",
                 graded=ny >= 2))
    k = R["top_k"]
    dt = R["drop_top"]
    ch.append(_c("droptop", f"Resta positiva senza i {k} trade migliori?", GREEN if dt > 0 else RED,
                 f"{fmt(dt)} punti/trade senza i {k} migliori",
                 "Se togliendo pochi trade eccezionali il risultato diventa negativo, la strategia è una lotteria."))
    dc = R["decay"]
    oos = dc["oos"]
    if oos["n"]:
        st = GREEN if (oos["mean"] > 0 and oos["p_pos"] < 0.05 and (dc["ratio"] >= 0.5)) else \
            YELLOW if oos["mean"] > 0 else RED
        ttl = "Tiene fuori campione?" if dc["true_oos"] else "È stabile nel tempo (primi 2/3 contro ultimo 1/3)?"
        ch.append(_c("oos", ttl, st,
                     f"dentro {fmt(dc['is']['mean'])} → fuori {fmt(oos['mean'])} punti/trade (rapporto {fmt(dc['ratio'])})",
                     "Le regolarità vere mantengono la dimensione (rapporto 0,8-1,2); quelle trovate scavando si "
                     "restringono a 0,35-0,7 o cambiano segno." + ("" if dc["true_oos"] else
                                                                   " Senza la data di fine ottimizzazione è solo un controllo di stabilità."),
                     graded=dc["true_oos"]))
    la = R.get("lookahead")
    if la:
        ch.append(_c("lookahead", "Il codice usa informazione dal futuro?", GREEN if la["ok"] else RED,
                     f"{len(la['problems'])} violazioni su {la['n_runs']} prove" +
                     ("" if la.get("control_caught", True) else " (ATTENZIONE: controllo positivo non catturato)"),
                     "Alteriamo il futuro dopo un istante T (anche esattamente all'ingresso dei trade) e controlliamo "
                     "che i trade decisi prima di T non cambino. Una strategia onesta non se ne accorge."))
    else:
        ch.append(_c("lookahead", "Il codice usa informazione dal futuro?", GREY, "non eseguito",
                     "Richiede il codice della strategia come funzione Python (--strategy).", graded=False))
    return ch


def grade(R: dict, checks: list[dict]) -> dict:
    c = {x["key"]: x for x in checks}
    flags = {"beta": bool(R.get("beta", {}) and R["beta"]["flag"]), "leak": False, "data": False}
    reasons = []
    if "lookahead" in c and c["lookahead"]["status"] == RED:
        flags["leak"] = True
        reasons.append("il codice usa informazione futura (look-ahead)")
    if c["dati"]["status"] == RED:
        flags["data"] = True
        reasons.append("i P&L dichiarati non tornano con i dati di mercato")
    if reasons:
        g = "F"
    elif R["boot"]["mean"] <= 0:
        g = "E"
        reasons.append("la media per trade al netto dei costi è negativa o nulla")
    else:
        core_fail = []
        if c["netto"]["status"] != GREEN:
            core_fail.append("il guadagno netto non è statisticamente distinguibile da zero")
        if c["beta"]["status"] in (RED, YELLOW):
            core_fail.append("il risultato è spiegato in larga parte dal beta (il mercato nelle ore di esposizione)")
        if c["placebo"]["status"] in (RED, YELLOW):
            core_fail.append("non si distingue dalle strategie casuali con la stessa struttura")
        if core_fail:
            g = "D"
            reasons += core_fail
        else:
            rob = [x for x in checks if x["key"] in ("dsr", "anni", "droptop", "oos", "numerosita", "placebo_lati")
                   and x["graded"]]
            reds = [x for x in rob if x["status"] == RED]
            yel = [x for x in rob if x["status"] == YELLOW]
            dsr = R["dsr"]["dsr"]
            if not reds and not yel:
                g = "A"
            elif len(reds) <= 1 and (dsr >= 0.80) and c["numerosita"]["status"] != RED:
                g = "B"
            else:
                g = "C"
            reasons += [f"riserva: {x['title']} ({x['value']})" for x in reds + yel]
            if g == "A" and (c["beta"]["status"] == GREY or c["placebo"]["status"] == GREY):
                g = "B"
                reasons.append("senza dati di mercato beta e placebo non sono verificati")
    flags["no_edge"] = g in ("D", "E")
    return {"grade": g, "headline": GRADE_TEXT[g], "reasons": reasons, "flags": flags}
