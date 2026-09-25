from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4


def create_draft_pos(plan):
    if plan.get("status") != "plan_found":
        raise ValueError("A valid purchasing plan is required.")

    orders = plan.get("orders", [])

    if not orders:
        raise ValueError("The plan contains no orders.")

    batch_id = uuid4().hex[:8].upper()
    drafts = []

    for index, order in enumerate(orders, start=1):
        drafts.append({
            "po_id": f"PO-{batch_id}-{index}",
            "product": plan["product"],
            "supplier": order["supplier"],
            "quantity": order["quantity"],
            "estimated_delivery_days": order["estimated_delivery_days"],
            "total_cost_sgd": order["cost_sgd"],
            "status": "DRAFT",
            "approved_at": None,
            "simulation": True,
            "note": (
                "Includes delivery fee; excludes tax. "
                "Delivery time is estimated. Not sent to supplier."
            ),
        })

    return drafts


def review_draft_pos(drafts):
    # Work on a copy so these reviewed values stay separate.
    reviewed = deepcopy(drafts)

    print("\n--- REVIEW PURCHASE ORDERS ---")

    total = Decimal("0.00")

    for po in reviewed:
        total += Decimal(po["total_cost_sgd"])

        print(f"\nPO: {po['po_id']}")
        print(f"Product: {po['product']}")
        print(f"Supplier: {po['supplier']}")
        print(f"Quantity: {po['quantity']} units")
        print(f"Estimated delivery: {po['estimated_delivery_days']} days")
        print(f"Total including delivery: SGD {po['total_cost_sgd']}")

    print(f"\nCombined total: SGD {total:.2f}")
    print("Tax excluded. Simulation only; no orders will be sent.")

    # Approval comes directly from terminal input, not the AI.
    decision = input(
        "\nType APPROVE to approve this exact batch, "
        "REJECT to reject it, or press Enter to keep drafts: "
    ).strip()

    if decision == "APPROVE":
        approved_at = datetime.now(timezone.utc).isoformat()

        for po in reviewed:
            po["status"] = "APPROVED_SIMULATION"
            po["approved_at"] = approved_at

        print("Batch approved in simulation. Nothing was sent.")

    elif decision == "REJECT":
        for po in reviewed:
            po["status"] = "REJECTED"

        print("Batch rejected.")

    else:
        print("Orders remain drafts.")

    return reviewed