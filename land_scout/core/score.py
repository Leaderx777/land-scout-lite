from typing import Dict, List, Optional

import pandas as pd

# Default bands (price-per-acre, USD):
# <=1000 => excellent, <=4000 => very_good, <=8000 => look_closer, else avoid
DEFAULT_THRESHOLDS = [1000, 4000, 8000]

# Starter bands per county (tune these as you get comps)
# These are just pragmatic starting points—not market gospel.
COUNTY_THRESHOLDS: Dict[str, List[float]] = {
    "peoria": [1200, 4500, 9000],
    "knox": [1000, 4000, 8000],
    "woodford": [1500, 5000, 10000],
    "chicago": [5000, 15000, 40000],  # urban fringe, outliers likely
    "tazewell": [1300, 4500, 9000],
    "henry": [1100, 4200, 8500],
    "canton": [1100, 4200, 8500],  # using similar to Henry as a placeholder
}


def _pick_thresholds(
    row: pd.Series,
    thresholds_by_county: Optional[Dict[str, List[float]]] = None,
    default: Optional[List[float]] = None,
) -> List[float]:
    default = default or DEFAULT_THRESHOLDS
    tbl = {
        k.strip().lower(): v
        for k, v in (thresholds_by_county or COUNTY_THRESHOLDS).items()
    }
    county = str(row.get("county", "")).strip().lower()
    return tbl.get(county, default)


def _categorize(p_per_acre: Optional[float], thr: List[float]) -> str:
    if p_per_acre is None:
        return "look_closer"
    if p_per_acre <= thr[0]:
        return "excellent"
    if p_per_acre <= thr[1]:
        return "very_good"
    if p_per_acre <= thr[2]:
        return "look_closer"
    return "avoid"


def apply(
    df: pd.DataFrame,
    thresholds: Optional[List[float]] = None,
    thresholds_by_county: Optional[Dict[str, List[float]]] = None,
) -> pd.DataFrame:
    # normalize columns
    cols = [c.lower().strip().replace(" ", "_") for c in df.columns]
    df = df.copy()
    df.columns = cols

    # compute price_per_acre when possible
    acre_col = "acre" if "acre" in cols else ("acres" if "acres" in cols else None)
    if "price" in cols and acre_col:
        df["price_per_acre"] = (
            df["price"].astype(float) / df[acre_col].astype(float)
        ).round(2)
    else:
        df["price_per_acre"] = None

    # choose per-row thresholds (county-aware), falling back to global/default
    if thresholds_by_county or "county" in df.columns:
        chosen = df.apply(
            lambda r: _pick_thresholds(
                r, thresholds_by_county, thresholds or DEFAULT_THRESHOLDS
            ),
            axis=1,
        )
        df["category"] = [
            _categorize(p, thr) for p, thr in zip(df["price_per_acre"], chosen)
        ]
    else:
        thr = thresholds or DEFAULT_THRESHOLDS
        df["category"] = df["price_per_acre"].apply(lambda p: _categorize(p, thr))

    return df
