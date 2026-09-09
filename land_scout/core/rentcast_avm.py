from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests

from land_scout.core.rentcast_source import RentCastError


RENTCAST_VALUE_ESTIMATE_URL = "https://api.rentcast.io/v1/avm/value"


@dataclass(frozen=True)
class RentCastAvmRequest:
    address: str
    property_type: str = ""
    bedrooms: float | None = None
    bathrooms: float | None = None
    square_feet: float | None = None
    max_radius: float = 5.0
    days_old: int = 270
    comp_count: int = 20

    def validate(self) -> None:
        if not self.address.strip():
            raise ValueError("A full property address is required for ARV lookup.")
        if self.max_radius <= 0:
            raise ValueError("Comparable radius must be greater than zero.")
        if self.days_old <= 0:
            raise ValueError("Comparable lookback must be greater than zero.")
        if not 1 <= int(self.comp_count) <= 50:
            raise ValueError("Comparable count must be between 1 and 50.")


@dataclass(frozen=True)
class RentCastAvmResult:
    estimated_value: float
    range_low: float
    range_high: float
    subject_property: dict[str, Any]
    comparables: pd.DataFrame

    @property
    def comp_count(self) -> int:
        return len(self.comparables)

    @property
    def range_width_percent(self) -> float:
        if self.estimated_value <= 0:
            return 0.0
        return (self.range_high - self.range_low) / self.estimated_value * 100.0

    @property
    def confidence_label(self) -> str:
        # This is an app-side usability label based on estimate-range width,
        # not a claim about RentCast's statistical confidence level.
        width = self.range_width_percent
        if self.comp_count >= 5 and width <= 20:
            return "HIGH"
        if self.comp_count >= 3 and width <= 35:
            return "MEDIUM"
        return "LOW"


def _request_params(request: RentCastAvmRequest) -> dict[str, object]:
    request.validate()
    params: dict[str, object] = {
        "address": request.address.strip(),
        "maxRadius": float(request.max_radius),
        "daysOld": int(request.days_old),
        "compCount": int(request.comp_count),
    }
    if request.property_type.strip():
        params["propertyType"] = request.property_type.strip()
    if request.bedrooms is not None and float(request.bedrooms) >= 0:
        params["bedrooms"] = float(request.bedrooms)
    if request.bathrooms is not None and float(request.bathrooms) >= 0:
        params["bathrooms"] = float(request.bathrooms)
    if request.square_feet is not None and float(request.square_feet) > 0:
        params["squareFootage"] = int(float(request.square_feet))
    return params


def rentcast_comps_to_dataframe(records: list[dict] | None) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        rows.append(
            {
                "address": record.get("formattedAddress") or record.get("addressLine1") or "",
                "price": record.get("price"),
                "status": record.get("status") or "",
                "listing_type": record.get("listingType") or "",
                "bedrooms": record.get("bedrooms"),
                "bathrooms": record.get("bathrooms"),
                "square_feet": record.get("squareFootage"),
                "year_built": record.get("yearBuilt"),
                "distance_miles": record.get("distance"),
                "days_old": record.get("daysOld"),
                "correlation": record.get("correlation"),
                "listed_date": record.get("listedDate"),
                "removed_date": record.get("removedDate"),
                "last_seen_date": record.get("lastSeenDate"),
                "days_on_market": record.get("daysOnMarket"),
            }
        )
    return pd.DataFrame(rows)


def parse_rentcast_avm_payload(payload: dict[str, Any]) -> RentCastAvmResult:
    if not isinstance(payload, dict):
        raise RentCastError("RentCast returned an unexpected valuation response shape.")

    price = payload.get("price")
    low = payload.get("priceRangeLow")
    high = payload.get("priceRangeHigh")
    try:
        price_value = float(price)
        low_value = float(low)
        high_value = float(high)
    except (TypeError, ValueError) as exc:
        raise RentCastError("RentCast valuation response is missing a usable value range.") from exc

    if price_value <= 0 or low_value <= 0 or high_value <= 0:
        raise RentCastError("RentCast valuation response contains non-positive values.")

    subject = payload.get("subjectProperty")
    if not isinstance(subject, dict):
        subject = {}

    comparables = rentcast_comps_to_dataframe(payload.get("comparables"))
    return RentCastAvmResult(
        estimated_value=price_value,
        range_low=low_value,
        range_high=high_value,
        subject_property=subject,
        comparables=comparables,
    )


def fetch_rentcast_value_estimate(
    api_key: str,
    request: RentCastAvmRequest,
    session=requests,
    timeout: float = 20.0,
) -> RentCastAvmResult:
    """Fetch RentCast's value estimate and sale comparables for one property."""
    if not api_key or not api_key.strip():
        raise ValueError("A RentCast API key is required.")

    response = session.get(
        RENTCAST_VALUE_ESTIMATE_URL,
        params=_request_params(request),
        headers={"Accept": "application/json", "X-Api-Key": api_key.strip()},
        timeout=timeout,
    )
    if response.status_code == 401:
        raise RentCastError("RentCast rejected the API key.")
    if response.status_code >= 400:
        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = str(body.get("message") or body.get("error") or "").strip()
        except Exception:
            detail = ""
        suffix = f": {detail}" if detail else "."
        raise RentCastError(f"RentCast valuation request failed with HTTP {response.status_code}{suffix}")

    try:
        payload = response.json()
    except Exception as exc:
        raise RentCastError("RentCast returned invalid JSON for the valuation request.") from exc

    return parse_rentcast_avm_payload(payload)
