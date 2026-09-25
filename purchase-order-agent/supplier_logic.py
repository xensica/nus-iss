# Simulated suppliers for Bottled Coffee.
# All prices are in SGD cents to avoid rounding errors.

SUPPLIERS = [
    {
        "name": "Supplier A",
        "unit_price_cents": 200,
        "delivery_fee_cents": 1500,
        "delivery_days": 2,
        "available_units": 500,
        "minimum_order": 50,
        "quality_score": 95,
        "on_time_percent": 98,
        "approved": True,
    },
    {
        "name": "Supplier B",
        "unit_price_cents": 160,
        "delivery_fee_cents": 1000,
        "delivery_days": 7,
        "available_units": 1000,
        "minimum_order": 100,
        "quality_score": 85,
        "on_time_percent": 90,
        "approved": True,
    },
    {
        "name": "Supplier C",
        "unit_price_cents": 180,
        "delivery_fee_cents": 1200,
        "delivery_days": 4,
        "available_units": 300,
        "minimum_order": 50,
        "quality_score": 90,
        "on_time_percent": 95,
        "approved": True,
    },
]


def compare_suppliers(quantity, required_within_days):
    for name, value in {
        "quantity": quantity,
        "required_within_days": required_within_days,
    }.items():
        if type(value) is not int or not 0 <= value <= 1_000_000:
            raise ValueError(f"{name} must be a non-negative whole number.")

    if quantity == 0:
        return {
            "status": "no_purchase_needed",
            "recommended_supplier": None,
            "eligible": [],
            "excluded": [],
        }

    # Fixed business rules for this prototype.
    minimum_quality = 85
    minimum_reliability = 90

    eligible = []
    excluded = []

    for supplier in SUPPLIERS:
        reasons = []

        if not supplier["approved"]:
            reasons.append("Supplier is not approved.")

        if supplier["quality_score"] < minimum_quality:
            reasons.append("Quality score is below the minimum.")

        if supplier["on_time_percent"] < minimum_reliability:
            reasons.append("Delivery reliability is below the minimum.")

        if supplier["delivery_days"] > required_within_days:
            reasons.append("Estimated delivery misses the deadline.")

        if supplier["available_units"] < quantity:
            reasons.append("Insufficient stock for the full order.")

        if quantity < supplier["minimum_order"]:
            reasons.append("Requested quantity is below the minimum order.")

        if reasons:
            excluded.append({
                "supplier": supplier["name"],
                "reasons": reasons,
            })
            continue

        total_cents = (
            quantity * supplier["unit_price_cents"]
            + supplier["delivery_fee_cents"]
        )

        eligible.append({
            "supplier": supplier["name"],
            "quantity": quantity,
            "total_cost_sgd": f"{total_cents / 100:.2f}",
            "total_cost_cents": total_cents,
            "delivery_days": supplier["delivery_days"],
            "quality_score": supplier["quality_score"],
            "on_time_percent": supplier["on_time_percent"],
        })

    eligible.sort(
        key=lambda item: (
            item["total_cost_cents"],
            item["delivery_days"],
        )
    )

    return {
        "product": "Bottled Coffee",
        "data_source": "simulated",
        "status": "options_found" if eligible else "no_eligible_supplier",
        "recommended_supplier": eligible[0]["supplier"] if eligible else None,
        "eligible": eligible,
        "excluded": excluded,
        "note": "Delivery times are estimates, not guarantees.",
    }


if __name__ == "__main__":
    import json

    result = compare_suppliers(quantity=200, required_within_days=5)
    print(json.dumps(result, indent=2))