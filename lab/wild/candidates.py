"""Candidati congelati della famiglia «wild».

NESSUN CANDIDATO. Motivazione (dettagli in REPORT.md):
- nessuna delle 21 idee selvagge (93 test distinti) passa i quattro criteri del PROTOCOLLO sul
  discovery al netto dei costi;
- il miglior netto (W12 «record freschi», +2,48 punti, p 0,029) vive su una sola finestra
  (90 e 150 minuti non reggono), ha EV negativo senza i 20 trade migliori ed e' in linea con il
  tasso di falsi positivi misurato sui placebo per orizzonti «fino alla chiusura»;
- l'unica regolarita' lorda (W03m, asimmetria di velocita' -> ora successiva, +0,70 punti lordi,
  p bilaterale 0,014, 9/9 anni) e' stata trovata POST-HOC come specchio dell'ipotesi dichiarata, e
  in regressione con il rendimento della mattina perde significativita' (t 1,03): e' in gran parte
  momentum della mattina travestito, territorio di un'altra famiglia.
Inviare candidati deboli alzerebbe K e quindi la soglia Bonferroni 0,05/K per tutte le famiglie.
"""
CANDIDATES: list[dict] = []


def _test():
    assert CANDIDATES == []
    print("wild: 0 candidati (scelta motivata in REPORT.md)")


if __name__ == "__main__":
    _test()
