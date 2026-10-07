"""Strumenti comuni della famiglia `micro` (dinamica a scala di minuti).

Unita' dichiarata PRIMA di guardare qualunque risultato (2026-09-23):
  primaria  = punti NQ NETTI per operazione da 1 contratto (lordo - 0,75), CI a blocchi per giorno;
  secondaria = stessa quantita' sul solo 2016-2018 (rapporto costi/volatilita' piu' vicino a oggi).

Esecuzione (identica per tutti i test):
  - il segnale e' noto alla CHIUSURA della barra i; si entra all'OPEN della barra i+1 (stessa sessione);
  - uscita a tempo: close dell'ultima barra che termina entro entry_ts + H minuti (mai oltre il
    limite di sessione/fascia `end_idx` passato dal chiamante);
  - target preso solo con trade-through di 1 tick (long: high >= T + 0,25);
  - stop: al prezzo di stop, ma se la barra APRE gia' oltre lo stop si esce all'open (piu' conservativo);
  - stop e target toccati nella stessa barra 1m -> conta lo stop (il peggiore);
  - tutti i prezzi sono adj_* (continui ai roll).
Non sovrapposizione: `nonoverlap` tiene un solo trade aperto alla volta (scelta causale: dipende solo
dall'uscita dei trade precedenti).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

from lab import core

FAMILY = "micro"
TICK = core.TICK
COST = core.COST_RT_POINTS


# --------------------------------------------------------------------------- dati

class Data:
    """Array numpy delle barre + qualche feature causale."""

    def __init__(self, phase: str = "discovery", warmup_days: int = 25, bars=None, daily=None,
                 seasonal_volume: bool = True):
        if bars is None:
            bars, daily = core.load(phase, warmup_days=warmup_days)
        self.bars, self.daily = bars, daily
        self.ts = bars.index.asi8.copy()                      # ns UTC
        self.o = bars["adj_open"].to_numpy()
        self.h = bars["adj_high"].to_numpy()
        self.l = bars["adj_low"].to_numpy()
        self.c = bars["adj_close"].to_numpy()
        self.ro = bars["open"].to_numpy()
        self.rh = bars["high"].to_numpy()
        self.rl = bars["low"].to_numpy()
        self.rc = bars["close"].to_numpy()
        self.v = bars["volume"].to_numpy().astype(float)
        self.sess = bars["session"].to_numpy().astype("datetime64[D]")
        self.scode = pd.factorize(self.sess)[0].astype(np.int64)
        self.m = bars["ny_min"].to_numpy().astype(np.int64)
        self.rth = bars["rth"].to_numpy()
        self.inph = bars["in_phase"].to_numpy()
        self.year = pd.DatetimeIndex(self.sess).year.to_numpy()
        n = len(self.c)
        # ultimo indice della sessione per ogni barra
        last = np.r_[np.nonzero(np.diff(self.scode))[0], n - 1]
        self.sess_last = last[self.scode]
        first = np.r_[0, np.nonzero(np.diff(self.scode))[0] + 1]
        self.sess_first = first[self.scode]
        # ultimo indice RTH (barra 15:59) della sessione, -1 se assente
        rth_last = pd.Series(np.arange(n))[self.rth].groupby(self.scode[self.rth]).max()
        rl = np.full(self.scode.max() + 1, -1, np.int64)
        rl[rth_last.index.to_numpy()] = rth_last.to_numpy()
        self.rth_last = rl[self.scode]
        # rendimento 1m close-to-close (nan al primo della sessione)
        r = np.diff(self.c, prepend=np.nan)
        r[self.sess_first == np.arange(n)] = np.nan
        self.r1 = r
        # volatilita' recente: std delle ultime 60 variazioni 1m, NOTA fino alla barra i-1
        self.sig60 = pd.Series(r).rolling(60, min_periods=30).std().shift(1).to_numpy()
        # range medio delle ultime 60 barre (fino a i-1)
        self.rng = self.h - self.l
        self.rng60 = pd.Series(self.rng).rolling(60, min_periods=30).mean().shift(1).to_numpy()
        self.vol60 = pd.Series(self.v).rolling(60, min_periods=30).mean().shift(1).to_numpy()
        if not seasonal_volume:
            self.vseas = np.full(n, np.nan)
            return
        # volume stagionale: mediana del volume allo stesso minuto NY nelle 20 sessioni PRECEDENTI
        piv = pd.DataFrame({"s": self.scode, "m": self.m, "v": self.v}).pivot_table(
            index="s", columns="m", values="v", aggfunc="first")
        med = piv.rolling(20, min_periods=10).median().shift(1)
        self.vseas = med.to_numpy()[self.scode, np.searchsorted(med.columns.to_numpy(), self.m)]
        self.vol60 = pd.Series(self.v).rolling(60, min_periods=30).mean().shift(1).to_numpy()

    def sessions_in_phase(self):
        return self.daily.index[self.daily["in_phase"]]


# --------------------------------------------------------------------------- simulatore

@njit(cache=True)
def _sim(sig, side, H, stop_d, tgt_d, end_idx, ts, o, h, l, c, scode, tick):
    n = len(sig)
    entry_i = np.full(n, -1, np.int64)
    exit_i = np.full(n, -1, np.int64)
    gross = np.full(n, np.nan)
    reason = np.zeros(n, np.int8)       # 1 tempo, 2 stop, 3 target
    one_min = 60_000_000_000
    N = len(c)
    for k in range(n):
        i = sig[k]
        e = i + 1
        if e >= N or scode[e] != scode[i] or e > end_idx[k]:
            continue
        s = side[k]
        px = o[e]
        tlim = ts[e] + H[k] * one_min
        stop = px - s * stop_d[k] if stop_d[k] == stop_d[k] else np.nan
        tgt = px + s * tgt_d[k] if tgt_d[k] == tgt_d[k] else np.nan
        j = e
        out = np.nan
        last_j = e
        while j <= end_idx[k] and j < N and scode[j] == scode[i] and ts[j] + one_min <= tlim:
            last_j = j
            if stop == stop:
                if s > 0:
                    if o[j] <= stop and j > e:
                        out = o[j]; reason[k] = 2; break
                    if l[j] <= stop:
                        out = stop; reason[k] = 2; break
                else:
                    if o[j] >= stop and j > e:
                        out = o[j]; reason[k] = 2; break
                    if h[j] >= stop:
                        out = stop; reason[k] = 2; break
            if tgt == tgt:
                if s > 0 and h[j] >= tgt + tick:
                    out = tgt; reason[k] = 3; break
                if s < 0 and l[j] <= tgt - tick:
                    out = tgt; reason[k] = 3; break
            j += 1
        if out != out:
            out = c[last_j]; reason[k] = 1; j = last_j
        entry_i[k] = e
        exit_i[k] = j
        gross[k] = s * (out - px)
    return entry_i, exit_i, gross, reason


@njit(cache=True)
def _nonoverlap(entry_i, exit_i):
    keep = np.zeros(len(entry_i), np.bool_)
    busy = -1
    for k in range(len(entry_i)):
        if entry_i[k] < 0:
            continue
        if entry_i[k] > busy:
            keep[k] = True
            busy = exit_i[k]
    return keep


def simulate(D: Data, sig, side, H, stop=None, tgt=None, end="session", nonoverlap=True) -> pd.DataFrame:
    """sig: indici di barra (segnale alla chiusura). side: +1/-1 (scalare o array). H: minuti.
    stop/tgt: distanze in punti (scalare/array/None). end: 'session' | 'rth' (uscita entro le 15:59)."""
    sig = np.asarray(sig, np.int64)
    order = np.argsort(sig, kind="stable")
    sig = sig[order]
    n = len(sig)

    def arr(x, dtype=float):
        if x is None:
            return np.full(n, np.nan)
        a = np.broadcast_to(np.asarray(x, dtype), (n,)) if np.ndim(x) == 0 else np.asarray(x, dtype)[order]
        return np.ascontiguousarray(a, dtype=dtype)

    side_a = arr(side, np.int64) if np.ndim(side) else np.full(n, int(side), np.int64)
    H_a = arr(H, np.int64) if np.ndim(H) else np.full(n, int(H), np.int64)
    end_idx = D.sess_last[sig] if end == "session" else D.rth_last[sig]
    end_idx = np.ascontiguousarray(end_idx, np.int64)
    ei, xi, g, rsn = _sim(sig, side_a, H_a, arr(stop), arr(tgt), end_idx, D.ts, D.o, D.h, D.l, D.c,
                          D.scode, TICK)
    ok = ei >= 0
    if nonoverlap:
        keep = _nonoverlap(np.where(ok, ei, -1), xi)
    else:
        keep = ok
    k = keep
    return pd.DataFrame({
        "sig_i": sig[k], "entry_i": ei[k], "exit_i": xi[k],
        "session": pd.DatetimeIndex(D.sess[ei[k]]),
        "entry_ts": pd.to_datetime(D.ts[ei[k]], utc=True),
        "exit_ts": pd.to_datetime(D.ts[xi[k]], utc=True),
        "side": side_a[k], "gross_pts": g[k], "reason": rsn[k], "H": H_a[k],
        "entry_min": D.m[ei[k]], "in_phase": D.inph[ei[k]],
    })


# --------------------------------------------------------------------------- beta / deriva

_DRIFT_CACHE: dict = {}


def drift_table(D: Data, H: int, end="session") -> np.ndarray:
    """Media (su tutte le barre in fase) del rendimento long a H minuti, per minuto NY d'ingresso:
    la deriva passiva della stessa finestra oraria. Indicizzata per minuto 0..1439."""
    key = (id(D), H, end)
    if key in _DRIFT_CACHE:
        return _DRIFT_CACHE[key]
    idx = np.nonzero(D.inph)[0]
    idx = idx[idx < len(D.c) - 1]
    t = simulate(D, idx, 1, H, end=end, nonoverlap=False)
    tab = t.groupby("entry_min")["gross_pts"].mean().reindex(range(1440)).fillna(0.0).to_numpy()
    _DRIFT_CACHE[key] = tab
    return tab


# --------------------------------------------------------------------------- valutazione

def evaluate(D: Data, t: pd.DataFrame, test_id: str, desc: str, record=True, beta=True, n_boot=4000,
             end="session", quiet=False) -> dict:
    t = t[t["in_phase"]].copy()
    if len(t) == 0:
        st = {"n": 0}
        if record:
            core.record(FAMILY, test_id, desc, "discovery", st)
        return st
    t["net"] = t["gross_pts"] - COST
    days = t["session"].to_numpy()
    st = core.day_block_bootstrap(t["net"].to_numpy(), days, n_boot=n_boot)
    st["mean_gross"] = float(t["gross_pts"].mean())
    y = core.yearly(t["net"].to_numpy(), days)
    st["years_pos"] = f"{int((y['mean'] > 0).sum())}/{len(y)}"
    st["yearly"] = {int(k): round(float(v), 3) for k, v in y["mean"].items()}
    rec = t[t["session"].dt.year >= 2016]
    if len(rec):
        s2 = core.day_block_bootstrap(rec["net"].to_numpy(), rec["session"].to_numpy(), n_boot=n_boot)
        st["n_1618"] = s2["n"]; st["mean_1618"] = s2["mean"]; st["lo_1618"] = s2["lo"]; st["p_pos_1618"] = s2["p_pos"]
    st["drop20"] = core.drop_top(t["net"].to_numpy(), 20)
    st["long_share"] = float((t["side"] > 0).mean())
    if beta:
        bsum = np.zeros(len(t))
        for H in np.unique(t["H"]):
            tab = drift_table(D, int(H), end)
            mk = (t["H"] == H).to_numpy()
            bsum[mk] = t["side"].to_numpy()[mk] * tab[t["entry_min"].to_numpy()[mk]]
        st["beta_pts"] = float(bsum.mean())
        st["mean_net_exbeta"] = float(st["mean"] - bsum.mean())
    if record:
        core.record(FAMILY, test_id, desc, "discovery", st)
    if not quiet:
        print(f"{test_id:38s} n={st['n']:6d} gross={st['mean_gross']:+.3f} net={st['mean']:+.3f} "
              f"[{st['lo']:+.3f};{st['hi']:+.3f}] p={st['p_pos']:.3f} yrs={st['years_pos']} "
              f"1618={st.get('mean_1618', np.nan):+.3f}(p{st.get('p_pos_1618', np.nan):.3f}) "
              f"d20={st['drop20']:+.3f} beta={st.get('beta_pts', 0):+.3f}")
    return st


def fwd_regularity(D: Data, sig, side, H, test_id, desc, record=True, end="session"):
    """Rendimento lordo firmato a H minuti (senza costi) — per il binario 'regolarita''."""
    t = simulate(D, sig, side, H, end=end, nonoverlap=False)
    t = t[t["in_phase"]]
    st = core.day_block_bootstrap(t["gross_pts"].to_numpy(), t["session"].to_numpy(), n_boot=4000)
    y = core.yearly(t["gross_pts"].to_numpy(), t["session"].to_numpy())
    st["years_pos"] = f"{int((y['mean'] > 0).sum())}/{len(y)}"
    st["kind"] = "gross_regularity"
    if record:
        core.record(FAMILY, test_id, desc, "discovery", st)
    print(f"{test_id:38s} n={st['n']:6d} GROSS={st['mean']:+.3f} [{st['lo']:+.3f};{st['hi']:+.3f}] "
          f"p2={st['p_two']:.3f} yrs+={st['years_pos']}")
    return st


def evaluate_pair(D: Data, sig, fade_side, H, test_id, desc, stop=None, tgt=None, end="session",
                  nonoverlap=True, record=True, quiet=False) -> dict:
    """Valuta la stessa popolazione in due versi (fade = lato dato, cont = opposto) e registra UNA riga
    con entrambi: e' un solo test guardato con due letture speculari."""
    sa = evaluate(D, simulate(D, sig, fade_side, H, stop, tgt, end, nonoverlap), test_id + "|fade",
                  desc + " [fade]", record=False, quiet=True, end=end)
    sb = evaluate(D, simulate(D, sig, -np.asarray(fade_side), H, stop, tgt, end, nonoverlap),
                  test_id + "|cont", desc + " [cont]", record=False, quiet=True, end=end)
    row = {f"fade_{k}": v for k, v in sa.items()}
    row.update({f"cont_{k}": v for k, v in sb.items()})
    row["n"] = sa.get("n", 0)
    if record:
        core.record(FAMILY, test_id, desc + " (fade e continuazione)", "discovery", row)
    if not quiet and sa.get("n", 0):
        for tag, s in (("F", sa), ("C", sb)):
            print(f"{test_id:34s}{tag} n={s['n']:6d} g={s['mean_gross']:+.3f} net={s['mean']:+.3f} "
                  f"[{s['lo']:+.3f};{s['hi']:+.3f}] p={s['p_pos']:.3f} y={s['years_pos']} "
                  f"1618={s.get('mean_1618', np.nan):+.3f}(p{s.get('p_pos_1618', np.nan):.3f}) "
                  f"d20={s['drop20']:+.3f} b={s.get('beta_pts', 0):+.3f}")
    return {"fade": sa, "cont": sb}
