import pandas as pd

from land_scout.core.residential_listings import (
    analyze_ready_residential_listings,
    ingest_residential_listings,
    normalize_residential_listings,
)


def test_normalizes_common_listing_columns():
    source = pd.DataFrame(
        [
            {
                "Street Address": "123 Main St",
                "Price": "$42,500",
                "Beds": 2,
                "Baths": 1,
                "SqFt": "1,050",
                "URL": "https://example.com/123",
            }
        ]
    )

    normalized = normalize_residential_listings(source)

    assert normalized.loc[0, "address"] == "123 Main St"
    assert normalized.loc[0, "asking_price"] == 42500
    assert normalized.loc[0, "square_feet"] == 1050
    assert normalized.loc[0, "listing_url"] == "https://example.com/123"


def test_keeps_one_bedroom_and_oddball_properties():
    source = pd.DataFrame(
        [
            {"address": "1 Tiny Ln", "price": 30000, "beds": 1, "property_type": "cottage"},
            {"address": "2 Duplex Rd", "price": 45000, "beds": 2, "property_type": "duplex"},
        ]
    )

    result = ingest_residential_listings(source)

    assert len(result.listings) == 2
    assert set(result.listings["bedrooms"].tolist()) == {1, 2}
    assert set(result.listings["property_type"].tolist()) == {"cottage", "duplex"}


def test_can_exclude_land_while_keeping_residential_oddballs():
    source = pd.DataFrame(
        [
            {"address": "10 House St", "price": 30000, "property_type": "Single Family"},
            {"address": "20 Duplex Rd", "price": 45000, "property_type": "Duplex"},
            {"address": "30 Lot Ln", "price": 7000, "property_type": "Land"},
            {"address": "40 Acre Rd", "price": 9000, "property_type": "Vacant Land"},
            {"address": "50 Parcel Ave", "price": 10000, "property_type": "Residential Lot"},
        ]
    )

    result = ingest_residential_listings(source, exclude_land=True)

    assert result.listings["address"].tolist() == ["10 House St", "20 Duplex Rd"]
    assert set(result.rejected["address"].tolist()) == {"30 Lot Ln", "40 Acre Rd", "50 Parcel Ave"}


def test_rejects_missing_address_invalid_price_and_over_budget():
    source = pd.DataFrame(
        [
            {"address": "Good", "price": 50000},
            {"address": "Too Much", "price": 50001},
            {"address": "", "price": 25000},
            {"address": "No Price", "price": ""},
        ]
    )

    result = ingest_residential_listings(source)

    assert result.listings["address"].tolist() == ["Good"]
    assert len(result.rejected) == 3


def test_marks_listing_status_by_available_estimates():
    source = pd.DataFrame(
        [
            {"address": "Needs ARV", "price": 30000},
            {"address": "Needs Rehab", "price": 32000, "arv": 100000},
            {"address": "Ready", "price": 35000, "arv": 110000, "rehab": 15000},
        ]
    )

    result = ingest_residential_listings(source)
    statuses = dict(zip(result.listings["address"], result.listings["screening_status"]))

    assert statuses["Needs ARV"] == "NEEDS_ARV"
    assert statuses["Needs Rehab"] == "NEEDS_REHAB"
    assert statuses["Ready"] == "READY_TO_ANALYZE"


def test_analyzes_and_ranks_ready_listings():
    source = pd.DataFrame(
        [
            {"address": "Deal A", "price": 40000, "rehab": 15000, "arv": 110000},
            {"address": "Deal B", "price": 49000, "rehab": 20000, "arv": 90000},
            {"address": "Incomplete", "price": 30000},
        ]
    )

    ingested = ingest_residential_listings(source).listings
    ranked = analyze_ready_residential_listings(ingested)

    assert ranked["address"].tolist()[0] == "Deal A"
    assert "projected_profit" in ranked.columns
    assert "roi_percent" in ranked.columns
    assert "max_offer" in ranked.columns
    assert "decision" in ranked.columns
    assert "Incomplete" not in ranked["address"].tolist()
