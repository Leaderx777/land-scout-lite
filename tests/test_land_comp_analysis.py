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
    assert result.evidence_type == "LISTING_ASKS"
    assert result.confidence_label == "PRELIMINARY"


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


def test_verified_sales_take_priority_over_listing_asks():
    comps = pd.DataFrame({
        "price": [50000, 60000, 70000],
        "sale_price": [12000, 15000, 18000],
        "lot_size": [43560, 43560, 43560],
        "status": ["Inactive", "Inactive", "Active"],
    })
    result = analyze_land_comps(43560, comps)
    assert result.evidence_type == "VERIFIED_SALES"
    assert result.sold_comp_count == 3
    assert result.estimated_value == 15000
    assert result.median_price_per_acre == 15000


def test_one_sale_does_not_override_multiple_listing_comps():
    comps = pd.DataFrame({
        "price": [10000, 15000, 20000],
        "sale_price": [12000, None, None],
        "lot_size": [43560, 43560, 43560],
    })
    result = analyze_land_comps(43560, comps)
    assert result.evidence_type == "LISTING_ASKS"
    assert result.estimated_value == 15000
    assert result.sold_comp_count == 0


def test_listing_status_counts_are_reported():
    comps = pd.DataFrame({
        "price": [10000, 15000, 20000],
        "lot_size": [43560, 43560, 43560],
        "status": ["Active", "Inactive", "Inactive"],
    })
    result = analyze_land_comps(43560, comps)
    assert result.active_comp_count == 1
    assert result.inactive_comp_count == 2
