import re
from pathlib import Path

from nqml.config import config_hash, git_commit, load_config


def test_load_config_has_expected_sections():
    cfg = load_config("config.yaml")
    assert cfg["data"]["symbol"] == "NQ.v.0"
    assert cfg["instrument"]["tick_size"] == 0.25
    assert cfg["detector"]["max_excursion_minutes"] == 90
    assert cfg["sessions"]["min_rth_bars"] == 300


def test_config_hash_is_12_hex_and_stable(tmp_path: Path):
    p = tmp_path / "c.yaml"
    p.write_text("a: 1\n", encoding="utf-8")
    h1 = config_hash(p)
    h2 = config_hash(p)
    assert h1 == h2 and re.fullmatch(r"[0-9a-f]{12}", h1)
    p.write_text("a: 2\n", encoding="utf-8")
    assert config_hash(p) != h1


def test_git_commit_returns_short_hash_or_unknown():
    c = git_commit()
    assert c == "unknown" or re.fullmatch(r"[0-9a-f]{7,12}", c)


def test_config_has_milestone_1a_sections():
    cfg = load_config("config.yaml")
    assert cfg["vault"]["start"] == "2026-03-20"
    assert cfg["walkforward"]["test_windows"][0] == ["2023-10-01", "2024-03-31"]
    assert cfg["walkforward"]["test_windows"][-1] == ["2025-10-01", "2026-03-19"]
    assert cfg["decision"]["margin_r"] == 0.1
    assert cfg["backtest"]["bootstrap_n"] == 10000
    original_signs = {"vol_slope_excursion": -1, "vol_reentry_bar": 1, "rr_ratio": -1}
    assert all(cfg["model"]["monotone"][k] == v for k, v in original_signs.items())


def test_config_has_milestone_1b_sections():
    cfg = load_config("config.yaml")
    assert cfg["data"]["tick_budget_usd"] == 105
    assert cfg["tick"]["fraction"] == 0.45 and cfg["tick"]["seed"] == 0 and cfg["tick"]["extreme_zone_ticks"] == 4
    assert cfg["model"]["monotone"]["delta_excursion"] == 1 and cfg["model"]["monotone"]["absorption_score"] == 1
    assert cfg["model"]["monotone"]["delta_reentry"] == 1
    assert cfg["model"]["calibration_split"] == 0.5
    assert [r["feature"] for r in cfg["baselines"]["rules_by_version"]["1b"]] == ["vol_slope_excursion", "vol_reentry_bar", "delta_excursion"]
