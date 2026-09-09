from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from land_scout.core.flip import analyze_flip


COLUMN_ALIASES = {
    "address": ["address", "property_address", "street_address", "street"],
    "city": ["city", "town", "municipality"],
    "state": ["state", "state_code"],
    "zip_code": ["zip", "zipcode", "zip_code", "postal_code"],
    "asking_price": ["asking_price", "price", "list_price", "listing_price"],
    "bedrooms": ["bedrooms", "beds", "bed"],
    "bathrooms": ["bathrooms", "baths", "bath"],
    "square_feet": ["square_feet", "sqft", "sq_ft", "living_area"],
    "lot_size": ["lot_size", "lotsize", "lot_sqft", "lot_square_feet"],
    "year_built": ["year_built", "built", "year"],
    "property_type": ["property_type", "type", "home_type"],
    "days_on_market": ["days_on_market", "dom"],
    "listing_url": ["listing_url", "url", "link"],
    "description": ["description", "remarks", "notes"],
    "rehab_estimate": ["rehab_estimate", "rehab", "repair_estimate", "repairs"],
    "arv_estimate": ["arv_estimate", "arv", "after_repair_value"],
}


@dataclass(frozen=True)
class ListingIngestionResult:
    listings: pd.DataFrame
    rejected: pd.DataFrame


def _normalize_name(name: object) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def _find_source_column(columns: Iterable[object], aliases: list[str]) -> object | None:
    normalized = {_normalize_name(column): column for column in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None


def _number_series(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(r"[$,]", "", regex=True)
        .str.replace(r"[^0-9.\-]", "", regex=True)
        .replace("", pd.NA)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _land_listing_mask(property_types: pd.Series) -> pd.Series:
    """Identify vacant-land style property types without excluding residential oddballs."""
    normalized = property_types.fillna("").astype(str).str.strip().str.lower()
    return normalized.str.contains(r"\bland\b|\blot\b|vacant", regex=True)


def normalize_residential_listings(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize common property-listing columns into one Property Scout schema."""
    if df is None or df.empty:
        return pd.DataFrame(columns=list(COLUMN_ALIASES))

    normalized = pd.DataFrame(index=df.index)
    for canonical, aliases in COLUMN_ALIASES.items():
        source = _find_source_column(df.columns, aliases)
        if source is not None:
            normalized[canonical] = df[source]
        else:
            normalized[canonical] = pd.NA

    text_columns = [
        "address",
        "city",
        "state",
        "zip_code",
        "property_type",
        "listing_url",
        "description",
    ]
    for column in text_columns:
        normalized[column] = normalized[column].fillna("").astype(str).str.strip()

    number_columns = [
        "asking_price",
        "bedrooms",
        "bathrooms",
        "square_feet",
        "lot_size",
        "year_built",
        "days_on_market",
        "rehab_estimate",
        "arv_estimate",
    ]
    for column in number_columns:
        normalized[column] = _number_series(normalized[column])

    return normalized.reset_index(drop=True)


def ingest_property_listings(
    df: pd.DataFrame,
    max_purchase_price: float = 50000.0,
    allowed_property_types: Iterable[str] | None = None,
) -> ListingIngestionResult:
    """Normalize and validate listings for Residential, Commercial, or Land scouting."""
    normalized = normalize_residential_listings(df)
    valid_address = normalized["address"].str.len() > 0
    valid_price = normalized["asking_price"].notna() & (normalized["asking_price"] > 0)
    within_price = normalized["asking_price"] <= float(max_purchase_price)

    if allowed_property_types is None:
        allowed_type = pd.Series(True, index=normalized.index)
    else:
        allowed = {str(value).strip().lower() for value in allowed_property_types}
        allowed_type = normalized["property_type"].str.lower().isin(allowed)

    accepted_mask = valid_address & valid_price & within_price & allowed_type
    accepted = normalized.loc[accepted_mask].copy()
    rejected = normalized.loc[~accepted_mask].copy()

    if not accepted.empty:
        accepted["screening_status"] = "READY_FOR_REVIEW"
        accepted = accepted.sort_values(by=["asking_price"], ascending=True).reset_index(drop=True)

    return ListingIngestionResult(
        listings=accepted.reset_index(drop=True),
        rejected=rejected.reset_index(drop=True),
    )


def ingest_residential_listings(
    df: pd.DataFrame,
    max_purchase_price: float = 50000.0,
    exclude_land: bool = False,
) -> ListingIngestionResult:
    """Normalize listings and apply the residential flip buy-box filter.

    Listings are not filtered by bedroom count. Property type remains broad by
    default, while callers focused on house flips can set ``exclude_land=True``
    to remove vacant land and lot listings from the candidate pipeline.
    """
    normalized = normalize_residential_listings(df)
    valid_address = normalized["address"].str.len() > 0
    valid_price = normalized["asking_price"].notna() & (normalized["asking_price"] > 0)
    within_price = normalized["asking_price"] <= float(max_purchase_price)
    allowed_property_type = ~_land_listing_mask(normalized["property_type"]) if exclude_land else True

    accepted_mask = valid_address & valid_price & within_price & allowed_property_type
    accepted = normalized.loc[accepted_mask].copy()
    rejected = normalized.loc[~accepted_mask].copy()

    accepted["screening_status"] = "NEEDS_ARV"
    has_arv = accepted["arv_estimate"].notna() & (accepted["arv_estimate"] > 0)
    has_rehab = accepted["rehab_estimate"].notna() & (accepted["rehab_estimate"] >= 0)
    accepted.loc[has_arv & ~has_rehab, "screening_status"] = "NEEDS_REHAB"
    accepted.loc[has_arv & has_rehab, "screening_status"] = "READY_TO_ANALYZE"

    if not accepted.empty:
        accepted = accepted.sort_values(
            by=["screening_status", "asking_price"],
            ascending=[True, True],
        ).reset_index(drop=True)

    return ListingIngestionResult(
        listings=accepted.reset_index(drop=True),
        rejected=rejected.reset_index(drop=True),
    )


def analyze_ready_residential_listings(
    listings: pd.DataFrame,
    holding_cost: float = 4000.0,
    selling_cost_percent: float = 0.08,
    target_profit: float = 25000.0,
) -> pd.DataFrame:
    """Run flip math only on rows that already have explicit ARV and rehab estimates."""
    rows: list[dict] = []
    for _, row in listings.iterrows():
        asking = row.get("asking_price")
        rehab = row.get("rehab_estimate")
        arv = row.get("arv_estimate")
        if pd.isna(asking) or pd.isna(rehab) or pd.isna(arv) or float(arv) <= 0:
            continue

        selling_cost = float(arv) * float(selling_cost_percent)
        flip = analyze_flip(
            purchase_price=float(asking),
            rehab_cost=float(rehab),
            holding_cost=float(holding_cost),
            selling_cost=selling_cost,
            arv=float(arv),
            target_profit=float(target_profit),
        )
        result = row.to_dict()
        result.update(
            {
                "holding_cost": holding_cost,
                "selling_cost": selling_cost,
                "projected_profit": flip.projected_profit,
                "roi_percent": flip.roi_percent,
                "max_offer": flip.max_offer,
                "decision": flip.decision,
            }
        )
        rows.append(result)

    if not rows:
        return pd.DataFrame()

    ranked = pd.DataFrame(rows)
    decision_rank = {"BUY": 0, "REVIEW": 1, "PASS": 2}
    ranked["decision_rank"] = ranked["decision"].map(decision_rank).fillna(3)
    return ranked.sort_values(
        by=["decision_rank", "projected_profit", "roi_percent"],
        ascending=[True, False, False],
    ).drop(columns=["decision_rank"]).reset_index(drop=True)
