from land_scout.core.flip import analyze_flip


def test_analyze_flip_buy_case():
    result = analyze_flip(
        purchase_price=40000,
        rehab_cost=15000,
        holding_cost=4000,
        selling_cost=9000,
        arv=110000,
    )

    assert result.total_cost == 68000
    assert result.projected_profit == 42000
    assert round(result.roi_percent, 1) == 61.8
    assert result.max_offer == 57000
    assert result.decision == "BUY"


def test_analyze_flip_review_case():
    result = analyze_flip(
        purchase_price=55000,
        rehab_cost=15000,
        holding_cost=4000,
        selling_cost=9000,
        arv=110000,
    )

    assert result.decision == "REVIEW"


def test_analyze_flip_pass_case():
    result = analyze_flip(
        purchase_price=60000,
        rehab_cost=30000,
        holding_cost=5000,
        selling_cost=10000,
        arv=110000,
    )

    assert result.decision == "PASS"
