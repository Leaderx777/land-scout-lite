from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import requests


TRELLISTATE_LISTINGS_URL = "https://trellistate.com/api/v1/listings"


class TrellistateError(RuntimeError):
    """Raised when Trellistate cannot return usable listing data."""


@dataclass(frozen=True)
class TrellistateSearch:
    city: str = ""
    state: str = "IL"
    postal_code: str = ""
    max_price: float = 500000.0
    limit: int = 100

    def validate(self) -> None:
        if not self.city.strip() and not self.postal_code.strip():
            raise ValueError("Enter a city or ZIP code for the commercial listing search.")
        if self.city.strip() and not self.state.strip():
            raise ValueError("State is required when searching by city.")
        if self.max_price <= 0:
            raise ValueError("Maximum price must be greater than zero.")
        if not 1 <= int(self.limit) <= 100:
            raise ValueError("Trellistate limit must be between 1 and 100.")


def _request_params(search: TrellistateSearch) -> dict[str, object]:
    search.validate()
    params: dict[str, object] = {
        "listing_type": "sale",
        "status": "active",
        "max_price": int(search.max_price),
        "limit": int(search.limit),
        "sort": "price_asc",
    }
    if search.postal_code.strip():
        params["postal_code"] = search.postal_code.strip()
    else:
        params["city"] = search.city.strip()
        params["state"] = search.state.strip().upper()
    return params


def _commercial_mask(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool)

    property_type = frame.get("property_type", pd.Series("", index=frame.index)).fillna("").astype(str).str.lower()
    text = (
        frame.get("title", pd.Series("", index=frame.index)).fillna("").astype(str)
        + " "
        + frame.get("description", pd.Series("", index=frame.index)).fillna("").astype(str)
    ).str.lower()

    commercial_terms = (
        "commercial|office|retail|industrial|warehouse|mixed[- ]?use|multifamily|multi[- ]?family|"
        "apartment|hospitality|hotel|motel|restaurant|medical|investment"
    )
    return property_type.str.contains(commercial_terms, regex=True) | text.str.contains(commercial_terms, regex=True)


def trellistate_records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        rows.append(
            {
                "listing_id": record.get("id") or "",
                "title": record.get("title") or "",
                "address": record.get("address") or record.get("formatted_address") or record.get("title") or "",
                "city": record.get("city") or "",
                "state": record.get("state") or "",
                "zip_code": record.get("postal_code") or "",
                "asking_price": record.get("price"),
                "bedrooms": record.get("beds"),
                "bathrooms": record.get("baths"),
                "square_feet": record.get("square_feet"),
                "lot_size": record.get("lot_size"),
                "year_built": record.get("year_built"),
                "property_type": record.get("property_type") or "",
                "listing_url": record.get("url") or "",
                "description": record.get("description") or "",
                "listing_status": record.get("status") or "",
                "listing_type": record.get("listing_type") or "",
                "updated_at": record.get("updated_at"),
                "source": "Trellistate",
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    for column in ("asking_price", "bedrooms", "bathrooms", "square_feet", "lot_size", "year_built"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame.loc[_commercial_mask(frame)].reset_index(drop=True)


def fetch_trellistate_commercial_listings(
    search: TrellistateSearch,
    session=requests,
    timeout: float = 20.0,
) -> pd.DataFrame:
    """Fetch public active commercial listings from Trellistate.

    Trellistate public reads require no API key. Results are filtered locally so
    residential listings returned by a broad city search do not enter the commercial pipeline.
    """
    response = session.get(
        TRELLISTATE_LISTINGS_URL,
        params=_request_params(search),
        headers={"Accept": "application/json"},
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise TrellistateError(f"Trellistate request failed with HTTP {response.status_code}.")

    try:
        payload = response.json()
    except Exception as exc:
        raise TrellistateError("Trellistate returned invalid JSON.") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise TrellistateError("Trellistate returned an unexpected response shape.")

    return trellistate_records_to_dataframe(payload["data"])
