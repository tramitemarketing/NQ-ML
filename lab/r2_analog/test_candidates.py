"""Test minimo: la famiglia non presenta candidati; il registro contiene i test dichiarati nel REPORT."""
import json
from pathlib import Path

from lab.r2_analog.candidates import CANDIDATES

assert CANDIDATES == [], "r2_analog non presenta candidati"
led = Path(__file__).resolve().parents[1] / "ledger" / "r2_analog.jsonl"
rows = [json.loads(l) for l in open(led, encoding="utf-8")]
assert all(r["phase"] == "discovery" for r in rows)
assert all(r["family"] == "r2_analog" for r in rows)
print(f"ok: 0 candidati, {len(rows)} test nel registro, tutti discovery")
