"""Riga PIANO del registro: dichiarazioni fissate PRIMA di guardare qualunque esito del giro 2."""
from lab import core

PIANO = """
FAMIGLIA r2_costaware (giro 2). Domanda: un filtro di costo PRINCIPIATO rende incassabili segnali con vantaggio lordo
piccolo in unita' di volatilita'?
Dati: solo discovery. Istanti di decisione: 12 slot 10:00..15:30 NY (griglia di lab/ml/features.build_dataset),
sessioni valide, ingresso all'open della barra dello slot, uscita al close della barra t+h-1 (h = 30, 60, 120 minuti
se entro le 15:59) oppure alla chiusura RTH (close 15:59).
Unita': (1) regolarita'/diagnostica: rendimento firmato in unita' di vol = punti / (sig1m*sqrt(h)), sig1m = media
delle std 1m RTH delle 20 sessioni precedenti; (2) strategie: PUNTI NETTI per contratto (costo 0,75).
Componenti (segno fissato a priori dalle lezioni del giro 1, non stimato): z_ml = (previsione ensemble 5 semi dei
modelli congelati lab/ml/models - mediana mobile 3000 prev. precedenti) / std mobile 3000 (+);
z_day = r_sess = (P - open RTH)/(sig1m*sqrt(min dall'apertura)) (+, continuazione); z_20d = r_20d (+, momentum 20g);
z_surp = r15 se |r15|>=3 altrimenti 0 (+, sorpresa). Ogni componente scalata dalla sua std mobile passata (3000 righe)
e tagliata a +-3. Compositi a pesi uguali FISSI: COMP3 = (z_ml+z_day+z_20d)/sqrt(3) (solo 2012-2018 per il ML),
COMP2 = (z_day+z_20d)/sqrt(2) (tutto il discovery).
Regola di costo (idea nuova): punti attesi E = b_h * COMP * sigma_h, sigma_h = sig1m*sqrt(h) (h=minuti a fine RTH
per 'close'), b_h = pendenza OLS per l'origine di y_h (unita' vol) su COMP stimata SOLO su sessioni precedenti
(espansiva, min 250 sessioni). Si opera se |E| >= m * 0,75 con m in {1; 1,5; 2}, lato = segno(E).
Un trade alla volta per sessione (il primo slot che qualifica, poi si aspetta l'uscita). Griglia dichiarata:
{COMP2, COMP3} x h {30,60,120,close} x m {1,1.5,2} = 24 regole. Sensibilita' dichiarata: sigma_h con
moltiplicatore HAR (previsione HAR di RV oggi / media 20 RV passate, radice).
Controlli obbligatori per ogni regola guardata: netto, CI blocchi per giorno, anni, senza i 20 migliori, beta
(controller.beta_component), netto SENZA 2011/2015/2018 (trappola 'alta vol = anni specifici'), specchio (lato opposto),
placebo per permutazione (COMP rimescolato fra sessioni dentro lo slot, stessa regola, 100 permutazioni).
Criterio personale di promozione: tutti i 4 criteri del protocollo su discovery + senza-2011/15/18 > 0 + placebo p<0,05.
"""

if __name__ == "__main__":
    core.record("r2_costaware", "PIANO", PIANO.strip(), "discovery", {})
    print("ok")
