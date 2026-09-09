from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class LandCompEstimate:
    estimated_value: float | None
    range_low: float | None
    range_high: float | None
    usable_comp_count: int
    median_price_per_acre: float | None
    comparables: pd.DataFrame


def analyze_land_comps(subject_lot_size: float | int | None, comparables: pd.DataFrame) -> LandCompEstimate:
    """Estimate land value from comparable price-per-acre when a direct AVM is unavailable.

    Requires a positive subject lot size and at least two comparable land records with
    both positive price and positive lot size. The estimate uses the median comparable
    price per acre; the range uses the 25th and 75th percentiles.
    """
    comps = comparables.copy()
    if comps.empty:
        return LandCompEstimate(None, None, None, 0, None, comps)

    prices = pd.to_numeric(comps.get("price"), errors="coerce")
    lots = pd.to_numeric(comps.get("lot_size"), errors="coerce")
    valid = prices.notna() & lots.notna() & (prices > 0) & (lots > 0)
    comps = comps.loc[valid].copy()
    if comps.empty:
        return LandCompEstimate(None, None, None, 0, None, comps)

    comps["acres"] = (pd.to_numeric(comps["lot_size"], errors="coerce") / 43560.0).round(3)
    comps["price_per_acre"] = (
        pd.to_numeric(comps["price"], errors="coerce") / comps["acres"].where(comps["acres"] > 0)
    ).round(0)
    comps = comps[comps["price_per_acre"].notna() & (comps["price_per_acre"] > 0)].copy()

    usable = len(comps)
    try:
        subject_lot = float(subject_lot_size) if subject_lot_size is not None else 0.0
    except (TypeError, ValueError):
        subject_lot = 0.0
    if subject_lot <= 0 or usable < 2:
        return LandCompEstimate(None, None, None, usable, None, comps)

    subject_acres = subject_lot / 43560.0
    ppa = pd.to_numeric(comps["price_per_acre"], errors="coerce").dropna()
    median_ppa = float(ppa.median())
    low_ppa = float(ppa.quantile(0.25))
    high_ppa = float(ppa.quantile(0.75))

    return LandCompEstimate(
        estimated_value=round(median_ppa * subject_acres, 0),
        range_low=round(low_ppa * subject_acres, 0),
        range_high=round(high_ppa * subject_acres, 0),
        usable_comp_count=usable,
        median_price_per_acre=round(median_ppa, 0),
        comparables=comps,
    )
