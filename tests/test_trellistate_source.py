import pandas as pd
import pytest

from land_scout.core.trellistate_source import (
    TRELLISTATE_LISTINGS_URL,
    TrellistateError,
    TrellistateSearch,
    fetch_trellistate_commercial_listings,
    trellistate_records_to_dataframe,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return self.response


def test_commercial_records_are_kept_and_residential_filtered():
    frame = trellistate_records_to_dataframe(
        [
            {
                "id": "c1",
                "title": "Downtown Mixed-Use Building",
                "listing_type": "sale",
                "property_type": "commercial",
                "price": 150000,
                "city": "Galesburg",
                "state": "IL",
                "postal_code": "61401",
                "square_feet": 5000,
                "status": "active",
            },
            {
                "id": "r1",
                "title": "Three Bedroom House",
                "listing_type": "sale",
                "property_type": "single_family",
                "price": 90000,
                "city": "Galesburg",
                "state": "IL",
                "status": "active",
            },
        ]
    )
    assert len(frame) == 1
    assert frame.loc[0, "listing_id"] == "c1"
    assert frame.loc[0, "source"] == "Trellistate"


def test_search_builds_public_sale_query_without_api_key():
    session = FakeSession(FakeResponse(payload={"data": [], "next_cursor": None}))
    result = fetch_trellistate_commercial_listings(
        TrellistateSearch(city="Galesburg", state="IL", max_price=500000, limit=25),
        session=session,
    )
    assert isinstance(result, pd.DataFrame)
    call = session.calls[0]
    assert call["url"] == TRELLISTATE_LISTINGS_URL
    assert call["params"]["city"] == "Galesburg"
    assert call["params"]["state"] == "IL"
    assert call["params"]["listing_type"] == "sale"
    assert call["params"]["status"] == "active"
    assert call["params"]["max_price"] == 500000
    assert "Authorization" not in call["headers"]


def test_zip_search_uses_postal_code():
    session = FakeSession(FakeResponse(payload={"data": []}))
    fetch_trellistate_commercial_listings(
        TrellistateSearch(city="Ignored", state="IL", postal_code="61401"),
        session=session,
    )
    params = session.calls[0]["params"]
    assert params["postal_code"] == "61401"
    assert "city" not in params


def test_requires_location():
    with pytest.raises(ValueError):
        TrellistateSearch().validate()


def test_http_error_is_clear():
    session = FakeSession(FakeResponse(status_code=500, payload={}))
    with pytest.raises(TrellistateError, match="HTTP 500"):
        fetch_trellistate_commercial_listings(
            TrellistateSearch(city="Galesburg", state="IL"),
            session=session,
        )


def test_bad_payload_is_rejected():
    session = FakeSession(FakeResponse(payload=[]))
    with pytest.raises(TrellistateError, match="unexpected response shape"):
        fetch_trellistate_commercial_listings(
            TrellistateSearch(city="Galesburg", state="IL"),
            session=session,
        )
