"""Famiglia r2_execution (giro 2): esecuzione aggressiva contro passiva sugli STESSI segnali.

REGOLE DI SIMULAZIONE fissate il 2026-09-23 PRIMA di guardare qualunque risultato (riga PIANO del
registro). Unita' primaria: punti NQ NETTI per SEGNALE (1 contratto); i segnali passivi non eseguiti
contano 0 e restano nel denominatore. Tutti i prezzi adj_*.

Segnale: noto alla CHIUSURA della barra 1m i (prezzo c_i). Uscita a tempo: close della barra `xi`
(fissata dal segnale, identica per le due esecuzioni: l'orologio parte dal segnale, non dal fill).

AGG (aggressiva, convenzione del progetto): ingresso all'open della barra i+1; target a limite preso
solo con trade-through di 1 tick; stop al prezzo di stop (o all'open se la barra apre oltre); stop e
target nella stessa barra -> stop. Costo fisso 0,75 punti a/r (2x commissione 0,125 + 2x 1 tick).

PAS (passiva): alla chiusura della barra i si mette un limite nel verso favorevole
  long: compra a L = c_i - off ; short: vende a L = c_i + off   (off >= 0 punti, arrotondato al tick
  verso l'esterno). Eseguito alla prima barra j in [i+1, i+N] (e j <= xi) con low_j <= L - tt*tick
  (long) / high_j >= L + tt*tick (short): TRADE-THROUGH di tt tick (1 = regola base, 2 = sensibilita').
  Prezzo di esecuzione = L anche se la barra apre oltre (nessun miglioramento). Se non eseguito entro N
  minuti: trade PERSO, P&L 0, niente commissioni (resta nel campione).
  Nella barra di esecuzione j: si controlla SOLO lo stop (se l'estremo avverso della barra lo tocca, si
  assume stop nella stessa barra); il target non puo' essere preso nella barra del fill.
  Uscite: target a limite al prezzo esatto con la stessa regola di trade-through (nessuno slippage);
  stop a mercato = prezzo di stop (o open se la barra apre oltre) PEGGIORATO di 1 tick; tempo a mercato
  = close di xi PEGGIORATO di 1 tick. Commissioni 0,25 a/r sempre sui trade eseguiti.
  Costo effettivo PAS: 0,25 (uscita a target) oppure 0,50 (uscita a stop/tempo).
Diagnostica ottimista (MAI usata per decidere): TOUCH = eseguito se low_j <= L (tt=0).

OCO a due lati (fornitura di liquidita'): due limiti simmetrici; se nella stessa barra entrambi sono
attraversati si assume il lato con il P&L finale PEGGIORE (conservativo).

Selezione avversa (misura esplicita): sugli stessi segnali, lordo AGG dei segnali eseguiti in PAS
contro lordo AGG dei segnali mancati. AS = lordoAGG(mancati) - lordoAGG(eseguiti) > 0 = vieni eseguito
quando il segnale va male.

Beta: stesso metodo del controller (lato x somma della deriva media per minuto NY sulle barre tenute).
Non sovrapposizione: causale e INDIPENDENTE dall'esecuzione (un nuovo segnale solo dopo xi del
precedente), cosi' AGG e PAS vedono esattamente lo stesso insieme di segnali.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

from lab import core
from lab.micro.common import Data  # riuso del contenitore di array (nessuna modifica)

FAMILY = "r2_execution"
TICK = core.TICK
COMM = 0.25            # commissioni a/r in punti (2 x 2,50 $ / 20)
COST_AGG = core.COST_RT_POINTS


@njit(cache=True)
def _agg(sig, side, xi, stop_d, tgt_d, o, h, l, c, tick):
    n = len(sig)
    gross = np.full(n, np.nan)
    reason = np.zeros(n, np.int8)
    for k in range(n):
        i = sig[k]; e = i + 1; s = side[k]; X = xi[k]
        if e > X:
            continue
        px = o[e]
        stop = px - s * stop_d[k] if stop_d[k] == stop_d[k] else np.nan
        tgt = px + s * tgt_d[k] if tgt_d[k] == tgt_d[k] else np.nan
        out = np.nan
        for j in range(e, X + 1):
            if stop == stop:
                if s > 0:
                    if j > e and o[j] <= stop:
                        out = o[j]; reason[k] = 2; break
                    if l[j] <= stop:
                        out = stop; reason[k] = 2; break
                else:
                    if j > e and o[j] >= stop:
                        out = o[j]; reason[k] = 2; break
                    if h[j] >= stop:
                        out = stop; reason[k] = 2; break
            if tgt == tgt:
                if s > 0 and h[j] >= tgt + tick:
                    out = tgt; reason[k] = 3; break
                if s < 0 and l[j] <= tgt - tick:
                    out = tgt; reason[k] = 3; break
        if out != out:
            out = c[X]; reason[k] = 1
        gross[k] = s * (out - px)
    return gross, reason


@njit(cache=True)
def _pas_one(s, L, fill_j, X, stop_d, tgt_d, o, h, l, c, tick, tt):
    """P&L dopo lo slippage delle uscite a mercato, prima delle commissioni; motivo; barra d'uscita."""
    stop = L - s * stop_d if stop_d == stop_d else np.nan
    tgt = L + s * tgt_d if tgt_d == tgt_d else np.nan
    for j in range(fill_j, X + 1):
        if stop == stop:
            if s > 0:
                if j > fill_j and o[j] <= stop:
                    return (o[j] - tick) - L, 2, j
                if l[j] <= stop:
                    return (stop - tick) - L, 2, j
            else:
                if j > fill_j and o[j] >= stop:
                    return L - (o[j] + tick), 2, j
                if h[j] >= stop:
                    return L - (stop + tick), 2, j
        if tgt == tgt and j > fill_j:
            if s > 0 and h[j] >= tgt + tt * tick:
                return tgt - L, 3, j
            if s < 0 and l[j] <= tgt - tt * tick:
                return L - tgt, 3, j
    if s > 0:
        return (c[X] - tick) - L, 1, X
    return L - (c[X] + tick), 1, X


@njit(cache=True)
def _limit_price(ci, s, off, tick):
    if s > 0:
        return np.floor((ci - off) / tick + 1e-9) * tick
    return np.ceil((ci + off) / tick - 1e-9) * tick


@njit(cache=True)
def _pas(sig, side, xi, off, N, stop_d, tgt_d, o, h, l, c, tick, tt, chase):
    """filled: 0 = nessun ingresso, 1 = limite eseguito, 2 = inseguito a mercato (solo se chase)."""
    n = len(sig)
    raw = np.zeros(n)
    filled = np.zeros(n, np.int8)
    fill_i = np.full(n, -1, np.int64)
    exit_i = np.full(n, -1, np.int64)
    reason = np.zeros(n, np.int8)
    for k in range(n):
        i = sig[k]; s = side[k]; X = xi[k]
        if i + 1 > X:
            continue
        L = _limit_price(c[i], s, off[k], tick)
        jmax = min(i + N[k], X)
        fj = -1
        for j in range(i + 1, jmax + 1):
            if s > 0 and l[j] <= L - tt * tick:
                fj = j; break
            if s < 0 and h[j] >= L + tt * tick:
                fj = j; break
        how = 1
        if fj < 0:
            if not chase or jmax + 1 > X:
                continue
            # LIMITE POI MERCATO: allo scadere di N si entra all'open della barra successiva + 1 tick
            fj = jmax + 1
            L = o[fj] + s * tick
            how = 2
        r, rs, ej = _pas_one(s, L, fj, X, stop_d[k], tgt_d[k], o, h, l, c, tick, tt)
        raw[k] = r; filled[k] = how; fill_i[k] = fj; exit_i[k] = ej; reason[k] = rs
    return raw, filled, fill_i, exit_i, reason


@njit(cache=True)
def _oco(sig, xi, off, N, stop_d, tgt_d, o, h, l, c, tick, tt):
    """Due limiti (buy c-off, sell c+off). Il primo attraversato vince; entrambi nella stessa barra ->
    lato con P&L peggiore."""
    n = len(sig)
    raw = np.zeros(n); filled = np.zeros(n, np.bool_); side = np.zeros(n, np.int64)
    fill_i = np.full(n, -1, np.int64); exit_i = np.full(n, -1, np.int64); reason = np.zeros(n, np.int8)
    for k in range(n):
        i = sig[k]; X = xi[k]
        if i + 1 > X:
            continue
        Lb = _limit_price(c[i], 1, off[k], tick)
        Ls = _limit_price(c[i], -1, off[k], tick)
        jmax = min(i + N[k], X)
        for j in range(i + 1, jmax + 1):
            fb = l[j] <= Lb - tt * tick
            fs = h[j] >= Ls + tt * tick
            if not (fb or fs):
                continue
            best_r = 1e18; best = 0; be = -1; brs = 0
            if fb:
                r, rs, ej = _pas_one(1, Lb, j, X, stop_d[k], tgt_d[k], o, h, l, c, tick, tt)
                best_r = r; best = 1; be = ej; brs = rs
            if fs:
                r, rs, ej = _pas_one(-1, Ls, j, X, stop_d[k], tgt_d[k], o, h, l, c, tick, tt)
                if r < best_r:
                    best_r = r; best = -1; be = ej; brs = rs
            raw[k] = best_r; filled[k] = True; side[k] = best; fill_i[k] = j; exit_i[k] = be; reason[k] = brs
            break
    return raw, filled, side, fill_i, exit_i, reason


@njit(cache=True)
def nonoverlap_sched(sig, xi):
    keep = np.zeros(len(sig), np.bool_)
    busy = -1
    for k in range(len(sig)):
        if sig[k] > busy:
            keep[k] = True
            busy = xi[k]
    return keep


# --------------------------------------------------------------------------- beta (come il controller)

class Beta:
    def __init__(self, D: Data):
        inph = D.inph
        r = np.diff(D.c, prepend=np.nan)
        r[0] = 0.0
        r = np.where(np.isfinite(r), r, 0.0)
        prof = pd.Series(r[inph]).groupby(D.m[inph]).mean()
        mu = prof.reindex(np.arange(1440)).fillna(0.0).to_numpy()[D.m]
        self.C = np.concatenate([[0.0], np.cumsum(mu)])

    def __call__(self, side, i0, i1):
        """deriva dall'open della barra i0 al close della barra i1 (inclusa)."""
        return np.asarray(side) * (self.C[np.asarray(i1) + 1] - self.C[np.asarray(i0)])


# --------------------------------------------------------------------------- confronto

def _vec(x, n, dtype=float):
    if x is None:
        return np.full(n, np.nan)
    if np.ndim(x) == 0:
        return np.full(n, x, dtype=dtype)
    return np.asarray(x, dtype).copy()


def compare(D: Data, B: Beta, sig, side, xi, off, N, stop=None, tgt=None, oco=False,
            nonoverlap=True, extra_tt=(2, 0), chase=False) -> pd.DataFrame:
    """chase=True: modo LIMITE POI MERCATO (terza esecuzione, dichiarata in b5). Con N=0 diventa
    ingresso aggressivo (open i+1 + 1 tick) con uscita a target a limite e uscite a mercato con 1 tick."""
    """Un DataFrame per segnale con AGG e PAS (tt=1) + sensibilita' tt=2 e TOUCH (diagnostica)."""
    sig = np.asarray(sig, np.int64)
    n = len(sig)
    cols = dict(xi=_vec(xi, n, np.int64), side=_vec(1 if oco else side, n, np.int64), off=_vec(off, n),
                N=_vec(N, n, np.int64), st=_vec(stop, n), tg=_vec(tgt, n))
    o_ = np.argsort(sig, kind="stable")
    sig = sig[o_]
    cols = {k: v[o_] for k, v in cols.items()}
    last = len(D.c) - 1
    ok = (cols["xi"] > sig) & (cols["xi"] <= last) & np.isfinite(cols["off"]) & (cols["off"] >= 0)
    ok &= D.scode[np.minimum(cols["xi"], last)] == D.scode[sig]
    sig = sig[ok]; cols = {k: v[ok] for k, v in cols.items()}
    if nonoverlap:
        keep = nonoverlap_sched(sig, cols["xi"])
        sig = sig[keep]; cols = {k: v[keep] for k, v in cols.items()}
    xi, off_a, N_a, st_a, tg_a = cols["xi"], cols["off"], cols["N"], cols["st"], cols["tg"]
    out = pd.DataFrame({"sig_i": sig, "xi": xi, "session": pd.DatetimeIndex(D.sess[sig]),
                        "in_phase": D.inph[sig], "min": D.m[sig]})
    res = {}
    for tt in (1,) + tuple(extra_tt):
        if oco:
            res[tt] = _oco(sig, xi, off_a, N_a, st_a, tg_a, D.o, D.h, D.l, D.c, TICK, tt)
        else:
            raw, fl, fi, ei, rs = _pas(sig, cols["side"], xi, off_a, N_a, st_a, tg_a, D.o, D.h, D.l, D.c, TICK, tt, chase)
            res[tt] = (raw, fl, cols["side"], fi, ei, rs)
    raw, fl, sd, fi, ei, rs = res[1]
    side_eff = np.where(fl > 0, sd, 1) if oco else cols["side"]
    out["side"] = side_eff
    g, r_agg = _agg(sig, side_eff.astype(np.int64), xi, st_a, tg_a, D.o, D.h, D.l, D.c, TICK)
    out["agg_gross"] = g
    out["agg_net"] = g - COST_AGG
    out["agg_reason"] = r_agg
    out["agg_beta"] = B(side_eff, sig + 1, xi)
    for tt, (raw, fl, sd, fi, ei, rs) in res.items():
        tag = {1: "", 2: "_tt2", 0: "_touch"}[tt]
        fl = np.asarray(fl).astype(np.int8)
        out["filled" + tag] = fl == 1                 # eseguito AL LIMITE (base della selezione avversa)
        out["entered" + tag] = fl > 0
        out["pas_net" + tag] = np.where(fl > 0, raw - COMM, 0.0)
        if tt == 1:
            out["fill_i"] = fi; out["exit_i"] = ei; out["reason"] = rs
            out["pas_beta"] = np.where(fl > 0, B(side_eff, np.maximum(fi, 0), np.maximum(ei, 0)), 0.0)
    return out


def summarize(t: pd.DataFrame, test_id: str, desc: str, record=True, quiet=False, n_boot=2000, **extra):
    t = t[t["in_phase"]]
    days = t["session"].to_numpy()
    if len(t) < 20:
        st = {"n": int(len(t))}
        if record:
            core.record(FAMILY, test_id, desc, "discovery", st, **extra)
        print(f"{test_id:44s} n={len(t)} (troppo pochi)")
        return st
    pn = t["pas_net"].to_numpy()
    st = core.day_block_bootstrap(pn, days, n_boot=n_boot)
    fl = t["filled"].to_numpy()
    st["fill_rate"] = float(fl.mean())
    y = core.yearly(pn, days)
    st["years_pos"] = f"{int((y['mean'] > 0).sum())}/{len(y)}"
    st["yearly"] = {int(k): round(float(v), 3) for k, v in y["mean"].items()}
    st["drop20"] = core.drop_top(pn, 20)
    st["beta"] = float(t["pas_beta"].mean())
    sb = core.day_block_bootstrap(pn - t["pas_beta"].to_numpy(), days, n_boot=n_boot)
    st["exbeta_mean"] = sb["mean"]; st["exbeta_p_pos"] = sb["p_pos"]
    a = core.day_block_bootstrap(t["agg_net"].to_numpy(), days, n_boot=n_boot)
    st["agg_net"] = a["mean"]; st["agg_lo"] = a["lo"]; st["agg_hi"] = a["hi"]; st["agg_p_pos"] = a["p_pos"]
    st["agg_gross"] = float(t["agg_gross"].mean())
    st["agg_gross_filled"] = float(t.loc[fl, "agg_gross"].mean()) if fl.any() else np.nan
    st["agg_gross_missed"] = float(t.loc[~fl, "agg_gross"].mean()) if (~fl).any() else np.nan
    st["adverse_sel"] = st["agg_gross_missed"] - st["agg_gross_filled"]
    st["pas_net_per_fill"] = float(pn[fl].mean()) if fl.any() else np.nan
    for tag in ("_tt2", "_touch"):
        if "pas_net" + tag in t:
            st["pas_net" + tag] = float(t["pas_net" + tag].mean())
            st["fill" + tag] = float(t["filled" + tag].mean())
    if "pas_net_tt2" in t:
        s2 = core.day_block_bootstrap(t["pas_net_tt2"].to_numpy(), days, n_boot=n_boot)
        st["tt2_lo"] = s2["lo"]; st["tt2_p_pos"] = s2["p_pos"]
    if record:
        core.record(FAMILY, test_id, desc, "discovery", st, **extra)
    if not quiet:
        print(f"{test_id:44s} n={st['n']:6d} fill={st['fill_rate']:.2f} PAS={st['mean']:+.3f}"
              f"[{st['lo']:+.2f};{st['hi']:+.2f}] p={st['p_pos']:.3f} y={st['years_pos']} "
              f"tt2={st.get('pas_net_tt2', np.nan):+.3f} touch={st.get('pas_net_touch', np.nan):+.3f} | "
              f"AGG={st['agg_net']:+.3f} AS={st['adverse_sel']:+.2f} (f {st['agg_gross_filled']:+.2f} "
              f"m {st['agg_gross_missed']:+.2f}) d20={st['drop20']:+.3f} xb={st['exbeta_mean']:+.3f}", flush=True)
    return st


def load(warmup_days=25):
    D = Data("discovery", warmup_days=warmup_days, seasonal_volume=False)
    return D, Beta(D)


def xi_at_minute(D: Data, sig, ny_min_exit):
    """Indice dell'ultima barra della stessa sessione con minuto NY < ny_min_exit (uscita al suo close)."""
    sig = np.asarray(sig, np.int64)
    out = np.empty(len(sig), np.int64)
    n = len(D.c)
    for k, i in enumerate(sig):
        j = i
        s = D.scode[i]
        while j + 1 < n and D.scode[j + 1] == s and D.m[j + 1] < ny_min_exit and D.m[j + 1] >= D.m[i]:
            j += 1
        out[k] = j
    return out


def xi_after(D: Data, sig, H):
    """Ultima barra che termina entro (open della barra i+1) + H minuti, stessa sessione, mai oltre le 15:59
    se il segnale e' in RTH."""
    sig = np.asarray(sig, np.int64)
    n = len(D.c)
    e = np.minimum(sig + 1, n - 1)
    tlim = D.ts[e] + np.int64(H) * 60_000_000_000
    j = np.searchsorted(D.ts, tlim - 60_000_000_000, side="right") - 1
    j = np.minimum(j, D.sess_last[sig])
    rth_sig = D.rth[sig]
    j = np.where(rth_sig & (D.rth_last[sig] >= 0), np.minimum(j, D.rth_last[sig]), j)
    return j.astype(np.int64)
