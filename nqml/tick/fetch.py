"""Trade tick per finestra: costo esatto prima (get_cost, gratis), download atomico e ripristinabile dopo."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from nqml.data.databento_client import FetchSpec, cached_fetch_month, estimate_cost
from nqml.tick.windows import TRADE_COLS, window_path


def trades_spec(cfg: dict, win_start: pd.Timestamp, win_end: pd.Timestamp) -> FetchSpec:
    d = cfg["data"]
    fmt = "%Y-%m-%dT%H:%M:%S"
    return FetchSpec(d["dataset"], d["symbol"], d["stype_in"], "trades",
                     win_start.tz_convert("UTC").strftime(fmt), win_end.tz_convert("UTC").strftime(fmt))


def estimate_windows_cost(client, windows: pd.DataFrame, cfg: dict, progress: bool = False) -> pd.DataFrame:
    out = windows.copy()
    costs = []
    for i, r in enumerate(out.itertuples()):
        costs.append(estimate_cost(client, trades_spec(cfg, r.win_start, r.win_end)))
        if progress and i % 250 == 0:
            print(f"  costo: {i}/{len(out)} finestre")
    out["cost_usd"] = costs
    return out


def fetch_trades_window(client, spec: FetchSpec) -> pd.DataFrame:
    df = client.timeseries.get_range(dataset=spec.dataset, symbols=[spec.symbol], stype_in=spec.stype_in,
                                     schema=spec.schema, start=spec.start, end=spec.end).to_df()
    df = df[TRADE_COLS].copy()
    df["side"] = df["side"].astype(str)
    df.index = pd.DatetimeIndex(df.index).tz_convert("UTC")
    df.index.name = "ts_event"
    return df


def fetch_all_windows(client, windows: pd.DataFrame, trades_dir: Path, cfg: dict, progress: bool = False,
                      workers: int = 1) -> int:
    """Scarica le finestre mancanti; con workers > 1 in parallelo (thread), una finestra per thread: ogni
    finestra ha il proprio Parquet atomico, quindi nessuna puo' essere scaricata (e pagata) due volte."""
    todo = [(r.win_start, r.win_end, window_path(trades_dir, r.session_date, r.win_start, r.win_end))
            for r in windows.itertuples()]
    todo = [t for t in todo if not t[2].exists()]

    def one(t):
        cached_fetch_month(client, trades_spec(cfg, t[0], t[1]), t[2], fetch=fetch_trades_window)

    n_new = 0
    if workers <= 1:
        for i, t in enumerate(todo):
            one(t)
            n_new += 1
            if progress and i % 100 == 0:
                print(f"  download: {i}/{len(todo)} finestre mancanti")
        return n_new
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(one, t) for t in todo]
        for i, f in enumerate(as_completed(futures)):
            f.result()                                   # rilancia l'eccezione del thread (nessun errore silenzioso)
            n_new += 1
            if progress and i % 100 == 0:
                print(f"  download: {i}/{len(todo)} finestre mancanti ({workers} thread)")
    return n_new
