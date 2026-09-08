import pytest

from land_scout.core.flip import analyze_flip


def test_analyze_flip_buy_case():
    result = analyze_flip(
        purchase_price=40_000,
        rehab_cost=15_000,
        arv=110_000,
        buying_costs=2_000,
        holding_costs=3_000,
        selling_costs=7_000,
        contingency=3_000,
    )

    assert result["total_cost"] == 70_000
    assert result["projected_profit"] == 40_000
    assert result["max_offer"] == 55_000
    assert result["decision"] == "BUY"


def test_analyze_flip_pass_case():
    result = analyze_flip(
        purchase_price=50_000,
        rehab_cost=20_000,
        arv=90_000,
        buying_costs=2_000,
        holding_costs=3_000,
        selling_costs=6_000,
    )

    assert result["projected_profit"] == 9_000
    assert result["decision"] == "PASS"


def test_negative_values_rejected():
    with pytest.raises(ValueError):
        analyze_flip(purchase_price=-1, rehab_cost=0, arv=100_000)
