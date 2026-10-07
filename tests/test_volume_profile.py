import numpy as np
import pandas as pd
import pytest

from nqml.profile.volume_profile import ValueArea, VolumeProfile, value_area_from_histogram


def test_single_price_bar_collapses_to_one_level():
    vp = VolumeProfile(tick_size=0.25)
    vp.add_bar(low=100.0, high=100.0, volume=10)
    va = vp.value_area()
    assert va == ValueArea(poc=100.0, vah=100.0, val=100.0, total_volume=10.0, n_levels=1)


def test_bar_volume_is_spread_uniformly_over_levels():
    vp = VolumeProfile(tick_size=0.25)
    vp.add_bar(low=1.0, high=1.75, volume=8)  # 4 livelli -> 2 ciascuno
    levels, vols = vp.histogram()
    assert list(levels) == [1.0, 1.25, 1.5, 1.75]
    assert list(vols) == [2.0, 2.0, 2.0, 2.0]


def test_value_area_hand_computed():
    levels = np.array([1.0, 1.25, 1.5, 1.75, 2.0])
    vols = np.array([1.0, 3.0, 10.0, 2.0, 1.0])  # tot 17, 70% = 11.9
    va = value_area_from_histogram(levels, vols, 0.70)
    # POC 1.5 (10). Sopra: 2+1=3, sotto: 3+1=4 -> si scende: acc 14 >= 11.9
    assert va.poc == 1.5 and va.val == 1.0 and va.vah == 1.5
    assert va.total_volume == 17.0 and va.n_levels == 5


def test_value_area_reached_exactly_at_poc():
    levels = np.array([1.0, 1.25, 1.5, 1.75, 2.0])
    vols = np.array([0.0, 0.0, 7.0, 3.0, 0.0])  # 70% di 10 = 7 = POC da solo
    va = value_area_from_histogram(levels, vols, 0.70)
    assert (va.poc, va.val, va.vah) == (1.5, 1.5, 1.5)


def test_poc_tie_breaks_toward_center_of_range():
    levels = np.array([1.0, 1.25, 1.5, 1.75, 2.0])
    vols = np.array([5.0, 0.0, 1.0, 0.0, 5.0])
    va = value_area_from_histogram(levels, vols, 0.70)
    # 1.0 e 2.0 sono a pari distanza dal centro 1.5: a parità di distanza vince il più basso
    assert va.poc == 1.0


def test_poc_tie_breaks_toward_closer_level_when_not_equidistant():
    levels = np.array([1.0, 1.25, 1.5, 1.75, 2.0])
    vols = np.array([5.0, 0.0, 0.0, 5.0, 0.0])
    va = value_area_from_histogram(levels, vols, 0.70)
    # 1.0 e 1.75 sono in parita' di volume, ma 1.75 e' piu' vicino al centro 1.5 (0.25 contro 0.5): vince 1.75
    assert va.poc == 1.75


def test_incremental_equals_batch():
    df = pd.DataFrame({
        "low": [100.0, 100.5, 99.75], "high": [100.5, 101.0, 100.0], "volume": [4, 6, 2],
    })
    inc = VolumeProfile()
    for _, r in df.iterrows():
        inc.add_bar(r["low"], r["high"], r["volume"])
    batch = VolumeProfile()
    batch.add_bars(df)
    assert inc.value_area() == batch.value_area()
    assert inc.n_bars == batch.n_bars == 3


def test_empty_profile_returns_none():
    assert VolumeProfile().value_area() is None
