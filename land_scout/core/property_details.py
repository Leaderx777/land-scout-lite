from dataclasses import dataclass


@dataclass
class PropertyDetails:
    address: str = ""
    bedrooms: int = 0
    bathrooms: float = 0.0
    square_feet: int = 0
    year_built: int = 0
    listing_url: str = ""
    notes: str = ""
