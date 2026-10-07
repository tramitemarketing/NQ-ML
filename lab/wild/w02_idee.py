"""IDEE SELVAGGE, giro 2 (dopo aver visto w01; tutto cio' che segue e' dichiarato POST-HOC).

(a) Specchi dei risultati fortemente negativi di w01 (scelti DOPO averli visti: contano come test
    nuovi e vanno letti con la correzione per i tentativi) — con test bilaterale sul lordo per il
    binario «regolarita'».
(b) Sensibilita' di W12_records_fresh (unico p<0,05 del giro 1).
(c) Idee nuove, direzione dichiarata qui prima di guardarle:
W15 magnete all'apertura: alle 09:30 se il prezzo grezzo e' entro 0,15 % da un multiplo di 100,
    vai verso il livello fino alle 10:30.
W16 buco di liquidita': barra RTH con escursione > 4x la mediana dello stesso minuto (20 sess.) ma
    volume sotto la mediana (mossa senza scambi = senza informazione) -> CONTRO la barra, 15 / 60 min.
W17 complessita' di Lempel-Ziv della sequenza su/giu' della mattina: bassa -> prosecuzione.
W18 orologio degli algoritmi: somma dei rendimenti delle barre ai minuti :00 :15 :30 :45 della mattina
    (escluse 09:30 e 10:00, notizie) = flusso di ordini figli a orario -> prosecuzione 11:30->16:00.
W19 impronta MOC/VWAP di fine giornata: volume normalizzato 14:00-15:30 nel terzile alto -> segui la
    direzione 14:00-15:30 da 15:30 a 16:00.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.wild import common as C
from lab.wild import features as F
from lab.wild.w01_idee import ev, OUT


def lz_complexity(bits):
    s = "".join("1" if b else "0" for b in bits)
    i, c, n = 0, 0, len(s)
    seen = set()
    w = ""
    for ch in s:
        w += ch
        if w not in seen:
            seen.add(w); c += 1; w = ""
    return c + (1 if w else 0)


def main():
    g = C.grid()
    P, V, sess = g["P"], g["V"], g["sess"]
    S = len(sess); allS = np.arange(S)
    mdir = np.sign(P[:, 120] - P[:, 0])
    r1 = np.diff(P, axis=1)

    # ---------------- (a) specchi post-hoc
    for L in (100, 50):
        lvl = np.floor(P / L); cross = np.diff(lvl, axis=1) != 0
        for h in (15, 60):
            s_l, k_l, sd_l = [], [], []
            for s in range(S):
                js = np.flatnonzero(cross[s, 30:330]) + 30
                if len(js):
                    j = js[0] + 1
                    s_l.append(s); k_l.append(j); sd_l.append(-np.sign(P[s, j] - P[s, j - 1]))
            ev(f"W01m_round{L}_cross_first_FADE_h{h}", f"POST-HOC specchio di W01: contro il primo "
               f"attraversamento di {L}, {h} min", s_l, k_l, np.array(k_l) + h, sd_l)
            ev(f"W01m_round{L}_cross_first_gross2_h{h}", f"POST-HOC regolarita': lordo (bilaterale) della "
               f"prosecuzione dopo il primo attraversamento di {L}, {h} min",
               s_l, k_l, np.array(k_l) + h, -np.array(sd_l), gross_test=True)
    asym = F.speed_asym(P, 0, 120)
    for kout, nm in ((180, "h60"), (390, "close")):
        ev(f"W03m_speedasym_FOLLOW_{nm}", "POST-HOC specchio di W03: SEGUI l'asimmetria di velocita' "
           f"(salite violente -> su), 11:30->{nm}", allS, np.full(S, 120), np.full(S, kout), np.sign(asym))
        ev(f"W03m_speedasym_gross2_{nm}", "POST-HOC regolarita': lordo bilaterale di segno(asimmetria) x "
           f"rendimento 11:30->{nm}", allS, np.full(S, 120), np.full(S, kout), np.sign(asym), gross_test=True)
    # controllo: l'asimmetria e' solo la direzione della mattina travestita?
    ev("W03c_same_sign_as_morning_share", "CONTROLLO: segui la mattina solo quando asimmetria e mattina "
       "concordano 11:30->12:30", allS, np.full(S, 120), np.full(S, 180),
       np.where(np.sign(asym) == mdir, mdir, 0))
    ev("W03c_disagree", "CONTROLLO: segui l'asimmetria quando e' DISCORDE dalla mattina 11:30->12:30",
       allS, np.full(S, 120), np.full(S, 180), np.where(np.sign(asym) != mdir, np.sign(asym), 0))

    # ---------------- (b) sensibilita' W12 fresh
    for win in (90, 120, 150):
        nh, nl, last = F.records(P, 0, win)
        for fr in (5, 10, 15, 30):
            fresh = last >= (win - 5 - fr)
            ev(f"W12s_fresh_w{win}_f{fr}_close", f"sensibilita' W12: finestra 09:30+{win}m, ultimo record entro "
               f"{fr} min dalla fine, prosecuzione -> 16:00", allS, np.full(S, win), np.full(S, 390),
               np.where(fresh, np.sign(nh - nl), 0))
    # la stessa cosa usando il verso dell'ULTIMO record invece di nh-nl
    nh, nl, last = F.records(P, 0, 120)
    seg = P[:, 0:121]
    runmax = np.maximum.accumulate(seg, 1); runmin = np.minimum.accumulate(seg, 1)
    at_hi = seg[:, 120] >= runmax[:, 119]; at_lo = seg[:, 120] <= runmin[:, 119]
    ev("W12s_at_extreme_close", "variante: alle 11:30 il prezzo e' sul massimo (minimo) della mattina -> "
       "long (short) fino alle 16:00", allS, np.full(S, 120), np.full(S, 390),
       np.where(at_hi & ~at_lo, 1.0, np.where(at_lo & ~at_hi, -1.0, 0.0)))

    # ---------------- W15 magnete all'apertura
    for L in (100, 50):
        x = P[:, 0]; near = np.round(x / L) * L; dist = near - x
        ok = (np.abs(dist) <= 0.0015 * x) & (np.abs(dist) >= 1.0)
        ev(f"W15_openmagnet{L}_h60", f"09:30 entro 0,15% dal multiplo di {L}: verso il livello fino alle 10:30",
           allS, np.zeros(S), np.full(S, 60), np.where(ok, np.sign(dist), 0))

    # ---------------- W16 buco di liquidita'
    rng_bar = np.abs(r1[:, :390])
    medr = pd.DataFrame(rng_bar).rolling(20, min_periods=10).median().shift(1).to_numpy()
    medv = pd.DataFrame(V).rolling(20, min_periods=10).median().shift(1).to_numpy()
    for h in (15, 60):
        s_l, k_l, sd_l = [], [], []
        for s in range(S):
            last = -999
            cand = np.flatnonzero((rng_bar[s, 15:375] > 4 * np.maximum(medr[s, 15:375], 0.25)) &
                                  (V[s, 15:375] < medv[s, 15:375])) + 15
            for j in cand:
                if j + 1 - last < h or j + 1 + h > 390:
                    continue
                s_l.append(s); k_l.append(j + 1); sd_l.append(-np.sign(r1[s, j])); last = j + 1
        ev(f"W16_liqhole_fade_h{h}", f"barra con escursione >4x mediana e volume < mediana: contro, {h} min",
           s_l, k_l, np.array(k_l) + h, sd_l)

    # ---------------- W17 Lempel-Ziv
    lz = np.array([lz_complexity(r1[s, :120][r1[s, :120] != 0] > 0) for s in range(S)], float)
    lzl = F.roll_q(lz, 1 / 3)
    ev("W17_lowLZ_cont_close", "complessita' LZ della sequenza su/giu' 09:30-11:30 nel terzile basso -> "
       "prosecuzione 11:30->16:00", allS, np.full(S, 120), np.full(S, 390), np.where(lz < lzl, mdir, 0))

    # ---------------- W18 orologio degli algoritmi
    clock = [k for k in range(0, 120) if (k % 15 == 0) and k not in (0, 30)]   # 09:45, 10:15, 10:30, ...
    cs = r1[:, clock].sum(1)
    ev("W18_clockflow_cont_close", "segno della somma dei rendimenti delle barre :00/:15/:30/:45 della "
       "mattina (escluse 09:30, 10:00) -> 11:30->16:00", allS, np.full(S, 120), np.full(S, 390), np.sign(cs))
    ev("W18_clockflow_cont_h60", "idem 11:30->12:30", allS, np.full(S, 120), np.full(S, 180), np.sign(cs))

    # ---------------- W19 impronta di fine giornata
    vn = F.vol_profile_norm(V)
    lv = np.nanmean(vn[:, 270:360], 1); lvh = F.roll_q(lv, 2 / 3)
    d2 = np.sign(P[:, 360] - P[:, 270])
    ev("W19_latevol_cont_last30", "volume normalizzato 14:00-15:30 nel terzile alto -> segui 14:00-15:30 "
       "da 15:30 a 16:00", allS, np.full(S, 360), np.full(S, 390), np.where(lv > lvh, d2, 0))
    ev("W19_latevol_cont_last30_all", "controllo: segui 14:00-15:30 da 15:30 a 16:00, tutti i giorni",
       allS, np.full(S, 360), np.full(S, 390), d2)

    pd.DataFrame(OUT).to_csv(C.__file__.replace("common.py", "wild_results_2.csv"), index=False)


if __name__ == "__main__":
    main()
