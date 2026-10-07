"""Implementazione di riferimento di range_atteso.pine, barra per barra, con gli STESSI numeri.

- Coefficienti e input di default vengono LETTI dal file .pine (niente copie a mano che possano divergere).
- f_forecast(): macchina a stati sulle barre da 30m, riga per riga come nel Pine (var, reset a
  timeframe.change("D"), aggiornamento notte/RTH, previsione alla barra delle 09:00).
- request.security(..., expr[1], lookahead_on): la barra del grafico che inizia alle 09:30 riceve il valore
  calcolato alla CHIUSURA della barra 30m delle 09:00 (vedi `chart_side`).
- Grafico: apertura RTH = open della prima barra >= 09:30 della sessione (qui barre da 1 minuto),
  bande = apertura ± k × previsto; ATR(14) = ta.rma(ta.tr(true), 14) sulle barre giornaliere, [1].

Verifiche (python pine_reference.py):
  1. previsione del riferimento == previsione di model.py (coefficienti arrotondati a 6 decimali nel Pine)
  2. audit anti look-ahead: per 60 sessioni a caso si ricalcola la previsione usando SOLO le barre fino alle
     09:29:59 di quella sessione (dati successivi tagliati) -> deve essere identica al calcolo sull'intera serie
  3. numeri fuori campione ricalcolati con il riferimento (devono coincidere con risultati_oos.json)
  4. tabella di controllo per TradingView (ultime sessioni prima del 2026-03-20)
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import features as F  # noqa: E402

PINE = HERE / "range_atteso.pine"


def pine_params(path: Path = PINE) -> dict:
    src = path.read_text(encoding="utf-8")
    p = {}
    for name in ("B0", "B_L1", "B_M5", "B_M22", "B_ON", "N_HIST", "MIN_RTH_30M", "TICK_NQ"):
        m = re.search(rf"^{name}\s*=\s*([-0-9.]+)\s*$", src, re.M)
        if not m:
            raise ValueError(f"{name} non trovato nel Pine")
        p[name] = float(m.group(1))
    for name in ("kIn", "kOut", "usdNQ", "usdMNQ"):
        m = re.search(rf"^{name}\s*=\s*input\.float\(([-0-9.]+)", src, re.M)
        p[name] = float(m.group(1))
    p["N_HIST"] = int(p["N_HIST"])
    p["MIN_RTH_30M"] = int(p["MIN_RTH_30M"])
    return p


def f_forecast(b30: pd.DataFrame, P: dict) -> pd.DataFrame:
    """b30: righe (session, ord) con colonne m, open, high, low, close, in ordine temporale.
    Restituisce una riga per barra 30m con fcPts/fcPct/ref/nh DOPO la barra (prima dell'offset [1])."""
    sess = b30.index.get_level_values(0).to_numpy()
    m_arr = b30["m"].to_numpy()
    o_, h_, l_, c_ = (b30[c].to_numpy() for c in ("open", "high", "low", "close"))
    n = len(b30)
    out_fc = np.full(n, np.nan); out_pct = np.full(n, np.nan); out_ref = np.full(n, np.nan)
    out_nh = np.zeros(n, int)
    nan = math.nan
    onH = onL = rH = rL = rO = nan
    nR = 0
    ys: list[float] = []
    fcPts = fcPct = ref = nan
    prev_s = None
    for i in range(n):
        if sess[i] != prev_s:                                   # timeframe.change("D")
            if nR >= P["MIN_RTH_30M"] and not math.isnan(rO) and rO > 0:
                ys.append(math.log(100.0 * (rH - rL) / rO))
                if len(ys) > P["N_HIST"]:
                    ys.pop(0)
            onH = onL = rH = rL = rO = nan
            nR = 0
            fcPts = fcPct = ref = nan
            prev_s = sess[i]
        m = m_arr[i]
        if m >= 1080 or m < 570:
            onH = h_[i] if math.isnan(onH) else max(onH, h_[i])
            onL = l_[i] if math.isnan(onL) else min(onL, l_[i])
        elif m < 960:
            if math.isnan(rO):
                rO = o_[i]
            rH = h_[i] if math.isnan(rH) else max(rH, h_[i])
            rL = l_[i] if math.isnan(rL) else min(rL, l_[i])
            nR += 1
        if m == 540 and len(ys) >= P["N_HIST"] and not math.isnan(onH):
            k = len(ys)
            l1 = ys[k - 1]
            m5 = sum(ys[k - 5:k]) / 5.0
            m22 = sum(ys) / k
            lon = math.log(100.0 * max(onH - onL, P["TICK_NQ"]) / c_[i])
            fcPct = math.exp(P["B0"] + P["B_L1"] * l1 + P["B_M5"] * m5 + P["B_M22"] * m22 + P["B_ON"] * lon)
            fcPts = fcPct / 100.0 * c_[i]
            ref = c_[i]
        out_fc[i], out_pct[i], out_ref[i], out_nh[i] = fcPts, fcPct, ref, len(ys)
    return pd.DataFrame({"m": m_arr, "fcPts": out_fc, "fcPct": out_pct, "ref": out_ref, "nh": out_nh},
                        index=b30.index)


def security_at_0930(fb: pd.DataFrame) -> pd.DataFrame:
    """Valore che request.security("30", expr[1], lookahead_on) consegna alla barra del grafico delle 09:30:
    expr[1] della barra 30m delle 09:30 = valore alla chiusura della barra 30m precedente (09:00)."""
    shifted = fb[["fcPts", "fcPct", "ref", "nh"]].shift(1)          # [1]
    shifted["m"] = fb["m"]
    at = shifted[shifted["m"] == 570]
    at.index = pd.DatetimeIndex(at.index.get_level_values(0))
    return at.drop(columns="m")


def daily_atr_prev(b30: pd.DataFrame) -> pd.Series:
    g = b30.groupby(level=0)
    d = pd.DataFrame({"h": g["high"].max(), "l": g["low"].min(), "c": g["close"].last()})
    d.index = pd.DatetimeIndex(d.index)
    pc = d["c"].shift(1)
    tr = np.maximum(d["h"] - d["l"], np.maximum((d["h"] - pc).abs(), (d["l"] - pc).abs())).fillna(d["h"] - d["l"])
    return pd.Series(F.rma(tr.to_numpy(), 14), index=d.index).shift(1)   # ta.atr(14)[1]


def chart_side(bars: pd.DataFrame, fb: pd.DataFrame, b30: pd.DataFrame, P: dict) -> pd.DataFrame:
    sp = F.session_prices(bars)
    rth = sp[(sp["ny_min"] >= 570) & (sp["ny_min"] < 960)]
    g = rth.groupby("session")
    day = pd.DataFrame({"dayOpen": g["p_open"].first(), "curH": g["p_high"].max(), "curL": g["p_low"].min()})
    day.index = pd.DatetimeIndex(day.index)
    sec = security_at_0930(fb)
    day = day.join(sec, how="left").rename(columns={"fcPts": "dayFc", "fcPct": "dayPct", "ref": "dayRef", "nh": "dayNh"})
    day["dayAtr"] = daily_atr_prev(b30).reindex(day.index)
    for k, nm in ((P["kIn"], "In"), (P["kOut"], "Out")):
        day[f"up{nm}"] = day["dayOpen"] + k * day["dayFc"]
        day[f"dn{nm}"] = day["dayOpen"] - k * day["dayFc"]
    day["usdNQ"] = day["dayFc"] * P["usdNQ"]
    day["usdMNQ"] = day["dayFc"] * P["usdMNQ"]
    day["rangeFinale"] = day["curH"] - day["curL"]
    return day


def main():
    P = pine_params()
    print("parametri letti dal Pine:", P)
    bars, _ = F.load_bars()
    b30 = F.bars30(bars)
    fb = f_forecast(b30, P)
    day = chart_side(bars, fb, b30, P)

    # 1. confronto con model.py (stessa tabella di feature, coefficienti a piena precisione)
    import model as M
    t = F.daily_table(bars)
    coef = json.load(open(HERE / "coefficienti.json"))
    z = (coef["b0_adj"] + coef["b_l1"] * t["l1"] + coef["b_m5"] * t["m5"] + coef["b_m22"] * t["m22"]
         + coef["b_on"] * t["lon"])
    mp = np.exp(z) / 100 * t["ref"]
    j = day.index.intersection(mp.dropna().index)
    both = day.loc[j, "dayFc"].notna()
    rel = (day.loc[j, "dayFc"] / mp[j] - 1).abs()
    print(f"\n[1] sessioni con previsione: riferimento {int(day['dayFc'].notna().sum())}, model {int(mp.notna().sum())}; "
          f"in comune {int(both.sum())}")
    print(f"    max |diff relativa| riferimento vs model: {rel[both].max():.2e} (arrotondamento a 6 decimali)")
    only_model = mp.dropna().index.difference(day.index[day['dayFc'].notna()])
    print(f"    sessioni con previsione solo in model (senza RTH, es. festivi): {len(only_model)}")
    atr_diff = (day["dayAtr"] - t["atr14_prev"].reindex(day.index)).abs().max()
    print(f"    max |ATR riferimento - ATR model|: {atr_diff:.2e}")

    # 2. audit anti look-ahead: taglio tutto cio' che segue le 09:29:59 della sessione S
    rng = np.random.default_rng(7)
    sess_all = pd.DatetimeIndex(b30.index.get_level_values(0).unique())
    cand = day.index[day["dayFc"].notna()]
    pick = rng.choice(len(cand), 60, replace=False)
    lvl0 = pd.DatetimeIndex(b30.index.get_level_values(0))
    bad = 0
    for p in pick:
        S = cand[p]
        i0 = max(0, sess_all.get_loc(S) - 60)
        start = sess_all[i0]
        sub = b30[(lvl0 >= start) & (lvl0 <= S)]
        sub = sub[~((pd.DatetimeIndex(sub.index.get_level_values(0)) == S) & (sub["m"] >= 570) & (sub["m"] < 1080))]
        # la barra 30m che inizia alle 09:30 serve solo come "portatore" di expr[1]: la ricreo con prezzi
        # FALSI (1e9) per dimostrare che il suo contenuto non entra nella previsione
        fake = pd.DataFrame({"b30": [19], "open": [1e9], "high": [1e9], "low": [1e9], "close": [1e9], "m": [570]},
                            index=pd.MultiIndex.from_tuples([(S.to_datetime64(), 999)]))
        sub = pd.concat([sub, fake])
        v = security_at_0930(f_forecast(sub, P))
        got = v["fcPts"].get(S, np.nan)
        if not np.isclose(got, day.at[S, "dayFc"], rtol=0, atol=1e-9):
            bad += 1
    print(f"\n[2] audit look-ahead: {len(pick) - bad}/{len(pick)} sessioni identiche con i dati dopo le 09:29:59 tagliati "
          f"e la barra delle 09:30 falsificata")

    # 3. numeri fuori campione dal riferimento
    test = day[(day.index >= M.TEST[0]) & (day.index <= M.TEST[1])].copy()
    test = test[t["valid"].reindex(test.index).fillna(False) & test["dayFc"].notna()]
    r, p = test["rangeFinale"].to_numpy(), test["dayFc"].to_numpy()
    mm = M.metrics(r, p)
    inside = lambda k: float(((test["curH"] < test["dayOpen"] + k * test["dayFc"])
                              & (test["curL"] > test["dayOpen"] - k * test["dayFc"])).mean())
    print(f"\n[3] test dal riferimento: n {mm['n']}  R2 punti {mm['r2_punti']:.3f}  R2 log {mm['r2_log']:.3f}  "
          f"MAE {mm['mae_punti']:.1f}  range<=1x {np.mean(r <= p):.3f}  dentro ±0.5x {inside(0.5):.3f}  "
          f"dentro ±1x {inside(1.0):.3f}  dentro ±1.5x {inside(1.5):.3f}")
    print("    (in model.py 'dentro' usa <=/>= cioe' 'non toccata'; qui < e > stretti: differenze solo per tocchi esatti)")

    # 4. tabella di controllo per TradingView
    last = day[day.index <= M.TEST[1]].tail(10)
    cols = ["dayRef", "dayFc", "dayPct", "dayOpen", "dnIn", "upIn", "dnOut", "upOut", "usdNQ", "usdMNQ", "dayAtr",
            "rangeFinale", "dayNh"]
    last[cols].round(2).to_csv(HERE / "verifica_riferimento_pine.csv", index_label="sessione")
    pd.set_option("display.width", 250)
    print("\n[4] ultime sessioni (salvate in verifica_riferimento_pine.csv):")
    print(last[cols].round(1).to_string())


if __name__ == "__main__":
    main()
