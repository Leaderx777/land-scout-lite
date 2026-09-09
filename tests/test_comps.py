import pytest

from land_scout.core.comps import ComparableSale, estimate_arv_from_comps


def test_estimate_arv_uses_median_price_per_square_foot():
    comps = [
        ComparableSale("A", 100000, 1000),
        ComparableSale("B", 126000, 1200),
        ComparableSale("C", 110000, 1000),
    ]

    result = estimate_arv_from_comps(1200, comps)

    assert result.median_price_per_sqft == pytest.approx(105.0)
    assert result.estimated_arv == pytest.approx(126000.0)
    assert result.comp_count == 3


def test_confidence_is_high_for_three_tight_comps():
    comps = [
        ComparableSale("A", 100000, 1000),
        ComparableSale("B", 103000, 1000),
        ComparableSale("C", 108000, 1000),
    ]

    result = estimate_arv_from_comps(1000, comps)

    assert result.confidence == "HIGH"
    assert result.low_arv == pytest.approx(100000.0)
    assert result.high_arv == pytest.approx(108000.0)


def test_confidence_is_low_for_one_comp():
    result = estimate_arv_from_comps(
        1000,
        [ComparableSale("A", 100000, 1000)],
    )

    assert result.confidence == "LOW"


def test_invalid_subject_size_raises():
    with pytest.raises(ValueError):
        estimate_arv_from_comps(0, [ComparableSale("A", 100000, 1000)])


def test_no_valid_comps_raises():
    with pytest.raises(ValueError):
        estimate_arv_from_comps(1000, [ComparableSale("A", 0, 1000)])
