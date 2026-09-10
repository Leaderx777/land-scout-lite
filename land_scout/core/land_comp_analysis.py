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
    evidence_type: str = "LISTING_ASKS"
    confidence_label: str = "PRELIMINARY"
    sold_comp_count: int = 0
    active_comp_count: int = 0
    inactive_comp_count: int = 0


def _positive_numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(index=frame.index, dtype="float64")
    values = pd.to_numeric(frame[column], errors="coerce")
    return values.where(values > 0)


def _listing_status_counts(frame: pd.DataFrame) -> tuple[int, int]:
    if "status" not in frame.columns:
        return 0, 0
    status = frame["status"].fillna("").astype(str).str.strip().str.lower()
    return int((status == "active").sum()), int((status == "inactive").sum())


def _confidence(evidence_type: str, count: int, ppa: pd.Series) -> str:
    if evidence_type != "VERIFIED_SALES":
        return "PRELIMINARY"
    if count < 2 or ppa.empty:
        return "LOW"
    median = float(ppa.median())
    if median <= 0:
        return "LOW"
    spread = float(ppa.quantile(0.75) - ppa.quantile(0.25)) / median
    if count >= 5 and spread <= 0.35:
        return "HIGH"
    if count >= 3 and spread <= 0.60:
        return "MEDIUM"
    return "LOW"


def analyze_land_comps(subject_lot_size: float | int | None, comparables: pd.DataFrame) -> LandCompEstimate:
    """Estimate land value from comparable price-per-acre evidence.

    Evidence hierarchy:
    1. Verified sale-price columns (``sale_price`` or ``last_sale_price``) when at least
       two usable sale records are available.
    2. Listing asking prices (``price``) as a preliminary fallback only.

    RentCast AVM comparable records expose listing prices, not closed-sale prices, so
    active/inactive listing comps are never mislabeled as sold comps here.
    """
    comps = comparables.copy()
    if comps.empty:
        return LandCompEstimate(None, None, None, 0, None, comps)

    lots = _positive_numeric(comps, "lot_size")

    sale_price = _positive_numeric(comps, "sale_price")
    if sale_price.notna().sum() < 2:
        sale_price = _positive_numeric(comps, "last_sale_price")

    use_sales = int((sale_price.notna() & lots.notna()).sum()) >= 2
    if use_sales:
        valuation_price = sale_price
        evidence_type = "VERIFIED_SALES"
    else:
        valuation_price = _positive_numeric(comps, "price")
        evidence_type = "LISTING_ASKS"

    valid = valuation_price.notna() & lots.notna()
    comps = comps.loc[valid].copy()
    if comps.empty:
        return LandCompEstimate(None, None, None, 0, None, comps, evidence_type=evidence_type)

    comps["valuation_price"] = valuation_price.loc[comps.index]
    comps["evidence_type"] = evidence_type
    comps["acres"] = (lots.loc[comps.index] / 43560.0).round(3)
    comps["price_per_acre"] = (
        pd.to_numeric(comps["valuation_price"], errors="coerce")
        / comps["acres"].where(comps["acres"] > 0)
    ).round(0)
    comps = comps[comps["price_per_acre"].notna() & (comps["price_per_acre"] > 0)].copy()

    usable = len(comps)
    sold_count = usable if evidence_type == "VERIFIED_SALES" else 0
    active_count, inactive_count = _listing_status_counts(comps)

    try:
        subject_lot = float(subject_lot_size) if subject_lot_size is not None else 0.0
    except (TypeError, ValueError):
        subject_lot = 0.0

    ppa = pd.to_numeric(comps["price_per_acre"], errors="coerce").dropna()
    confidence = _confidence(evidence_type, usable, ppa)

    if subject_lot <= 0 or usable < 2:
        median_ppa = float(ppa.median()) if not ppa.empty else None
        return LandCompEstimate(
            None,
            None,
            None,
            usable,
            round(median_ppa, 0) if median_ppa is not None else None,
            comps,
            evidence_type=evidence_type,
            confidence_label=confidence,
            sold_comp_count=sold_count,
            active_comp_count=active_count,
            inactive_comp_count=inactive_count,
        )

    subject_acres = subject_lot / 43560.0
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
        evidence_type=evidence_type,
        confidence_label=confidence,
        sold_comp_count=sold_count,
        active_comp_count=active_count,
        inactive_comp_count=inactive_count,
    )
