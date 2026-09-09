import pytest

from land_scout.core.rentcast_avm import (
    RentCastAvmRequest,
    fetch_rentcast_comparables,
    fetch_rentcast_value_estimate,
    parse_rentcast_avm_payload,
    parse_rentcast_comparables_payload,
)
from land_scout.core.rentcast_source import RentCastError


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
        self.last_url = None
        self.last_params = None
        self.last_headers = None

    def get(self, url, params=None, headers=None, timeout=None):
        self.last_url = url
        self.last_params = params
        self.last_headers = headers
        return self.response


def sample_payload():
    return {
        "price": 110000,
        "priceRangeLow": 98000,
        "priceRangeHigh": 122000,
        "subjectProperty": {
            "formattedAddress": "123 Main St, Galesburg, IL 61401",
            "bedrooms": 3,
            "bathrooms": 1,
            "squareFootage": 1200,
        },
        "comparables": [
            {
                "formattedAddress": "120 Main St, Galesburg, IL 61401",
                "price": 112000,
                "status": "Inactive",
                "propertyType": "Single Family",
                "listingType": "Standard",
                "bedrooms": 3,
                "bathrooms": 1,
                "squareFootage": 1180,
                "lotSize": 8500,
                "distance": 0.2,
                "daysOld": 45,
                "correlation": 0.94,
            },
            {
                "formattedAddress": "222 Oak St, Galesburg, IL 61401",
                "price": 106000,
                "status": "Inactive",
                "propertyType": "Single Family",
                "listingType": "Standard",
                "bedrooms": 3,
                "bathrooms": 1,
                "squareFootage": 1210,
                "lotSize": 9000,
                "distance": 0.5,
                "daysOld": 80,
                "correlation": 0.90,
            },
            {
                "formattedAddress": "14 Pine St, Galesburg, IL 61401",
                "price": 115000,
                "status": "Inactive",
                "propertyType": "Single Family",
                "listingType": "Standard",
                "bedrooms": 3,
                "bathrooms": 1.5,
                "squareFootage": 1250,
                "lotSize": 9200,
                "distance": 0.8,
                "daysOld": 120,
                "correlation": 0.87,
            },
        ],
    }


def test_parse_avm_payload_returns_value_range_and_comps():
    result = parse_rentcast_avm_payload(sample_payload())
    assert result.estimated_value == 110000
    assert result.range_low == 98000
    assert result.range_high == 122000
    assert result.comp_count == 3
    assert result.comparables.iloc[0]["distance_miles"] == 0.2
    assert result.comparables.iloc[0]["lot_size"] == 8500
    assert result.comparables.iloc[0]["property_type"] == "Single Family"
    assert result.confidence_label == "MEDIUM"


def test_fetch_avm_sends_subject_attributes_and_comp_settings():
    session = FakeSession(FakeResponse(payload=sample_payload()))
    request = RentCastAvmRequest(
        address="123 Main St, Galesburg, IL 61401",
        property_type="Single Family",
        bedrooms=3,
        bathrooms=1,
        square_feet=1200,
        max_radius=3,
        days_old=180,
        comp_count=10,
    )
    fetch_rentcast_value_estimate("abc123", request, session=session)
    assert session.last_params["address"] == "123 Main St, Galesburg, IL 61401"
    assert session.last_params["propertyType"] == "Single Family"
    assert session.last_params["bedrooms"] == 3.0
    assert session.last_params["bathrooms"] == 1.0
    assert session.last_params["squareFootage"] == 1200
    assert session.last_params["maxRadius"] == 3.0
    assert session.last_params["daysOld"] == 180
    assert session.last_params["compCount"] == 10
    assert session.last_headers["X-Api-Key"] == "abc123"


def test_avm_requires_address():
    with pytest.raises(ValueError, match="full property address"):
        RentCastAvmRequest(address="").validate()


def test_avm_rejects_comp_count_outside_api_range():
    with pytest.raises(ValueError, match="between 5 and 25"):
        RentCastAvmRequest(address="123 Main St", comp_count=4).validate()


def test_avm_rejects_bad_api_key():
    session = FakeSession(FakeResponse(status_code=401, payload={}))
    with pytest.raises(RentCastError, match="rejected the API key"):
        fetch_rentcast_value_estimate(
            "bad",
            RentCastAvmRequest(address="123 Main St, Galesburg, IL 61401"),
            session=session,
        )


def test_avm_rejects_missing_value_range():
    with pytest.raises(RentCastError, match="missing a usable value range"):
        parse_rentcast_avm_payload({"price": 100000, "comparables": []})


def test_comparables_can_be_parsed_when_avm_values_are_zero():
    payload = sample_payload()
    payload["price"] = 0
    payload["priceRangeLow"] = 0
    payload["priceRangeHigh"] = 0
    comps = parse_rentcast_comparables_payload(payload)
    assert len(comps) == 3
    assert comps.iloc[0]["price"] == 112000


def test_fetch_comparables_does_not_require_positive_avm():
    payload = sample_payload()
    payload["price"] = 0
    payload["priceRangeLow"] = 0
    payload["priceRangeHigh"] = 0
    session = FakeSession(FakeResponse(payload=payload))
    comps = fetch_rentcast_comparables(
        "abc123",
        RentCastAvmRequest(address="123 Main St, Galesburg, IL 61401"),
        session=session,
    )
    assert len(comps) == 3
