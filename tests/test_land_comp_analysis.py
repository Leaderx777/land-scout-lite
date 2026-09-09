import pandas as pd

from land_scout.core.land_comp_analysis import analyze_land_comps


def test_land_comp_estimate_uses_median_price_per_acre():
    comps = pd.DataFrame({
        "price": [10000, 15000, 20000],
        "lot_size": [43560, 43560, 43560],
    })
    result = analyze_land_comps(87120, comps)
    assert result.usable_comp_count == 3
    assert result.median_price_per_acre == 15000
    assert result.estimated_value == 30000


def test_land_comp_estimate_requires_two_usable_comps():
    comps = pd.DataFrame({"price": [10000], "lot_size": [43560]})
    result = analyze_land_comps(43560, comps)
    assert result.estimated_value is None
    assert result.usable_comp_count == 1


def test_land_comp_estimate_filters_invalid_records():
    comps = pd.DataFrame({
        "price": [10000, 0, 20000],
        "lot_size": [43560, 43560, None],
    })
    result = analyze_land_comps(43560, comps)
    assert result.usable_comp_count == 1
    assert result.estimated_value is None


def test_land_comp_estimate_requires_subject_lot_size():
    comps = pd.DataFrame({"price": [10000, 15000], "lot_size": [43560, 43560]})
    result = analyze_land_comps(None, comps)
    assert result.estimated_value is None
    assert result.usable_comp_count == 2
