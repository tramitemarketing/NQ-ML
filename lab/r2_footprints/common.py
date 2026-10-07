"""Famiglia r2_footprints (giro 2): IMPRONTE MECCANICHE di istituzioni con orologi, obblighi e algoritmi.

PIANO fissato il 2026-09-23 PRIMA di guardare qualunque risultato (riga PIANO del registro).

Domanda di fondo: esistono flussi FORZATI e prevedibili (per orario, per obbligo contrattuale, per
algoritmo) che lasciano un'impronta nei dati 1m di NQ (volume, volatilita', direzione)? E dopo il flusso
il prezzo rientra (pressione temporanea) o resta (informazione)?

BATTERIE (ognuna registrata test per test):
 F1 OROLOGI - profilo del volume e della volatilita' al minuto (log del rapporto fra il minuto e la
    mediana dei +-10 minuti vicini, esclusi +-1), per anno: 09:30, 10:00, 11:00 (fixing WM/R di Londra
    16:00), 11:30 (chiusura cash europea 17:30 CET), 14:00, 15:00 (chiusura obbligazionario), 15:45,
    15:50 (pubblicazione sbilanciamenti MOC/closing cross), 15:59 (settlement CME 15:59:30-16:00), 16:15.
    Nessun orario istituzionale e' dato per certo: si MISURA quando compare il salto, anno per anno.
 F2 ESPERIMENTO NATURALE DST: USA e Regno Unito/UE cambiano ora in date diverse (2-3 settimane a marzo,
    1 settimana a ottobre/novembre). In quelle settimane il fixing di Londra e la chiusura europea cadono
    alle 12:00 e 12:30 NY invece che alle 11:00 e 11:30. Se l'impronta si sposta con l'orologio europeo
    e' un flusso istituzionale europeo, non un'abitudine americana. (Idem per l'apertura di Tokyo, senza DST.)
 F3 PRESSIONE E RIENTRO: rendimento nella finestra del flusso (15:50-16:00, 15:59, 11:00 fix) contro
    il rendimento DOPO (16:00-16:15, sera, open di domani). Segno della correlazione = temporaneo o no.
 F4 LEVERAGED ETF (Cheng-Madhavan 2009): il ribilanciamento compra nel verso del rendimento del giorno
    (dal close di ieri 16:00) nell'ultima mezz'ora; la dimensione scala con l'AUM (cresciuto nel tempo).
    Test: coefficiente di (rendimento 15:45-16:00) su (rendimento close ieri->15:44) per anno, trend nel
    tempo; e rientro dopo le 16:00. NON e' il momentum ultima mezz'ora del giro 1 (09:30->15:30, uscita
    16:00, filtro di regime): qui il segnale e' dal close di IERI e l'ipotesi e' il trend nel tempo
    e il rientro.
 F5 FINE MESE / FINE TRIMESTRE / OPEX: stesse misure di F3 nei giorni di obbligo (ultimo giorno del
    mese, del trimestre, terzo venerdi', quadruple witching).
 F6 ALGORITMI: periodicita' del volume a :00/:15/:30/:45 (e ogni 5 minuti); uno sbilanciamento di
    flusso PERSISTENTE (Bulk Volume Classification di Easley-Lopez de Prado-O'Hara sul 1m: quota di
    volume "compratore" = Phi(dC/sigma)) per ore prevede la continuazione? (ordine grosso non finito)
 F7 TEMPO DEL VOLUME: rendimenti su barre di volume vs barre di tempo (curtosi, normalita'); il
    segnale di continuazione/rientro cambia se misurato in tempo-volume?
 F8 IRREVERSIBILITA' TEMPORALE (Zumbach): asimmetria fra la serie e la serie al contrario
    (E[r_t^2 r_{t+k}] - E[r_t r_{t+k}^2], e il "leverage" intraday) come indicatore di regime: predice
    la volatilita' o la direzione di domani oltre all'HAR?

UNITA' (dichiarate prima):
 - impronte (F1, F2, F6, F7): log-rapporti di volume/volatilita', adimensionali;
 - direzione (F3-F5, F8 direzionale): PUNTI lordi per contratto (per le regolarita') e PUNTI NETTI
   (costo 0,75) per i tradeable; diagnostica in unita' di sigma.
ESECUZIONE dei tradeable: segnale alla chiusura della barra i, ingresso all'OPEN della barra i+1, uscita
 alla CLOSE della barra finale, prezzi adj_*. Beta = lato x somma della deriva media per minuto (stesso
 metodo del controller). Sempre: anno per anno, senza i 20 migliori, beta, griglie dichiarate qui sotto.
GRIGLIE DICHIARATE: finestre di pressione {15:45, 15:50, 15:55}->16:00; rientro 16:00->{16:15, 17:00,
 09:30 domani}; soglie sui segnali in quantili causali {0.5, 0.7, 0.9} (quantile sulle 250 sessioni
 precedenti); BVC: finestra {60, 120, 180} minuti, orizzonte {30, 60} minuti.
"""
from __future__ import annotations

import datetime as dt
import pickle
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from lab import core

FAM = "r2_footprints"
COST = core.COST_RT_POINTS
HERE = Path(__file__).resolve().parent
NSM = 1380                     # minuti di sessione 18:00 -> 16:59 (sm = (ny_min - 1080) % 1440)


def sm_of(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return ((h * 60 + m) - 1080) % 1440


def build(bars: pd.DataFrame, daily: pd.DataFrame) -> dict:
    """Matrici sessione x minuto-di-sessione (18:00=0 ... 16:59=1379). Le barre 17:00-17:15 (fino al 2015)
    vengono scartate. NaN dove manca la barra; versioni 'f' con close riempita in avanti."""
    sess = pd.DatetimeIndex(daily.index)
    code = sess.get_indexer(pd.DatetimeIndex(bars["session"].to_numpy()))
    sm = ((bars["ny_min"].to_numpy().astype(int) - 1080) % 1440)
    ok = (code >= 0) & (sm < NSM)
    D = {"sess": sess}
    for col in ("adj_open", "adj_high", "adj_low", "adj_close", "close", "volume"):
        M = np.full((len(sess), NSM), np.nan)
        M[code[ok], sm[ok]] = bars[col].to_numpy()[ok]
        D[col] = M
    D["has"] = ~np.isnan(D["adj_close"])
    C = pd.DataFrame(D["adj_close"]).ffill(axis=1).to_numpy()
    O = D["adj_open"].copy()
    prevC = np.concatenate([np.full((len(sess), 1), np.nan), C[:, :-1]], axis=1)
    O = np.where(np.isnan(O), prevC, O)
    D["Cf"], D["Of"] = C, O
    D["V0"] = np.nan_to_num(D["volume"])
    D["rawCf"] = pd.DataFrame(D["close"]).ffill(axis=1).to_numpy()
    D["valid"] = daily["valid"].to_numpy().astype(bool)
    D["in_phase"] = daily["in_phase"].to_numpy().astype(bool) if "in_phase" in daily else np.ones(len(sess), bool)
    ny, lon = ZoneInfo("America/New_York"), ZoneInfo("Europe/London")
    diff, usd = [], []
    for s in sess:
        t = dt.datetime(s.year, s.month, s.day, 12, 0, tzinfo=ny)
        diff.append((t.astimezone(lon).utcoffset() - t.utcoffset()).total_seconds() / 3600)
        usd.append(t.dst().total_seconds() > 0)
    D["lon_minus_ny"] = np.array(diff)     # 5 normale, 4 nelle settimane di disallineamento
    D["us_dst"] = np.array(usd)
    return D


def get(warmup_days: int = 260):
    f = HERE / "cache" / "disc.pkl"
    if f.exists():
        return pickle.load(open(f, "rb"))
    f.parent.mkdir(exist_ok=True)
    bars, daily = core.load("discovery", warmup_days=warmup_days)
    D = build(bars, daily)
    out = (D, daily)
    pickle.dump(out, open(f, "wb"), protocol=4)
    return out


def rec(test_id: str, desc: str, values, days, **extra) -> dict:
    st = core.day_block_bootstrap(np.asarray(values, float), np.asarray(days), n_boot=4000)
    core.record(FAM, test_id, desc, "discovery", st, **extra)
    return st


def drift_per_sm(D: dict, mask: np.ndarray) -> np.ndarray:
    """Deriva media per minuto di sessione (punti): barra m contribuisce C[m]-C[m-1] (m=0: C-O)."""
    C = D["Cf"][mask]
    r = np.diff(C, axis=1, prepend=np.nan)
    r[:, 0] = C[:, 0] - D["Of"][mask][:, 0]
    return np.nanmean(r, axis=0)


def trade(D: dict, rows, i_sig, j_exit, side, drift=None) -> pd.DataFrame:
    """Segnale alla chiusura della barra i_sig -> ingresso open i_sig+1, uscita close j_exit."""
    rows, i_sig, j_exit, side = (np.asarray(x) for x in (rows, i_sig, j_exit, side))
    e = i_sig + 1
    ent = D["Of"][rows, e]
    ex = D["Cf"][rows, j_exit]
    g = side * (ex - ent)
    out = pd.DataFrame({"session": D["sess"][rows], "row": rows, "i": e, "j": j_exit, "side": side,
                        "gross_pts": g})
    if drift is not None:
        cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(drift))])
        out["beta"] = side * (cs[j_exit + 1] - cs[e])
    return out.dropna(subset=["gross_pts"])


def full_report(tid: str, desc: str, t: pd.DataFrame, net: bool = True, record: bool = True, **extra) -> dict:
    v = t["gross_pts"].to_numpy() - (COST if net else 0.0)
    st = core.day_block_bootstrap(v, t["session"].to_numpy(), n_boot=4000)
    y = core.yearly(v, t["session"])
    extra = dict(extra)
    extra["years_pos"] = f"{int((y['mean'] > 0).sum())}/{len(y)}"
    extra["drop20"] = core.drop_top(v, 20)
    extra["net"] = net
    if "beta" in t:
        vb = v - t["beta"].to_numpy()
        sb = core.day_block_bootstrap(vb, t["session"].to_numpy(), n_boot=4000)
        extra["minus_beta"] = sb["mean"]
        extra["p_minus_beta"] = sb["p_pos"]
    if record:
        core.record(FAM, tid, desc, "discovery", st, **extra)
    st.update(extra)
    st["yearly"] = y
    return st


def fmt(st: dict) -> str:
    keys = ["n", "mean", "lo", "hi", "p_two", "p_pos", "years_pos", "drop20", "minus_beta", "p_minus_beta"]
    return " ".join(f"{k}={st[k]:.4g}" if isinstance(st.get(k), float) else f"{k}={st.get(k)}" for k in keys if k in st)
