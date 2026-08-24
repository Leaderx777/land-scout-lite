"""Central Illinois target-market configuration for Land Scout Lite."""

CENTRAL_ILLINOIS_COUNTIES = [
    "Peoria",
    "Tazewell",
    "Woodford",
    "Fulton",
    "Knox",
    "McLean",
    "Marshall",
    "Stark",
    "Mason",
    "Logan",
]

MARKET_CENTER = "Peoria, IL"


def is_target_county(county: str) -> bool:
    """Return True when a county is in the initial Central Illinois market."""
    normalized = county.strip().lower().removesuffix(" county")
    return normalized in {name.lower() for name in CENTRAL_ILLINOIS_COUNTIES}
