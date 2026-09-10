import pandas as pd

from land_scout.core.land_scoring import score_land_candidates


def test_empty_land_frame_returns_score_columns():
    result = score_land_candidates(pd.DataFrame())
    assert "land_deal_score" in result.columns
    assert "deal_rating" in result.columns
    assert "discount_to_value_pct" in result.columns
    assert result.empty


def test_land_candidates_are_ranked_best_score_first():
    frame = pd.DataFrame({
        "address": ["Cheap Acre", "Expensive Small", "Middle"],
        "asking_price": [10000, 40000, 20000],
        "price_per_acre": [5000, 40000, 10000],
        "acres": [2.0, 1.0, 1.5],
        "days_on_market": [120, 10, 45],
    })
    result = score_land_candidates(frame)
    assert result.iloc[0]["address"] == "Cheap Acre"
    assert result.iloc[0]["land_deal_score"] > result.iloc[-1]["land_deal_score"]


def test_land_score_stays_between_zero_and_one_hundred():
    frame = pd.DataFrame({
        "asking_price": [5000, 10000, 15000, 20000],
        "price_per_acre": [1000, 2000, 3000, 4000],
        "acres": [4.0, 3.0, 2.0, 1.0],
        "days_on_market": [200, 100, 50, 5],
    })
    result = score_land_candidates(frame)
    assert result["land_deal_score"].between(0, 100).all()


def test_unvalued_land_cannot_be_called_best_deal():
    frame = pd.DataFrame({"asking_price": [5000, 50000], "price_per_acre": [1000, 50000], "acres": [5, .2], "days_on_market": [200, 1]})
    result = score_land_candidates(frame)
    assert "Best Deal" not in set(result["deal_rating"])


def test_value_discount_creates_equity_and_boosts_rank():
    frame = pd.DataFrame({
        "address": ["Discounted", "Near Value"],
        "asking_price": [10000, 19000],
        "price_per_acre": [10000, 19000],
        "acres": [1.0, 1.0],
        "days_on_market": [30, 30],
        "estimated_value": [20000, 20000],
        "value_range_low": [18000, 18000],
        "value_range_high": [22000, 22000],
        "value_comp_count": [10, 10],
    })
    result = score_land_candidates(frame)
    discounted = result[result.address == "Discounted"].iloc[0]
    near = result[result.address == "Near Value"].iloc[0]
    assert discounted["discount_to_value_pct"] == 50.0
    assert discounted["estimated_equity"] == 10000
    assert discounted["land_deal_score"] > near["land_deal_score"]
    assert discounted["deal_rating"] == "Best Deal"


def test_overpriced_valued_land_scores_lower():
    frame = pd.DataFrame({
        "asking_price": [25000], "price_per_acre": [25000], "acres": [1.0], "days_on_market": [30],
        "estimated_value": [20000], "value_range_low": [18000], "value_range_high": [22000], "value_comp_count": [10],
    })
    result = score_land_candidates(frame)
    assert result.iloc[0]["discount_to_value_pct"] == -25.0
    assert result.iloc[0]["deal_rating"] == "Skip for now"


def test_listing_ask_fallback_cannot_be_called_best_deal():
    frame = pd.DataFrame({
        "address": ["Looks Cheap"],
        "asking_price": [10000],
        "price_per_acre": [10000],
        "acres": [1.0],
        "days_on_market": [120],
        "estimated_value": [30000],
        "value_range_low": [25000],
        "value_range_high": [35000],
        "value_comp_count": [12],
        "value_source": ["Land comp $/acre"],
    })
    result = score_land_candidates(frame)
    assert result.iloc[0]["deal_rating"] == "Worth Reviewing"
    assert result.iloc[0]["land_deal_score"] < 100


def test_verified_sold_comps_can_support_best_deal_label():
    frame = pd.DataFrame({
        "address": ["Verified Discount"],
        "asking_price": [10000],
        "price_per_acre": [10000],
        "acres": [1.0],
        "days_on_market": [120],
        "estimated_value": [30000],
        "value_range_low": [25000],
        "value_range_high": [35000],
        "value_comp_count": [8],
        "value_source": ["Verified sold comps"],
    })
    result = score_land_candidates(frame)
    assert result.iloc[0]["deal_rating"] == "Best Deal"
