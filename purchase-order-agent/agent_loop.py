import json
import math
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from purchase_logic import calculate_purchase_quantity
from supplier_logic import compare_suppliers
from split_order_logic import optimise_order_split
from po_logic import create_draft_pos, review_draft_pos
from po_storage import (
    save_new_batch,
    load_batch,
    update_review,
    list_batches,
)

load_dotenv(Path(__file__).with_name(".env"))

URL = os.getenv("LLM_GATEWAY_URL", "").strip()
KEY = os.getenv("LLM_GATEWAY_API_KEY", "").strip()
MODEL = os.getenv("LLM_MODEL", "").strip()

if not all([URL, KEY, MODEL]):
    raise SystemExit("Missing configuration. Check your .env file.")

SYSTEM_PROMPT = """
You are a purchasing assistant.

You have the following tools:
calculate_purchase_quantity(
    expected_demand,
    safety_stock,
    current_stock,
    incoming_stock
)

All arguments must be non-negative numbers.
Incoming stock means confirmed stock arriving before it is needed.
Safety stock is a quantity in units, not a percentage.

For purchasing calculations, use the tool instead of calculating yourself.
If required information is missing, ask the user. Do not invent values.
Never claim that a purchase order has been placed.

Respond with exactly one JSON object, without markdown.

To request the tool:
{
  "type": "tool",
  "name": "calculate_purchase_quantity",
  "arguments": {
    "expected_demand": 350,
    "safety_stock": 20,
    "current_stock": 100,
    "incoming_stock": 50
  }
}

To give an answer or ask a question:
{
  "type": "answer",
  "message": "Your short response here"
}

After receiving a tool result, continue using tools if needed to complete
the user's request. Give the final answer when the requested work is complete.

A second tool is available:

compare_suppliers(quantity, required_within_days)

Both arguments must be non-negative whole numbers.
This tool currently supports Bottled Coffee only, using simulated suppliers.
Ask for the deadline if it is missing. Do not invent supplier information.

To request this tool:
{
  "type": "tool",
  "name": "compare_suppliers",
  "arguments": {
    "quantity": 200,
    "required_within_days": 5
  }
}

If asked to calculate restocking needs and select a supplier:
1. Call calculate_purchase_quantity first.
2. Use its returned quantity in compare_suppliers.
3. Explain the recommendation using the actual tool results.

If the calculated purchase quantity is zero, no supplier selection is needed.
If no supplier qualifies, explain why and ask what the user wants to change.
Do not silently relax quality, reliability, quantity or deadline requirements.
Delivery times are estimates, not guarantees.
Never claim that an order has been placed.
Always describe supplier delivery times as estimates, never guarantees.

A third tool is available:

optimise_order_split(
    total_quantity,
    urgent_quantity,
    urgent_days,
    final_days
)

Use it when the user wants to compare split orders or has different
deadlines for portions of the purchase.

All arguments are non-negative whole numbers.
total_quantity is the total amount to PURCHASE, not total expected sales.
urgent_quantity is included in total_quantity, not additional to it.
Deadlines are days from today.
Ask for missing quantities or deadlines instead of inventing them.

Example tool request:
{
  "type": "tool",
  "name": "optimise_order_split",
  "arguments": {
    "total_quantity": 200,
    "urgent_quantity": 50,
    "urgent_days": 2,
    "final_days": 8
  }
}

The tool supports Bottled Coffee only.
It compares single-supplier and split orders.
Use its returned costs and savings; do not invent savings.
If no feasible plan exists, explain this and ask which constraints can change.
Never silently relax requirements or claim that an order has been placed.

Only application PO review records confirm that drafts were saved,
approved or rejected. Never invent PO IDs or approval status.
You cannot approve orders.
For saved order history, direct the user to /orders.
To reopen a draft batch, direct the user to /review.
Any purchase-order text you write yourself is only a summary.

/po creates and reviews a NEW draft batch from the latest purchasing plan.
/orders lists saved batches.
/review reopens an EXISTING saved draft batch using its batch ID.
Never tell the user to use /review to create a new draft.
"""


def ask_model(messages):
    response = requests.post(
        f"{URL.rstrip('/')}/api/chat",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": KEY,
        },
        json={
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": 400},
        },
        timeout=60,
    )

    if not response.ok:
        # Show the gateway's error without exposing the API key.
        error_text = response.text.replace(KEY, "[REDACTED]")
        print("Gateway error:", error_text[:2000])
        print("Request body size:", len(response.request.body), "bytes")
        raise RuntimeError(f"Gateway returned HTTP {response.status_code}")

    content = response.json().get("message", {}).get("content")

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Gateway returned no message content.")

    return content


def run_tool(action):
    if action.get("name") == "optimise_order_split":
        arguments = action.get("arguments")
        required = {
            "total_quantity",
            "urgent_quantity",
            "urgent_days",
            "final_days",
        }

        if not isinstance(arguments, dict) or set(arguments) != required:
            raise ValueError("Missing or unexpected split-order arguments.")

        return optimise_order_split(**arguments)
    if action.get("name") == "compare_suppliers":
        arguments = action.get("arguments")

        if (
            not isinstance(arguments, dict)
            or set(arguments) != {"quantity", "required_within_days"}
        ):
            raise ValueError("Missing or unexpected supplier-tool arguments.")

        return compare_suppliers(**arguments)
    # Only this explicitly allowed function can be executed.
    if action.get("name") != "calculate_purchase_quantity":
        raise ValueError("Unknown tool requested.")

    arguments = action.get("arguments")
    required = {
        "expected_demand",
        "safety_stock",
        "current_stock",
        "incoming_stock",
    }

    if not isinstance(arguments, dict) or set(arguments) != required:
        raise ValueError("Tool arguments are missing or unexpected.")

    for name, value in arguments.items():
        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or value < 0
            or value > 1_000_000
        ):
            raise ValueError(f"Invalid quantity for {name}.")

    quantity = calculate_purchase_quantity(**arguments)

    return {"recommended_purchase_units": quantity}


def main():
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    print("Purchasing agent ready. Type 'exit' to stop.")
    print("Type 'reset' to start a new conversation.")

    latest_plan = None
    reviewed_pos = []

    while True:
        request = input("\nYou: ").strip()

        if request.lower() == "exit":
            print("Conversation ended.")
            return
        
        if request.lower() == "reset":
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
            ]
            latest_plan = None
            reviewed_pos = []
            print("Conversation and purchasing plan cleared.")
            continue

        if not request:
            continue

        if request.lower() == "/orders":
            batches = list_batches()

            if not batches:
                print("No saved PO batches yet.")

            for batch_id, created_at, status in batches:
                print(f"{batch_id} | {status} | {created_at}")

            continue

        if request.lower() == "/review":
            batch_id = input("Batch ID from /orders: ").strip().upper()
            drafts = load_batch(batch_id)

            if drafts is None:
                print("Batch not found.")
                continue

            if any(po["status"] != "DRAFT" for po in drafts):
                print("This batch is already approved or rejected.")
                continue

            reviewed_pos = review_draft_pos(drafts)
            update_review(batch_id, reviewed_pos)

            messages.append({
                "role": "user",
                "content": (
                    "Application PO review record: "
                    + json.dumps({
                        "batch_id": batch_id,
                        "orders": reviewed_pos,
                    })
                    + "\nThis is saved simulation data. Nothing was sent."
                ),
            })

            print(f"Saved review for {batch_id}.")
            continue

        if request.lower() == "/po":
            if latest_plan is None:
                print("First ask the agent to produce a split-order plan.")
                continue

            drafts = create_draft_pos(latest_plan)

            # Save before review so pressing Enter keeps a retrievable draft.
            batch_id = save_new_batch(drafts)
            latest_plan = None

            print(f"Saved batch: {batch_id}")
            reviewed_pos = review_draft_pos(drafts)
            update_review(batch_id, reviewed_pos)

            messages.append({
                "role": "user",
                "content": (
                    "Application PO review record: "
                    + json.dumps({
                        "batch_id": batch_id,
                        "orders": reviewed_pos,
                    })
                    + "\nThis is saved simulation data. Nothing was sent."
                ),
            })

            continue
            if latest_plan is None:
                print("First ask the agent to produce a split-order plan.")
                continue

            drafts = create_draft_pos(latest_plan)
            reviewed_pos = review_draft_pos(drafts)

            # Consume the plan to prevent accidental duplicate PO batches.
            latest_plan = None
            continue

        # A new request may change quantities or deadlines.
        # Require a fresh plan before creating another PO batch.
        latest_plan = None

        messages.append({"role": "user", "content": request})

        # Maximum four AI calls for each user message.
        for step in range(4):
            print(f"\nStep {step + 1}: asking AI...")
            content = ask_model(messages).strip()
            print("Raw AI response:", repr(content))

            if content.startswith("```") and content.endswith("```"):
                content = "\n".join(
                    content.splitlines()[1:-1]
                ).strip()

            try:
                action = json.loads(content)
            except json.JSONDecodeError:
                # Display ordinary text, but never execute it as a tool.
                print("\nAI:", content)
                messages.append({
                    "role": "assistant",
                    "content": content,
                })

                if latest_plan is not None:
                    print("\nApp: Type /po to create and review draft POs.")

                break

            if not isinstance(action, dict):
                raise ValueError("Expected a JSON object from the AI.")

            messages.append({
                "role": "assistant",
                "content": content,
            })

            if action.get("type") == "answer":
                answer = action.get("message")

                if not isinstance(answer, str) or not answer.strip():
                    raise ValueError("AI returned an empty answer.")

                print("\nAI:", answer)
                break

            if action.get("type") != "tool":
                raise ValueError("AI returned an unsupported action.")

            print("Tool requested:", action.get("name"))
            print("Inputs:", action.get("arguments"))

            try:
                result = run_tool(action)
            except ValueError as error:
                result = {"error": str(error)}

            print("Tool result:", result)

            if (
                action.get("name") == "optimise_order_split"
                and result.get("status") == "plan_found"
            ):
                latest_plan = result

            messages.append({
                "role": "user",
                "content": (
                    "Application tool result: "
                    + json.dumps(result)
                    + "\nUse this result to respond to the user's request."
                ),
            })

        else:
            print("Step limit reached. Please clarify your request.")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.Timeout:
        print("The gateway timed out. Try again later.")
    except requests.exceptions.RequestException:
        print("Could not connect to the gateway.")
    except (ValueError, RuntimeError) as error:
        print("Stopped:", error)