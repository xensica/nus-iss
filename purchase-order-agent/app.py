from decimal import Decimal

import streamlit as st

from copy import deepcopy
from datetime import datetime, timezone

from po_storage import list_batches, load_batch, update_review

st.set_page_config(
    page_title="Purchasing Agent",
    page_icon="📦",
    layout="wide",
)

st.title("📦 Purchasing Agent")
st.caption("Prototype • Simulated suppliers • No orders sent")

st.button("Refresh saved orders")

batches = list_batches()

total_column, draft_column, approved_column = st.columns(3)

total_column.metric("Saved batches", len(batches))
draft_column.metric(
    "Draft batches",
    sum(status == "DRAFT" for _, _, status in batches),
)
approved_column.metric(
    "Approved batches",
    sum(status == "APPROVED_SIMULATION" for _, _, status in batches),
)

st.subheader("Purchase order history")

if not batches:
    st.info("No saved batches yet. Create one using your terminal agent.")
else:
    st.dataframe(
        [
            {
                "Batch ID": batch_id,
                "Created at (UTC)": created_at,
                "Status": status,
            }
            for batch_id, created_at, status in batches
        ],
        hide_index=True,
    )

    selected_batch = st.selectbox(
        "Select a batch to view",
        options=[batch_id for batch_id, _, _ in batches],
    )

    orders = load_batch(selected_batch)

    if orders:
        st.write(f"**Status:** {orders[0]['status']}")

        st.dataframe(
            [
                {
                    "PO ID": po["po_id"],
                    "Product": po["product"],
                    "Supplier": po["supplier"],
                    "Quantity": po["quantity"],
                    "Estimated delivery (days)": po["estimated_delivery_days"],
                    "Cost (SGD)": po["total_cost_sgd"],
                }
                for po in orders
            ],
            hide_index=True,
        )

        total = sum(
            (Decimal(po["total_cost_sgd"]) for po in orders),
            Decimal("0.00"),
        )

        st.metric("Batch total", f"SGD {total:,.2f}")
        st.caption(
            "Includes delivery fees; excludes tax. "
            "Delivery times are estimates, not guarantees."
        )
    else:
        st.warning("This batch could not be found. Refresh the page.")
# Review the batch currently displayed above.
if batches and orders:
    st.divider()
    st.subheader("Review this batch")

    if all(po["status"] == "DRAFT" for po in orders):
        with st.form(
            key=f"review_{selected_batch}",
            enter_to_submit=False,
        ):
            confirmed = st.checkbox(
                "I have reviewed the quantities, suppliers and total cost."
            )

            approve_column, reject_column = st.columns(2)

            with approve_column:
                approve = st.form_submit_button("Approve batch")

            with reject_column:
                reject = st.form_submit_button("Reject batch")

        if approve or reject:
            if approve and not confirmed:
                st.warning("Tick the review checkbox before approving.")
            else:
                reviewed = deepcopy(orders)
                status = (
                    "APPROVED_SIMULATION" if approve else "REJECTED"
                )
                approved_at = (
                    datetime.now(timezone.utc).isoformat()
                    if approve else None
                )

                for po in reviewed:
                    po["status"] = status
                    po["approved_at"] = approved_at

                try:
                    update_review(selected_batch, reviewed)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.rerun()

    else:
        st.info(
            "This batch is already approved or rejected. "
            "Its status cannot be changed here."
        )

    st.caption("Simulation only. No orders are sent to suppliers.")