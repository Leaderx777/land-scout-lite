import pandas as pd
import pytest

from land_scout.core.rentcast_source import (
    RENTCAST_SALE_LISTINGS_URL,
    RentCastError,
    RentCastSearch,
    fetch_rentcast_sale_listings,
    rentcast_records_to_dataframe,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = [] if payload is None else payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(
            {"url": url, "params": params, "headers": headers, "timeout": timeout}
        )
        return self.response


def sample_record():
    return {
        "id": "123-Main-St,-Galesburg,-IL-61401",
        "formattedAddress": "123 Main St, Galesburg, IL 61401",
        "city": "Galesburg",
        "state": "IL",
        "zipCode": "61401",
        "county": "Knox",
        "latitude": 40.9478,
        "longitude": -90.3712,
        "propertyType": "Single Family",
        "bedrooms": 2,
        "bathrooms": 1,
        "squareFootage": 950,
        "lotSize": 8712,
        "yearBuilt": 1940,
        "status": "Active",
        "price": 42000,
        "listingType": "Standard",
        "daysOnMarket": 18,
        "mlsName": "Test MLS",
        "mlsNumber": "ABC123",
    }


def test_records_convert_to_property_scout_schema():
    frame = rentcast_records_to_dataframe([sample_record()])
    assert frame.loc[0, "address"] == "123 Main St, Galesburg, IL 61401"
    assert frame.loc[0, "asking_price"] == 42000
    assert frame.loc[0, "square_feet"] == 950
    assert frame.loc[0, "lot_size"] == 8712
    assert frame.loc[0, "property_type"] == "Single Family"
    assert frame.loc[0, "source"] == "RentCast"
    assert frame.loc[0, "listing_id"].startswith("123-Main")


def test_fetch_builds_active_price_filtered_city_query():
    session = FakeSession(FakeResponse(payload=[sample_record()]))
    result = fetch_rentcast_sale_listings(
        "secret",
        RentCastSearch(city="Galesburg", state="IL", max_price=50000, limit=25),
        session=session,
    )
    assert isinstance(result, pd.DataFrame)
    call = session.calls[0]
    assert call["url"] == RENTCAST_SALE_LISTINGS_URL
    assert call["headers"]["X-Api-Key"] == "secret"
    assert call["params"]["status"] == "Active"
    assert call["params"]["price"] == "1:50000"
    assert call["params"]["city"] == "Galesburg"
    assert call["params"]["state"] == "IL"
    assert call["params"]["limit"] == 25


def test_property_types_are_sent_as_rentcast_multi_value_filter():
    session = FakeSession(FakeResponse(payload=[]))
    fetch_rentcast_sale_listings(
        "secret",
        RentCastSearch(
            city="Canton",
            state="IL",
            property_types=("Single Family", "Multi-Family"),
        ),
        session=session,
    )
    assert session.calls[0]["params"]["propertyType"] == "Single Family|Multi-Family"


def test_land_mode_can_query_land_only():
    session = FakeSession(FakeResponse(payload=[]))
    fetch_rentcast_sale_listings(
        "secret",
        RentCastSearch(city="Galesburg", state="IL", property_types=("Land",)),
        session=session,
    )
    assert session.calls[0]["params"]["propertyType"] == "Land"


def test_zip_search_uses_zip_instead_of_city():
    session = FakeSession(FakeResponse(payload=[]))
    fetch_rentcast_sale_listings(
        "secret",
        RentCastSearch(city="Ignored", state="IL", zip_code="61401"),
        session=session,
    )
    params = session.calls[0]["params"]
    assert params["zipCode"] == "61401"
    assert "city" not in params


def test_search_requires_location():
    with pytest.raises(ValueError):
        RentCastSearch().validate()


def test_search_rejects_unsupported_property_type():
    with pytest.raises(ValueError, match="Unsupported RentCast property type"):
        RentCastSearch(city="Galesburg", property_types=("Retail",)).validate()


def test_auth_error_is_clear():
    session = FakeSession(FakeResponse(status_code=401, payload={}))
    with pytest.raises(RentCastError, match="API key"):
        fetch_rentcast_sale_listings(
            "bad-key",
            RentCastSearch(city="Galesburg", state="IL"),
            session=session,
        )
