import datetime as dt

import pandas as pd
import pytest

from nqml.config import load_config
from nqml.model.walkforward import assert_no_vault, fold_slices, make_folds, trading_dates

CFG = load_config("config.yaml")


def _days():
    d = pd.bdate_range("2021-09-20", "2026-09-19")     # giorni feriali come proxy delle sessioni
    return pd.DataFrame({"session_date": d.date, "valid": True})


def test_trading_dates_exclude_vault():
    td = trading_dates(_days(), CFG)
    assert td[0] == dt.date(2021, 9, 20) and td[-1] == dt.date(2026, 3, 19)


def test_make_folds_matches_spec_windows_with_embargo():
    folds = make_folds(trading_dates(_days(), CFG), CFG)
    assert len(folds) == 5 and [f.k for f in folds] == [0, 1, 2, 3, 4]
    f0 = folds[0]
    assert f0.train_start == dt.date(2021, 9, 20) and f0.test_start == dt.date(2023, 10, 2) and f0.test_end == dt.date(2024, 3, 29)
    assert f0.val_end == dt.date(2023, 9, 28)       # 2023-09-29 e' il giorno di embargo
    assert f0.val_start == dt.date(2023, 6, 29) and f0.fit_end == dt.date(2023, 6, 28)
    assert folds[-1].test_end == dt.date(2026, 3, 19)
    for a, b in zip(folds, folds[1:]):
        assert a.test_end < b.test_start and b.train_start == a.train_start and b.val_end > a.val_end


def test_fold_slices_are_disjoint_and_ordered():
    folds = make_folds(trading_dates(_days(), CFG), CFG)
    df = _days().rename(columns={}).assign(x=1.0)
    fit, val, test = fold_slices(df, folds[0])
    assert fit["session_date"].max() < val["session_date"].min() < test["session_date"].min()
    assert len(fit) + len(val) + len(test) < len(df)            # l'embargo e il futuro restano fuori
    assert set(fit["session_date"]).isdisjoint(test["session_date"])


def test_assert_no_vault():
    ok = pd.DataFrame({"session_date": [dt.date(2026, 3, 19)]})
    assert_no_vault(ok, CFG)
    with pytest.raises(ValueError):
        assert_no_vault(pd.DataFrame({"session_date": [dt.date(2026, 3, 20)]}), CFG)
