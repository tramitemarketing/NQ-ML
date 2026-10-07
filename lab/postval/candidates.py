"""Ipotesi registrata DOPO la validazione e PRIMA della conferma (PROTOCOLLO §8).

La regolarita' `cross_session_rth_to_evening` ha superato la validazione come fatto lordo (+1,70 punti,
p 0,0013). Qui la stessa identica regola viene sottoposta alla conferma come STRATEGIA, con i quattro
criteri tradeable. Nessuna evidenza della validazione conta a suo favore: la giudica solo la conferma.
"""
from lab.cross_session.candidates import rth_direction_continues_after_halt

CANDIDATES = [
    dict(
        id="postval_rth_to_evening_trade",
        description=("Alle 16:15 NY (o alla prima barra successiva) entra nel verso del rendimento RTH "
                     "09:30->16:00; esci al close dell'ultima barra prima delle 17:00. 1 contratto, costi 0,75."),
        rationale="continuazione post-chiusura della direzione del giorno (coperture/ribilanciamenti non completati)",
        warmup_days=5,
        kind="tradeable",
        fn=rth_direction_continues_after_halt,
        validation_seen=dict(n=1186, mean_net=0.949, lo=-0.099, hi=2.004, p_pos=0.0387, drop20=-0.327,
                             note="visto dopo la validazione: per questo non conta come prova"),
    ),
]
