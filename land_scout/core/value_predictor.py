import os

import requests

DEFAULT_URL = "http://127.0.0.1:8000"


def estimate_land_value(
    acres: float,
    distance_to_city_miles: float,
    road_frontage_ft: float,
    zoning_score: int,
    utilities: int,
    api_url: str | None = None,
) -> dict:
    base_url = (api_url or os.getenv("LAND_VALUE_API_URL") or DEFAULT_URL).rstrip("/")
    payload = {
        "acres": acres,
        "distance_to_city_miles": distance_to_city_miles,
        "road_frontage_ft": road_frontage_ft,
        "zoning_score": zoning_score,
        "utilities": utilities,
    }
    response = requests.post(f"{base_url}/predict", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()
