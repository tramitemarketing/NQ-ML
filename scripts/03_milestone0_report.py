"""Report Milestone 0: quanti eventi, che geometria, quanto costano i tick nelle finestre.
Uso: .venv\\Scripts\\python scripts\\03_milestone0_report.py"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from nqml.config import config_hash, git_commit, load_config
from nqml.data.databento_client import FetchSpec, estimate_cost, make_client
from nqml.profile.sessions import ny_minutes

N_SAMPLE = 40
SEED = 0


def q(s: pd.Series) -> str:
    qs = s.quantile([0.1, 0.25, 0.5, 0.75, 0.9])
    return " | ".join(f"{v:.2f}" for v in qs)


def windows(e: pd.DataFrame) -> pd.DataFrame:
    w = e[["session_date", "break_ts", "reentry_ts"]].drop_duplicates().copy()
    w["minutes"] = (w["reentry_ts"] - w["break_ts"]).dt.total_seconds() / 60
    return w


def sample_cost(client, cfg: dict, w: pd.DataFrame) -> tuple[float, int]:
    d = cfg["data"]
    if len(w) == 0:
        return 0.0, 0
    s = w.sample(n=min(N_SAMPLE, len(w)), random_state=SEED)
    total = 0.0
    for r in s.itertuples():
        spec = FetchSpec(d["dataset"], d["symbol"], d["stype_in"], "trades",
                         r.break_ts.strftime("%Y-%m-%dT%H:%M"), r.reentry_ts.strftime("%Y-%m-%dT%H:%M"))
        total += estimate_cost(client, spec)
    return total / len(s), len(s)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    e = pd.read_parquet("data/events/events.parquet")
    days = pd.read_parquet("data/events/days.parquet")
    e["year"] = pd.to_datetime(e["session_date"]).dt.year
    e["stop_pts"] = (e["entry_ref_price"] - e["stop_price"]).abs()
    e["target_pts"] = (e["target_price"] - e["entry_ref_price"]).abs()
    e["rr"] = e["target_pts"] / e["stop_pts"].replace(0, np.nan)
    tick_start = dt.date.fromisoformat(cfg["data"]["tick_start"])
    e5 = e[pd.to_datetime(e["session_date"]).dt.date >= tick_start]
    valid_days = days[days["valid"]]
    valid5 = valid_days[pd.to_datetime(valid_days["session_date"]).dt.date >= tick_start]

    load_dotenv(".env")
    client = make_client(os.environ["DATABENTO_API_KEY"])
    w_all = windows(e)
    w_dates = pd.to_datetime(w_all["session_date"]).dt.date
    w5 = w_all[w_dates >= tick_start]
    w_old = w_all[w_dates < tick_start]
    c5_mean, n5 = sample_cost(client, cfg, w5)
    cold_mean, nold = sample_cost(client, cfg, w_old)
    cost5 = c5_mean * len(w5)
    cost10 = cost5 + cold_mean * len(w_old)

    n5_events = len(e5)
    decision = ("5 anni di tick (N5 >= 6000)" if n5_events >= 6000
                else f"10 anni di tick (N5 = {n5_events} < 6000), STIMA ${cost10:.0f}")

    L = []
    L.append("# Milestone 0 — conteggio eventi e geometria\n")
    L.append(f"Generato il {dt.date.today().isoformat()} · config `{config_hash('config.yaml')}` · commit `{git_commit()}`\n")
    L.append("Tutte le cifre sono misurate da `data/events/*.parquet`; i costi tick sono estrapolati da "
             f"{n5} + {nold} finestre campionate con `metadata.get_cost` (seed {SEED}).\n")
    L.append("## Giorni\n")
    L.append(f"- sessioni totali: {len(days)}; valide (>= {cfg['sessions']['min_rth_bars']} barre RTH): {len(valid_days)}; "
             f"valide dal {tick_start}: {len(valid5)}\n")
    L.append("## Eventi per anno × va_type × side\n")
    L.append(e.pivot_table(index="year", columns=["va_type", "side"], values="event_id", aggfunc="count", fill_value=0)
              .to_markdown() + "\n")
    L.append(f"\n- **Totale 10 anni: {len(e)}** · **dal {tick_start} (N5): {n5_events}** · "
             f"eventi/giorno valido: {len(e)/max(len(valid_days),1):.2f}\n")
    L.append("## Geometria (quantili 10 | 25 | 50 | 75 | 90)\n")
    L.append("| misura | q10 | q25 | q50 | q75 | q90 |\n|---|---|---|---|---|---|\n")
    L.append(f"| stop (punti) | {q(e['stop_pts'])} |\n")
    L.append(f"| target (punti) | {q(e['target_pts'])} |\n")
    L.append(f"| rr_ratio | {q(e['rr'].dropna())} |\n")
    L.append(f"| excursion_minutes | {q(e['excursion_minutes'])} |\n")
    L.append(f"| bars_outside | {q(e['bars_outside'])} |\n")
    L.append(f"| minuti finestra tick | {q(w_all['minutes'])} |\n")
    L.append(f"\n- eventi con rr_ratio < 1: {(e['rr'] < 1).mean()*100:.1f}% · rr >= 2: {(e['rr'] >= 2).mean()*100:.1f}%\n")
    reentry_ny_min = ny_minutes(pd.DatetimeIndex(e["reentry_ts"]))
    early_dev = int(((e["va_type"] == "DEV") & (reentry_ny_min <= 9 * 60 + 45)).sum())
    L.append(f"- eventi DEV con rientro entro le 09:45 (profilo con <= 3 barre): {early_dev}\n")
    L.append("## Costo tick nelle finestre (schema `trades`)\n")
    L.append(f"- finestre uniche dal {tick_start}: {len(w5)} · costo medio campionato ${c5_mean:.4f} → **STIMA ${cost5:.2f}**\n")
    L.append(f"- finestre uniche 2016→{tick_start}: {len(w_old)} · costo medio campionato ${cold_mean:.4f} → 10 anni **STIMA ${cost10:.2f}**\n")
    L.append("## Decisione (regola spec §12: N5 >= 6000 → 5 anni, altrimenti 10)\n")
    L.append(f"**{decision}**\n")
    Path("reports").mkdir(exist_ok=True)
    Path("reports/milestone0_counts.md").write_text("".join(L), encoding="utf-8")
    print("".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
