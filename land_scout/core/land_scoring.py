from __future__ import annotations

import pandas as pd


def _percentile_score(series: pd.Series, lower_is_better: bool) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() <= 1:
        return pd.Series(50.0, index=series.index)
    ranks = numeric.rank(method="average", pct=True)
    scores = (1.0 - ranks) * 100.0 if lower_is_better else ranks * 100.0
    return scores.fillna(50.0)


def _source_strength(value_source: object) -> str:
    source = str(value_source or "").strip().lower()
    if "verified" in source or "sold" in source:
        return "STRONG"
    if "land comp" in source or "listing" in source or "$ / acre" in source or "$/acre" in source:
        return "PRELIMINARY"
    if "avm" in source:
        return "MODEL"
    return "MODEL"


def _rating(score: float, has_value: bool, source_strength: str = "MODEL") -> str:
    if has_value:
        # Asking-price comp fallbacks are useful for triage, but not enough evidence to
        # call a parcel a "Best Deal". Strong sold evidence or a direct model estimate
        # can earn that label.
        if score >= 75 and source_strength != "PRELIMINARY":
            return "Best Deal"
        if score >= 55:
            return "Worth Reviewing"
        return "Skip for now"
    # Listing-only scores are deliberately not allowed to claim a Best Deal.
    return "Preliminary review" if score >= 45 else "Low preliminary rank"


def score_land_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Rank land using listing facts, and valuation evidence when available.

    Listing-side facts produce a preliminary score. If estimated_value is present,
    the score shifts most of its weight to discount-to-value and valuation confidence.
    Asking-price comp fallbacks remain explicitly preliminary and cannot receive the
    strongest deal label.
    """
    scored = frame.copy()
    if scored.empty:
        for column in ("land_deal_score", "deal_rating", "discount_to_value_pct", "estimated_equity"):
            scored[column] = pd.Series(dtype="float64" if column != "deal_rating" else "object")
        return scored

    asking = pd.to_numeric(scored.get("asking_price"), errors="coerce")
    ppa = pd.to_numeric(scored.get("price_per_acre"), errors="coerce")
    acres = pd.to_numeric(scored.get("acres"), errors="coerce")
    dom = pd.to_numeric(scored.get("days_on_market"), errors="coerce")

    preliminary = (
        _percentile_score(asking, True) * 0.30
        + _percentile_score(ppa, True) * 0.35
        + _percentile_score(acres, False) * 0.20
        + _percentile_score(dom, False) * 0.15
    )

    estimated = pd.to_numeric(scored.get("estimated_value", pd.Series(index=scored.index, dtype="float64")), errors="coerce")
    low = pd.to_numeric(scored.get("value_range_low", pd.Series(index=scored.index, dtype="float64")), errors="coerce")
    high = pd.to_numeric(scored.get("value_range_high", pd.Series(index=scored.index, dtype="float64")), errors="coerce")
    comp_count = pd.to_numeric(scored.get("value_comp_count", pd.Series(index=scored.index, dtype="float64")), errors="coerce")

    has_value = estimated.notna() & (estimated > 0) & asking.notna() & (asking > 0)
    scored["discount_to_value_pct"] = pd.NA
    scored["estimated_equity"] = pd.NA
    scored.loc[has_value, "discount_to_value_pct"] = ((estimated[has_value] - asking[has_value]) / estimated[has_value] * 100.0).round(1)
    scored.loc[has_value, "estimated_equity"] = (estimated[has_value] - asking[has_value]).round(0)

    # Discount score: 0% discount = 35 points, 20% = 65, 40%+ = 95.
    discount = pd.to_numeric(scored["discount_to_value_pct"], errors="coerce")
    discount_score = (35.0 + discount * 1.5).clip(lower=0.0, upper=100.0)

    range_width = pd.Series(index=scored.index, dtype="float64")
    valid_range = has_value & low.notna() & high.notna() & (high >= low)
    range_width.loc[valid_range] = ((high[valid_range] - low[valid_range]) / estimated[valid_range] * 100.0)
    confidence_score = pd.Series(35.0, index=scored.index)
    confidence_score.loc[range_width <= 35] = 65.0
    confidence_score.loc[range_width <= 20] = 85.0
    confidence_score = confidence_score + comp_count.fillna(0).clip(lower=0, upper=15) / 15.0 * 15.0
    confidence_score = confidence_score.clip(upper=100.0)

    source_series = scored.get("value_source", pd.Series("", index=scored.index)).fillna("").astype(str)
    source_strength = source_series.map(_source_strength)

    # Listing-ask fallback estimates should carry a confidence penalty. They are useful
    # for ranking candidates, but they are not transaction evidence.
    confidence_score.loc[source_strength == "PRELIMINARY"] = confidence_score.loc[
        source_strength == "PRELIMINARY"
    ].clip(upper=55.0)

    final_score = preliminary.copy()
    final_score.loc[has_value] = (
        discount_score.loc[has_value] * 0.60
        + confidence_score.loc[has_value] * 0.20
        + preliminary.loc[has_value] * 0.20
    )
    scored["land_deal_score"] = final_score.round(1)
    scored["deal_rating"] = [
        _rating(float(score), bool(valued), strength)
        for score, valued, strength in zip(scored["land_deal_score"], has_value, source_strength)
    ]
    return scored.sort_values(["land_deal_score", "asking_price"], ascending=[False, True], na_position="last").reset_index(drop=True)
