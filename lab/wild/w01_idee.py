"""IDEE SELVAGGE (famiglia wild), discovery 2010-06 -> 2018-12.

Unita' dichiarata prima: punti netti (0,75 a/r) per 1 contratto, trade tutti in RTH (nessun roll).
Ipotesi e DIREZIONE dichiarate qui prima di guardare; ogni variante e' registrata.

W01 numeri tondi, attraversamento (Osler 2003: stop oltre i tondi -> prosecuzione). Primo close RTH
    (10:00-15:00) che attraversa un multiplo di 100 (o 50) del prezzo GREZZO; lato = verso
    dell'attraversamento; 15 / 60 min.
W02 numeri tondi, magnete/pinning (Ni-Pearson-Poteshman 2005): alle 15:00 (o 15:30) se il prezzo
    grezzo dista <= 0,15 % dal multiplo di 100 (o 50) piu' vicino, vai verso il livello fino alle 16:00.
W03 asimmetria di velocita': log(|salita media al minuto| / |discesa media|) 09:30-11:30. Salite
    «violente» = ricopertura forzata, transitoria -> il pomeriggio va CONTRO (lato = -segno).
W04 asimmetria come skewness dei rendimenti 1m 09:30-11:30, lato = -segno(skew), stesso meccanismo.
W05 giorni-tipo: k-means sulla forma normalizzata delle prime 2 ore; segno per gruppo stimato su
    una meta' del discovery e applicato all'altra (cross-fitting 2 blocchi), 11:30 -> 16:00.
W06 percorso liscio (efficiency ratio 09:30-11:30) = impronta di un ordine padre eseguito a TWAP ->
    prosecuzione nel pomeriggio quando ER nel terzile alto (quantile mobile dei giorni precedenti).
W07 profilo del volume piatto (CV basso del volume normalizzato per minuto, 10:00-11:30) = algoritmo
    a tempo -> prosecuzione della direzione della mattina.
W08 barre anomale: barra RTH con volume > X volte la mediana dello stesso minuto (20 sessioni prima),
    lato = direzione della barra (blocco informato -> prosecuzione), 15 / 60 min. Esclusi 10:00 e 14:00.
W09 minuti vuoti: notte con molti minuti senza scambi (terzile alto) = mossa notturna poco
    informativa -> si va CONTRO il gap nella prima ora.
W10 entropia di permutazione (ordine 3) dei rendimenti 1m della mattina: bassa = ordine -> prosecuzione.
W11 Hurst/variance ratio VR(10) delle 5 sessioni precedenti: VR>1 regime di trend -> segui la prima
    ora (10:30 -> 16:00); VR<1 -> vai contro.
W12 ritmo dei nuovi massimi: segno(#nuovi massimi - #nuovi minimi) 09:30-11:30 -> prosecuzione.
W13 cifre dei prezzi: quota di close 1m della mattina su punto intero (.00) molto alta (terzile alto)
    = flusso «umano»/retail -> il pomeriggio va CONTRO la mattina.
W14 divergenza volume-prezzo: mattina su ma volume dei minuti in salita < volume dei minuti in
    discesa (o viceversa) -> il pomeriggio va CONTRO la mattina.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from lab import core
from lab.wild import common as C
from lab.wild import features as F

OUT = []


def ev(tid, desc, s, kin, kout, side, gross_test=False):
    s = np.asarray(s); kin = np.asarray(kin); kout = np.asarray(kout); side = np.asarray(side, float)
    ok = np.isfinite(side) & (side != 0)
    t = C.trades_from(s[ok], kin[ok], kout[ok], side[ok])
    st = C.evaluate(t, gross_test=gross_test)
    C.rec("wild_" + tid, desc, st)
    print(C.fmt(tid, st)); sys.stdout.flush()
    OUT.append(dict(test_id="wild_" + tid, **{k: st.get(k) for k in (
        "n", "mean", "lo", "hi", "p_pos", "mean_beta", "beta_adj", "years_pos", "drop20", "pass_all",
        "pass_all_bonf")}))
    return t, st


def main():
    g = C.grid()
    P, V, sess = g["P"], g["V"], g["sess"]
    S = len(sess); allS = np.arange(S)
    raw_last = P  # prezzi grezzi (RTH non attraversa i roll)

    # ---------------- W01 attraversamento dei tondi
    for L in (100, 50):
        lvl = np.floor(P / L)
        cross = np.diff(lvl, axis=1) != 0                      # cross[:, j]: fra istante j e j+1
        for h in (15, 60):
            s_l, k_l, sd_l = [], [], []
            for s in range(S):
                js = np.flatnonzero(cross[s, 30:330 - 0]) + 30  # istante j+1 in [31, 330]
                if len(js):
                    j = js[0] + 1
                    if j + h <= 390:
                        s_l.append(s); k_l.append(j); sd_l.append(np.sign(P[s, j] - P[s, j - 1]))
            ev(f"W01_round{L}_cross_first_h{h}", f"primo attraversamento RTH 10:00-15:00 di un multiplo di "
               f"{L} (prezzo grezzo), prosecuzione {h} min", s_l, k_l, np.array(k_l) + h, sd_l)

    # ---------------- W02 magnete verso il tondo
    for L in (100, 50):
        for k0 in (330, 360):
            x = P[:, k0]
            near = np.round(x / L) * L
            dist = near - x
            ok = (np.abs(dist) <= 0.0015 * x) & (np.abs(dist) >= 1.0)
            side = np.where(ok, np.sign(dist), 0)
            ev(f"W02_magnet{L}_k{k0}", f"alle {9.5 + k0 / 60:.2f}h se entro 0,15% dal multiplo di {L} "
               f"piu' vicino, vai verso il livello fino alle 16:00", allS, np.full(S, k0), np.full(S, 390), side)

    # ---------------- W03/W04 asimmetria di velocita'
    asym = F.speed_asym(P, 0, 120)
    ev("W03_speedasym_fade_close", "lato = -segno(log velocita' salita/discesa 09:30-11:30), 11:30->16:00",
       allS, np.full(S, 120), np.full(S, 390), -np.sign(asym))
    ev("W03_speedasym_fade_h60", "lato = -segno(asimmetria), 11:30->12:30",
       allS, np.full(S, 120), np.full(S, 180), -np.sign(asym))
    hi, lo = F.roll_q(asym, 2 / 3), F.roll_q(asym, 1 / 3)
    side = np.where(asym > hi, -1.0, np.where(asym < lo, 1.0, 0.0))
    ev("W03_speedasym_fade_terz_close", "solo terzili estremi (quantili mobili), contro, 11:30->16:00",
       allS, np.full(S, 120), np.full(S, 390), side)
    r = np.diff(P[:, 0:121], axis=1)
    sk = pd.DataFrame(r).skew(axis=1).to_numpy()
    ev("W04_skew_fade_close", "lato = -segno(skew rendimenti 1m 09:30-11:30), 11:30->16:00",
       allS, np.full(S, 120), np.full(S, 390), -np.sign(sk))

    # ---------------- W05 giorni-tipo (cross-fitting)
    from sklearn.cluster import KMeans
    ks = np.arange(10, 121, 10)
    rng_m = P[:, :121].max(1) - P[:, :121].min(1)
    X = (P[:, ks] - P[:, [0]]) / np.where(rng_m > 0, rng_m, np.nan)[:, None]
    fut = P[:, 390] - P[:, 120]
    half = sess.year.to_numpy() <= 2014
    for K in (4, 6, 8):
        side = np.zeros(S)
        for fit_mask in (half, ~half):
            km = KMeans(K, n_init=10, random_state=0).fit(X[fit_mask])
            lab_fit = km.labels_
            sg = np.array([np.sign(fut[fit_mask][lab_fit == c].mean()) for c in range(K)])
            lab_other = km.predict(X[~fit_mask])
            side[~fit_mask] = sg[lab_other]
        ev(f"W05_daytype_K{K}_close", f"k-means K={K} sulla forma 09:30-11:30, segno per gruppo stimato "
           f"sull'altra meta' (2010-14 / 2015-18), 11:30->16:00", allS, np.full(S, 120), np.full(S, 390), side)

    mdir = np.sign(P[:, 120] - P[:, 0])
    # ---------------- W06 efficiency ratio
    er = F.efficiency_ratio(P, 0, 120)
    erh, erl = F.roll_q(er, 2 / 3), F.roll_q(er, 1 / 3)
    ev("W06_ER_high_cont_close", "ER 09:30-11:30 nel terzile alto -> prosecuzione 11:30->16:00",
       allS, np.full(S, 120), np.full(S, 390), np.where(er > erh, mdir, 0))
    ev("W06_ER_high_cont_h60", "ER terzile alto -> prosecuzione 11:30->12:30",
       allS, np.full(S, 120), np.full(S, 180), np.where(er > erh, mdir, 0))
    ev("W06_ER_low_cont_close", "controllo: ER terzile basso -> prosecuzione 11:30->16:00",
       allS, np.full(S, 120), np.full(S, 390), np.where(er < erl, mdir, 0))

    # ---------------- W07 volume piatto
    vn = F.vol_profile_norm(V)
    seg = vn[:, 30:120]
    cv = np.nanstd(seg, 1) / np.nanmean(seg, 1)
    cvl = F.roll_q(cv, 1 / 3)
    ev("W07_flatvol_cont_close", "CV del volume normalizzato 10:00-11:30 nel terzile basso -> "
       "prosecuzione della mattina 11:30->16:00", allS, np.full(S, 120), np.full(S, 390), np.where(cv < cvl, mdir, 0))
    ev("W07_flatvol_cont_h60", "idem, 11:30->12:30", allS, np.full(S, 120), np.full(S, 180),
       np.where(cv < cvl, mdir, 0))

    # ---------------- W08 barre anomale
    excl = np.zeros(390, bool); excl[[30, 31, 270, 271]] = True
    for X_ in (5, 10):
        for h in (15, 60):
            s_l, k_l, sd_l = [], [], []
            for s in range(S):
                last = -999
                for j in np.flatnonzero(vn[s, 15:375] > X_) + 15:     # barra che inizia a j
                    if excl[j] or j + 1 - last < h:
                        continue
                    d = np.sign(P[s, j + 1] - g["P"][s, j])            # close - close precedente
                    if d == 0 or j + 1 + h > 390:
                        continue
                    s_l.append(s); k_l.append(j + 1); sd_l.append(d); last = j + 1
            ev(f"W08_bigbar{X_}x_cont_h{h}", f"barra RTH con volume > {X_}x mediana dello stesso minuto "
               f"(20 sess. prec.), prosecuzione {h} min", s_l, k_l, np.array(k_l) + h, sd_l)

    # ---------------- W09 minuti vuoti nella notte
    bars, daily = core.load("discovery")
    night = bars[(~bars["rth"]) & ((bars["ny_min"] >= 1080) | (bars["ny_min"] < 570))]
    nbar = night.groupby("session").size().reindex(sess).to_numpy()
    empt = 1 - nbar / 930.0
    gap = g["daily"]["rth_open"].to_numpy() - g["daily"]["glbx_open"].to_numpy()
    eh = F.roll_q(empt, 2 / 3); el = F.roll_q(empt, 1 / 3)
    ev("W09_thinnight_fadegap_h60", "notte con quota di minuti vuoti nel terzile alto -> contro la mossa "
       "notturna 09:30->10:30", allS, np.zeros(S), np.full(S, 60), np.where(empt > eh, -np.sign(gap), 0))
    ev("W09_thinnight_fadegap_close", "idem, 09:30->16:00", allS, np.zeros(S), np.full(S, 390),
       np.where(empt > eh, -np.sign(gap), 0))
    ev("W09_thicknight_fadegap_h60", "controllo: notte piena (terzile basso) -> contro il gap 09:30->10:30",
       allS, np.zeros(S), np.full(S, 60), np.where(empt < el, -np.sign(gap), 0))

    # ---------------- W10 entropia di permutazione
    pe = F.perm_entropy(P, 0, 120)
    pel, peh = F.roll_q(pe, 1 / 3), F.roll_q(pe, 2 / 3)
    ev("W10_lowPE_cont_close", "entropia di permutazione 09:30-11:30 terzile basso -> prosecuzione 11:30->16:00",
       allS, np.full(S, 120), np.full(S, 390), np.where(pe < pel, mdir, 0))
    ev("W10_lowPE_cont_h60", "idem 11:30->12:30", allS, np.full(S, 120), np.full(S, 180), np.where(pe < pel, mdir, 0))
    ev("W10_highPE_fade_close", "entropia alta -> contro la mattina 11:30->16:00",
       allS, np.full(S, 120), np.full(S, 390), np.where(pe > peh, -mdir, 0))

    # ---------------- W11 variance ratio delle 5 sessioni precedenti
    r1 = np.diff(P, axis=1)
    r10 = P[:, 10::10][:, :39] - P[:, 0:381:10][:, :39]
    v1 = pd.Series((r1 ** 2).sum(1)).rolling(5).sum().shift(1).to_numpy()
    v10 = pd.Series((r10 ** 2).sum(1)).rolling(5).sum().shift(1).to_numpy()
    vr = v10 / v1          # stessa finestra: sotto random walk ~1 (390 min = 39 blocchi da 10)
    fh = np.sign(P[:, 60] - P[:, 0])
    side = np.where(vr > 1, fh, np.where(vr < 1, -fh, 0))
    ev("W11_VR5d_regime_close", "VR(10) delle 5 sessioni precedenti: >1 segui la prima ora, <1 vai contro; 10:30->16:00",
       allS, np.full(S, 60), np.full(S, 390), side)
    ev("W11_VR5d_trendonly_close", "solo VR>1: segui la prima ora 10:30->16:00",
       allS, np.full(S, 60), np.full(S, 390), np.where(vr > 1, fh, 0))
    ev("W11_VR5d_revonly_close", "solo VR<1: contro la prima ora 10:30->16:00",
       allS, np.full(S, 60), np.full(S, 390), np.where(vr < 1, -fh, 0))

    # ---------------- W12 ritmo dei massimi nuovi
    nh, nl, last = F.records(P, 0, 120)
    ev("W12_records_cont_close", "segno(#nuovi massimi - #nuovi minimi 09:30-11:30) -> 11:30->16:00",
       allS, np.full(S, 120), np.full(S, 390), np.sign(nh - nl))
    ev("W12_records_cont_h60", "idem 11:30->12:30", allS, np.full(S, 120), np.full(S, 180), np.sign(nh - nl))
    fresh = last >= (120 - 5 - 15)
    ev("W12_records_fresh_close", "record nell'ultimo quarto d'ora della finestra: prosecuzione del verso "
       "dell'ultimo record 11:30->16:00", allS, np.full(S, 120), np.full(S, 390),
       np.where(fresh, np.sign(nh - nl), 0))

    # ---------------- W13 cifre dei prezzi
    frac = np.mod(P[:, 1:121], 1.0)
    whole = (np.abs(frac) < 1e-9).mean(1)
    wh = F.roll_q(whole, 2 / 3)
    ev("W13_wholeprice_fade_close", "quota di close 1m su punto intero 09:30-11:30 nel terzile alto -> "
       "contro la mattina 11:30->16:00", allS, np.full(S, 120), np.full(S, 390), np.where(whole > wh, -mdir, 0))

    # ---------------- W14 divergenza volume-prezzo
    vv = V[:, 0:120]
    up = (r1[:, 0:120] > 0); dn = (r1[:, 0:120] < 0)
    imb = (vv * up).sum(1) - (vv * dn).sum(1)
    div = np.sign(imb) != mdir
    ev("W14_voldiv_fade_close", "mattina con squilibrio di volume (minuti su - giu') di segno opposto al "
       "prezzo -> contro la mattina 11:30->16:00", allS, np.full(S, 120), np.full(S, 390),
       np.where(div & (mdir != 0) & (imb != 0), -mdir, 0))
    ev("W14_voldiv_fade_h60", "idem 11:30->12:30", allS, np.full(S, 120), np.full(S, 180),
       np.where(div & (mdir != 0) & (imb != 0), -mdir, 0))

    pd.DataFrame(OUT).to_csv(C.__file__.replace("common.py", "wild_results_1.csv"), index=False)


if __name__ == "__main__":
    main()
