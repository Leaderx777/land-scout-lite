from __future__ import annotations

import pandas as pd


def _percentile_score(series: pd.Series, lower_is_better: bool) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() <= 1:
        return pd.Series(50.0, index=series.index)

    ranks = numeric.rank(method="average", pct=True)
    scores = (1.0 - ranks) * 100.0 if lower_is_better else ranks * 100.0
    return scores.fillna(50.0)


def score_land_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Add a preliminary 0-100 land deal score using listing-side facts only.

    This is intentionally a screening score, not a valuation. It rewards lower
    asking price, lower price per acre, more acreage, and longer market time.
    AVM/comps and due diligence should be used before treating a parcel as a deal.
    """
    scored = frame.copy()
    if scored.empty:
        scored["land_deal_score"] = pd.Series(dtype="float64")
        scored["deal_rating"] = pd.Series(dtype="object")
        return scored

    asking = scored.get("asking_price", pd.Series(index=scored.index, dtype="float64"))
    ppa = scored.get("price_per_acre", pd.Series(index=scored.index, dtype="float64"))
    acres = scored.get("acres", pd.Series(index=scored.index, dtype="float64"))
    dom = scored.get("days_on_market", pd.Series(index=scored.index, dtype="float64"))

    asking_score = _percentile_score(asking, lower_is_better=True)
    ppa_score = _percentile_score(ppa, lower_is_better=True)
    acreage_score = _percentile_score(acres, lower_is_better=False)
    dom_score = _percentile_score(dom, lower_is_better=False)

    scored["land_deal_score"] = (
        asking_score * 0.30
        + ppa_score * 0.35
        + acreage_score * 0.20
        + dom_score * 0.15
    ).round(1)

    def rating(score: float) -> str:
        if score >= 75:
            return "Best Deal"
        if score >= 55:
            return "Worth Reviewing"
        return "Skip for now"

    scored["deal_rating"] = scored["land_deal_score"].map(rating)
    return scored.sort_values(
        ["land_deal_score", "asking_price"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)
