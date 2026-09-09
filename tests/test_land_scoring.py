import pandas as pd

from land_scout.core.land_scoring import score_land_candidates


def test_empty_land_frame_returns_score_columns():
    result = score_land_candidates(pd.DataFrame())
    assert "land_deal_score" in result.columns
    assert "deal_rating" in result.columns
    assert result.empty


def test_land_candidates_are_ranked_best_score_first():
    frame = pd.DataFrame(
        {
            "address": ["Cheap Acre", "Expensive Small", "Middle"],
            "asking_price": [10000, 40000, 20000],
            "price_per_acre": [5000, 40000, 10000],
            "acres": [2.0, 1.0, 1.5],
            "days_on_market": [120, 10, 45],
        }
    )

    result = score_land_candidates(frame)

    assert result.iloc[0]["address"] == "Cheap Acre"
    assert result.iloc[0]["land_deal_score"] > result.iloc[-1]["land_deal_score"]


def test_land_score_stays_between_zero_and_one_hundred():
    frame = pd.DataFrame(
        {
            "asking_price": [5000, 10000, 15000, 20000],
            "price_per_acre": [1000, 2000, 3000, 4000],
            "acres": [4.0, 3.0, 2.0, 1.0],
            "days_on_market": [200, 100, 50, 5],
        }
    )

    result = score_land_candidates(frame)

    assert result["land_deal_score"].between(0, 100).all()


def test_land_rating_labels_are_expected_values():
    frame = pd.DataFrame(
        {
            "asking_price": [5000, 10000, 15000, 20000, 25000],
            "price_per_acre": [1000, 2000, 3000, 4000, 5000],
            "acres": [5.0, 4.0, 3.0, 2.0, 1.0],
            "days_on_market": [200, 150, 100, 50, 10],
        }
    )

    result = score_land_candidates(frame)

    assert set(result["deal_rating"]).issubset({"Best Deal", "Worth Reviewing", "Skip for now"})
