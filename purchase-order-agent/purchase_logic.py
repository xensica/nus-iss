import math


def calculate_purchase_quantity(
    expected_demand,
    safety_stock,
    current_stock,
    incoming_stock,
):
    values = [expected_demand, safety_stock, current_stock, incoming_stock]

    if any(value < 0 for value in values):
        raise ValueError("Stock and demand values cannot be negative.")

    quantity = expected_demand + safety_stock - current_stock - incoming_stock

    # Round up to whole units. Never recommend a negative order.
    return max(0, math.ceil(quantity))


if __name__ == "__main__":
    product = "Bottled Coffee"

    # All quantities refer to the same planning period: next week.
    expected_demand = 350
    safety_stock = 20
    current_stock = 100

    # Only include confirmed stock arriving before it is needed.
    incoming_stock = 50

    quantity = calculate_purchase_quantity(
        expected_demand,
        safety_stock,
        current_stock,
        incoming_stock,
    )

    print(f"Product: {product}")
    print(f"Expected demand: {expected_demand} units")
    print(f"Safety stock: {safety_stock} units")
    print(f"Current stock: {current_stock} units")
    print(f"Incoming stock: {incoming_stock} units")
    print(f"Recommended purchase: {quantity} units")