"""Registra la riga PIANO (prima di ogni risultato) e costruisce la cache delle matrici."""
from lab import core
from lab.r2_footprints import common as C

if __name__ == "__main__":
    core.record(C.FAM, "PIANO",
                "PIANO fissato prima di ogni esito (2026-09-23): batterie F1-F8 descritte nella docstring di "
                "lab/r2_footprints/common.py (orologi istituzionali, esperimento naturale DST, pressione e rientro, "
                "leveraged ETF con trend temporale, fine mese/trimestre/opex, periodicita' degli algoritmi e BVC, "
                "tempo del volume, irreversibilita' temporale). Unita': log-rapporti per le impronte, punti lordi "
                "per le regolarita' direzionali, punti netti (0,75) per i tradeable. Esecuzione: segnale a chiusura "
                "barra, ingresso open barra dopo. Griglie: pressione {15:45,15:50,15:55}->16:00; rientro "
                "16:00->{16:15,17:00,09:30 domani}; quantili causali {0.5,0.7,0.9}; BVC finestra {60,120,180} "
                "orizzonte {30,60}.",
                "discovery", {})
    D, daily = C.get()
    print(D["adj_close"].shape, int(D["in_phase"].sum()), int(D["valid"].sum()))
