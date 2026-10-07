"""H1-ter 'sorpresa': movimento di k minuti misurato contro la volatilita' 1m delle 60 barre PRIMA della
finestra (sigma_pre = sigma60 alla barra i-k+1: nessuna barra del movimento nel denominatore).
Ipotesi: un salto improvviso rispetto al regime appena precedente = arrivo di informazione ->
sotto-reazione -> continuazione (lato = verso del movimento). Superficie k x z x H x fascia."""
import numpy as np
from lab.micro.common import Data, evaluate_pair


def surprise(D, k):
    n = len(D.c); idx = np.arange(n)
    prev = np.clip(idx - k, 0, None)
    mv = D.c - D.c[prev]
    sp = D.sig60[np.clip(idx - k + 1, 0, None)]
    ok = (D.scode[prev] == D.scode) & np.isfinite(sp) & (sp > 0)
    z = np.where(ok, mv / (sp * np.sqrt(k)), np.nan)
    return z, mv


if __name__ == "__main__":
    D = Data()
    idx = np.arange(len(D.c))
    bands = {"RTH": (D.rth & (D.m >= 575) & (D.m < 900), "rth"),
             "ETH": ((~D.rth) & ((D.m >= 1085) | (D.m < 509)), "session")}
    for k in (10, 15, 30):
        z, mv = surprise(D, k)
        for bn, (bm, end) in bands.items():
            for zt in (3, 4, 5):
                sel = bm & D.inph & (np.abs(np.nan_to_num(z)) >= zt)
                s = idx[sel]
                for H in (30, 60):
                    # lato dato = continuazione (riportato come 'F' nella stampa), 'C' = fade
                    evaluate_pair(D, s, np.sign(mv[s]).astype(int), H, f"H16_surp_k{k}_{bn}_z{zt}_H{H}",
                                  f"sorpresa: |mov {k}m|>={zt} sigma_pre*sqrt(k), {bn}, CONTINUAZIONE (lato dato), uscita {H}m", end=end)
