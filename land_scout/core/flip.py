from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FlipAnalysis:
    purchase_price: float
    rehab_cost: float
    arv: float
    buying_costs: float
    holding_costs: float
    selling_costs: float
    contingency: float
    total_cost: float
    projected_profit: float
    roi_pct: float
    profit_margin_pct: float
    max_offer: float
    decision: str


def analyze_flip(
    *,
    purchase_price: float,
    rehab_cost: float,
    arv: float,
    buying_costs: float = 0.0,
    holding_costs: float = 0.0,
    selling_costs: float = 0.0,
    contingency: float = 0.0,
    target_profit: float = 25_000.0,
    max_purchase_price: float = 50_000.0,
    target_rehab_max: float = 20_000.0,
) -> dict:
    """Analyze one residential flip using explicit user-supplied assumptions.

    This intentionally does not estimate ARV or rehab. It evaluates the deal using
    the numbers supplied by the user so the math stays auditable.
    """
    values = {
        "purchase_price": purchase_price,
        "rehab_cost": rehab_cost,
        "arv": arv,
        "buying_costs": buying_costs,
        "holding_costs": holding_costs,
        "selling_costs": selling_costs,
        "contingency": contingency,
        "target_profit": target_profit,
        "max_purchase_price": max_purchase_price,
        "target_rehab_max": target_rehab_max,
    }
    for name, value in values.items():
        if float(value) < 0:
            raise ValueError(f"{name} cannot be negative")

    total_cost = (
        float(purchase_price)
        + float(rehab_cost)
        + float(buying_costs)
        + float(holding_costs)
        + float(selling_costs)
        + float(contingency)
    )
    projected_profit = float(arv) - total_cost
    roi_pct = (projected_profit / total_cost * 100.0) if total_cost else 0.0
    profit_margin_pct = (projected_profit / float(arv) * 100.0) if arv else 0.0

    non_purchase_costs = total_cost - float(purchase_price)
    max_offer = max(0.0, float(arv) - non_purchase_costs - float(target_profit))

    if projected_profit >= target_profit and purchase_price <= max_purchase_price:
        decision = "BUY" if rehab_cost <= target_rehab_max else "REVIEW"
    elif projected_profit >= target_profit * 0.70:
        decision = "REVIEW"
    else:
        decision = "PASS"

    result = FlipAnalysis(
        purchase_price=round(float(purchase_price), 2),
        rehab_cost=round(float(rehab_cost), 2),
        arv=round(float(arv), 2),
        buying_costs=round(float(buying_costs), 2),
        holding_costs=round(float(holding_costs), 2),
        selling_costs=round(float(selling_costs), 2),
        contingency=round(float(contingency), 2),
        total_cost=round(total_cost, 2),
        projected_profit=round(projected_profit, 2),
        roi_pct=round(roi_pct, 2),
        profit_margin_pct=round(profit_margin_pct, 2),
        max_offer=round(max_offer, 2),
        decision=decision,
    )
    return asdict(result)
