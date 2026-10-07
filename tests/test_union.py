import numpy as np
import pandas as pd
import pytest

from nqml.features.union import union_tick


def _fa():
    return pd.DataFrame({"event_id": ["a", "b", "c"], "session_date": ["2024-01-02"] * 3, "rr_ratio": [1.0, 2.0, 3.0],
                         "feature_version": ["1a"] * 3})


def test_union_left_joins_tick_columns_with_nan_elsewhere():
    fb = pd.DataFrame({"event_id": ["b"], "session_date": ["2024-01-02"], "rr_ratio": [2.0], "feature_version": ["1b"],
                       "delta_excursion": [0.1], "delta_reentry": [0.2], "absorption_score": [0.3]})
    out = union_tick(_fa(), fb, ["delta_excursion", "delta_reentry", "absorption_score"])
    assert len(out) == 3 and list(out["event_id"]) == ["a", "b", "c"]
    assert out.loc[out["event_id"] == "b", "delta_excursion"].item() == 0.1
    assert out.loc[out["event_id"] == "a", "delta_excursion"].isna().all()
    assert (out["feature_version"] == "1c").all() and out["rr_ratio"].tolist() == [1.0, 2.0, 3.0]


def test_union_refuses_a_common_column_that_differs():
    fb = pd.DataFrame({"event_id": ["b"], "session_date": ["2024-01-02"], "rr_ratio": [99.0], "feature_version": ["1b"],
                       "delta_excursion": [0.1], "delta_reentry": [0.2], "absorption_score": [0.3]})
    with pytest.raises(ValueError, match="rr_ratio"):
        union_tick(_fa(), fb, ["delta_excursion", "delta_reentry", "absorption_score"])


def test_union_refuses_duplicate_event_ids():
    fb = pd.DataFrame({"event_id": ["b", "b"], "session_date": ["2024-01-02"] * 2, "rr_ratio": [2.0, 2.0],
                       "feature_version": ["1b"] * 2, "delta_excursion": [0.1, 0.1], "delta_reentry": [0.2, 0.2],
                       "absorption_score": [0.3, 0.3]})
    with pytest.raises(ValueError, match="duplicat"):
        union_tick(_fa(), fb, ["delta_excursion", "delta_reentry", "absorption_score"])
