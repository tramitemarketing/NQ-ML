"""Passo 0 di r6_community (PREREG): copertura, scala di sigma, qualita' del placebo. Nessun tasso di successo."""
import numpy as np
import pandas as pd
from scipy import stats

from lab import core


def minute_matrix(bars: pd.DataFrame, sessions: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    """Rendimenti log a 1 minuto (adj) per sessione x minuto di sessione (0 = 18:00, 1379 = 16:59).
    Minuto senza barra = rendimento 0 (prezzo fermo). Il primo minuto porta il salto dalla sessione prima."""
    b = bars[bars["session"].isin(sessions.values)]
    lc = np.log(b["adj_close"].to_numpy())
    r = np.diff(lc, prepend=lc[0])
    msess = ((b["ny_min"].to_numpy().astype(int) - 1080) % 1440)
    si = pd.Index(sessions).get_indexer(pd.DatetimeIndex(b["session"].to_numpy()))
    M = np.zeros((len(sessions), 1380))
    have = np.zeros((len(sessions), 1380), bool)
    ok = msess < 1380
    M[si[ok], msess[ok]] = r[ok]
    have[si[ok], msess[ok]] = True
    return M, have


def shuffle(M: np.ndarray, years: np.ndarray, rng, scaled: bool) -> np.ndarray:
    """Rimescola ogni minuto fra le sessioni dello stesso anno. scaled=True: prima divide ogni giornata per la
    sua volatilita' realizzata e poi la rimoltiplica (conserva il livello di vol del giorno, non la memoria)."""
    out = np.empty_like(M)
    vol = np.sqrt((M ** 2).sum(1))[:, None] + 1e-12
    Z = M / vol if scaled else M
    for y in np.unique(years):
        rows = np.where(years == y)[0]
        for j in range(M.shape[1]):
            out[rows, j] = Z[rng.permutation(rows), j]
    return out * vol if scaled else out


if __name__ == "__main__":
    bars, daily = core.load("discovery")
    d = daily[daily["valid"] & daily["in_phase"]]
    S = d.index
    M, have = minute_matrix(bars, S)
    years = S.year.to_numpy()

    print("1. copertura 00:00-09:29 ET (% di minuti con barra), per anno")
    cols = np.arange(360, 930)                    # 00:00 -> 09:29
    print(pd.Series(have[:, cols].mean(1), index=S).groupby(years).mean().mul(100).round(2).to_string())

    print("\n2. 0,25 sigma in punti (sigma = SD 20 rendimenti 16:00->16:00 fino a t-1, x prezzo), per anno")
    c16 = d["rth_close"]
    sig = np.log(c16).diff().rolling(20).std().shift(1)
    raw_close = bars[bars["rth"]].groupby("session")["close"].last().reindex(S)
    q = (0.25 * sig * raw_close).groupby(years).describe()[["count", "25%", "50%", "75%"]]
    print(q.round(2).to_string())

    print("\n3. placebo: conserva profilo e code? (reale / rimescolato semplice / rimescolato scalato)")
    rng = np.random.default_rng(0)
    P1, P2 = shuffle(M, years, rng, False), shuffle(M, years, rng, True)
    rth = np.arange(930, 1320)                    # 09:30 -> 15:59
    rows = []
    for name, X in (("reale", M), ("semplice", P1), ("scalato", P2)):
        day = X[:, rth].sum(1)
        absd = np.abs(day)
        rows.append({"serie": name,
                     "SD per minuto / reale (mediana)": np.median(X[:, rth].std(0) / M[:, rth].std(0)),
                     "curtosi 1m RTH": stats.kurtosis(X[:, rth].ravel()),
                     "curtosi rend. RTH giornaliero": stats.kurtosis(day),
                     "autocorr |rend. giornaliero|": np.corrcoef(absd[1:], absd[:-1])[0, 1],
                     "autocorr 1m RTH": np.corrcoef(X[:, rth][:, 1:].ravel(), X[:, rth][:, :-1].ravel())[0, 1],
                     "SD rend. RTH giornaliero x1e4": day.std() * 1e4})
    tab = pd.DataFrame(rows).set_index("serie").round(4)
    print(tab.to_string())
    core.record("r6_community", "passo0_placebo_quality", "Passo 0: qualita' del placebo (profilo, code, memoria)",
                "discovery", {k: v for k, v in tab.to_dict(orient="index").items()})
