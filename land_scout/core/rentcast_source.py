from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import requests


RENTCAST_SALE_LISTINGS_URL = "https://api.rentcast.io/v1/listings/sale"


class RentCastError(RuntimeError):
    """Raised when RentCast cannot return usable listing data."""


@dataclass(frozen=True)
class RentCastSearch:
    city: str = ""
    state: str = "IL"
    zip_code: str = ""
    max_price: float = 50000.0
    limit: int = 50
    offset: int = 0
    days_old: int | None = None

    def validate(self) -> None:
        if not self.city.strip() and not self.zip_code.strip():
            raise ValueError("Enter a city or ZIP code for the listing search.")
        if self.city.strip() and not self.state.strip():
            raise ValueError("State is required when searching by city.")
        if self.max_price <= 0:
            raise ValueError("Maximum price must be greater than zero.")
        if not 1 <= int(self.limit) <= 500:
            raise ValueError("RentCast limit must be between 1 and 500.")
        if int(self.offset) < 0:
            raise ValueError("RentCast offset cannot be negative.")


def _request_params(search: RentCastSearch) -> dict[str, object]:
    search.validate()
    params: dict[str, object] = {
        "status": "Active",
        "price": f"1:{int(search.max_price)}",
        "limit": int(search.limit),
        "offset": int(search.offset),
    }
    if search.zip_code.strip():
        params["zipCode"] = search.zip_code.strip()
    else:
        params["city"] = search.city.strip()
        params["state"] = search.state.strip().upper()
    if search.days_old is not None and int(search.days_old) > 0:
        params["daysOld"] = f"1:{int(search.days_old)}"
    return params


def rentcast_records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    """Convert RentCast sale-listing records into Property Scout's intake schema."""
    rows: list[dict[str, object]] = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        mls_name = record.get("mlsName") or ""
        mls_number = record.get("mlsNumber") or ""
        listing_type = record.get("listingType") or ""
        description_bits = [str(v) for v in (listing_type, mls_name, mls_number) if v]
        rows.append(
            {
                "address": record.get("formattedAddress") or record.get("addressLine1") or "",
                "city": record.get("city") or "",
                "state": record.get("state") or "",
                "zip_code": record.get("zipCode") or "",
                "asking_price": record.get("price"),
                "bedrooms": record.get("bedrooms"),
                "bathrooms": record.get("bathrooms"),
                "square_feet": record.get("squareFootage"),
                "year_built": record.get("yearBuilt"),
                "property_type": record.get("propertyType") or "",
                "listing_url": "",
                "description": " | ".join(description_bits),
                "rehab_estimate": None,
                "arv_estimate": None,
                "listing_id": record.get("id") or "",
                "county": record.get("county") or "",
                "listing_status": record.get("status") or "",
                "listing_type": listing_type,
                "days_on_market": record.get("daysOnMarket"),
                "latitude": record.get("latitude"),
                "longitude": record.get("longitude"),
                "source": "RentCast",
            }
        )
    return pd.DataFrame(rows)


def fetch_rentcast_sale_listings(
    api_key: str,
    search: RentCastSearch,
    session=requests,
    timeout: float = 20.0,
) -> pd.DataFrame:
    """Fetch active sale listings from RentCast and return a normalized source DataFrame."""
    if not api_key or not api_key.strip():
        raise ValueError("A RentCast API key is required.")

    response = session.get(
        RENTCAST_SALE_LISTINGS_URL,
        params=_request_params(search),
        headers={"Accept": "application/json", "X-Api-Key": api_key.strip()},
        timeout=timeout,
    )
    if response.status_code == 401:
        raise RentCastError("RentCast rejected the API key.")
    if response.status_code >= 400:
        raise RentCastError(f"RentCast request failed with HTTP {response.status_code}.")

    try:
        payload = response.json()
    except Exception as exc:  # requests may raise different JSON errors by version
        raise RentCastError("RentCast returned an invalid JSON response.") from exc

    if not isinstance(payload, list):
        raise RentCastError("RentCast returned an unexpected response shape.")
    return rentcast_records_to_dataframe(payload)
