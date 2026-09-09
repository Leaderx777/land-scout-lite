from dataclasses import dataclass
from statistics import median
from typing import Iterable


@dataclass(frozen=True)
class ComparableSale:
    address: str
    sale_price: float
    square_feet: int
    bedrooms: int = 0
    bathrooms: float = 0.0
    distance_miles: float = 0.0

    @property
    def price_per_sqft(self) -> float:
        if self.square_feet <= 0:
            return 0.0
        return self.sale_price / self.square_feet


@dataclass(frozen=True)
class ArvEstimate:
    estimated_arv: float
    median_price_per_sqft: float
    low_arv: float
    high_arv: float
    comp_count: int
    confidence: str
    spread_percent: float


def estimate_arv_from_comps(subject_square_feet: int, comps: Iterable[ComparableSale]) -> ArvEstimate:
    valid = [
        comp
        for comp in comps
        if comp.sale_price > 0 and comp.square_feet > 0 and comp.price_per_sqft > 0
    ]

    if subject_square_feet <= 0:
        raise ValueError("Subject square feet must be greater than zero.")
    if not valid:
        raise ValueError("At least one valid comparable sale is required.")

    prices_per_sqft = sorted(comp.price_per_sqft for comp in valid)
    median_ppsf = median(prices_per_sqft)
    low_ppsf = prices_per_sqft[0]
    high_ppsf = prices_per_sqft[-1]

    estimated_arv = subject_square_feet * median_ppsf
    low_arv = subject_square_feet * low_ppsf
    high_arv = subject_square_feet * high_ppsf

    spread_percent = ((high_ppsf - low_ppsf) / median_ppsf * 100) if median_ppsf else 0.0

    if len(valid) >= 3 and spread_percent <= 20:
        confidence = "HIGH"
    elif len(valid) >= 2 and spread_percent <= 35:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return ArvEstimate(
        estimated_arv=estimated_arv,
        median_price_per_sqft=median_ppsf,
        low_arv=low_arv,
        high_arv=high_arv,
        comp_count=len(valid),
        confidence=confidence,
        spread_percent=spread_percent,
    )
