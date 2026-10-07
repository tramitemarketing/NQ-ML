"""Passo 0, parte 1: scarica le opzioni NQ (definition + tbbo) SOLO per il discovery.

Costo stampato prima di comprare; si compra solo con --yes e solo se il totale sta nel budget autorizzato
dall'utente (2026-10-07: credito residuo ~26 $). Guardia: la fine dell'intervallo deve essere < 2019-01-01
(validazione e conferma non si toccano, PREREG e PROTOCOLLO §21).

Uso: .venv/Scripts/python.exe -m lab.r7_opzioni.s00_dati [--yes]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from lab import core

DATASET = "GLBX.MDP3"
PARENTS = ["NQ.OPT", "QN1.OPT", "QN2.OPT", "QN3.OPT", "QN4.OPT", "QN5.OPT"]
SCHEMAS = ["definition", "tbbo"]
START, END = "2010-06-07", "2019-01-01"          # END esclusivo
BUDGET_USD = 22.0                                # margine sotto il credito residuo
OUT = core.ROOT / "data" / "ext_paid" / "opzioni"

assert pd.Timestamp(END) <= pd.Timestamp("2019-01-01"), "solo discovery"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


DEF_COLS = ["instrument_id", "raw_symbol", "instrument_class", "expiration", "strike_price", "underlying_id",
            "underlying", "asset", "security_type", "contract_multiplier", "min_price_increment", "activation"]
TBBO_COLS = ["ts_event", "instrument_id", "price", "size", "side", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00"]


def convert(store, schema: str) -> pd.DataFrame:
    """A blocchi: le definizioni si ripetono ogni giorno per ogni contratto (170 MB compressi, >9 GB in
    memoria in un colpo solo) -> una riga per instrument_id (l'ultima). tbbo: solo le colonne utili."""
    parts = []
    for ch in store.to_df(count=500_000):
        if schema == "definition":
            ch = ch[DEF_COLS].drop_duplicates("instrument_id", keep="last")
        else:
            ch = ch.reset_index()
            ch = ch[[c for c in TBBO_COLS if c in ch.columns] + ["ts_recv"]]
        parts.append(ch)
    df = pd.concat(parts, ignore_index=True)
    if schema == "definition":
        df = df.drop_duplicates("instrument_id", keep="last").reset_index(drop=True)
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    load_dotenv(core.ROOT / ".env")
    import databento as db
    c = db.Historical(os.environ["DATABENTO_API_KEY"])
    jobs, total = [], 0.0
    for p in PARENTS:
        for s in SCHEMAS:
            kw = dict(dataset=DATASET, symbols=[p], stype_in="parent", schema=s, start=START, end=END)
            usd = float(c.metadata.get_cost(**kw))
            total += usd
            jobs.append((p, s, kw, usd))
            print(f"{p:8s} {s:10s} {usd:7.2f} $")
    print(f"totale {total:.2f} $ (budget {BUDGET_USD:.2f} $)")
    if total > BUDGET_USD:
        raise SystemExit("sopra il budget autorizzato: non compro")
    if not a.yes:
        raise SystemExit("solo stima: rilanciare con --yes per comprare")
    OUT.mkdir(parents=True, exist_ok=True)
    log = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "dataset": DATASET, "start": START, "end": END, "files": []}
    # i file mancanti si chiedono con l'API batch (lo streaming di get_range e' risultato lentissimo per le QN*)
    pending = {}
    for p, s, kw, usd in jobs:
        raw = OUT / f"{p.replace('.', '_')}_{s}.dbn.zst"
        if not raw.exists():
            job = c.batch.submit_job(encoding="dbn", compression="zstd", split_duration="none", **kw)
            pending[job["id"]] = raw
            print("batch inviato", p, s, job["id"], flush=True)
    while pending:
        time.sleep(30)
        done = {j["id"] for j in c.batch.list_jobs(states=["done"]) if j["id"] in pending}
        for jid in done:
            files = c.batch.download(job_id=jid, output_dir=OUT / "batch")
            dbn = [f for f in files if str(f).endswith(".dbn.zst")]
            assert len(dbn) == 1, files
            os.replace(dbn[0], pending.pop(jid))
            print("scaricato", jid, flush=True)
    for p, s, kw, usd in jobs:
        raw = OUT / f"{p.replace('.', '_')}_{s}.dbn.zst"
        df = convert(db.DBNStore.from_file(str(raw)), s)
        pq = raw.with_suffix("").with_suffix(".parquet")
        df.to_parquet(pq)
        log["files"].append({"parent": p, "schema": s, "usd": usd, "rows": len(df), "raw": raw.name,
                             "sha256": sha256(raw)})
        print(f"{p} {s}: {len(df):,} righe -> {pq.name}")
    log["total_usd"] = total
    (OUT / "download.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
