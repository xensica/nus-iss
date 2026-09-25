from supplier_logic import SUPPLIERS


def optimise_order_split(
    total_quantity,
    urgent_quantity,
    urgent_days,
    final_days,
):
    inputs = [total_quantity, urgent_quantity, urgent_days, final_days]

    if any(type(value) is not int or value < 0 for value in inputs):
        raise ValueError("All inputs must be non-negative whole numbers.")

    if urgent_quantity > total_quantity:
        raise ValueError("Urgent quantity cannot exceed total quantity.")

    if urgent_days > final_days:
        raise ValueError("Urgent deadline cannot be after the final deadline.")

    # Keep exhaustive comparison small for our first prototype.
    if total_quantity > 1000:
        raise ValueError("This prototype supports up to 1,000 units per plan.")

    if total_quantity == 0:
        return {"status": "no_purchase_needed", "orders": []}

    if len(SUPPLIERS) != 3:
        raise ValueError("This prototype expects exactly three suppliers.")

    def valid_allocation(supplier, quantity):
        if quantity == 0:
            return True

        return (
            supplier["approved"]
            and supplier["quality_score"] >= 85
            and supplier["on_time_percent"] >= 90
            and supplier["delivery_days"] <= final_days
            and supplier["minimum_order"] <= quantity
            <= supplier["available_units"]
        )

    def allocation_cost(supplier, quantity):
        if quantity == 0:
            return 0

        return (
            quantity * supplier["unit_price_cents"]
            + supplier["delivery_fee_cents"]
        )

    best = None
    cheapest_single_cents = None

    # Choose quantities for A and B; C receives the remainder.
    for quantity_a in range(total_quantity + 1):
        if not valid_allocation(SUPPLIERS[0], quantity_a):
            continue

        for quantity_b in range(total_quantity - quantity_a + 1):
            quantity_c = total_quantity - quantity_a - quantity_b
            quantities = [quantity_a, quantity_b, quantity_c]

            if not all(
                valid_allocation(supplier, quantity)
                for supplier, quantity in zip(SUPPLIERS, quantities)
            ):
                continue

            arriving_early = sum(
                quantity
                for supplier, quantity in zip(SUPPLIERS, quantities)
                if supplier["delivery_days"] <= urgent_days
            )

            if arriving_early < urgent_quantity:
                continue

            total_cents = sum(
                allocation_cost(supplier, quantity)
                for supplier, quantity in zip(SUPPLIERS, quantities)
            )

            order_count = sum(quantity > 0 for quantity in quantities)

            if order_count == 1:
                if (
                    cheapest_single_cents is None
                    or total_cents < cheapest_single_cents
                ):
                    cheapest_single_cents = total_cents

            # Prefer fewer orders when total costs are equal.
            ranking = (total_cents, order_count)

            if best is None or ranking < best["ranking"]:
                best = {
                    "ranking": ranking,
                    "quantities": quantities,
                    "total_cents": total_cents,
                }

    if best is None:
        return {
            "status": "no_feasible_plan",
            "reason": (
                "No allocation meets both deadlines, stock availability, "
                "minimum orders and quality/reliability requirements."
            ),
        }

    orders = []

    for supplier, quantity in zip(SUPPLIERS, best["quantities"]):
        if quantity == 0:
            continue

        cost_cents = allocation_cost(supplier, quantity)

        orders.append({
            "supplier": supplier["name"],
            "quantity": quantity,
            "estimated_delivery_days": supplier["delivery_days"],
            "cost_sgd": f"{cost_cents / 100:.2f}",
            "quality_score": supplier["quality_score"],
            "on_time_percent": supplier["on_time_percent"],
        })

    savings_cents = (
        cheapest_single_cents - best["total_cents"]
        if cheapest_single_cents is not None
        else None
    )

    return {
        "status": "plan_found",
        "product": "Bottled Coffee",
        "data_source": "simulated",
        "total_quantity": total_quantity,
        "urgent_quantity": urgent_quantity,
        "urgent_deadline_days": urgent_days,
        "final_deadline_days": final_days,
        "orders": orders,
        "total_cost_sgd": f"{best['total_cents'] / 100:.2f}",
        "cheapest_feasible_single_supplier_cost_sgd": (
            f"{cheapest_single_cents / 100:.2f}"
            if cheapest_single_cents is not None else None
        ),
        "savings_vs_single_supplier_sgd": (
            f"{savings_cents / 100:.2f}"
            if savings_cents is not None else None
        ),
        "note": (
            "Delivery times are estimates. Costs include one delivery fee "
            "per supplier, excluding tax. No orders have been placed."
        ),
    }


if __name__ == "__main__":
    import json

    result = optimise_order_split(
        total_quantity=200,
        urgent_quantity=50,
        urgent_days=2,
        final_days=8,
    )
    print(json.dumps(result, indent=2))