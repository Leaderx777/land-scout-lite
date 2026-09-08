from dataclasses import dataclass


@dataclass
class FlipAnalysis:
    purchase_price: float
    rehab_cost: float
    holding_cost: float
    selling_cost: float
    arv: float
    target_profit: float
    total_cost: float
    projected_profit: float
    roi_percent: float
    max_offer: float
    decision: str


def analyze_flip(
    purchase_price: float,
    rehab_cost: float,
    holding_cost: float,
    selling_cost: float,
    arv: float,
    target_profit: float = 25000.0,
    max_purchase_price: float = 50000.0,
    max_rehab_cost: float = 20000.0,
) -> FlipAnalysis:
    total_cost = purchase_price + rehab_cost + holding_cost + selling_cost
    projected_profit = arv - total_cost
    roi_percent = (projected_profit / total_cost * 100) if total_cost > 0 else 0.0
    max_offer = arv - rehab_cost - holding_cost - selling_cost - target_profit

    rules_met = [
        projected_profit >= target_profit,
        purchase_price <= max_purchase_price,
        rehab_cost <= max_rehab_cost,
    ]
    rules_passed = sum(rules_met)

    if rules_passed == 3:
        decision = "BUY"
    elif rules_passed == 2:
        decision = "REVIEW"
    else:
        decision = "PASS"

    return FlipAnalysis(
        purchase_price=purchase_price,
        rehab_cost=rehab_cost,
        holding_cost=holding_cost,
        selling_cost=selling_cost,
        arv=arv,
        target_profit=target_profit,
        total_cost=total_cost,
        projected_profit=projected_profit,
        roi_percent=roi_percent,
        max_offer=max_offer,
        decision=decision,
    )
