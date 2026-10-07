"""Milestone 1b-S: campione di giorni, finestre unite, costo esatto (get_cost, gratis) e — solo con --yes — download.
Uso:  .venv\\Scripts\\python scripts\\08_tick_windows.py            # campiona, calcola il costo, scrive reports/1b_sampling.md, si ferma
      .venv\\Scripts\\python scripts\\08_tick_windows.py --yes      # scarica le finestre (dopo conferma dell'utente)
      .venv\\Scripts\\python scripts\\08_tick_windows.py --yes --resume  # riprende senza rifare i get_cost: usa data/tick/windows.parquet
                                                                  # solo se coincide con reports/1b_sampling.md
      .venv\\Scripts\\python scripts\\08_tick_windows.py --check    # integrità + convenzione del lato sui dati scaricati"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from nqml.config import config_hash, git_commit, load_config
from nqml.data.bars import load_bars, rth_bars, sessions_iter
from nqml.data.databento_client import CostAboveThreshold, guard_cost, make_client
from nqml.model.walkforward import trading_dates
from nqml.tick.fetch import estimate_windows_cost, fetch_all_windows
from nqml.tick.sampling import budget_fraction, sample_days
from nqml.tick.windows import load_day_trades, windows_for_days


def _patch_requests_retry(max_retries: int = 6, base_delay: float = 2.0) -> None:
    """Il client Databento chiama requests.post/get senza sessione persistente e senza retry: su ~2.300
    chiamate get_cost di fila un reset di connessione transitorio (osservato in pratica) altrimenti
    interrompe l'intera pianificazione. Avvolgiamo le due funzioni con un retry esponenziale sugli
    errori di rete transitori (connessione, timeout) — nessuna finestra viene saltata, si ritenta la
    singola chiamata HTTP fallita.
    Copertura: vale per tutte le chiamate del client, quindi anche per le `get_range` del percorso --yes
    (POST con stream=True), ma solo per errori sollevati PRIMA della risposta (connessione, handshake,
    timeout); una caduta a metà stream esce da qui e fa fallire lo script, che al rilancio riparte dalle
    finestre non ancora scritte (Parquet atomici). Gli errori HTTP 4xx/5xx non passano di qui: il client
    li trasforma in BentoClientError/BentoServerError dopo la risposta e non vengono ritentati."""
    for name in ("post", "get"):
        original = getattr(requests, name)

        def _wrapped(*args, _original=original, _name=name, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return _original(*args, **kwargs)
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                    if attempt == max_retries:
                        raise
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"  errore di rete su requests.{_name} ({exc.__class__.__name__}), "
                          f"tentativo {attempt}/{max_retries}, nuovo tentativo tra {delay:.0f}s...")
                    time.sleep(delay)

        setattr(requests, name, _wrapped)


def plan(cfg: dict, client) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Campiona i giorni alla quota di config, calcola il costo esatto; se supera il budget applica la regola e ricampiona."""
    tk, d = cfg["tick"], cfg["data"]
    days = pd.read_parquet(Path(d["events_dir"]) / "days.parquet")
    events = pd.read_parquet(Path(d["events_dir"]) / "events.parquet")
    pop = trading_dates(days, cfg)                                   # validi, < cassaforte
    start, end = dt.date.fromisoformat(cfg["walkforward"]["train_start"]), dt.date.fromisoformat(cfg["vault"]["start"])
    fraction = tk["fraction"]
    for attempt in (1, 2):
        sampled = sample_days(pop, fraction, tk["seed"], start, end)
        windows = windows_for_days(events, sampled)
        print(f"tentativo {attempt}: quota {fraction:.3f} -> {len(sampled)} giorni, {len(windows)} finestre; calcolo il costo esatto...")
        windows = estimate_windows_cost(client, windows, cfg, progress=True)
        total = float(windows["cost_usd"].sum())
        print(f"  costo esatto ${total:.2f} (budget ${d['tick_budget_usd']:.2f})")
        new_fraction = budget_fraction(fraction, total, float(d["tick_budget_usd"]))
        if new_fraction == fraction:
            return sampled, windows, fraction
        fraction = new_fraction
    return sampled, windows, fraction


def write_sampling_report(cfg: dict, sampled: pd.DataFrame, windows: pd.DataFrame, fraction: float, out: Path) -> None:
    total = float(windows["cost_usd"].sum())
    per_month = sampled.groupby("month").agg(n_validi=("n_valid_in_month", "first"), n_scelti=("session_date", "count")).reset_index()
    L = ["# Milestone 1b-S — campionamento pre-registrato e costo esatto\n",
         f"Generato il {dt.date.today().isoformat()} · config `{config_hash('config.yaml')}` · commit `{git_commit()}`\n",
         f"- Popolazione: giorni validi in [{cfg['walkforward']['train_start']}, {cfg['vault']['start']}) · strato = mese · "
         f"quota di config {cfg['tick']['fraction']} · **quota effettiva {fraction}** · seed {cfg['tick']['seed']}\n",
         f"- Giorni campionati: **{len(sampled)}** su {int(per_month['n_validi'].sum())} · finestre unite: **{len(windows)}** · "
         f"minuti totali: {int(((windows['win_end'] - windows['win_start']).dt.total_seconds() / 60).sum())}\n",
         f"- **Costo esatto (somma di {len(windows)} `get_cost`): ${total:.2f}** · budget ${cfg['data']['tick_budget_usd']:.2f} · "
         f"costo medio per finestra ${total / max(len(windows), 1):.4f}\n",
         "\n## Giorni per mese\n", per_month.to_markdown(index=False), "\n",
         "\n## Regola: nessun acquisto senza `--yes` dopo che questo file è stato letto e committato. "
         "I giorni non campionati non entrano in nessuna esecuzione 1b né 1a-S.\n"]
    out.write_text("\n".join(L), encoding="utf-8")


def registered_cost(report_path: Path) -> tuple[int, float]:
    """Legge dal report committato (pre-registrazione) il numero di finestre e il costo esatto."""
    m = re.search(r"somma di (\d+) `get_cost`\): \$([0-9]+\.[0-9]{2})", report_path.read_text(encoding="utf-8"))
    if not m:
        raise ValueError(f"costo pre-registrato non trovato in {report_path}")
    return int(m.group(1)), float(m.group(2))


def verify_against_registration(windows: pd.DataFrame, report_path: Path) -> None:
    """Il percorso `--yes` senza `--resume` NON deve riprezzare e sovrascrivere la pre-registrazione: confronta
    conteggio e costo esatto del ricampionamento con quanto committato in reports/1b_sampling.md (Important 3).
    Solleva ValueError su disaccordo; non scrive nulla."""
    n_reg, cost_reg = registered_cost(report_path)
    total = float(windows["cost_usd"].sum())
    if len(windows) != n_reg or abs(round(total, 2) - cost_reg) > 0.005:
        raise ValueError(f"il ricampionamento ({len(windows)} finestre, ${total:.2f}) non coincide con la "
                         f"pre-registrazione ({n_reg} finestre, ${cost_reg:.2f}): rilanciare senza --yes e "
                         f"ricommittare il report prima di acquistare")


def resume_plan(cfg: dict, report_path: Path) -> pd.DataFrame:
    """--resume: riusa data/tick/windows.parquet già prezzato invece di rifare ~2.000 get_cost, ma SOLO se numero di
    finestre e costo totale coincidono al centesimo con la pre-registrazione committata; altrimenti ValueError."""
    windows = pd.read_parquet(Path(cfg["tick"]["tick_dir"]) / "windows.parquet")
    n_reg, cost_reg = registered_cost(report_path)
    total = round(float(windows["cost_usd"].sum()), 2)
    if len(windows) != n_reg or abs(total - cost_reg) > 0.005:
        raise ValueError(f"windows.parquet ({len(windows)} finestre, ${total:.2f}) non coincide con la pre-registrazione "
                         f"({n_reg} finestre, ${cost_reg:.2f}): rilanciare senza --resume")
    return windows


def check(cfg: dict) -> int:
    """Integrità dei trade scaricati e verifica della convenzione del lato (A = vendita aggressiva, B = acquisto)."""
    tk, d, s = cfg["tick"], cfg["data"], cfg["sessions"]
    windows = pd.read_parquet(Path(tk["tick_dir"]) / "windows.parquet")
    trades_dir = Path(tk["trades_dir"])
    bars = load_bars(Path(d["raw_dir"]))
    sampled = set(pd.to_datetime(windows["session_date"]).dt.date)
    n_days, n_trades, agree, tested, missing = 0, 0, 0, 0, 0
    sides = {}
    for sd, day in sessions_iter(bars):
        if sd not in sampled:
            continue
        tr = load_day_trades(trades_dir, sd)
        if tr is None:
            missing += 1
            continue
        n_days += 1; n_trades += len(tr)
        for k, v in tr["side"].value_counts().items():
            sides[k] = sides.get(k, 0) + int(v)
        rth = rth_bars(day, s["rth_open"], s["rth_close"])
        moves = rth[(rth["close"] - rth["open"]).abs() >= 2.0]                       # barre 1m con spostamento >= 2 pt
        for ts, b in moves.iterrows():
            seg = tr.loc[(tr.index >= ts) & (tr.index < ts + pd.Timedelta(minutes=1))]
            if len(seg) < 20:
                continue
            buy = seg.loc[seg["side"] == "B", "size"].sum(); sell = seg.loc[seg["side"] == "A", "size"].sum()
            if buy == sell:
                continue
            tested += 1
            agree += int((b["close"] > b["open"]) == (buy > sell))
    print(f"giorni con trade {n_days} (mancanti {missing}), trade totali {n_trades:,}, lati {sides}")
    print(f"convenzione lato: su {tested} barre 1m con |close-open| >= 2 pt e >= 20 trade, B>A quando la barra sale nel "
          f"{agree / max(tested, 1) * 100:.1f}% dei casi (atteso >> 50%; sotto 60% la convenzione è invertita: FERMARSI)")
    return 0 if (missing == 0 and tested > 0 and agree / max(tested, 1) > 0.6) else 3


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="conferma l'acquisto al costo esatto scritto in reports/1b_sampling.md")
    ap.add_argument("--check", action="store_true", help="verifica integrità e convenzione del lato sui dati scaricati")
    ap.add_argument("--resume", action="store_true",
                    help="con --yes: riprende il download usando data/tick/windows.parquet, verificato contro reports/1b_sampling.md")
    ap.add_argument("--workers", type=int, default=1,
                    help="download in parallelo (thread); una finestra per thread, cache atomica per finestra")
    args = ap.parse_args()
    cfg = load_config("config.yaml")
    if args.check:
        return check(cfg)
    report_path = Path(cfg["backtest"]["reports_dir"]) / "1b_sampling.md"
    if args.resume and not args.yes:
        print("FERMATO: --resume ha senso solo insieme a --yes")
        return 2
    _patch_requests_retry()
    load_dotenv(".env")
    client = make_client(os.environ["DATABENTO_API_KEY"])
    tick_dir = Path(cfg["tick"]["tick_dir"]); tick_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if args.resume:
        windows = resume_plan(cfg, report_path)
        total = float(windows["cost_usd"].sum())
        print(f"--resume: {len(windows)} finestre, costo pre-registrato ${total:.2f} confermato da {report_path}; nessun get_cost rifatto")
    else:
        sampled, windows, fraction = plan(cfg, client)
        sampled.to_parquet(tick_dir / "sampled_days.parquet", index=False)
        windows.to_parquet(tick_dir / "windows.parquet", index=False)
        total = float(windows["cost_usd"].sum())
        if args.yes:
            # --yes senza --resume: NON riscrive la pre-registrazione, si confronta con essa (Important 3).
            if not report_path.exists():
                print(f"FERMATO: pre-registrazione mancante ({report_path}): eseguire prima senza flag e "
                      "committare il report prima di acquistare")
                return 2
            try:
                verify_against_registration(windows, report_path)
            except ValueError as ex:
                print(f"FERMATO: {ex}")
                return 2
            print(f"scritti data/tick/sampled_days.parquet, data/tick/windows.parquet in {time.time()-t0:.0f}s "
                  f"(pre-registrazione {report_path} verificata, non riscritta)")
        else:
            write_sampling_report(cfg, sampled, windows, fraction, report_path)
            print(f"scritti data/tick/sampled_days.parquet, data/tick/windows.parquet, reports/1b_sampling.md in {time.time()-t0:.0f}s")
    try:
        guard_cost(total, float(cfg["data"]["max_auto_cost_usd"]), confirmed=args.yes)
    except CostAboveThreshold as ex:
        print(f"FERMATO: {ex}")
        return 2
    if total > float(cfg["data"]["tick_budget_usd"]):
        print(f"FERMATO: il costo esatto ${total:.2f} supera il budget ${cfg['data']['tick_budget_usd']:.2f} anche dopo la regola di riduzione")
        return 2
    n = fetch_all_windows(client, windows, Path(cfg["tick"]["trades_dir"]), cfg, progress=True, workers=max(1, args.workers))
    print(f"scaricate {n} finestre nuove ({len(windows)} totali) in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
