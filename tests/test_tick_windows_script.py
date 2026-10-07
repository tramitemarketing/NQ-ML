"""--resume di scripts/08_tick_windows.py: riusa windows.parquet solo se coincide con la pre-registrazione committata."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "08_tick_windows.py"
spec = importlib.util.spec_from_file_location("tick_windows_script", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

REPORT = ("# Milestone 1b-S\n\n- **Costo esatto (somma di 3 `get_cost`): $0.30** · budget $105.00 · "
          "costo medio per finestra $0.1000\n")


def _windows(costs):
    ts = pd.Timestamp("2024-01-02 15:00", tz="UTC")
    return pd.DataFrame({"session_date": [ts.date()] * len(costs), "win_start": [ts] * len(costs),
                         "win_end": [ts + pd.Timedelta(minutes=10)] * len(costs), "cost_usd": costs})


def _cfg(tmp_path):
    return {"tick": {"tick_dir": str(tmp_path)}}


def test_registered_cost_parses_the_committed_report(tmp_path):
    rp = tmp_path / "1b_sampling.md"
    rp.write_text(REPORT, encoding="utf-8")
    assert mod.registered_cost(rp) == (3, 0.30)


def test_registered_cost_raises_without_the_line(tmp_path):
    rp = tmp_path / "1b_sampling.md"
    rp.write_text("# vuoto\n", encoding="utf-8")
    with pytest.raises(ValueError):
        mod.registered_cost(rp)


def test_resume_plan_accepts_matching_windows(tmp_path):
    rp = tmp_path / "1b_sampling.md"
    rp.write_text(REPORT, encoding="utf-8")
    _windows([0.1, 0.1, 0.1]).to_parquet(tmp_path / "windows.parquet", index=False)
    w = mod.resume_plan(_cfg(tmp_path), rp)
    assert len(w) == 3 and round(float(w["cost_usd"].sum()), 2) == 0.30


@pytest.mark.parametrize("costs", [[0.1, 0.1], [0.1, 0.1, 0.2]])
def test_resume_plan_rejects_count_or_cost_mismatch(tmp_path, costs):
    rp = tmp_path / "1b_sampling.md"
    rp.write_text(REPORT, encoding="utf-8")
    _windows(costs).to_parquet(tmp_path / "windows.parquet", index=False)
    with pytest.raises(ValueError, match="non coincide"):
        mod.resume_plan(_cfg(tmp_path), rp)


def test_verify_against_registration_passes_on_match(tmp_path):
    rp = tmp_path / "1b_sampling.md"
    rp.write_text(REPORT, encoding="utf-8")
    mod.verify_against_registration(_windows([0.1, 0.1, 0.1]), rp)   # non deve sollevare


@pytest.mark.parametrize("costs", [[0.1, 0.1], [0.1, 0.1, 0.2]])
def test_verify_against_registration_raises_on_count_or_cost_mismatch(tmp_path, costs):
    rp = tmp_path / "1b_sampling.md"
    rp.write_text(REPORT, encoding="utf-8")
    with pytest.raises(ValueError, match="non coincide"):
        mod.verify_against_registration(_windows(costs), rp)
