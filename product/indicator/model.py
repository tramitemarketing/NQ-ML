"""Stima (coefficienti FISSI) e valutazione fuori campione dell'indicatore «Range Atteso».

  stima       2010-06-07 -> 2023-09-30   (discovery + validation del laboratorio)
  test        2023-10-01 -> 2026-03-19   (confirmation; la cassaforte >= 2026-03-20 resta chiusa)

Modello principale (log-HAR sul range + notte), stimato UNA volta con OLS:
  y_S = b0 + b1*l1 + b2*m5 + b3*m22 + b4*lon + e
  range previsto (punti) = exp(b0' + b1*l1 + b2*m5 + b3*m22 + b4*lon) / 100 * ref
  b0' = b0 + ln(media exp(residui in stima))       [correzione di smearing di Duan: livello, non mediana]

Uso:  .venv/Scripts/python.exe product/indicator/model.py
Scrive coefficienti.json, risultati_oos.json, verifica_tradingview.csv nella cartella dell'indicatore.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import features as F  # noqa: E402

from lab import core, extdata  # noqa: E402

TRAIN = (pd.Timestamp("2010-06-07"), pd.Timestamp("2023-09-30"))
TEST = (pd.Timestamp("2023-10-01"), pd.Timestamp("2026-03-19"))
BASE = ["l1", "m5", "m22", "lon"]
MULTS = (0.5, 1.0, 1.5)
KS = (0.5, 0.75, 1.0, 1.5)


def ols(X: np.ndarray, y: np.ndarray):
    A = np.column_stack([np.ones(len(X)), X])
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ b
    n, k = A.shape
    s2 = res @ res / (n - k)
    # errori standard HAC (Newey-West, 10 lag): i residui del range sono un po' autocorrelati
    L = 10
    Xe = A * res[:, None]
    S = Xe.T @ Xe
    for l in range(1, L + 1):
        w = 1 - l / (L + 1)
        G = Xe[l:].T @ Xe[:-l]
        S += w * (G + G.T)
    Ainv = np.linalg.inv(A.T @ A)
    se = np.sqrt(np.diag(Ainv @ S @ Ainv))
    r2 = 1 - res @ res / ((y - y.mean()) @ (y - y.mean()))
    return b, se, res, r2, np.sqrt(s2)


def fit(t: pd.DataFrame, cols: list[str]) -> dict:
    d = t[(t.index >= TRAIN[0]) & (t.index <= TRAIN[1]) & t["valid"]].dropna(subset=cols + ["y"])
    b, se, res, r2, s = ols(d[cols].to_numpy(), d["y"].to_numpy())
    smear = float(np.mean(np.exp(res)))
    return {"cols": cols, "b": b.tolist(), "se_hac": se.tolist(), "b0_adj": float(b[0] + np.log(smear)),
            "smear": smear, "r2_log_in": float(r2), "resid_sd": float(s), "n": int(len(d)),
            "first": str(d.index[0].date()), "last": str(d.index[-1].date())}


def predict(t: pd.DataFrame, m: dict) -> pd.Series:
    b = np.asarray(m["b"])
    z = m["b0_adj"] + t[m["cols"]].to_numpy() @ b[1:]
    return pd.Series(np.exp(z) / 100 * t["ref"].to_numpy(), index=t.index)


def rolling_pred(t: pd.DataFrame, cols: list[str], win: int = 500, minp: int = 150) -> pd.Series:
    """Confronto: stessa specifica ma ristimata ogni giorno sulle 500 sessioni valide precedenti (come nel lab)."""
    v = t[t["valid"]].dropna(subset=cols + ["y", "ref"])
    X = np.column_stack([np.ones(len(v)), v[cols].to_numpy()])
    y = v["y"].to_numpy()
    out = np.full(len(v), np.nan)
    for i in range(minp, len(v)):
        lo = max(0, i - win)
        b, *_ = np.linalg.lstsq(X[lo:i], y[lo:i], rcond=None)
        sm = np.mean(np.exp(y[lo:i] - X[lo:i] @ b))
        out[i] = np.exp(X[i] @ b) * sm / 100 * v["ref"].iat[i]
    return pd.Series(out, index=v.index).reindex(t.index)


def metrics(real: np.ndarray, pred: np.ndarray) -> dict:
    ok = np.isfinite(real) & np.isfinite(pred) & (pred > 0)
    r, p = real[ok], pred[ok]
    e = r - p
    lr, lp = np.log(r), np.log(p)
    return {"n": int(ok.sum()),
            "r2_punti": float(1 - (e @ e) / ((r - r.mean()) @ (r - r.mean()))),
            "r2_log": float(1 - ((lr - lp) @ (lr - lp)) / ((lr - lr.mean()) @ (lr - lr.mean()))),
            "mae_punti": float(np.mean(np.abs(e))), "mediana_ae_punti": float(np.median(np.abs(e))),
            "mape_pct": float(np.mean(np.abs(e) / r) * 100),
            "bias_punti": float(np.mean(p - r)), "range_medio_reale": float(r.mean()),
            "previsto_medio": float(p.mean()), "corr": float(np.corrcoef(r, p)[0, 1])}


def coverage(t: pd.DataFrame, pred: pd.Series) -> dict:
    ok = pred.notna() & t["rng"].notna()
    d, p = t[ok], pred[ok]
    out = {}
    for mlt in MULTS:
        out[f"range_sotto_{mlt}x"] = float((d["rng"] <= mlt * p).mean())
    for k in KS:
        up, dn = d["rth_open"] + k * p, d["rth_open"] - k * p
        hit_up, hit_dn = d["rth_hi"] >= up, d["rth_lo"] <= dn
        out[f"k{k}_dentro_entrambe"] = float((~hit_up & ~hit_dn).mean())
        out[f"k{k}_tocca_sopra"] = float(hit_up.mean())
        out[f"k{k}_tocca_sotto"] = float(hit_dn.mean())
        out[f"k{k}_tocca_entrambe"] = float((hit_up & hit_dn).mean())
    return out


def dm_test(real, p_a, p_b, days) -> dict:
    """Differenza di perdita (errore quadratico in log) A - B per giorno; >0 = B migliore. Bootstrap a blocchi di giorno."""
    ok = np.isfinite(real) & np.isfinite(p_a) & np.isfinite(p_b)
    la = (np.log(real[ok]) - np.log(p_a[ok])) ** 2
    lb = (np.log(real[ok]) - np.log(p_b[ok])) ** 2
    st = core.day_block_bootstrap(la - lb, np.asarray(days)[ok], n_boot=10000)
    return {k: st[k] for k in ("n", "mean", "lo", "hi", "p_two", "p_pos")}


def yearly_r2(t: pd.DataFrame, pred: pd.Series) -> dict:
    out = {}
    d = t.assign(p=pred).dropna(subset=["p", "rng"])
    for yr, g in d.groupby(d.index.year):
        mm = metrics(g["rng"].to_numpy(), g["p"].to_numpy())
        out[int(yr)] = {"n": mm["n"], "r2_log": round(mm["r2_log"], 3), "r2_punti": round(mm["r2_punti"], 3),
                        "mae": round(mm["mae_punti"], 1), "range_medio": round(mm["range_medio_reale"], 1)}
    return out


def main():
    bars, daily = F.load_bars()
    t = F.daily_table(bars)
    del bars
    assert t.index.max() <= TEST[1]
    # coerenza con la tabella del laboratorio: stessi range RTH (adj) sui giorni validi
    common = t.index.intersection(daily.index[daily["valid"]])
    diff = (t.loc[common, "rng"] - (daily.loc[common, "rth_high"] - daily.loc[common, "rth_low"])).abs().max()
    print(f"[check] max |range 30m - range lab 1m| sui giorni validi: {diff:.6f} punti")
    print(f"[check] giorni validi 30m {int(t['valid'].sum())}, lab {int(daily['valid'].sum())}, "
          f"discordanti {int((t['valid'] != daily['valid'].reindex(t.index).fillna(False)).sum())}")

    vxn = extdata.known_at_open(t.index)["VXN"]
    t["lvxn"] = np.log(vxn)

    models = {
        "har_notte": fit(t, BASE),
        "solo_har": fit(t, ["l1", "m5", "m22"]),
        "har_notte_vxn": fit(t, BASE + ["lvxn"]),
    }
    for k, m in models.items():
        print(k, {c: round(b, 4) for c, b in zip(["b0"] + m["cols"], m["b"])}, "b0'", round(m["b0_adj"], 4),
              "R2log in", round(m["r2_log_in"], 3), "n", m["n"])

    test = t[(t.index >= TEST[0]) & (t.index <= TEST[1]) & t["valid"]].copy()
    train = t[(t.index >= TRAIN[0]) & (t.index <= TRAIN[1]) & t["valid"]].copy()

    # baseline ATR14 scalato: fattore fisso stimato in campione (minimi quadrati nell'origine, punti)
    tr_ok = train.dropna(subset=["atr14_prev", "rng"])
    atr_k = float((tr_ok["rng"] * tr_ok["atr14_prev"]).sum() / (tr_ok["atr14_prev"] ** 2).sum())
    m20_k = float((tr_ok.dropna(subset=["mean20"])["rng"] * tr_ok.dropna(subset=["mean20"])["mean20"]).sum()
                  / (tr_ok.dropna(subset=["mean20"])["mean20"] ** 2).sum())

    preds = {
        "HAR+notte (fisso) [INDICATORE]": predict(test, models["har_notte"]),
        "HAR+notte+VXN (fisso)": predict(test, models["har_notte_vxn"]),
        "solo HAR, senza notte (fisso)": predict(test, models["solo_har"]),
        "HAR+notte ristimato ogni giorno (500 sess.)": rolling_pred(t, BASE).reindex(test.index),
        "media range RTH 20 giorni": test["mean20"],
        "ATR(14) giornaliero Globex, grezzo": test["atr14_prev"],
        f"ATR(14) x {atr_k:.3f} (fattore fisso in campione)": test["atr14_prev"] * atr_k,
    }
    # campione comune per tutti i confronti
    common_ok = np.logical_and.reduce([np.isfinite(p.to_numpy()) for p in preds.values()] + [np.isfinite(test["rng"].to_numpy())])
    tc = test[common_ok]
    print(f"\nTEST {tc.index[0].date()} -> {tc.index[-1].date()}  n={len(tc)}")
    res = {"periodo_test": [str(tc.index[0].date()), str(tc.index[-1].date())], "n_test": len(tc),
           "fattore_atr": atr_k, "fattore_media20_in_campione": m20_k, "modelli": models, "confronto": {},
           "copertura": {}, "annuale": {}}
    for name, p in preds.items():
        mm = metrics(tc["rng"].to_numpy(), p[common_ok].to_numpy())
        res["confronto"][name] = mm
        res["copertura"][name] = coverage(tc, p[common_ok])
        print(f"{name:52s} R2pt {mm['r2_punti']:.3f}  R2log {mm['r2_log']:.3f}  MAE {mm['mae_punti']:.1f}  "
              f"MedAE {mm['mediana_ae_punti']:.1f}  MAPE {mm['mape_pct']:.1f}%  bias {mm['bias_punti']:+.1f}")
    main_p = preds["HAR+notte (fisso) [INDICATORE]"][common_ok]
    res["annuale"]["test"] = yearly_r2(tc, main_p)
    # anno per anno nel test: MAE di ogni metodo (il R2 di un anno solo e' severo: confronta con la media
    # di QUELL'anno, che nessuno conosce in anticipo)
    res["annuale"]["test_mae_per_metodo"] = {}
    for name, p in preds.items():
        yy = yearly_r2(tc, p[common_ok])
        res["annuale"]["test_mae_per_metodo"][name] = {y: (v["mae"], v["r2_log"]) for y, v in yy.items()}
        print(f"  per anno {name[:40]:40s}", {y: v["mae"] for y, v in yy.items()})
    res["annuale"]["stima_in_campione"] = yearly_r2(train, predict(train, models["har_notte"]))
    # stesso numero in campione, per vedere se il test regge
    trc = train.dropna(subset=BASE + ["y"])
    res["in_campione"] = metrics(trc["rng"].to_numpy(), predict(trc, models["har_notte"]).to_numpy())
    res["copertura_in_campione"] = coverage(trc, predict(trc, models["har_notte"]))

    days = tc.index.to_numpy()
    r = tc["rng"].to_numpy()
    P = {k: v[common_ok].to_numpy() for k, v in preds.items()}
    names = list(P)
    res["test_differenze"] = {
        "VXN_vs_base": dm_test(r, P[names[0]], P[names[1]], days),
        "base_vs_ATRscalato": dm_test(r, P[names[6]], P[names[0]], days),
        "base_vs_media20": dm_test(r, P[names[4]], P[names[0]], days),
        "senza_notte_vs_base": dm_test(r, P[names[2]], P[names[0]], days),
        "fisso_vs_ristimato": dm_test(r, P[names[0]], P[names[3]], days),
        "nota": "mean = perdita(A) - perdita(B), perdita = (ln reale - ln previsto)^2; >0 = il secondo e' migliore",
    }
    # stesso confronto VXN sul periodo di validazione (con coefficienti stimati SOLO su discovery):
    # e' il numero del laboratorio, rifatto qui per coerenza
    for k, v in res["test_differenze"].items():
        if isinstance(v, dict):
            print(f"  DM {k:22s} mean {v['mean']:+.4f} [{v['lo']:+.4f},{v['hi']:+.4f}] p_two {v['p_two']:.4f}")
    cov = res["copertura"][names[0]]
    print("copertura indicatore:", {k: round(v, 3) for k, v in cov.items()})
    print("copertura VXN:", {k: round(v, 3) for k, v in res["copertura"][names[1]].items() if "dentro" in k or "sotto_" in k})
    print("in campione:", {k: round(v, 3) for k, v in res["in_campione"].items()})

    # errori peggiori nel test (giorni di notizie?)
    ratio = (tc["rng"] / main_p).sort_values(ascending=False)
    res["peggiori_sottostime"] = [{"data": str(d.date()), "reale": round(float(tc.at[d, "rng"]), 1),
                                   "previsto": round(float(main_p[d]), 1), "rapporto": round(float(v), 2)}
                                  for d, v in ratio.head(12).items()]
    res["peggiori_sovrastime"] = [{"data": str(d.date()), "reale": round(float(tc.at[d, "rng"]), 1),
                                   "previsto": round(float(main_p[d]), 1), "rapporto": round(float(v), 2)}
                                  for d, v in ratio.tail(6).items()]
    q = np.quantile(ratio, [0.05, 0.25, 0.5, 0.75, 0.95])
    res["quantili_reale_su_previsto"] = dict(zip(["q05", "q25", "q50", "q75", "q95"], np.round(q, 3).tolist()))
    print("quantili reale/previsto:", res["quantili_reale_su_previsto"])
    print("peggiori sottostime:", res["peggiori_sottostime"][:8])

    # VXN: il suo peso nel tempo (stima su sotto-periodi)
    for lo, hi in (("2010-06-07", "2018-12-31"), ("2019-01-01", "2023-09-30")):
        sub = t[(t.index >= lo) & (t.index <= hi) & t["valid"]].dropna(subset=BASE + ["lvxn", "y"])
        b, se, *_ = ols(sub[BASE + ["lvxn"]].to_numpy(), sub["y"].to_numpy())
        res.setdefault("vxn_per_periodo", {})[f"{lo}..{hi}"] = {"b_vxn": float(b[-1]), "se_hac": float(se[-1])}
        print(f"  coeff. VXN {lo}..{hi}: {b[-1]:.3f} (se {se[-1]:.3f})")

    here = Path(__file__).resolve().parent
    m = models["har_notte"]
    coef = {"modello": "ln range% = b0' + b_l1*l1 + b_m5*m5 + b_m22*m22 + b_on*lon",
            "b0_adj": m["b0_adj"], "b0_ols": m["b"][0], "smearing": m["smear"],
            "b_l1": m["b"][1], "b_m5": m["b"][2], "b_m22": m["b"][3], "b_on": m["b"][4],
            "stima": [m["first"], m["last"]], "n_stima": m["n"],
            "variante_vxn": dict(zip(["b0_adj", "b_l1", "b_m5", "b_m22", "b_on", "b_lvxn"],
                                     [models["har_notte_vxn"]["b0_adj"]] + models["har_notte_vxn"]["b"][1:]))}
    json.dump(coef, open(here / "coefficienti.json", "w"), indent=2)
    json.dump(res, open(here / "risultati_oos.json", "w"), indent=2, default=float)

    # valori di controllo per TradingView: ultime 15 sessioni prima della cassaforte
    chk = t[(t.index <= TEST[1])].tail(15).copy()
    chk["previsto_punti"] = predict(chk, models["har_notte"])
    chk["previsto_pct"] = chk["previsto_punti"] / chk["ref"] * 100
    chk["banda_sup_k1"] = chk["rth_open"] + chk["previsto_punti"]
    chk["banda_inf_k1"] = chk["rth_open"] - chk["previsto_punti"]
    cols = ["ref", "on_hi", "on_lo", "l1", "m5", "m22", "lon", "previsto_pct", "previsto_punti", "rth_open",
            "banda_sup_k1", "banda_inf_k1", "atr14_prev", "rng", "valid"]
    chk[cols].round(4).to_csv(here / "verifica_tradingview.csv", index_label="sessione")
    print("\nscritti coefficienti.json, risultati_oos.json, verifica_tradingview.csv")
    return t, models


if __name__ == "__main__":
    main()
