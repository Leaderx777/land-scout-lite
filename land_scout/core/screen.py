"""Batch screening logic for Central Illinois land opportunities."""

import pandas as pd

from land_scout.core.market import is_target_county
from land_scout.predictor_client import predict_land_value

REQUIRED_COLUMNS = {
    "listing_id",
    "county",
    "acres",
    "price",
    "distance_to_city_miles",
    "road_frontage_ft",
    "zoning_score",
    "utilities",
}


def screen_deals(df: pd.DataFrame) -> pd.DataFrame:
    """Predict values, calculate spreads, and rank target-market listings."""
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    rows = []
    for _, row in df.iterrows():
        if not is_target_county(str(row["county"])):
            continue

        estimated_value = predict_land_value(
            acres=float(row["acres"]),
            distance_to_city_miles=float(row["distance_to_city_miles"]),
            road_frontage_ft=float(row["road_frontage_ft"]),
            zoning_score=int(row["zoning_score"]),
            utilities=int(row["utilities"]),
        )
        asking_price = float(row["price"])
        spread = estimated_value - asking_price
        discount_pct = (spread / estimated_value * 100) if estimated_value else 0.0

        result = row.to_dict()
        result.update(
            estimated_value=round(estimated_value, 2),
            value_spread=round(spread, 2),
            discount_to_estimated_value_pct=round(discount_pct, 2),
        )
        rows.append(result)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values(
        ["discount_to_estimated_value_pct", "value_spread"],
        ascending=False,
    ).reset_index(drop=True)
