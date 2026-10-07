"""Strumenti comuni della famiglia calendar.

Unita' dichiarata PRIMA di guardare qualunque risultato (2026-09-23):
  - primaria: PUNTI NQ per 1 contratto (quella su cui il controller giudica), netto = lordo - 0,75;
  - secondaria (robustezza, perche' i punti pesano di piu' gli anni recenti): rendimento in
    basis point del prezzo d'ingresso.

Calendari usati (tutti noti in anticipo, nessuno ricavato dall'esito):
  - festivita' di borsa USA per regola (NYSE), calcolabili per qualunque anno;
  - date FOMC programmate: inserite a mano dal calendario pubblico della Federal Reserve
    (federalreserve.gov/monetarypolicy/fomccalendars.htm), verificate contro il picco di volume;
  - NFP: regola BLS (terzo venerdi' dopo la settimana di riferimento che contiene il 12),
    verificata contro il picco di volume delle 8:30.

Minuto di sessione: sm = (ny_min - 1080) mod 1440, quindi 18:00 NY = 0, 09:30 = 930,
16:00 = 1320, 17:00 = 1380. Il "prezzo al tempo t" e' l'adj_open della barra che inizia a t;
se la barra manca, l'ultimo adj_close precedente (nella stessa sessione).
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
from dateutil.easter import easter

from lab import core

FAMILY = "calendar"
COST = core.COST_RT_POINTS


def hm(h: int, m: int = 0) -> int:
    """Minuto di sessione (18:00 NY = 0) di un orario NY."""
    return (h * 60 + m - 1080) % 1440


RTH_OPEN, RTH_CLOSE = hm(9, 30), hm(16, 0)


# --------------------------------------------------------------------------- calendari

def _nth_weekday(y, m, wd, n):
    d = dt.date(y, m, 1)
    while d.weekday() != wd:
        d += dt.timedelta(days=1)
    return d + dt.timedelta(weeks=n - 1)


def _last_weekday(y, m, wd):
    d = dt.date(y, m + 1, 1) - dt.timedelta(days=1) if m < 12 else dt.date(y, 12, 31)
    while d.weekday() != wd:
        d -= dt.timedelta(days=1)
    return d


def _observed(d):
    if d.weekday() == 5:
        return d - dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def exchange_holidays(y0: int = 2009, y1: int = 2027) -> set:
    """Festivita' NYSE per regola (le chiusure straordinarie non annunciate in anticipo, es. Sandy
    2012 o funerali di Stato, NON sono incluse: non erano note prima)."""
    out = set()
    for y in range(y0, y1 + 1):
        nyd = _observed(dt.date(y, 1, 1))
        if nyd.year == y:          # se il 1 gennaio cade di sabato NYSE non chiude il 31/12
            out.add(nyd)
        out.add(_nth_weekday(y, 1, 0, 3))      # MLK
        out.add(_nth_weekday(y, 2, 0, 3))      # Presidents
        out.add(easter(y) - dt.timedelta(days=2))  # Good Friday
        out.add(_last_weekday(y, 5, 0))        # Memorial
        if y >= 2022:
            out.add(_observed(dt.date(y, 6, 19)))  # Juneteenth
        out.add(_observed(dt.date(y, 7, 4)))
        out.add(_nth_weekday(y, 9, 0, 1))      # Labor
        out.add(_nth_weekday(y, 11, 3, 4))     # Thanksgiving
        out.add(_observed(dt.date(y, 12, 25)))
    return out


def trading_calendar(y0: int = 2009, y1: int = 2027) -> pd.DatetimeIndex:
    """Giorni di borsa previsti (feriali meno festivita' per regola)."""
    hol = exchange_holidays(y0, y1)
    days = pd.bdate_range(f"{y0}-01-01", f"{y1}-12-31")
    return pd.DatetimeIndex([d for d in days if d.date() not in hol])


# Date FOMC programmate (giorno del comunicato), dal calendario pubblico della Fed.
# Ora del comunicato: 14:15 fino al 2012 (12:30 nei giorni con conferenza stampa, apr-2011..dic-2012),
# 14:00 da marzo 2013 (verificato sul volume: il 30/1/2013 il picco e' ancora alle 14:15).
FOMC = {
    2010: ["01-27", "03-16", "04-28", "06-23", "08-10", "09-21", "11-03", "12-14"],
    2011: ["01-26", "03-15", "04-27", "06-22", "08-09", "09-21", "11-02", "12-13"],
    2012: ["01-25", "03-13", "04-25", "06-20", "08-01", "09-13", "10-24", "12-12"],
    2013: ["01-30", "03-20", "05-01", "06-19", "07-31", "09-18", "10-30", "12-18"],
    2014: ["01-29", "03-19", "04-30", "06-18", "07-30", "09-17", "10-29", "12-17"],
    2015: ["01-28", "03-18", "04-29", "06-17", "07-29", "09-17", "10-28", "12-16"],
    2016: ["01-27", "03-16", "04-27", "06-15", "07-27", "09-21", "11-02", "12-14"],
    2017: ["02-01", "03-15", "05-03", "06-14", "07-26", "09-20", "11-01", "12-13"],
    2018: ["01-31", "03-21", "05-02", "06-13", "08-01", "09-26", "11-08", "12-19"],
    2019: ["01-30", "03-20", "05-01", "06-19", "07-31", "09-18", "10-30", "12-11"],
    2020: ["01-29", "03-03", "03-15", "04-29", "06-10", "07-29", "09-16", "11-05", "12-16"],
    2021: ["01-27", "03-17", "04-28", "06-16", "07-28", "09-22", "11-03", "12-15"],
    2022: ["01-26", "03-16", "05-04", "06-15", "07-27", "09-21", "11-02", "12-14"],
    2023: ["02-01", "03-22", "05-03", "06-14", "07-26", "09-20", "11-01", "12-13"],
    2024: ["01-31", "03-20", "05-01", "06-12", "07-31", "09-18", "11-07", "12-18"],
    2025: ["01-29", "03-19", "05-07", "06-18", "07-30", "09-17", "10-29", "12-10"],
    2026: ["01-28", "03-18"],
}
# NB 2020-03-03 e 2020-03-15 sono tagli d'emergenza NON programmati (il 15/3 e' domenica): esclusi
# da fomc_dates(scheduled_only=True).
_UNSCHEDULED = {"2020-03-03", "2020-03-15"}
_PRESS_1230 = {"2011-04-27", "2011-06-22", "2011-11-02", "2012-01-25", "2012-04-25", "2012-06-20",
               "2012-09-13", "2012-12-12"}


def fomc_dates(scheduled_only: bool = True) -> pd.DatetimeIndex:
    out = []
    for y, ds in FOMC.items():
        for s in ds:
            k = f"{y}-{s}"
            if scheduled_only and k in _UNSCHEDULED:
                continue
            out.append(pd.Timestamp(k))
    return pd.DatetimeIndex(out)


def fomc_time_ny(d: pd.Timestamp) -> tuple[int, int]:
    k = d.strftime("%Y-%m-%d")
    if k in _PRESS_1230:
        return (12, 30)
    return (14, 15) if d < pd.Timestamp("2013-03-01") else (14, 0)


def nfp_dates(y0: int = 2009, y1: int = 2026) -> pd.DatetimeIndex:
    """Regola BLS standard: il rapporto esce il terzo venerdi' dopo la fine della settimana di
    riferimento (dom-sab che contiene il 12), con le correzioni sotto; verificata sul volume delle 8:30
    nel discovery (tutte le date hanno il picco tranne poche giornate a volume basso). Lo shutdown
    2025 (validation/confirmation) NON e' modellato: dichiarato."""
    out = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            d12 = dt.date(y, m, 12)
            sat = d12 + dt.timedelta(days=(5 - d12.weekday()) % 7)  # sabato che chiude la settimana
            fri = sat + dt.timedelta(days=6 + 14)                     # terzo venerdi' successivo
            out.append(pd.Timestamp(fri))
    idx = pd.DatetimeIndex(out)
    hol = exchange_holidays(y0, y1)
    # regola BLS: se la data cade in un festivo si anticipa al giorno lavorativo precedente;
    # se cade entro il 2 gennaio (o il 3 quando il 12 dic. e' presto) il BLS la sposta di una settimana.
    fixed = []
    for d in idx:
        if d.month == 1 and d.day <= 3:
            d = d + pd.Timedelta(days=7)
        gf = pd.Timestamp(easter(d.year)) - pd.Timedelta(days=2)
        while d.date() in hol and d != gf:      # il Venerdi' Santo il BLS pubblica comunque
            d = d - pd.Timedelta(days=1)
        fixed.append(d)
    idx = pd.DatetimeIndex(fixed)
    # eccezione nota (shutdown 2013): rapporto di settembre uscito martedi' 22/10/2013
    idx = idx.map(lambda d: pd.Timestamp("2013-10-22") if d == pd.Timestamp("2013-10-04") else d)
    return pd.DatetimeIndex(idx)


# --------------------------------------------------------------------------- prezzi

class Px:
    """Matrici sessione x minuto-di-sessione dei prezzi adj (open e close), per estrarre rendimenti
    fra due istanti qualunque senza ricalcoli."""

    def __init__(self, bars: pd.DataFrame, daily: pd.DataFrame):
        self.daily = daily
        self.sessions = daily.index
        sidx = pd.Index(self.sessions).get_indexer(pd.DatetimeIndex(bars["session"]))
        sm = ((bars["ny_min"].to_numpy().astype(int) - 1080) % 1440)
        ns = len(self.sessions)
        self.O = np.full((ns, 1440), np.nan)
        self.C = np.full((ns, 1440), np.nan)
        self.V = np.zeros((ns, 1440))
        ok = sidx >= 0
        self.O[sidx[ok], sm[ok]] = bars["adj_open"].to_numpy()[ok]
        self.C[sidx[ok], sm[ok]] = bars["adj_close"].to_numpy()[ok]
        self.V[sidx[ok], sm[ok]] = bars["volume"].to_numpy()[ok]
        self.RAW = np.full((ns, 1440), np.nan)
        self.RAW[sidx[ok], sm[ok]] = bars["open"].to_numpy()[ok]
        # close ffill dentro la sessione
        Cf = pd.DataFrame(self.C).ffill(axis=1).to_numpy()
        self.Cf = Cf
        # ts UTC di ogni barra (per entry/exit_ts)
        self.TS = np.full((ns, 1440), np.datetime64("NaT"), dtype="datetime64[ns]")
        self.TS[sidx[ok], sm[ok]] = bars.index.tz_convert("UTC").tz_localize(None).to_numpy()[ok]

    def price(self, t: int) -> np.ndarray:
        """Prezzo al minuto di sessione t per ogni sessione: open della barra t, altrimenti l'ultimo
        close prima di t nella stessa sessione (NaN se nessuna barra prima)."""
        p = self.O[:, t].copy()
        if t > 0:
            miss = np.isnan(p)
            p[miss] = self.Cf[miss, t - 1]
        return p

    def ts(self, t: int) -> np.ndarray:
        """Timestamp UTC della barra >= t nella sessione (prima barra disponibile da t in poi)."""
        out = np.full(len(self.sessions), np.datetime64("NaT"), dtype="datetime64[ns]")
        for k in range(t, min(t + 30, 1440)):
            m = np.isnat(out) & ~np.isnat(self.TS[:, k])
            out[m] = self.TS[m, k]
        return out

    def ret(self, t0: int, t1: int, lag_days: int = 0) -> pd.Series:
        """Punti da (sessione s - lag_days, t0) a (sessione s, t1)."""
        p1 = self.price(t1)
        p0 = self.price(t0)
        if lag_days:
            p0 = np.concatenate([np.full(lag_days, np.nan), p0[:-lag_days]])
        return pd.Series(p1 - p0, index=self.sessions), pd.Series(p0, index=self.sessions)


def stats(values, days, **extra) -> dict:
    s = core.day_block_bootstrap(np.asarray(values), np.asarray(days))
    s.update(extra)
    return s


def full_check(gross: pd.Series, side: pd.Series | float = 1.0, base_gross: pd.Series | None = None,
               entry_px: pd.Series | None = None) -> dict:
    """Controlli standard su una serie di trade indicizzata per sessione.
    gross = punti lordi del trade (gia' con il segno del lato). base_gross = rendimento long della
    STESSA finestra oraria su tutti i giorni validi (per il beta)."""
    g = gross.dropna()
    net = g - COST
    days = g.index.to_numpy()
    out = stats(net.to_numpy(), days)
    out["mean_gross"] = float(g.mean())
    yr = core.yearly(net.to_numpy(), days)
    out["years_pos"] = f"{int((yr['mean'] > 0).sum())}/{len(yr)}"
    out["yearly"] = {int(k): round(float(v), 3) for k, v in yr["mean"].items()}
    out["drop20"] = core.drop_top(net.to_numpy(), 20)
    if base_gross is not None:
        sd = side if np.isscalar(side) else side.reindex(g.index)
        exp = float(np.mean(sd)) if not np.isscalar(sd) else float(sd)
        beta = exp * float(base_gross.dropna().mean())
        out["beta_pts"] = beta
        out["net_minus_beta"] = out["mean"] - beta
        # eccesso sul giorno qualunque, con CI: evento - media della stessa finestra
        ex = g - (sd if np.isscalar(sd) else sd.to_numpy()) * float(base_gross.dropna().mean())
        eb = core.day_block_bootstrap(ex.to_numpy(), days)
        out["excess_gross"] = eb["mean"]
        out["excess_lo"], out["excess_hi"], out["excess_p_pos"] = eb["lo"], eb["hi"], eb["p_pos"]
    if entry_px is not None:
        bp = (g / entry_px.reindex(g.index) * 1e4).dropna()
        b = core.day_block_bootstrap(bp.to_numpy(), bp.index.to_numpy())
        out["bp_mean"], out["bp_lo"], out["bp_hi"] = b["mean"], b["lo"], b["hi"]
    return out


def rec(test_id: str, desc: str, st: dict, **extra):
    core.record(FAMILY, test_id, desc, "discovery", st, **extra)


def fmt(tid, st):
    keys = ["n", "mean", "lo", "hi", "p_pos", "years_pos", "drop20", "beta_pts", "net_minus_beta",
            "excess_gross", "excess_lo", "excess_hi", "bp_mean", "bp_lo", "bp_hi"]
    parts = []
    for k in keys:
        if k in st:
            v = st[k]
            parts.append(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}")
    return f"{tid}: " + " ".join(parts)
